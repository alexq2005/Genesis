"""
GENESIS Clipboard Manager — Historial de portapapeles con búsqueda y pin.
Monitorea cambios en el clipboard y mantiene un historial persistente.
"""
import threading
import time
import json
import os
from datetime import datetime
from typing import Optional


class ClipboardManager:
    """Gestor de historial del portapapeles."""

    def __init__(self, data_dir: str = "memory_data", max_history: int = 100):
        self._history: list[dict] = []
        self._pinned: list[dict] = []
        self._max = max_history
        self._lock = threading.RLock()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_content = ""
        self._data_file = os.path.join(data_dir, "clipboard_history.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ──────────────────────────────────
    def _load(self):
        try:
            if os.path.isfile(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._history = data.get("history", [])
                self._pinned = data.get("pinned", [])
        except Exception:
            pass

    def save(self):
        with self._lock:
            try:
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "history": self._history[-self._max:],
                        "pinned": self._pinned
                    }, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── Clipboard Access ──────────────────────────────
    @staticmethod
    def _get_clipboard() -> str:
        """Lee el contenido actual del portapapeles."""
        try:
            import subprocess
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace"
            )
            return r.stdout.strip()
        except Exception:
            return ""

    @staticmethod
    def _set_clipboard(text: str):
        """Escribe texto al portapapeles."""
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Set-Clipboard -Value '{text.replace(chr(39), chr(39)+chr(39))}'"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    # ── Monitoreo ─────────────────────────────────────
    def start_monitoring(self, interval: float = 1.0):
        """Inicia monitoreo del portapapeles en background."""
        if self._monitoring:
            return "📋 El monitor de portapapeles ya está activo."

        self._monitoring = True
        self._last_content = self._get_clipboard()

        def _monitor():
            while self._monitoring:
                try:
                    current = self._get_clipboard()
                    if current and current != self._last_content:
                        self._add_to_history(current)
                        self._last_content = current
                except Exception:
                    pass
                time.sleep(interval)

        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()
        return "📋 Monitor de portapapeles activado — guardando historial automáticamente."

    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self._monitoring = False
        self.save()
        return "📋 Monitor de portapapeles detenido."

    # ── Historial ─────────────────────────────────────
    def _add_to_history(self, content: str):
        """Agrega un item al historial."""
        with self._lock:
            # No duplicar el último item
            if self._history and self._history[-1]["content"] == content:
                return
            entry = {
                "id": len(self._history) + 1,
                "content": content,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "preview": content[:80] + ("..." if len(content) > 80 else "")
            }
            self._history.append(entry)
            if len(self._history) > self._max:
                self._history = self._history[-self._max:]
        self.save()

    def capture_current(self) -> str:
        """Captura manualmente el contenido actual del portapapeles."""
        content = self._get_clipboard()
        if not content:
            return "📋 El portapapeles está vacío."
        self._add_to_history(content)
        preview = content[:100] + ("..." if len(content) > 100 else "")
        return f"📋 Capturado: {preview}"

    def list_history(self, limit: int = 10) -> str:
        """Lista el historial del portapapeles."""
        with self._lock:
            if not self._history and not self._pinned:
                return "📋 Historial de portapapeles vacío."

            lines = ["📋 **HISTORIAL DE PORTAPAPELES**\n"]

            # Pinned primero
            if self._pinned:
                lines.append("  📌 **Fijados:**")
                for p in self._pinned:
                    lines.append(f"    #{p['id']} — {p['preview']}")
                lines.append("")

            # Historial (más recientes primero)
            recent = list(reversed(self._history[-limit:]))
            if recent:
                lines.append(f"  📜 **Recientes** (últimos {len(recent)}):")
                for h in recent:
                    ts = h.get("timestamp", "?")
                    lines.append(f"    #{h['id']} [{ts}] — {h['preview']}")

            lines.append(f"\n  Total: {len(self._history)} items | Fijados: {len(self._pinned)}")
            return "\n".join(lines)

    def search(self, query: str) -> str:
        """Busca en el historial del portapapeles."""
        if not query.strip():
            return self.list_history()

        q = query.lower()
        with self._lock:
            matches = [h for h in self._history if q in h["content"].lower()]
            pin_matches = [p for p in self._pinned if q in p["content"].lower()]

        if not matches and not pin_matches:
            return f"📋 No encontré '{query}' en el historial."

        lines = [f"📋 **Búsqueda: '{query}'** — {len(matches) + len(pin_matches)} resultados\n"]
        for m in (pin_matches + matches)[:10]:
            lines.append(f"  #{m['id']} — {m['preview']}")
        return "\n".join(lines)

    def get_item(self, item_id: int) -> str:
        """Obtiene el contenido completo de un item y lo copia al portapapeles."""
        with self._lock:
            # Buscar en pinned + history
            all_items = self._pinned + self._history
            found = next((i for i in all_items if i["id"] == item_id), None)

        if not found:
            return f"📋 No encontré el item #{item_id}."

        self._set_clipboard(found["content"])
        return f"📋 Item #{item_id} copiado al portapapeles:\n\n{found['content']}"

    def pin(self, item_id: int) -> str:
        """Fija/desfija un item del historial."""
        with self._lock:
            # Check if already pinned
            for i, p in enumerate(self._pinned):
                if p["id"] == item_id:
                    self._pinned.pop(i)
                    self.save()
                    return f"📋 Item #{item_id} desfijado."

            # Find in history
            found = next((h for h in self._history if h["id"] == item_id), None)
            if not found:
                return f"📋 No encontré el item #{item_id}."

            self._pinned.append(found.copy())
            self.save()
            return f"📋 Item #{item_id} fijado — permanece incluso si se limpia el historial."

    def clear(self) -> str:
        """Limpia el historial (mantiene los pinned)."""
        with self._lock:
            count = len(self._history)
            self._history.clear()
        self.save()
        pinned_msg = f" ({len(self._pinned)} fijados preservados)" if self._pinned else ""
        return f"📋 Historial limpiado — {count} items eliminados{pinned_msg}."

    def get_current(self) -> str:
        """Muestra el contenido actual del portapapeles sin guardarlo."""
        content = self._get_clipboard()
        if not content:
            return "📋 El portapapeles está vacío."
        preview = content[:500] + ("..." if len(content) > 500 else "")
        return f"📋 **Portapapeles actual:**\n\n{preview}"

    def status(self) -> dict:
        """Estado del clipboard manager."""
        return {
            "history_count": len(self._history),
            "pinned_count": len(self._pinned),
            "monitoring": self._monitoring,
            "max_history": self._max
        }


# Singleton
clipboard_manager = ClipboardManager()
