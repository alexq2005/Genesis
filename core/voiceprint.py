"""
GENESIS — Huella de voz (reconocimiento del hablante) con resemblyzer.

Entrena la "voiceprint" del usuario (un embedding de 256-d) a partir de unos
segundos de su voz, y luego verifica si una muestra nueva es de la misma persona
(similitud coseno). 100% local. Útil para personalizar o que Genesis solo
obedezca al dueño.
"""
import os
import threading

import numpy as np

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VP_PATH = os.path.join(_BASE, "data", "voices", "voiceprint.npy")
_ENCODER = None
_SR = 16000
_THRESHOLD = 0.72  # similitud coseno mínima para considerar "es la misma voz"


def _encoder():
    global _ENCODER
    if _ENCODER is None:
        from resemblyzer import VoiceEncoder
        _ENCODER = VoiceEncoder("cpu", verbose=False)  # liviano en CPU
    return _ENCODER


def available():
    try:
        import resemblyzer  # noqa: F401
        import sounddevice  # noqa: F401
        return True
    except Exception:
        return False


def enrolled():
    return os.path.exists(_VP_PATH)


def _record(seconds):
    import sounddevice as sd
    audio = sd.rec(int(seconds * _SR), samplerate=_SR, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def _embed(audio_f32):
    from resemblyzer import preprocess_wav
    wav = preprocess_wav(audio_f32, source_sr=_SR)
    return _encoder().embed_utterance(wav)  # 256-d, L2-normalizado


def _speak(genesis, text):
    # Misma voz clonada que la cabina (con fallback automático a pyttsx3).
    try:
        from core import voice_clone
        voice_clone.speak_aloud(text)
    except Exception:
        pass


def start_enroll(genesis, seconds=15):
    """Entrena la huella de voz del usuario (graba `seconds`, en hilo aparte)."""
    if not available():
        return "🗣️ Falta resemblyzer/sounddevice para el reconocimiento de voz."

    def _job():
        try:
            _speak(genesis, f"Voy a grabar tu voz {seconds} segundos. Hablá normal, "
                            f"contame algo, ya.")
            audio = _record(seconds)
            emb = _embed(audio)
            os.makedirs(os.path.dirname(_VP_PATH), exist_ok=True)
            np.save(_VP_PATH, emb)
            _speak(genesis, "Listo. Tu voz quedó registrada.")
            try:
                genesis.log.debug("[voiceprint] enrolled OK")
            except Exception:
                pass
        except Exception as e:
            try:
                genesis.log.error(f"[voiceprint] enroll error: {e}")
            except Exception:
                pass
            _speak(genesis, "Hubo un problema grabando tu voz.")

    threading.Thread(target=_job, daemon=True).start()
    return (f"🗣️ **Entrenando tu voz** — grabando {seconds}s. **Hablá normal ahora** "
            f"(contá cualquier cosa). Te aviso por voz cuando termine.")


def start_verify(genesis, seconds=4):
    """Verifica si la voz actual es la del usuario entrenado (en hilo aparte)."""
    if not available():
        return "🗣️ Falta resemblyzer/sounddevice."
    if not enrolled():
        return "🗣️ Todavía no entrené tu voz. Decí «entrená mi voz» primero."

    def _job():
        try:
            _speak(genesis, f"Decí algo, te escucho {seconds} segundos.")
            audio = _record(seconds)
            emb = _embed(audio)
            ref = np.load(_VP_PATH)
            sim = float(np.dot(emb, ref))  # ambos L2-normalizados → coseno
            pct = round(sim * 100)
            if sim >= _THRESHOLD:
                _speak(genesis, f"Sos vos. Coincidencia del {pct} por ciento.")
            else:
                _speak(genesis, f"No te reconozco. Coincidencia del {pct} por ciento.")
            try:
                genesis.log.debug(f"[voiceprint] verify sim={sim:.3f}")
            except Exception:
                pass
        except Exception as e:
            try:
                genesis.log.error(f"[voiceprint] verify error: {e}")
            except Exception:
                pass

    threading.Thread(target=_job, daemon=True).start()
    return f"🗣️ **Verificando tu voz** — hablá {seconds}s. Te digo por voz si sos vos."


def verify_audio(audio_f32):
    """Verifica un array de audio ya capturado. Devuelve (es_usuario, similitud)."""
    if not enrolled():
        return (True, 1.0)  # sin huella → no bloquear
    try:
        emb = _embed(audio_f32)
        ref = np.load(_VP_PATH)
        sim = float(np.dot(emb, ref))
        return (sim >= _THRESHOLD, sim)
    except Exception:
        return (True, 0.0)
