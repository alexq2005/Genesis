"""
GENESIS Plugin Marketplace — Descubrimiento e instalacion de plugins.

Problema:
El PluginSystem actual solo carga plugins desde plugins/.
No hay forma de descubrir nuevos plugins, instalarlos desde un
registro, ni compartirlos entre usuarios.

Solucion:
Un marketplace local que:
1. Mantiene un registro de plugins disponibles (plugin_registry/)
2. Permite buscar, instalar, desinstalar y actualizar plugins
3. Genera templates para crear nuevos plugins facilmente
4. Sistema de ratings y metadata enriquecida

Estructura:
    GENESIS/
    ├── plugins/                 # Plugins activos (cargados por PluginSystem)
    └── plugin_registry/         # Registro de plugins disponibles
        ├── manifest.json        # Indice del marketplace
        └── available/           # Plugins descargables
            ├── ejemplo/
            │   ├── manifest.json
            │   └── plugin.py
            └── otro_plugin/
                ├── manifest.json
                └── plugin.py
"""
import os
import json
import shutil
import time
from pathlib import Path
from typing import Optional
from datetime import datetime


class PluginManifest:
    """Metadata de un plugin en el marketplace."""

    def __init__(self, name: str, version: str = "1.0.0",
                 author: str = "unknown", description: str = "",
                 tags: list = None, dependencies: list = None,
                 min_genesis_version: str = "1.0.0",
                 homepage: str = "", license: str = "MIT"):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.tags = tags or []
        self.dependencies = dependencies or []
        self.min_genesis_version = min_genesis_version
        self.homepage = homepage
        self.license = license

        # Marketplace metadata
        self.installed = False
        self.install_date: Optional[str] = None
        self.rating: float = 0.0
        self.rating_count: int = 0
        self.downloads: int = 0
        self.created_date: str = datetime.now().strftime("%Y-%m-%d")
        self.updated_date: str = self.created_date

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "min_genesis_version": self.min_genesis_version,
            "homepage": self.homepage,
            "license": self.license,
            "installed": self.installed,
            "install_date": self.install_date,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "downloads": self.downloads,
            "created_date": self.created_date,
            "updated_date": self.updated_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        m = cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "unknown"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            min_genesis_version=data.get("min_genesis_version", "1.0.0"),
            homepage=data.get("homepage", ""),
            license=data.get("license", "MIT"),
        )
        m.installed = data.get("installed", False)
        m.install_date = data.get("install_date")
        m.rating = data.get("rating", 0.0)
        m.rating_count = data.get("rating_count", 0)
        m.downloads = data.get("downloads", 0)
        m.created_date = data.get("created_date", "")
        m.updated_date = data.get("updated_date", "")
        return m

    def match_search(self, query: str) -> bool:
        """Verifica si el plugin matchea una busqueda."""
        q = query.lower()
        if q in self.name.lower():
            return True
        if q in self.description.lower():
            return True
        for tag in self.tags:
            if q in tag.lower():
                return True
        if q in self.author.lower():
            return True
        return False

    def format_card(self) -> str:
        """Formato tipo card para mostrar en marketplace."""
        stars = "*" * int(self.rating) + "-" * (5 - int(self.rating))
        installed_str = " [INSTALADO]" if self.installed else ""
        tags_str = ", ".join(self.tags) if self.tags else "sin tags"
        return (
            f"  {self.name} v{self.version}{installed_str}\n"
            f"    {self.description}\n"
            f"    Autor: {self.author} | Rating: [{stars}] ({self.rating_count}) | "
            f"Downloads: {self.downloads}\n"
            f"    Tags: {tags_str}"
        )


