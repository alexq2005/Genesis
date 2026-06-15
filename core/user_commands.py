"""Comandos personalizados del usuario (alias): «cuando diga X → hacé Y».

Persistente en data/user_commands.json. `expand()` reescribe la entrada del usuario
si matchea un alias, ANTES del ruteo normal — así el alias se comporta como cualquier
comando. Soporta un comodín {x} para capturar el resto de la frase:
    trigger="poné {x}"  action="reproducí {x}"   →  «poné bon jovi» = «reproducí bon jovi»

Es la base de la personalización: alias de voz, sinónimos de comandos y atajos propios.
"""
import os
import re
import json

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "user_commands.json")


def _load():
    try:
        with open(_PATH, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []


def _save(items):
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def list_all():
    """Lista de alias [{trigger, action}]."""
    return _load()


def add(trigger, action):
    """Crea/actualiza un alias. Devuelve (ok, mensaje)."""
    trigger = re.sub(r"\s+", " ", (trigger or "").strip().lower()).strip(" '\"«».,")
    action = re.sub(r"\s+", " ", (action or "").strip()).strip(" '\"«».")
    if len(trigger) < 2 or not action:
        return False, "Falta el gatillo o la acción."
    if trigger == action.lower():
        return False, "El gatillo y la acción no pueden ser iguales."
    items = [i for i in _load() if i.get("trigger", "").lower() != trigger]
    if len(items) >= 100:
        return False, "Llegaste al máximo de 100 comandos."
    items.append({"trigger": trigger, "action": action})
    _save(items)
    return True, f"Comando guardado: «{trigger}» → «{action}»"


def remove(trigger):
    """Borra un alias por gatillo (exacto, case-insensitive). True si borró algo."""
    trigger = (trigger or "").strip().lower().strip(" '\"«».,")
    items = _load()
    kept = [i for i in items if i.get("trigger", "").lower() != trigger]
    if len(kept) == len(items):
        return False
    _save(kept)
    return True


def expand(text):
    """Si `text` matchea un alias, devuelve la acción expandida; si no, None."""
    low = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not low:
        return None
    for it in _load():
        trig = (it.get("trigger") or "").strip().lower()
        act = (it.get("action") or "").strip()
        if len(trig) < 2 or not act:
            continue
        if "{x}" in trig:
            pat = "^" + re.escape(trig).replace(r"\{x\}", r"(.+)") + "$"
            m = re.match(pat, low)
            if m:
                return act.replace("{x}", m.group(1).strip())
        elif low == trig:
            return act
    return None
