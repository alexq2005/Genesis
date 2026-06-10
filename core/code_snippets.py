"""
GENESIS Code Snippets — Biblioteca personal de fragmentos de código.
Guarda, busca y reutiliza snippets con tags, lenguaje y fuzzy search.
"""
import os
import json
import threading
from datetime import datetime
from typing import Optional
from difflib import SequenceMatcher


class CodeSnippets:
    """Biblioteca personal de code snippets."""

    def __init__(self, data_dir: str = "memory_data"):
        self._snippets: dict[str, dict] = {}  # name -> {code, language, tags, created, uses}
        self._lock = threading.RLock()
        self._data_file = os.path.join(data_dir, "code_snippets.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ─────────────────────────────────
    def _load(self):
        """Carga snippets desde disco."""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    self._snippets = json.load(f)
        except Exception:
            pass

    def save(self):
        """Guarda snippets a disco."""
        with self._lock:
            try:
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(self._snippets, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── CRUD ─────────────────────────────────────────
    def add(self, name: str, code: str, language: str = "python",
            tags: Optional[list[str]] = None) -> str:
        """Guarda un nuevo snippet."""
        if not name or not name.strip():
            return "📎 Necesita un nombre para el snippet."
        if not code or not code.strip():
            return "📎 Necesita código para guardar."

        name = name.strip().lower()
        language = language.strip().lower()

        with self._lock:
            is_update = name in self._snippets
            self._snippets[name] = {
                "code": code,
                "language": language,
                "tags": [t.strip().lower() for t in (tags or [])],
                "created": datetime.now().isoformat(),
                "uses": self._snippets.get(name, {}).get("uses", 0)
            }
            self.save()

        action = "actualizado" if is_update else "guardado"
        tag_str = f" [tags: {', '.join(tags)}]" if tags else ""
        preview = code[:60].replace("\n", "↵") + ("..." if len(code) > 60 else "")
        return (f"📎 **Snippet '{name}' {action}** ({language}){tag_str}\n"
                f"  ```\n  {preview}\n  ```")

    def get(self, name: str) -> str:
        """Obtiene un snippet por nombre."""
        name = name.strip().lower()

        with self._lock:
            snippet = self._snippets.get(name)
            if not snippet:
                match = self._fuzzy_find(name)
                if match:
                    snippet = self._snippets[match]
                    name = match
                else:
                    return f"📎 No encontré el snippet '{name}'."

            snippet["uses"] = snippet.get("uses", 0) + 1
            self.save()

        tags = ", ".join(snippet.get("tags", [])) or "sin tags"
        return (f"📎 **{name}** ({snippet['language']}) — tags: {tags}\n"
                f"```{snippet['language']}\n{snippet['code']}\n```")

    def remove(self, name: str) -> str:
        """Elimina un snippet."""
        name = name.strip().lower()

        with self._lock:
            if name in self._snippets:
                del self._snippets[name]
                self.save()
                return f"📎 Snippet '{name}' eliminado."

            match = self._fuzzy_find(name)
            if match:
                return f"📎 No encontré '{name}'. ¿Quisiste decir '{match}'?"

            return f"📎 No encontré el snippet '{name}'."

    # ── Búsqueda ─────────────────────────────────────
    def search(self, query: str) -> str:
        """Busca snippets por nombre, tag o contenido."""
        if not query or not query.strip():
            return self.list_snippets()

        query = query.strip().lower()

        with self._lock:
            results = []
            for name, snippet in self._snippets.items():
                score = 0.0
                # Match en nombre
                score = max(score, SequenceMatcher(None, query, name).ratio())
                # Match en tags
                for tag in snippet.get("tags", []):
                    score = max(score, SequenceMatcher(None, query, tag).ratio())
                # Match en código
                if query in snippet["code"].lower():
                    score = max(score, 0.8)
                # Match en lenguaje
                if query == snippet["language"]:
                    score = max(score, 0.7)

                if score >= 0.4:
                    results.append((name, snippet, score))

        results.sort(key=lambda x: x[2], reverse=True)

        if not results:
            return f"📎 No encontré snippets para '{query}'."

        lines = [f"📎 **SNIPPETS PARA '{query}'** — {len(results)} encontrado(s)\n"]
        for name, snippet, score in results[:10]:
            preview = snippet["code"][:50].replace("\n", "↵")
            tags = ", ".join(snippet.get("tags", [])) or "-"
            lines.append(f"  📌 **{name}** ({snippet['language']}) — {score:.0%}")
            lines.append(f"     Tags: {tags} | `{preview}...`")

        return "\n".join(lines)

    def list_snippets(self) -> str:
        """Lista todos los snippets."""
        with self._lock:
            if not self._snippets:
                return "📎 No hay snippets guardados. Usá 'guardar snippet [nombre]: [código]'."

            lines = [f"📎 **MIS SNIPPETS** — {len(self._snippets)} snippet(s)\n"]

            # Agrupar por lenguaje
            by_lang: dict[str, list] = {}
            for name, snippet in sorted(self._snippets.items()):
                lang = snippet["language"]
                by_lang.setdefault(lang, []).append((name, snippet))

            for lang, snippets in sorted(by_lang.items()):
                lines.append(f"  **{lang.upper()}** ({len(snippets)}):")
                for name, snippet in snippets:
                    uses = snippet.get("uses", 0)
                    tags = ", ".join(snippet.get("tags", [])) or "-"
                    lines.append(f"    • **{name}** — {uses} usos, tags: {tags}")

            return "\n".join(lines)

    def list_by_tag(self, tag: str) -> str:
        """Lista snippets por tag."""
        tag = tag.strip().lower()

        with self._lock:
            results = []
            for name, snippet in self._snippets.items():
                if tag in snippet.get("tags", []):
                    results.append((name, snippet))

        if not results:
            return f"📎 No hay snippets con tag '{tag}'."

        lines = [f"📎 **SNIPPETS CON TAG '{tag}'** — {len(results)}\n"]
        for name, snippet in results:
            lines.append(f"  • **{name}** ({snippet['language']})")

        return "\n".join(lines)

    # ── Fuzzy matching ───────────────────────────────
    def _fuzzy_find(self, query: str) -> Optional[str]:
        """Busca snippet por nombre aproximado."""
        best_score = 0.0
        best_match = None
        for name in self._snippets:
            score = SequenceMatcher(None, query, name).ratio()
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = name
        return best_match

    # ── Status ───────────────────────────────────────
    def status(self) -> dict:
        """Estado de la biblioteca."""
        with self._lock:
            languages = set(s["language"] for s in self._snippets.values())
            total_uses = sum(s.get("uses", 0) for s in self._snippets.values())
            return {
                "total_snippets": len(self._snippets),
                "languages": len(languages),
                "total_uses": total_uses
            }


# Singleton
code_snippets = CodeSnippets()
