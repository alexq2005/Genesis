"""
GENESIS — Transcripción de voz (STT) precisa con faster-whisper.

vosk es barato y bueno para el wake-word en streaming, pero su vocabulario
cerrado destroza nombres propios (JBL→"jota belle", flip→"sierra"). Whisper
(faster-whisper) es mucho más preciso, sobre todo con marcas/nombres. Lo usamos
para transcribir el COMANDO una vez que vosk detectó la palabra de activación.

Corre en CPU (int8) para no competir por la VRAM con XTTS+Ollama. Modelo
'small' = buen balance precisión/velocidad en español (~0.5-1s por frase corta).
100% local tras bajar el modelo (~480MB) la primera vez.
"""
import numpy as np

_MODEL = None
_SIZE = "small"   # tiny/base/small/medium — 'small' buen balance ES en CPU
_SR = 16000


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def _model():
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(_SIZE, device="cpu", compute_type="int8")
    return _MODEL


def transcribe(audio, language: str = "es") -> str:
    """Transcribe audio (bytes int16 PCM 16k, o np.float32) → texto. '' si falla."""
    try:
        if isinstance(audio, (bytes, bytearray)):
            a = np.frombuffer(bytes(audio), dtype=np.int16).astype(np.float32) / 32768.0
        else:
            a = np.asarray(audio, dtype=np.float32)
        if a.size < int(_SR * 0.3):   # <0.3s → muy corto, ignorar
            return ""
        segs, _ = _model().transcribe(
            a, language=language, beam_size=1, vad_filter=True,
            condition_on_previous_text=False)
        return " ".join(s.text for s in segs).strip()
    except Exception:
        return ""


def warm() -> bool:
    """Pre-carga el modelo (lo baja si hace falta). Para llamar al arrancar."""
    try:
        _model()
        return True
    except Exception:
        return False
