"""
GENESIS — Registro de herramientas (N4: function-calling híbrido).

Cada herramienta declara: nombre, descripción, parámetros y una función que la
ejecuta (envolviendo lógica ya existente en los módulos core). El tool_router
usa `specs_text()` para que el LLM elija una herramienta por SIGNIFICADO cuando
el regex no matcheó, y `execute()` para correrla.

Capa ADITIVA: no reemplaza el regex de _auto_detect_tool, lo complementa.
"""


def _clima(a):
    from core.weather import weather_service
    loc = (a.get("lugar") or a.get("location") or "").strip()
    return weather_service.current(loc) if loc else weather_service.current()


def _noticias(a):
    from core.news import headlines
    return headlines((a.get("tema") or a.get("topic") or "").strip() or None)


def _seguridad(a):
    from core.security_check import check
    return check()


def _salida_audio(a):
    from core import audio_output
    dev = (a.get("dispositivo") or a.get("device") or "").strip()
    return audio_output.set_output(dev) if dev else audio_output.list_text()


def _listar_juegos(a):
    from core import game_launcher
    return game_launcher.list_text()


def _lanzar_juego(a):
    from core import game_launcher
    return game_launcher.launch_game((a.get("juego") or a.get("game") or "").strip())


def _pomodoro(a):
    from core.pomodoro import pomodoro
    mins = a.get("minutos") or a.get("minutes")
    try:
        mins = int(mins) if mins else None
    except Exception:
        mins = None
    return pomodoro.start(mins)


def _musica(a):
    from core import music_player
    q = (a.get("tema") or a.get("query") or a.get("cancion") or "").strip()
    if not q:
        return "🎵 ¿Qué tema reproduzco?"
    return music_player.play_in_app(q)


_LEN = {"km": 1000.0, "m": 1.0, "cm": 0.01, "mm": 0.001, "milla": 1609.34,
        "millas": 1609.34, "mi": 1609.34, "pie": 0.3048, "pies": 0.3048,
        "ft": 0.3048, "pulgada": 0.0254, "pulgadas": 0.0254, "in": 0.0254,
        "metro": 1.0, "metros": 1.0, "kilometro": 1000.0, "kilometros": 1000.0,
        "yarda": 0.9144, "yardas": 0.9144}
_MASS = {"kg": 1000.0, "g": 1.0, "mg": 0.001, "kilo": 1000.0, "kilos": 1000.0,
         "gramo": 1.0, "gramos": 1.0, "libra": 453.592, "libras": 453.592,
         "lb": 453.592, "onza": 28.3495, "onzas": 28.3495, "oz": 28.3495,
         "tonelada": 1e6, "toneladas": 1e6}


def _convertir(a):
    try:
        v = float(str(a.get("valor") or a.get("value")).replace(",", "."))
        fu = (a.get("de") or a.get("from") or "").lower().strip("°")
        tu = (a.get("a") or a.get("to") or "").lower().strip("°")
    except Exception:
        return None
    if fu in ("c", "celsius", "f", "fahrenheit", "k", "kelvin") and \
       tu in ("c", "celsius", "f", "fahrenheit", "k", "kelvin"):
        c = v if fu[0] == "c" else (v - 32) * 5 / 9 if fu[0] == "f" else v - 273.15
        o = c if tu[0] == "c" else c * 9 / 5 + 32 if tu[0] == "f" else c + 273.15
        return f"🔄 {v}°{fu[0].upper()} = **{round(o, 2)}°{tu[0].upper()}**"
    for tab in (_LEN, _MASS):
        if fu in tab and tu in tab:
            return f"🔄 {v} {fu} = **{round(v * tab[fu] / tab[tu], 4)} {tu}**"
    return None


TOOLS = [
    {"name": "clima", "fn": _clima,
     "description": "Tiempo/clima actual de un lugar (o el actual si no se indica).",
     "params": [{"name": "lugar", "type": "string", "required": False,
                 "desc": "ciudad, ej: Córdoba"}]},
    {"name": "noticias", "fn": _noticias,
     "description": "Titulares de noticias actuales, opcionalmente de un tema.",
     "params": [{"name": "tema", "type": "string", "required": False,
                 "desc": "ej: deportes, tecnología"}]},
    {"name": "seguridad_sistema", "fn": _seguridad,
     "description": "Chequeo de seguridad de Windows (Defender, firewall, updates).",
     "params": []},
    {"name": "cambiar_salida_audio", "fn": _salida_audio,
     "description": "Cambia el parlante/auricular de salida, o lista los disponibles.",
     "params": [{"name": "dispositivo", "type": "string", "required": False,
                 "desc": "ej: jbl, flip, logitech"}]},
    {"name": "listar_juegos", "fn": _listar_juegos,
     "description": "Lista los juegos instalados (Steam/Epic).", "params": []},
    {"name": "lanzar_juego", "fn": _lanzar_juego,
     "description": "Abre/lanza un juego instalado por nombre.",
     "params": [{"name": "juego", "type": "string", "required": True,
                 "desc": "nombre del juego"}]},
    {"name": "iniciar_pomodoro", "fn": _pomodoro,
     "description": "Inicia un temporizador pomodoro de productividad.",
     "params": [{"name": "minutos", "type": "number", "required": False,
                 "desc": "minutos de trabajo"}]},
    {"name": "reproducir_musica", "fn": _musica,
     "description": "Reproduce una canción/tema en YouTube Music.",
     "params": [{"name": "tema", "type": "string", "required": True,
                 "desc": "canción o artista"}]},
    {"name": "convertir_unidades", "fn": _convertir,
     "description": "Convierte unidades de distancia, peso o temperatura.",
     "params": [{"name": "valor", "type": "number", "required": True, "desc": "número"},
                {"name": "de", "type": "string", "required": True, "desc": "unidad origen"},
                {"name": "a", "type": "string", "required": True, "desc": "unidad destino"}]},
]

_BY_NAME = {t["name"]: t for t in TOOLS}


def specs_text():
    """Listado compacto de herramientas para el prompt del LLM."""
    out = []
    for t in TOOLS:
        ps = ", ".join(
            f"{p['name']}{'' if p['required'] else '?'}:{p['type']}"
            for p in t["params"]) or "—"
        out.append(f"- {t['name']}({ps}): {t['description']}")
    return "\n".join(out)


def names():
    return list(_BY_NAME.keys())


def execute(name, args):
    """Ejecuta una herramienta por nombre. Devuelve str resultado o None."""
    t = _BY_NAME.get(name)
    if not t:
        return None
    try:
        return t["fn"](args or {})
    except Exception as e:
        return f"[ERROR] herramienta {name}: {str(e)[:120]}"
