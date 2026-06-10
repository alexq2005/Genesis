"""
GENESIS Macro System — Grabar y ejecutar secuencias de comandos.
Define macros nombradas que ejecutan múltiples comandos auto-detect en secuencia.
Persistencia en JSON. Ejemplo: "macro trabajo: abre Chrome, abre VS Code, inicia pomodoro"
"""
import json
import os
import time
from typing import Optional, Callable
from datetime import datetime


class MacroSystem:
    """Sistema de macros para automatizar secuencias de comandos."""

    def __init__(self, data_dir: str = "memory_data"):
        self._macros: dict[str, dict] = {}
        self._data_file = os.path.join(data_dir, "macros.json")
        self._executor: Optional[Callable] = None
        self._history: list[dict] = []
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    def set_executor(self, fn: Callable):
        """Define la función que ejecuta cada comando individual.
        Normalmente será genesis._auto_detect_tool() o genesis.process_input()."""
        self._executor = fn

    # ── Persistencia ──────────────────────────────────
    def _load(self):
        try:
            if os.path.isfile(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._macros = data.get("macros", {})
                self._history = data.get("history", [])[-50:]
        except Exception:
            pass

    def save(self):
        try:
            with open(self._data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "macros": self._macros,
                    "history": self._history[-50:]
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── CRUD de macros ────────────────────────────────
    def create(self, name: str, commands: list[str], description: str = "") -> str:
        """Crea o actualiza una macro."""
        name = name.strip().lower()
        if not name:
            return "❌ La macro necesita un nombre."
        if not commands:
            return "❌ La macro necesita al menos un comando."

        # Limpiar comandos
        clean = [c.strip() for c in commands if c.strip()]
        if not clean:
            return "❌ No hay comandos válidos en la macro."

        is_update = name in self._macros
        self._macros[name] = {
            "commands": clean,
            "description": description or f"Macro con {len(clean)} comandos",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "run_count": self._macros.get(name, {}).get("run_count", 0),
        }
        self.save()

        action = "actualizada" if is_update else "creada"
        lines = [f"⚡ Macro **'{name}'** {action} ({len(clean)} comandos):"]
        for i, cmd in enumerate(clean, 1):
            lines.append(f"  {i}. `{cmd}`")
        return "\n".join(lines)

    def delete(self, name: str) -> str:
        """Elimina una macro."""
        name = name.strip().lower()
        if name not in self._macros:
            return f"❌ No encontré la macro '{name}'."
        del self._macros[name]
        self.save()
        return f"⚡ Macro **'{name}'** eliminada."

    def list_macros(self) -> str:
        """Lista todas las macros definidas."""
        if not self._macros:
            return ("⚡ No hay macros definidas.\n\n"
                    "  Creá una: `macro trabajo: abre Chrome, abre VS Code, inicia pomodoro`")

        lines = [f"⚡ **MACROS DISPONIBLES** ({len(self._macros)})\n"]
        for name, macro in sorted(self._macros.items()):
            desc = macro.get("description", "")
            count = len(macro.get("commands", []))
            runs = macro.get("run_count", 0)
            lines.append(f"  📦 **{name}** — {desc}")
            lines.append(f"     {count} comandos | {runs} ejecuciones")
        return "\n".join(lines)

    def show(self, name: str) -> str:
        """Muestra los detalles de una macro."""
        name = name.strip().lower()
        if name not in self._macros:
            return f"❌ No encontré la macro '{name}'."

        macro = self._macros[name]
        lines = [f"⚡ **MACRO: {name}**\n"]
        lines.append(f"  📝 {macro.get('description', '')}")
        lines.append(f"  📅 Creada: {macro.get('created', '?')}")
        lines.append(f"  🔄 Ejecuciones: {macro.get('run_count', 0)}")
        lines.append(f"\n  **Comandos:**")
        for i, cmd in enumerate(macro.get("commands", []), 1):
            lines.append(f"    {i}. `{cmd}`")
        return "\n".join(lines)

    # ── Ejecución ─────────────────────────────────────
    def execute(self, name: str) -> str:
        """Ejecuta una macro paso a paso."""
        name = name.strip().lower()
        if name not in self._macros:
            # Fuzzy match
            from difflib import SequenceMatcher
            best_match = max(self._macros.keys(),
                           key=lambda k: SequenceMatcher(None, name, k).ratio(),
                           default=None)
            if best_match and SequenceMatcher(None, name, best_match).ratio() > 0.6:
                name = best_match
            else:
                return f"❌ No encontré la macro '{name}'.\n\nMacros disponibles: {', '.join(self._macros.keys()) or 'ninguna'}"

        macro = self._macros[name]
        commands = macro.get("commands", [])

        if not self._executor:
            return ("❌ No hay ejecutor configurado para las macros.\n"
                    "  (El sistema necesita estar corriendo para ejecutar macros)")

        lines = [f"⚡ **EJECUTANDO MACRO: {name}** ({len(commands)} comandos)\n"]
        results = []
        t0 = time.time()

        for i, cmd in enumerate(commands, 1):
            lines.append(f"  ▶️ Paso {i}: `{cmd}`")
            try:
                result = self._executor(cmd)
                if result:
                    # Mostrar preview del resultado
                    preview = str(result)[:100].replace("\n", " ")
                    lines.append(f"     ✅ {preview}")
                    results.append(("ok", cmd, result))
                else:
                    lines.append(f"     ⚪ Sin respuesta directa")
                    results.append(("skip", cmd, None))
            except Exception as e:
                lines.append(f"     ❌ Error: {e}")
                results.append(("error", cmd, str(e)))

            # Pequeña pausa entre comandos para que el sistema procese
            time.sleep(0.3)

        elapsed = time.time() - t0
        ok_count = sum(1 for r in results if r[0] == "ok")

        # Actualizar stats
        macro["run_count"] = macro.get("run_count", 0) + 1
        self._history.append({
            "macro": name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "results": f"{ok_count}/{len(commands)} OK",
            "elapsed": f"{elapsed:.1f}s"
        })
        self.save()

        lines.append(f"\n  ✅ Completado: {ok_count}/{len(commands)} pasos OK ({elapsed:.1f}s)")
        return "\n".join(lines)

    def history(self) -> str:
        """Historial de ejecuciones de macros."""
        if not self._history:
            return "⚡ No hay historial de ejecuciones."

        lines = ["⚡ **HISTORIAL DE MACROS**\n"]
        for i, h in enumerate(reversed(self._history[-10:]), 1):
            lines.append(f"  {i}. **{h['macro']}** — {h['timestamp']} | {h['results']} | {h['elapsed']}")
        return "\n".join(lines)

    # ── Parser de entrada ─────────────────────────────
    @staticmethod
    def parse_macro_definition(text: str) -> Optional[tuple[str, list[str]]]:
        """Parsea 'macro nombre: cmd1, cmd2, cmd3' → (nombre, [comandos])."""
        import re

        # "macro trabajo: abre chrome, abre vscode, inicia pomodoro"
        m = re.match(r'(?:macro|crear macro|nueva macro)\s+(\w[\w\s]*?):\s*(.+)', text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            cmds_str = m.group(2).strip()
            # Split por ", " o " y luego " o "; "
            commands = re.split(r'\s*[,;]\s*|\s+y luego\s+|\s+después\s+|\s+luego\s+', cmds_str)
            commands = [c.strip() for c in commands if c.strip()]
            return name, commands

        return None

    def status(self) -> dict:
        """Estado del sistema de macros."""
        return {
            "total_macros": len(self._macros),
            "total_runs": sum(m.get("run_count", 0) for m in self._macros.values()),
            "history_count": len(self._history),
        }


# Singleton
macro_system = MacroSystem()
