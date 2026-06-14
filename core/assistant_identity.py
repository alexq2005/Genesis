"""Identidad del asistente: nombre configurable por el usuario.

Persistente en data/assistant_config.json. Afecta:
- la palabra de activación (handsfree),
- cómo se refiere a sí mismo (prompts de personalidad),
- el handler de "¿cómo te llamás?",
- el título de la ventana / búsqueda de la cabina.

Decisión del usuario (2026-06-14): al renombrar, el nombre nuevo REEMPLAZA al
viejo como palabra de activación. Red de seguridad: renombrar por TEXTO en la
cabina no necesita wake-word, así que siempre se puede volver atrás.
"""
import os
import re
import json

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "assistant_config.json")
_DEFAULT = "Genesis"

# Variantes del nombre por defecto que vosk-es suele confundir.
_GENESIS_WAKE = ("genesis", "génesis", "jarvis", "gemini", "yénesis",
                 "génisis", "jénesis")

_ACC = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}


def _strip_acc(s):
    return "".join(_ACC.get(c, c) for c in (s or "").lower())


def get_name():
    """Nombre actual del asistente (para mostrar). Default 'Genesis'."""
    try:
        with open(_PATH, encoding="utf-8") as f:
            n = (json.load(f).get("name") or "").strip()
            return n or _DEFAULT
    except Exception:
        return _DEFAULT


def set_name(new):
    """Cambia el nombre del asistente. Devuelve (ok: bool, nombre_o_error: str)."""
    new = (new or "").strip().strip(".,!¡¿?\"'")
    new = re.sub(r"\s+", " ", new)[:30].strip()
    if not re.match(r"^[a-zA-Z0-9áéíóúñüÁÉÍÓÚÑÜ ]{2,30}$", new):
        return False, "nombre inválido (usá 2-30 letras/números)"
    name = new.title()
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"name": name}, f, ensure_ascii=False)
        return True, name
    except Exception as e:
        return False, str(e)[:80]


def wake_words():
    """Palabras de activación para el nombre ACTUAL. Para el default 'Genesis'
    devuelve las variantes ricas (que vosk confunde); para un nombre custom, el
    nombre lower + su versión sin acentos + cada palabra suelta (≥3 letras)."""
    name = get_name()
    if _strip_acc(name) == "genesis":
        return _GENESIS_WAKE
    low = name.lower()
    variants = {low, _strip_acc(low)}
    for w in low.split():
        if len(w) >= 3:
            variants.add(w)
            variants.add(_strip_acc(w))
    return tuple(variants)
