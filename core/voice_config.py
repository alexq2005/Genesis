"""
GENESIS — Configuración de voz (compartida cabina + manos-libres).

Guarda la voz elegida y la velocidad en data/voice_config.json para que TODOS
los caminos de voz (TTS del navegador y voz server-side del manos-libres/
voiceprint) usen la misma. 100% local.
"""
import json
import os
import threading

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.path.join(_BASE, "data", "voice_config.json")
_LOCK = threading.Lock()

DEFAULT = {"voice": "clon:milton", "rate": 0}  # rate = % (-50..+50)

# Catálogo para la UI. clon:milton = voz clonada local (XTTS); el resto edge-tts.
VOICES = [
    {"id": "clon:milton", "label": "Milton — clon JARVIS (local)"},
    {"id": "es-AR-TomasNeural", "label": "Tomás — Argentino"},
    {"id": "es-AR-ElenaNeural", "label": "Elena — Argentina"},
    {"id": "es-ES-AlvaroNeural", "label": "Álvaro — España"},
    {"id": "es-ES-ElviraNeural", "label": "Elvira — España"},
    {"id": "es-MX-JorgeNeural", "label": "Jorge — México"},
    {"id": "es-MX-DaliaNeural", "label": "Dalia — México"},
    {"id": "es-US-AlonsoNeural", "label": "Alonso — Latino neutro"},
    {"id": "es-CO-GonzaloNeural", "label": "Gonzalo — Colombia"},
]


def get():
    try:
        with open(_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return {"voice": d.get("voice", DEFAULT["voice"]),
                "rate": int(d.get("rate", 0))}
    except Exception:
        return dict(DEFAULT)


def set(voice=None, rate=None):
    with _LOCK:
        cfg = get()
        if voice:
            cfg["voice"] = str(voice)
        if rate is not None:
            try:
                cfg["rate"] = max(-50, min(50, int(rate)))
            except Exception:
                pass
        try:
            os.makedirs(os.path.dirname(_PATH), exist_ok=True)
            with open(_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False)
        except Exception:
            pass
        return cfg


def rate_pct():
    """Velocidad en formato edge-tts: '+10%', '-20%', '+0%'."""
    r = get().get("rate", 0)
    return f"{'+' if r >= 0 else ''}{r}%"
