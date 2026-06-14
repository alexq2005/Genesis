"""
GENESIS — Router de herramientas por significado (N4: function-calling híbrido).

Cuando el regex de _auto_detect_tool NO matcheó, este router le pide al LLM que
elija una herramienta del registro (por SIGNIFICADO, no por keywords) y devuelva
un JSON {tool, args}. Se valida y se ejecuta la herramienta real.

Solo corre en el camino NONE → no agrega latencia al 90% que el regex resuelve.
Devuelve None si ninguna herramienta aplica (→ sigue al cerebro conversacional).
"""
import json
import re


def _extract_json(text):
    if not text:
        return None
    text = re.sub(r"```[a-zA-Z]*", "", text).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    blob = m.group(0)
    for attempt in (blob, blob.replace("'", '"')):
        try:
            return json.loads(attempt)
        except Exception:
            continue
    return None


def route(genesis, user_input):
    """Mapea `user_input` a una herramienta vía LLM. Devuelve resultado o None."""
    try:
        from core import tool_registry as reg
    except Exception:
        return None
    brain = getattr(genesis, "brain", None)
    if brain is None or not (user_input or "").strip():
        return None
    sys_p = (
        "Sos un enrutador de herramientas. Tenés EXACTAMENTE estas herramientas "
        "(nombre(params): descripción):\n" + reg.specs_text() + "\n\n"
        "Dado el pedido del usuario, si corresponde claramente a UNA herramienta, "
        'respondé SOLO un JSON: {"tool":"<nombre>","args":{...}}. '
        'Si NINGUNA aplica (charla, pregunta general, código, otra cosa), respondé '
        'SOLO {"tool":null}. No expliques, no agregues texto fuera del JSON.'
    )
    try:
        out = brain.think(sys_p, [{"role": "user", "content": user_input}],
                          temperature=0.0, max_tokens=120)
    except Exception:
        return None
    data = _extract_json(out or "")
    if not isinstance(data, dict):
        return None
    name = data.get("tool")
    if not name or name not in reg.names():
        return None
    args = data.get("args")
    if not isinstance(args, dict):
        args = {}
    try:
        genesis.log.debug(f"[toolrouter] {user_input!r} -> {name}({args})")
    except Exception:
        pass
    return reg.execute(name, args)
