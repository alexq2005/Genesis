"""
GENESIS — TTS local con Piper (voces neurales 100% offline).

A diferencia de edge-tts (que sintetiza en servidores de Microsoft), Piper corre
TODO en tu PC: no necesita internet. Modelos .onnx en models/piper/ (bajados con
`python -m piper.download_voices <voz> --data-dir models/piper`).
Voz id en el sistema: "piper:<nombre>" (ej: piper:es_ES-davefx-medium).
"""
import io
import os
import wave

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIR = os.path.join(_BASE, "models", "piper")
_CACHE = {}  # nombre -> PiperVoice (cacheado)


def _models_dir():
    return _DIR


def list_voices():
    """Nombres de voces Piper instaladas (sin extensión)."""
    out = []
    try:
        for f in os.listdir(_DIR):
            if f.endswith(".onnx"):
                out.append(f[:-5])
    except Exception:
        pass
    return sorted(out)


def available():
    try:
        import piper  # noqa: F401
        return bool(list_voices())
    except Exception:
        return False


def _load(name):
    if name not in _CACHE:
        from piper import PiperVoice
        path = os.path.join(_DIR, name + ".onnx")
        _CACHE[name] = PiperVoice.load(path)
    return _CACHE[name]


def synth_to_wav(text, name, out_path):
    """Sintetiza `text` con la voz `name` a un archivo WAV."""
    v = _load(name)
    with wave.open(out_path, "wb") as wf:
        v.synthesize_wav(text, wf)
    return out_path


def synth_bytes(text, name):
    """Sintetiza y devuelve los bytes de un WAV (para servir por HTTP)."""
    v = _load(name)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        v.synthesize_wav(text, wf)
    return buf.getvalue()


def warm(name=None):
    """Pre-carga una voz (la primera si no se indica) en memoria."""
    try:
        n = name or (list_voices() or [None])[0]
        if n:
            _load(n)
            return True
    except Exception:
        pass
    return False
