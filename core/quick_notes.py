"""
GENESIS Quick Notes — Sistema de notas rápidas persistentes.
Permite guardar, listar, buscar y eliminar notas desde la sidebar.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class QuickNotes:
    """Sistema de notas rápidas con persistencia JSON."""

    def __init__(self, data_dir: str = None):
        if data_dir:
            self._file = Path(data_dir) / "quick_notes.json"
        else:
            self._file = Path(__file__).parent.parent / "memory_data" / "quick_notes.json"
        self._notes: list[dict] = []
        self._load()

    def _load(self):
        """Carga notas desde disco."""
        try:
            if self._file.exists():
                with open(self._file, "r", encoding="utf-8") as f:
                    self._notes = json.load(f)
        except Exception:
            self._notes = []

    def save(self):
        """Guarda notas a disco."""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._notes, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, content: str, tag: str = "") -> str:
        """Agrega una nota nueva."""
        if not content.strip():
            return "No puedo guardar una nota vacía."
        note = {
            "id": len(self._notes) + 1,
            "content": content.strip(),
            "tag": tag.strip(),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pinned": False,
        }
        self._notes.append(note)
        self.save()
        tag_str = f" [{tag}]" if tag else ""
        return f"📝 Nota #{note['id']} guardada{tag_str}: \"{content.strip()[:80]}...\""  if len(content) > 80 else f"📝 Nota #{note['id']} guardada{tag_str}: \"{content.strip()}\""

    def list_notes(self, tag: str = "", limit: int = 15) -> str:
        """Lista notas, opcionalmente filtradas por tag."""
        if not self._notes:
            return "📝 No tenés notas guardadas. Usá 'nota: tu texto' para crear una."

        filtered = self._notes
        if tag:
            filtered = [n for n in filtered if tag.lower() in n.get("tag", "").lower()]

        if not filtered:
            return f"📝 No hay notas con tag '{tag}'."

        # Pinned primero, luego por fecha descendente
        pinned = [n for n in filtered if n.get("pinned")]
        normal = [n for n in filtered if not n.get("pinned")]
        ordered = pinned + list(reversed(normal))

        lines = [f"📝 **MIS NOTAS** ({len(filtered)} total)\n"]
        for note in ordered[:limit]:
            pin = "📌 " if note.get("pinned") else ""
            tag_str = f" `{note['tag']}`" if note.get("tag") else ""
            date = note.get("created", "")[:10]
            lines.append(f"  {pin}**#{note['id']}** ({date}){tag_str} — {note['content'][:100]}")

        if len(filtered) > limit:
            lines.append(f"\n  ... y {len(filtered) - limit} notas más")

        return "\n".join(lines)

    def search(self, query: str) -> str:
        """Busca notas por contenido."""
        if not query.strip():
            return self.list_notes()

        q = query.lower()
        matches = [n for n in self._notes if q in n["content"].lower() or q in n.get("tag", "").lower()]

        if not matches:
            return f"📝 No encontré notas con '{query}'."

        lines = [f"📝 **RESULTADOS** ({len(matches)} notas con '{query}')\n"]
        for note in matches[-10:]:
            tag_str = f" `{note['tag']}`" if note.get("tag") else ""
            lines.append(f"  **#{note['id']}** — {note['content'][:100]}{tag_str}")

        return "\n".join(lines)

    def delete(self, note_id: int) -> str:
        """Elimina una nota por ID."""
        for i, note in enumerate(self._notes):
            if note["id"] == note_id:
                content = note["content"][:50]
                self._notes.pop(i)
                self.save()
                return f"🗑️ Nota #{note_id} eliminada: \"{content}...\""
        return f"No encontré nota #{note_id}."

    def pin(self, note_id: int) -> str:
        """Fija/desfija una nota."""
        for note in self._notes:
            if note["id"] == note_id:
                note["pinned"] = not note.get("pinned", False)
                self.save()
                state = "fijada 📌" if note["pinned"] else "desfijada"
                return f"Nota #{note_id} {state}."
        return f"No encontré nota #{note_id}."

    def clear(self):
        """Elimina todas las notas."""
        count = len(self._notes)
        self._notes = []
        self.save()
        return f"🗑️ {count} notas eliminadas."

    def status(self) -> dict:
        """Estado del sistema de notas."""
        return {
            "total": len(self._notes),
            "pinned": sum(1 for n in self._notes if n.get("pinned")),
            "tags": list(set(n.get("tag", "") for n in self._notes if n.get("tag"))),
        }

    def get_stats(self) -> dict:
        return self.status()