class PluginMarketplace:
    """
    Marketplace de plugins para Genesis.

    Gestiona el registro local de plugins disponibles,
    su instalacion, actualizacion y descubrimiento.
    """

    def __init__(self, base_dir: str = ""):
        if not base_dir:
            base_dir = str(Path(__file__).parent.parent)
        self.base_dir = Path(base_dir)

        # Directorios
        self.plugins_dir = self.base_dir / "plugins"
        self.registry_dir = self.base_dir / "plugin_registry"
        self.available_dir = self.registry_dir / "available"
        self.manifest_file = self.registry_dir / "manifest.json"

        # Crear directorios
        self.plugins_dir.mkdir(exist_ok=True)
        self.registry_dir.mkdir(exist_ok=True)
        self.available_dir.mkdir(exist_ok=True)

        # Indice del marketplace
        self.manifests: dict[str, PluginManifest] = {}

        # Cargar indice
        self._load_manifest()
        self._scan_registry()

    def _load_manifest(self):
        """Carga el indice del marketplace desde JSON."""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, mdata in data.get("plugins", {}).items():
                    self.manifests[name] = PluginManifest.from_dict(mdata)
            except Exception:
                pass

    def _save_manifest(self):
        """Guarda el indice del marketplace a JSON."""
        data = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "plugins": {
                name: m.to_dict() for name, m in self.manifests.items()
            },
        }
        try:
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _scan_registry(self):
        """Escanea el directorio de plugins disponibles."""
        if not self.available_dir.exists():
            return

        for plugin_dir in self.available_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_file = plugin_dir / "manifest.json"
            plugin_file = plugin_dir / "plugin.py"

            if not plugin_file.exists():
                continue

            name = plugin_dir.name

            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        mdata = json.load(f)
                    manifest = PluginManifest.from_dict(mdata)
                    manifest.name = name
                except Exception:
                    manifest = PluginManifest(name=name)
            else:
                manifest = PluginManifest(name=name)

            # Verificar si esta instalado
            installed_path = self.plugins_dir / f"{name}.py"
            manifest.installed = installed_path.exists()

            # Actualizar en indice (merge con datos existentes como ratings)
            if name in self.manifests:
                existing = self.manifests[name]
                manifest.rating = existing.rating
                manifest.rating_count = existing.rating_count
                manifest.downloads = existing.downloads
                manifest.install_date = existing.install_date

            self.manifests[name] = manifest

        self._save_manifest()

    def search(self, query: str) -> list[PluginManifest]:
        """Busca plugins por nombre, descripcion o tags."""
        results = []
        for manifest in self.manifests.values():
            if manifest.match_search(query):
                results.append(manifest)
        # Ordenar por rating desc, luego por nombre
        results.sort(key=lambda m: (-m.rating, m.name))
        return results

    def list_available(self) -> list[PluginManifest]:
        """Lista todos los plugins disponibles."""
        return sorted(self.manifests.values(), key=lambda m: m.name)

    def list_installed(self) -> list[PluginManifest]:
        """Lista plugins instalados."""
        return [m for m in self.manifests.values() if m.installed]

    def get_manifest(self, name: str) -> Optional[PluginManifest]:
        """Obtiene el manifest de un plugin."""
        return self.manifests.get(name)

    def install_plugin(self, name: str) -> str:
        """
        Instala un plugin del registry a plugins/.

        Copia plugin.py del registry al directorio de plugins activos.
        """
        if name not in self.manifests:
            return f"Plugin '{name}' no encontrado en el registry."

        source_dir = self.available_dir / name
        source_file = source_dir / "plugin.py"

        if not source_file.exists():
            return f"Archivo de plugin no encontrado: {source_file}"

        dest_file = self.plugins_dir / f"{name}.py"

        # Verificar dependencias
        manifest = self.manifests[name]
        missing_deps = []
        for dep in manifest.dependencies:
            dep_installed = (self.plugins_dir / f"{dep}.py").exists()
            if not dep_installed:
                missing_deps.append(dep)

        if missing_deps:
            return (
                f"Dependencias faltantes para '{name}': "
                f"{', '.join(missing_deps)}. Instala primero."
            )

        try:
            shutil.copy2(str(source_file), str(dest_file))
            manifest.installed = True
            manifest.install_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            manifest.downloads += 1
            self._save_manifest()
            return f"Plugin '{name}' v{manifest.version} instalado exitosamente."
        except Exception as e:
            return f"Error instalando '{name}': {e}"

    def uninstall_plugin(self, name: str) -> str:
        """Desinstala un plugin (elimina de plugins/)."""
        dest_file = self.plugins_dir / f"{name}.py"

        if not dest_file.exists():
            return f"Plugin '{name}' no esta instalado."

        try:
            dest_file.unlink()
            if name in self.manifests:
                self.manifests[name].installed = False
                self.manifests[name].install_date = None
            self._save_manifest()
            return f"Plugin '{name}' desinstalado."
        except Exception as e:
            return f"Error desinstalando '{name}': {e}"

    def update_plugin(self, name: str) -> str:
        """Actualiza un plugin reinstalando desde el registry."""
        if name not in self.manifests or not self.manifests[name].installed:
            return f"Plugin '{name}' no esta instalado."

        # Desinstalar y reinstalar
        self.uninstall_plugin(name)
        return self.install_plugin(name)

    def rate_plugin(self, name: str, stars: int) -> str:
        """Califica un plugin (1-5 estrellas)."""
        if name not in self.manifests:
            return f"Plugin '{name}' no encontrado."

        stars = max(1, min(5, stars))
        manifest = self.manifests[name]

        # Promedio incremental
        total = manifest.rating * manifest.rating_count + stars
        manifest.rating_count += 1
        manifest.rating = round(total / manifest.rating_count, 1)

        self._save_manifest()
        return f"Plugin '{name}' calificado con {stars} estrellas (promedio: {manifest.rating})"

    def create_template(self, name: str, description: str = "") -> str:
        """
        Genera un template de plugin en el registry.

        Crea la estructura basica para un nuevo plugin.
        """
        plugin_dir = self.available_dir / name

        if plugin_dir.exists():
            return f"Ya existe un plugin '{name}' en el registry."

        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Crear manifest.json
        manifest_data = {
            "name": name,
            "version": "1.0.0",
            "author": "tu_nombre",
            "description": description or f"Plugin {name} para Genesis",
            "tags": [],
            "dependencies": [],
            "min_genesis_version": "1.8.0",
            "license": "MIT",
        }

        manifest_path = plugin_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # Crear plugin.py template
        plugin_code = f'''"""
Plugin: {name}
Descripcion: {description or f"Plugin {name} para Genesis"}
"""

PLUGIN_NAME = "{name}"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "{description or f"Plugin {name} para Genesis"}"


def on_load(genesis):
    """Se llama cuando el plugin se carga."""
    pass


def on_unload(genesis):
    """Se llama cuando el plugin se descarga."""
    pass


def register_commands():
    """Retorna comandos que el plugin agrega."""
    return {{
        "/{name}": {{
            "handler": cmd_{name},
            "help": "{description or f"Comando principal de {name}"}"
        }}
    }}


def cmd_{name}(genesis, args):
    """Handler del comando principal."""
    return f"Plugin {name} ejecutado con args: {{args}}"


def on_message(genesis, user_input, response):
    """Hook que se ejecuta en cada interaccion (opcional)."""
    pass
'''

        plugin_path = plugin_dir / "plugin.py"
        with open(plugin_path, "w", encoding="utf-8") as f:
            f.write(plugin_code)

        # Registrar en indice
        manifest = PluginManifest.from_dict(manifest_data)
        self.manifests[name] = manifest
        self._save_manifest()

        return (
            f"Template de plugin '{name}' creado en:\n"
            f"  {plugin_dir}\n"
            f"  - manifest.json (metadata)\n"
            f"  - plugin.py (codigo)\n"
            f"Edita plugin.py y luego usa /marketplace install {name}"
        )

    def remove_from_registry(self, name: str) -> str:
        """Elimina un plugin del registry (no de plugins/)."""
        plugin_dir = self.available_dir / name
        if not plugin_dir.exists():
            return f"Plugin '{name}' no esta en el registry."

        try:
            shutil.rmtree(str(plugin_dir))
            self.manifests.pop(name, None)
            self._save_manifest()
            return f"Plugin '{name}' eliminado del registry."
        except Exception as e:
            return f"Error eliminando '{name}': {e}"

    def get_stats(self) -> dict:
        """Estadisticas del marketplace."""
        total = len(self.manifests)
        installed = sum(1 for m in self.manifests.values() if m.installed)
        rated = sum(1 for m in self.manifests.values() if m.rating_count > 0)
        total_downloads = sum(m.downloads for m in self.manifests.values())
        return {
            "total": total,
            "installed": installed,
            "rated": rated,
            "total_downloads": total_downloads,
        }

    def format_marketplace(self) -> str:
        """Formato completo del marketplace para mostrar."""
        available = self.list_available()
        if not available:
            return (
                "  Marketplace vacio.\n"
                "  Usa /marketplace create <nombre> para crear un plugin.\n"
                f"  O agrega plugins manualmente en: {self.available_dir}"
            )

        lines = ["=== PLUGIN MARKETPLACE ==="]
        stats = self.get_stats()
        lines.append(
            f"  {stats['total']} disponibles | "
            f"{stats['installed']} instalados | "
            f"{stats['total_downloads']} descargas totales\n"
        )

        for manifest in available:
            lines.append(manifest.format_card())
            lines.append("")

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen breve para /status."""
        stats = self.get_stats()
        return (
            f"  Disponibles: {stats['total']} | Instalados: {stats['installed']} | "
            f"Downloads: {stats['total_downloads']}"
        )
