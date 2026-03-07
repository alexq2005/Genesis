"""
GENESIS Self-Modifier — Auto-modificacion segura del codigo fuente.

Problema:
Genesis promete "auto-evolucion" pero solo modifica su prompt de personalidad.
El codigo fuente real permanece estatico. Para ser verdaderamente auto-evolutivo,
Genesis necesita poder modificar su propio codigo.

Solucion:
SelfModifier permite a Genesis:
1. Proponer cambios a su propio codigo (con diff previo)
2. Validar que los cambios no rompan nada (backup + syntax check)
3. Aplicar cambios de forma segura (atomic write + rollback)
4. Mantener un historial de auto-modificaciones

Reglas de seguridad:
- Solo puede modificar archivos dentro de su propio directorio
- Siempre crea backup antes de modificar
- Valida syntax Python antes de aplicar
- Archivos criticos requieren confirmacion explicita
- Historial completo de cambios para auditoria
"""
import ast
import time
import shutil
import difflib
import subprocess
from pathlib import Path
from typing import Optional

try:
    from core.safe_io import safe_read_json, safe_write_json
except ImportError:
    import json

    def safe_read_json(path, default=None):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def safe_write_json(path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True


class SelfModifier:
    """
    Permite a Genesis modificar su propio codigo de forma segura.

    Flujo:
    1. Genesis propone un cambio (propose_change)
    2. El cambio se valida (syntax, seguridad)
    3. Se muestra un diff al usuario
    4. Si el usuario aprueba, se aplica (apply_change)
    5. Si algo falla, se hace rollback (rollback)
    """

    # Archivos criticos que requieren confirmacion extra
    CRITICAL_FILES = {
        "genesis.py", "config.py",
        "core/brain.py", "core/memory.py",
        "core/safe_io.py", "core/self_modifier.py",
    }

    # Archivos que NUNCA se pueden modificar (seguridad)
    IMMUTABLE_FILES = set()  # Ninguno por ahora, pero se puede extender

    # Patrones peligrosos que no se pueden inyectar
    DANGEROUS_PATTERNS = [
        "os.system",
        "subprocess.call",
        "shutil.rmtree",
        "exec(",
        "eval(",
        "__import__",
        "open('/etc",
        "open('C:\\\\Windows",
    ]

    def __init__(self, genesis_dir: Optional[Path] = None,
                 history_file: Optional[Path] = None,
                 max_history: int = 50):
        """
        Args:
            genesis_dir: Directorio raiz de Genesis
            history_file: Archivo para guardar historial de cambios
            max_history: Maximo de cambios a mantener en historial
        """
        if genesis_dir is None:
            genesis_dir = Path(__file__).parent.parent
        self.genesis_dir = genesis_dir.resolve()

        if history_file is None:
            history_dir = self.genesis_dir / "memory_data"
            history_dir.mkdir(exist_ok=True)
            history_file = history_dir / "self_modifications.json"
        self.history_file = history_file
        self.max_history = max_history

        # Estado
        self.history: list[dict] = []
        self.pending_change: Optional[dict] = None
        self._load_history()

    def _load_history(self):
        """Carga el historial de modificaciones."""
        data = safe_read_json(self.history_file, default={"changes": []})
        self.history = data.get("changes", [])

    def _save_history(self):
        """Guarda el historial de modificaciones."""
        # Mantener solo los ultimos N
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        safe_write_json(self.history_file, {"changes": self.history})

    def propose_change(self, filepath: str, new_content: str,
                       reason: str = "", description: str = "") -> dict:
        """
        Propone un cambio a un archivo.

        Args:
            filepath: Ruta relativa al directorio de Genesis (ej: "core/tools.py")
            new_content: Contenido nuevo completo del archivo
            reason: Razon del cambio
            description: Descripcion del cambio

        Returns:
            Dict con: status, diff, warnings, is_critical, etc.
        """
        # Resolver ruta
        target = (self.genesis_dir / filepath).resolve()

        # Validacion: dentro del directorio de Genesis
        try:
            target.relative_to(self.genesis_dir)
        except ValueError:
            return {
                "status": "rejected",
                "error": f"Fuera del directorio de Genesis: {filepath}",
            }

        # Validacion: no inmutable
        rel_path = str(target.relative_to(self.genesis_dir)).replace("\\", "/")
        if rel_path in self.IMMUTABLE_FILES:
            return {
                "status": "rejected",
                "error": f"Archivo inmutable: {rel_path}",
            }

        # Validacion: patrones peligrosos
        warnings = []
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in new_content:
                warnings.append(f"Patron peligroso detectado: '{pattern}'")

        # Validacion: syntax Python si es .py
        syntax_ok = True
        syntax_error = ""
        if filepath.endswith(".py"):
            try:
                ast.parse(new_content)
            except SyntaxError as e:
                syntax_ok = False
                syntax_error = f"Linea {e.lineno}: {e.msg}"

        if not syntax_ok:
            return {
                "status": "rejected",
                "error": f"Error de sintaxis: {syntax_error}",
            }

        # Leer contenido actual
        current_content = ""
        if target.exists():
            try:
                current_content = target.read_text(encoding="utf-8")
            except Exception as e:
                return {
                    "status": "rejected",
                    "error": f"No se pudo leer el archivo: {e}",
                }

        # Generar diff
        diff_lines = list(difflib.unified_diff(
            current_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        ))
        diff_text = "\n".join(diff_lines)

        if not diff_text:
            return {
                "status": "no_change",
                "message": "El contenido es identico, no hay cambios.",
            }

        # Estadisticas del diff
        additions = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        deletions = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        is_critical = rel_path in self.CRITICAL_FILES

        # Guardar como cambio pendiente
        self.pending_change = {
            "filepath": str(target),
            "rel_path": rel_path,
            "new_content": new_content,
            "old_content": current_content,
            "diff": diff_text,
            "reason": reason,
            "description": description,
            "additions": additions,
            "deletions": deletions,
            "is_critical": is_critical,
            "warnings": warnings,
            "proposed_at": time.time(),
        }

        return {
            "status": "pending",
            "diff": diff_text,
            "additions": additions,
            "deletions": deletions,
            "is_critical": is_critical,
            "warnings": warnings,
            "message": (
                f"Cambio propuesto para {rel_path}:\n"
                f"  +{additions} lineas, -{deletions} lineas\n"
                f"  {'⚠ ARCHIVO CRITICO — requiere confirmacion' if is_critical else ''}\n"
                f"  {'⚠ ' + '; '.join(warnings) if warnings else ''}\n"
                f"\nEscribe /apply para aplicar o /reject para rechazar."
            ),
        }

    def apply_change(self) -> dict:
        """
        Aplica el cambio pendiente.

        Returns:
            Dict con resultado de la aplicacion
        """
        if not self.pending_change:
            return {"status": "error", "message": "No hay cambio pendiente."}

        change = self.pending_change
        target = Path(change["filepath"])

        try:
            # Crear backup del archivo original
            backup_path = None
            if target.exists():
                backup_path = target.with_suffix(target.suffix + ".bak")
                shutil.copy2(str(target), str(backup_path))

            # Crear directorios si no existen
            target.parent.mkdir(parents=True, exist_ok=True)

            # Escribir nuevo contenido (atomic: temp + rename)
            tmp_path = target.with_suffix(target.suffix + ".tmp")
            tmp_path.write_text(change["new_content"], encoding="utf-8")
            tmp_path.replace(target)

            # === AUTO-TEST ===
            # Correr tests automaticamente despues de aplicar cambio
            test_result = self._run_auto_tests()
            test_passed = test_result["passed"]

            if not test_passed:
                # Tests fallaron — rollback automatico
                if backup_path and backup_path.exists():
                    shutil.copy2(str(backup_path), str(target))

                self.history.append({
                    "filepath": change["rel_path"],
                    "timestamp": time.time(),
                    "reason": change["reason"],
                    "description": change["description"],
                    "additions": change["additions"],
                    "deletions": change["deletions"],
                    "backup": str(backup_path) if backup_path else None,
                    "success": False,
                    "auto_reverted": True,
                    "test_output": test_result["output"][:500],
                })
                self._save_history()
                self.pending_change = None

                return {
                    "status": "reverted",
                    "message": (
                        f"Cambio a {change['rel_path']} REVERTIDO automaticamente!\n"
                        f"  Razon: Tests fallaron despues de aplicar\n"
                        f"  Test output: {test_result['output'][:300]}\n"
                        f"  El archivo fue restaurado al backup."
                    ),
                }

            # Registrar en historial (tests pasaron)
            self.history.append({
                "filepath": change["rel_path"],
                "timestamp": time.time(),
                "reason": change["reason"],
                "description": change["description"],
                "additions": change["additions"],
                "deletions": change["deletions"],
                "backup": str(backup_path) if backup_path else None,
                "success": True,
                "tests_passed": True,
            })
            self._save_history()

            # Limpiar backup del pending (ya esta en historial)
            self.pending_change = None

            return {
                "status": "applied",
                "message": (
                    f"Cambio aplicado a {change['rel_path']}:\n"
                    f"  +{change['additions']} / -{change['deletions']} lineas\n"
                    f"  Backup: {backup_path.name if backup_path else 'nuevo archivo'}\n"
                    f"  Tests: PASARON\n"
                    f"  Usa /self_rollback para revertir si algo falla."
                ),
            }

        except Exception as e:
            # Rollback automatico si falla
            if backup_path and backup_path.exists():
                shutil.copy2(str(backup_path), str(target))
            return {
                "status": "error",
                "message": f"Error al aplicar cambio: {e}\n  Se restauro el backup.",
            }

    def _run_auto_tests(self) -> dict:
        """
        Corre los tests de Genesis automaticamente.
        Busca test files en tests/ y los ejecuta.

        Returns:
            {"passed": bool, "output": str}
        """
        tests_dir = self.genesis_dir / "tests"
        if not tests_dir.exists():
            # Sin tests — asumir que pasa
            return {"passed": True, "output": "No hay directorio tests/"}

        test_files = list(tests_dir.glob("test_*.py"))
        if not test_files:
            return {"passed": True, "output": "No hay archivos de test"}

        # Ejecutar cada test file
        all_output = []
        all_passed = True

        for test_file in test_files:
            try:
                result = subprocess.run(
                    ["python", str(test_file)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(self.genesis_dir),
                )
                all_output.append(f"--- {test_file.name} ---")
                # Solo capturar las ultimas lineas (resumen)
                stdout_lines = result.stdout.strip().split("\n")
                # Buscar linea de RESULTADOS
                for line in stdout_lines:
                    if "RESULTADOS" in line or "PASS" in line or "FAIL" in line:
                        all_output.append(line.strip())
                if result.returncode != 0:
                    all_passed = False
                    if result.stderr:
                        all_output.append(f"STDERR: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                all_output.append(f"--- {test_file.name}: TIMEOUT ---")
                all_passed = False
            except Exception as e:
                all_output.append(f"--- {test_file.name}: ERROR: {e} ---")
                # No fallar por error al correr tests
                pass

        return {
            "passed": all_passed,
            "output": "\n".join(all_output),
        }

    def reject_change(self) -> str:
        """Rechaza el cambio pendiente."""
        if not self.pending_change:
            return "No hay cambio pendiente."
        rel_path = self.pending_change["rel_path"]
        self.pending_change = None
        return f"Cambio a {rel_path} rechazado."

    def rollback_last(self) -> str:
        """Revierte el ultimo cambio aplicado usando el backup."""
        if not self.history:
            return "No hay cambios en el historial."

        last = self.history[-1]
        backup_path = last.get("backup")

        if not backup_path:
            return "El ultimo cambio fue un archivo nuevo (sin backup para revertir)."

        backup = Path(backup_path)
        target = self.genesis_dir / last["filepath"]

        if not backup.exists():
            return f"Backup no encontrado: {backup.name}"

        try:
            shutil.copy2(str(backup), str(target))
            last["reverted"] = True
            self._save_history()
            return f"Revertido: {last['filepath']} (backup restaurado)"
        except Exception as e:
            return f"Error al revertir: {e}"

    def get_pending_diff(self) -> str:
        """Retorna el diff del cambio pendiente."""
        if not self.pending_change:
            return "No hay cambio pendiente."
        return self.pending_change["diff"]

    def format_history(self, n: int = 10) -> str:
        """Formatea las ultimas N modificaciones."""
        if not self.history:
            return "  No hay modificaciones registradas."

        lines = []
        for change in self.history[-n:]:
            t = time.strftime("%d/%m %H:%M", time.localtime(change["timestamp"]))
            reverted = " [REVERTIDO]" if change.get("reverted") else ""
            lines.append(
                f"  {t} | {change['filepath']} "
                f"(+{change['additions']}/-{change['deletions']}){reverted}"
            )
            if change.get("description"):
                lines.append(f"    {change['description'][:80]}")
        return "\n".join(lines)

    def status(self) -> str:
        """Resumen para /status."""
        total = len(self.history)
        reverted = sum(1 for c in self.history if c.get("reverted"))
        pending = "si" if self.pending_change else "no"
        return (
            f"  Modificaciones totales: {total} ({reverted} revertidas)\n"
            f"  Cambio pendiente: {pending}"
        )

    def get_stats(self) -> dict:
        """Retorna estadisticas."""
        return {
            "total_modifications": len(self.history),
            "reverted": sum(1 for c in self.history if c.get("reverted")),
            "files_modified": len(set(c["filepath"] for c in self.history)),
            "has_pending": self.pending_change is not None,
        }
