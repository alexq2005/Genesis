from __future__ import annotations
"""
GENESIS Config Manager — Export/Import de configuraciones completas.

Problema:
Genesis tiene 40+ subsistemas, cada uno con su propio estado y config.
Si algo se rompe, no hay forma de restaurar una configuracion buena.
Tampoco hay forma de replicar una configuracion en otra instancia.

Solucion:
Un ConfigManager que:
1. Captura snapshots de toda la configuracion activa
2. Exporta perfiles como archivos JSON portables
3. Importa y aplica perfiles, restaurando estado
4. Compara dos perfiles para ver diferencias

Uso:
    manager = ConfigManager(base_dir=str(BASE_DIR))
    manager.save_profile("mi_config")
    manager.list_profiles()
    manager.load_profile("mi_config")
"""
import json
import time
import shutil
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime


class ConfigProfile:
    """Un perfil de configuracion de Genesis."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.genesis_version = ""
        self.sections: dict[str, dict] = {}

    def add_section(self, name: str, data: dict):
        """Agrega una seccion de configuracion."""
        self.sections[name] = data

    def get_section(self, name: str) -> dict:
        """Obtiene una seccion."""
        return self.sections.get(name, {})

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "genesis_version": self.genesis_version,
            "sections": self.sections,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConfigProfile":
        p = cls(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
        )
        p.created_at = data.get("created_at", "")
        p.genesis_version = data.get("genesis_version", "")
        p.sections = data.get("sections", {})
        return p

    def summary(self) -> str:
        """Resumen del perfil."""
        sections = ", ".join(self.sections.keys()) if self.sections else "vacio"
        return (
            f"  {self.name} (v{self.genesis_version})\n"
            f"    {self.description}\n"
            f"    Creado: {self.created_at}\n"
            f"    Secciones: {sections}"
        )


class ConfigDiff:
    """Diferencia entre dos perfiles."""

    def __init__(self, profile_a: str, profile_b: str):
        self.profile_a = profile_a
        self.profile_b = profile_b
        self.added_sections: list[str] = []
        self.removed_sections: list[str] = []
        self.modified_sections: dict[str, list[str]] = {}

    def format(self) -> str:
        """Formato legible del diff."""
        lines = [f"=== DIFF: {self.profile_a} vs {self.profile_b} ==="]

        if self.added_sections:
            lines.append(f"\n  SECCIONES NUEVAS en {self.profile_b}:")
            for s in self.added_sections:
                lines.append(f"    + {s}")

        if self.removed_sections:
            lines.append(f"\n  SECCIONES ELIMINADAS en {self.profile_b}:")
            for s in self.removed_sections:
                lines.append(f"    - {s}")

        if self.modified_sections:
            lines.append(f"\n  SECCIONES MODIFICADAS:")
            for section, changes in self.modified_sections.items():
                lines.append(f"    ~ {section}:")
                for change in changes[:10]:  # Max 10 cambios por seccion
                    lines.append(f"      {change}")

        if not self.added_sections and not self.removed_sections and not self.modified_sections:
            lines.append("  Perfiles identicos.")

        return "\n".join(lines)


class ConfigManager:
    """
    Manager de configuraciones de Genesis.

    Captura, exporta, importa y compara perfiles de configuracion.
    """

    def __init__(self, base_dir: str = ""):
        if not base_dir:
            base_dir = str(Path(__file__).parent.parent)
        self.base_dir = Path(base_dir)

        # Directorio de perfiles
        self.profiles_dir = self.base_dir / "config_profiles"
        self.profiles_dir.mkdir(exist_ok=True)

        # Collectors: funciones que capturan config de cada subsistema
        self._collectors: dict[str, Callable] = {}

        # Appliers: funciones que aplican config a cada subsistema
        self._appliers: dict[str, Callable] = {}

        # Perfil activo
        self.active_profile: str = ""

    def register_collector(self, section: str, collector: Callable):
        """
        Registra un collector que captura la config de un subsistema.

        El collector debe retornar un dict serializable a JSON.
        """
        self._collectors[section] = collector

    def register_applier(self, section: str, applier: Callable):
        """
        Registra un applier que restaura la config de un subsistema.

        El applier recibe un dict y aplica los cambios.
        """
        self._appliers[section] = applier

    def capture_current(self, description: str = "") -> ConfigProfile:
        """
        Captura la configuracion actual de todos los subsistemas registrados.

        Returns:
            ConfigProfile con la configuracion actual
        """
        from config import GENESIS_VERSION

        profile = ConfigProfile(
            name=f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description=description or "Snapshot automatico",
        )
        profile.genesis_version = GENESIS_VERSION

        for section_name, collector in self._collectors.items():
            try:
                data = collector()
                if isinstance(data, dict):
                    profile.add_section(section_name, data)
            except Exception as e:
                profile.add_section(section_name, {"_error": str(e)})

        return profile

    def save_profile(self, name: str, description: str = "") -> str:
        """
        Captura y guarda un perfil con nombre.

        Args:
            name: Nombre del perfil
            description: Descripcion opcional

        Returns:
            Mensaje de confirmacion
        """
        profile = self.capture_current(description)
        profile.name = name

        filepath = self.profiles_dir / f"{name}.json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            self.active_profile = name
            return (
                f"Perfil '{name}' guardado con {len(profile.sections)} secciones.\n"
                f"  Archivo: {filepath}"
            )
        except Exception as e:
            return f"Error guardando perfil: {e}"

    def load_profile(self, name: str) -> Optional[ConfigProfile]:
        """Carga un perfil desde archivo."""
        filepath = self.profiles_dir / f"{name}.json"

        if not filepath.exists():
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ConfigProfile.from_dict(data)
        except Exception:
            return None

    def apply_profile(self, name: str) -> str:
        """
        Carga y aplica un perfil, restaurando la configuracion.

        Solo aplica secciones que tengan applier registrado.
        """
        profile = self.load_profile(name)
        if not profile:
            return f"Perfil '{name}' no encontrado."

        applied = []
        skipped = []
        errors = []

        for section_name, section_data in profile.sections.items():
            if "_error" in section_data:
                skipped.append(f"{section_name} (error en captura)")
                continue

            if section_name in self._appliers:
                try:
                    self._appliers[section_name](section_data)
                    applied.append(section_name)
                except Exception as e:
                    errors.append(f"{section_name}: {e}")
            else:
                skipped.append(section_name)

        self.active_profile = name

        lines = [f"Perfil '{name}' aplicado:"]
        if applied:
            lines.append(f"  Aplicados ({len(applied)}): {', '.join(applied)}")
        if skipped:
            lines.append(f"  Omitidos ({len(skipped)}): {', '.join(skipped)}")
        if errors:
            lines.append(f"  Errores ({len(errors)}):")
            for e in errors:
                lines.append(f"    - {e}")
        return "\n".join(lines)

    def delete_profile(self, name: str) -> str:
        """Elimina un perfil guardado."""
        filepath = self.profiles_dir / f"{name}.json"
        if not filepath.exists():
            return f"Perfil '{name}' no encontrado."

        try:
            filepath.unlink()
            if self.active_profile == name:
                self.active_profile = ""
            return f"Perfil '{name}' eliminado."
        except Exception as e:
            return f"Error eliminando perfil: {e}"

    def list_profiles(self) -> str:
        """Lista todos los perfiles guardados."""
        profiles = sorted(self.profiles_dir.glob("*.json"))

        if not profiles:
            return "  No hay perfiles guardados.\n  Usa /config save <nombre> para crear uno."

        lines = ["=== PERFILES DE CONFIGURACION ==="]
        for filepath in profiles:
            name = filepath.stem
            active = " [ACTIVO]" if name == self.active_profile else ""
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profile = ConfigProfile.from_dict(data)
                sections_count = len(profile.sections)
                lines.append(
                    f"  {name}{active} — v{profile.genesis_version}, "
                    f"{sections_count} secciones ({profile.created_at[:10]})"
                )
                if profile.description:
                    lines.append(f"    {profile.description}")
            except Exception:
                lines.append(f"  {name}{active} — (error leyendo)")

        return "\n".join(lines)

    def compare_profiles(self, name_a: str, name_b: str) -> str:
        """
        Compara dos perfiles y muestra diferencias.
        """
        profile_a = self.load_profile(name_a)
        profile_b = self.load_profile(name_b)

        if not profile_a:
            return f"Perfil '{name_a}' no encontrado."
        if not profile_b:
            return f"Perfil '{name_b}' no encontrado."

        diff = ConfigDiff(name_a, name_b)

        sections_a = set(profile_a.sections.keys())
        sections_b = set(profile_b.sections.keys())

        diff.added_sections = sorted(sections_b - sections_a)
        diff.removed_sections = sorted(sections_a - sections_b)

        # Comparar secciones comunes
        common = sections_a & sections_b
        for section in sorted(common):
            data_a = profile_a.sections[section]
            data_b = profile_b.sections[section]
            changes = self._diff_dicts(data_a, data_b)
            if changes:
                diff.modified_sections[section] = changes

        return diff.format()

    def _diff_dicts(self, a: dict, b: dict, prefix: str = "") -> list[str]:
        """Compara dos dicts recursivamente."""
        changes = []
        all_keys = set(list(a.keys()) + list(b.keys()))

        for key in sorted(all_keys):
            path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            val_a = a.get(key)
            val_b = b.get(key)

            if key not in a:
                changes.append(f"+ {path} = {self._truncate(val_b)}")
            elif key not in b:
                changes.append(f"- {path} = {self._truncate(val_a)}")
            elif val_a != val_b:
                if isinstance(val_a, dict) and isinstance(val_b, dict):
                    changes.extend(self._diff_dicts(val_a, val_b, f"{path}."))
                else:
                    changes.append(
                        f"~ {path}: {self._truncate(val_a)} -> {self._truncate(val_b)}"
                    )

        return changes

    def _truncate(self, value, max_len: int = 50) -> str:
        """Trunca un valor para display."""
        s = str(value)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s

    def export_profile(self, name: str, dest_path: str) -> str:
        """Exporta un perfil a una ruta externa."""
        filepath = self.profiles_dir / f"{name}.json"
        if not filepath.exists():
            return f"Perfil '{name}' no encontrado."

        try:
            dest = Path(dest_path)
            if dest.is_dir():
                dest = dest / f"{name}.genesis_profile.json"
            shutil.copy2(str(filepath), str(dest))
            return f"Perfil '{name}' exportado a: {dest}"
        except Exception as e:
            return f"Error exportando: {e}"

    def import_profile(self, source_path: str) -> str:
        """Importa un perfil desde una ruta externa."""
        source = Path(source_path)
        if not source.exists():
            return f"Archivo no encontrado: {source}"

        try:
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)

            profile = ConfigProfile.from_dict(data)
            name = profile.name

            # Evitar sobreescribir
            dest = self.profiles_dir / f"{name}.json"
            if dest.exists():
                name = f"{name}_{datetime.now().strftime('%H%M%S')}"
                dest = self.profiles_dir / f"{name}.json"
                profile.name = name

            with open(dest, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

            return f"Perfil '{name}' importado desde: {source}"
        except json.JSONDecodeError:
            return f"Error: archivo no es JSON valido."
        except Exception as e:
            return f"Error importando: {e}"

    def get_stats(self) -> dict:
        """Estadisticas del config manager."""
        n_profiles = len(list(self.profiles_dir.glob("*.json")))
        return {
            "profiles": n_profiles,
            "collectors": len(self._collectors),
            "appliers": len(self._appliers),
            "active": self.active_profile or "ninguno",
        }

    def status(self) -> str:
        """Resumen para /status."""
        stats = self.get_stats()
        return (
            f"  Perfiles: {stats['profiles']} | Collectors: {stats['collectors']} | "
            f"Activo: {stats['active']}"
        )
