"""
GENESIS — Router de herramientas por significado (N4: function-calling híbrido).

Cuando el regex de _auto_detect_tool NO matcheó, este router le pide al LLM que
elija una herramienta del registro (por SIGNIFICADO, no por keywords) y devuelva
un JSON {tool, args}. Se valida y se ejecuta la herramienta real.

Solo corre en el camino NONE → no agrega latencia al 90% que el regex resuelve.
Devuelve None si ninguna herramienta aplica (→ sigue al cerebro conversacional).
"""
import json
import os
import re
import urllib.request


def _ollama_json(system, user_msg, model, url, timeout=120):
    """Llama a Ollama /api/chat con format=json (constrained decoding → JSON
    siempre válido). Devuelve el contenido (string JSON)."""
    payload = {
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user_msg}],
        "options": {"temperature": 0.0, "num_predict": 200},
    }
    req = urllib.request.Request(
        url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d.get("message", {}).get("content", "")


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


# Pre-filtro barato: solo invocar el LLM si el mensaje roza algún dominio de
# herramienta. Evita meter una llamada LLM en cada charla ("hola", "contame un
# chiste") — el LLM solo decide la herramienta exacta + args, no la relevancia.
_HINTS = (
    "clima", "tiempo", "temperatura", "grados", "frio", "frío", "calor", "lluvia",
    "llover", "pronostic", "noticia", "titular", "novedad", "actualidad",
    "juego", "jugar", "jugá", "juga", "steam", "epic", "musica", "música",
    "cancion", "canción", "tema", "reproduc", "escuch", "sonar", "playlist",
    "salida", "audio", "parlante", "auricular", "altavoz", "altavoces", "jbl",
    "logitech", "philips", "pomodoro", "convert", "kilometro", "kilómetro",
    "milla", "metro", "pie", "pulgada", "kilo", "gramo", "libra", "onza",
    "celsius", "fahrenheit", "kelvin", " km", " kg", "segur", "defender",
    "firewall", "antivirus", "virus",
)


def route(genesis, user_input):
    """Mapea `user_input` a una herramienta vía LLM. Devuelve resultado o None."""
    try:
        from core import tool_registry as reg
    except Exception:
        return None
    brain = getattr(genesis, "brain", None)
    low = (user_input or "").lower().strip()
    if brain is None or not low:
        return None
    if not any(h in low for h in _HINTS):
        return None  # ni roza un dominio de herramienta → es charla, no gasto LLM
    sys_p = (
        "Sos un enrutador de herramientas. Herramientas (nombre(params): desc):\n"
        + reg.specs_text() + "\n\n"
        "Mapeá el pedido a UNA herramienta y sus argumentos. Respondé ÚNICAMENTE "
        "JSON en una sola línea: empezá con { y terminá con }. Nada de texto, "
        "explicaciones ni razonamiento. Si ninguna herramienta aplica (charla, "
        'pregunta general, código), respondé {"tool":null}.\n\n'
        "Ejemplos:\n"
        "Usuario: tirame las novedades de tecnología\n"
        '{"tool":"noticias","args":{"tema":"tecnología"}}\n'
        "Usuario: pasá 5 kilómetros a millas\n"
        '{"tool":"convertir_unidades","args":{"valor":5,"de":"km","a":"millas"}}\n'
        "Usuario: mandá el sonido a la jbl\n"
        '{"tool":"cambiar_salida_audio","args":{"dispositivo":"jbl"}}\n'
        "Usuario: gracias, sos un genio\n"
        '{"tool":null}'
    )
    # Modelo del router (configurable). Default: el mismo cerebro (genesis-q3).
    # format=json fuerza JSON válido → elimina vacíos/truncados.
    model = os.environ.get("GENESIS_TOOLCALL_MODEL",
                           getattr(brain, "model", None) or "genesis-q3")
    url = getattr(brain, "ollama_url", None) or "http://localhost:11434"
    data = None
    for _try in range(2):  # 1 reintento por las dudas
        try:
            out = _ollama_json(sys_p, user_input, model, url)
        except Exception:
            return None
        data = _extract_json(out or "")
        if isinstance(data, dict):
            break
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
