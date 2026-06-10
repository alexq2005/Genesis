"""
Plugin de Marcadores para Genesis.

Guarda enlaces, rutas de archivos, o textos importantes como marcadores
con tags para busqueda rapida. Persiste entre sesiones via JSON.
"""
import json
import time
from pathlib import Path

PLUGIN_NAME = "Marcadores"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Guarda y busca marcadores con tags"

_bookmarks_file = Path(__file__).parent.parent / "data" / "bookmarks.json"
_bookmarks = []


def _load():
    global _bookmarks
    try:
        if _bookmarks_file.exists():
            with open(_bookmarks_file, "r", encoding="utf-8") as f:
                _bookmarks = json.load(f)
    except Exception:
        _bookmarks = []


def _save():
    _bookmarks_file.parent.mkdir(exist_ok=True)
    with open(_bookmarks_file, "w", encoding="utf-8") as f:
        json.dump(_bookmarks, f, ensure_ascii=False, indent=2)


def on_load(genesis):
    _load()


def on_unload(genesis):
    _save()


def register_commands():
    return {
        "/bm": {
            "handler": cmd_bookmark,
            "help": "Guardar marcador. Ej: /bm https://ejemplo.com #web #ref",
        },
        "/bms": {
            "handler": cmd_list_bookmarks,
            "help": "Buscar marcadores. Ej: /bms #web o /bms (todos)",
        },
        "/bmd": {
            "handler": cmd_delete_bookmark,
            "help": "Eliminar marcador por ID. Ej: /bmd 3",
        },
    }


def cmd_bookmark(genesis, args: str) -> str:
    if not args:
        return "Uso: /bm <contenido> [#tag1 #tag2]\nEjemplo: /bm https://docs.python.org #python #docs"

    # Extraer tags
    tags = []
    content_parts = []
    for word in args.split():
        if word.startswith("#"):
            tags.append(word[1:].lower())
        else:
            content_parts.append(word)

    content = " ".join(content_parts)
    if not content:
        return "Error: el marcador necesita contenido (no solo tags)"

    bookmark = {
        "id": len(_bookmarks) + 1,
        "content": content,
        "tags": tags,
        "created": time.strftime("%Y-%m-%d %H:%M"),
    }
    _bookmarks.append(bookmark)
    _save()

    tags_str = " ".join(f"#{t}" for t in tags) if tags else "(sin tags)"
    return f"Marcador #{bookmark['id']} guardado: {content}\nTags: {tags_str}"


def cmd_list_bookmarks(genesis, args: str) -> str:
    if not _bookmarks:
        return "No hay marcadores. Usa /bm para agregar uno."

    # Filtrar por tag si se especifica
    query = args.strip().lower() if args else ""
    filtered = _bookmarks
    if query:
        if query.startswith("#"):
            tag = query[1:]
            filtered = [b for b in _bookmarks if tag in b.get("tags", [])]
        else:
            filtered = [b for b in _bookmarks if query in b["content"].lower()]

    if not filtered:
        return f"No hay marcadores que coincidan con '{args}'"

    lines = [f"Marcadores ({len(filtered)}):"]
    for b in filtered[-20:]:  # Ultimos 20
        tags_str = " ".join(f"#{t}" for t in b.get("tags", []))
        lines.append(f"  [{b['id']}] {b['content']}  {tags_str}  ({b['created']})")
    return "\n".join(lines)


def cmd_delete_bookmark(genesis, args: str) -> str:
    if not args:
        return "Uso: /bmd <id>"
    try:
        bid = int(args.strip())
        for i, b in enumerate(_bookmarks):
            if b["id"] == bid:
                removed = _bookmarks.pop(i)
                _save()
                return f"Marcador #{bid} eliminado: {removed['content']}"
        return f"Marcador #{bid} no encontrado"
    except ValueError:
        return "Uso: /bmd <numero>"
