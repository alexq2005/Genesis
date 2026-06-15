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

# Texto de entrenamiento: ~60-70s leído natural, fonéticamente rico (erres, eñes, ll,
# ch, vocales abiertas/cerradas, números) para una huella robusta.
_ENROLL_TEXT = (
    "Hola, soy yo, y esta es mi voz. La estoy grabando para que el asistente aprenda "
    "a reconocerme cuando le hable. Voy a leer tranquilo, con mi tono de siempre, sin "
    "apurarme ni forzar las palabras.\n\n"
    "El zorro veloz corría por el campo mientras la lluvia caía sobre los techos del "
    "pueblo. Quiero que distingas mi manera de hablar: las erres, las eñes, los sonidos "
    "suaves y los fuertes, las vocales largas y las cortas.\n\n"
    "Hoy es un buen día; son cerca de las tres de la tarde y el cielo está despejado. Me "
    "gusta la música, los proyectos y armar cosas que funcionen de verdad. Si todo sale "
    "bien, vas a entender mis órdenes aunque haya ruido alrededor, aunque esté jugando o "
    "escuchando algo.\n\n"
    "Repito con calma para darte más audio: uno, dos, tres, cuatro, cinco, seis, siete, "
    "ocho, nueve, diez. La rana saltó del charco, el barco zarpó del puerto al amanecer y "
    "el guitarrista afinó las cuerdas en la plaza. Gracias por escucharme; ya casi "
    "terminamos."
)


def enroll_text():
    """Texto sugerido para leer durante el entrenamiento (~60s)."""
    return _ENROLL_TEXT


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


def forget():
    """Borra la huella de voz entrenada. Devuelve True si había una.
    Tras esto, enrolled()=False y el manos-libres obedece a cualquier voz."""
    try:
        if os.path.exists(_VP_PATH):
            os.remove(_VP_PATH)
            return True
    except Exception:
        pass
    return False


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


def _pause_handsfree(genesis):
    """Pausa el manos-libres (si está activo) para que no reaccione a la voz de
    entrenamiento ni compita por el micrófono. Devuelve el listener o None."""
    try:
        from core import handsfree
        hf = handsfree.get(genesis)
        if getattr(hf, "running", False):
            hf.pause()
            return hf
    except Exception:
        pass
    return None


def _resume_handsfree(hf):
    try:
        if hf is not None:
            hf.resume()
    except Exception:
        pass


def start_enroll(genesis, seconds=60):
    """Entrena la huella de voz del usuario (graba `seconds`, en hilo aparte).
    60s por defecto: más audio = embedding más robusto y verificación más confiable."""
    if not available():
        return "🗣️ Falta resemblyzer/sounddevice para el reconocimiento de voz."

    def _job():
        _hf = _pause_handsfree(genesis)
        try:
            _speak(genesis, f"Voy a grabar tu voz {seconds} segundos. Leé en voz alta el "
                            f"texto que aparece en pantalla, con tu tono normal. Empezá ya.")
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
        finally:
            _resume_handsfree(_hf)

    threading.Thread(target=_job, daemon=True).start()
    # [[ENROLL]] = la cabina muestra el texto en un panel grande (NO lo lee el TTS, para
    # no contaminar la grabación). El texto sale de /api/voice/enroll_text.
    return (f"[[ENROLL]]🗣️ **Entrenando tu voz {seconds} segundos.** Leé en voz alta el "
            f"texto que aparece en pantalla, tranquilo y con tu tono normal.")


def start_verify(genesis, seconds=4):
    """Verifica si la voz actual es la del usuario entrenado (en hilo aparte)."""
    if not available():
        return "🗣️ Falta resemblyzer/sounddevice."
    if not enrolled():
        return "🗣️ Todavía no entrené tu voz. Decí «entrená mi voz» primero."

    def _job():
        _hf = _pause_handsfree(genesis)
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
        finally:
            _resume_handsfree(_hf)

    threading.Thread(target=_job, daemon=True).start()
    return f"🗣️ **Verificando tu voz** — hablá {seconds}s. Te digo por voz si sos vos."


def verify_audio(audio_f32, threshold=None):
    """Verifica un array de audio (float32 16kHz) contra la huella entrenada.
    Devuelve (es_usuario, similitud). Si NO hay huella o no se pudo calcular el
    embedding, devuelve (True, -1.0) → 'no se pudo verificar' (fail-open, no
    bloquea). Así quien llama distingue 'no sos vos' (sim≥0 y bajo) de 'no
    pude chequear' (sim<0)."""
    thr = _THRESHOLD if threshold is None else threshold
    if not enrolled():
        return (True, -1.0)
    try:
        emb = _embed(audio_f32)
        ref = np.load(_VP_PATH)
        sim = float(np.dot(emb, ref))
        return (sim >= thr, sim)
    except Exception:
        return (True, -1.0)
