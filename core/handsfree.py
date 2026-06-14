"""
GENESIS — Escucha manos libres (always-on) con wake-word.

Captura el micrófono en un hilo de fondo (sounddevice), transcribe en continuo
con vosk (offline) y, al oír la palabra de activación ("genesis"/"jarvis"),
ejecuta el comando que sigue y responde por voz (pyttsx3, lado servidor).

Pensado para gaming: funciona aunque haya un juego en pantalla completa, porque
el mic y la voz son del lado servidor (no dependen del navegador ni del foco).
Mientras Genesis habla, pausa la escucha (no se oye a sí mismo).
"""
import os
import re
import json
import threading

_listener = None  # instancia única

# Feed de interacciones por voz para que la CABINA las muestre en pantalla
# (el manos-libres corre server-side; sin esto, lo que decís no aparece en la UI).
_VOICE_FEED = []  # [{seq, request, response, ts}]
_FEED_SEQ = 0


def push_feed(request, response):
    global _FEED_SEQ
    try:
        _FEED_SEQ += 1
        _VOICE_FEED.append({"seq": _FEED_SEQ, "request": (request or "")[:300],
                            "response": (response or "")[:1500]})
        if len(_VOICE_FEED) > 60:
            del _VOICE_FEED[:-60]
    except Exception:
        pass


def get_feed(since=0):
    """Eventos con seq > since (para polling incremental de la cabina)."""
    return {"seq": _FEED_SEQ, "events": [e for e in _VOICE_FEED if e["seq"] > since]}


def _find_vosk_model():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mdir = os.path.join(base, "models")
    for name in ("vosk-model-small-es", "vosk-model-es", "vosk-model-small-es-0.42"):
        p = os.path.join(mdir, name)
        if os.path.isdir(p):
            return p
    try:
        for d in os.listdir(mdir):
            if "vosk" in d.lower() and os.path.isdir(os.path.join(mdir, d)):
                return os.path.join(mdir, d)
    except Exception:
        pass
    return None


class HandsFree:
    # Incluye variantes que vosk-es suele confundir (genesis→gemini/génesis/yénesis).
    WAKE = ("genesis", "génesis", "jarvis", "gemini", "yénesis", "génisis", "jénesis")
    # Similitud mínima de huella para aceptar el comando como "del dueño".
    # Más laxo que el verify formal (0.72) porque el mic en uso real es ruidoso.
    OWNER_MIN = 0.66

    def __init__(self, genesis):
        self.genesis = genesis
        self.running = False
        self._thread = None
        self._speaking = False
        self._paused = False
        self._owner_only = True   # solo obedecer si la voz coincide con la huella
        self._last = ""

    def status(self):
        modo = " · solo tu voz" if (self._owner_only and self._enrolled()) else ""
        return ("🎙️ Escucha manos libres: " + ("ACTIVA" if self.running else "apagada")
                + (" · esperando «genesis ...»" + modo if self.running else ""))

    @staticmethod
    def _enrolled():
        try:
            from core import voiceprint
            return voiceprint.enrolled()
        except Exception:
            return False

    def pause(self):
        """Suspende el procesamiento (lo usa el enroll/verify para no pisarse)."""
        self._paused = True

    def resume(self):
        self._paused = False

    def start(self):
        if self.running:
            return "🎙️ Ya estaba escuchando manos libres. Decí «genesis» + tu comando."
        try:
            import sounddevice  # noqa: F401
            import vosk  # noqa: F401
        except Exception as e:
            return f"🎙️ Falta una dependencia de audio: {str(e)[:80]}"
        if not _find_vosk_model():
            return "🎙️ No encontré el modelo de voz (models/vosk-model-small-es)."
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return ("🎙️ **Escucha manos libres ACTIVADA.** Decí «**genesis**» y después tu "
                "comando — aunque estés jugando. Ej: «genesis subí el volumen», "
                "«genesis pausá la música». Para apagar: «genesis dejá de escuchar».")

    def stop(self):
        self.running = False
        return "🎙️ Escucha manos libres apagada."

    def _loop(self):
        try:
            import sounddevice as sd
            import vosk
            vosk.SetLogLevel(-1)
            model = vosk.Model(_find_vosk_model())
            rec = vosk.KaldiRecognizer(model, 16000)
            utt = bytearray()  # audio crudo de la frase en curso (para huella)
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                                   channels=1) as stream:
                while self.running:
                    data, _ = stream.read(4000)
                    if self._speaking or self._paused:
                        utt = bytearray()  # descartar lo capturado mientras no escucha
                        continue
                    b = bytes(data)
                    utt.extend(b)
                    if rec.AcceptWaveform(b):
                        txt = json.loads(rec.Result()).get("text", "").strip()
                        audio = bytes(utt)
                        utt = bytearray()
                        if txt:
                            self._handle(txt, audio)
                    elif len(utt) > 16000 * 2 * 18:  # cota ~18s (16k·2bytes)
                        utt = utt[-16000 * 2 * 9:]
        except Exception as e:
            self.running = False
            try:
                self.genesis.log.error(f"HandsFree loop error: {e}")
            except Exception:
                pass

    def _handle(self, txt, audio=b""):
        low = txt.lower().strip()
        try:
            self.genesis.log.debug(f"[handsfree] oído: {low!r}")
        except Exception:
            pass
        # ¿está la palabra de activación?
        wpos = -1
        for w in self.WAKE:
            i = low.find(w)
            if i >= 0:
                wpos = i + len(w)
                break
        if wpos < 0:
            return
        cmd = low[wpos:].strip(" ,.:;")
        # Re-transcribir el comando con Whisper (preciso): vosk detecta barato el
        # wake-word, pero destroza nombres (JBL→"jota belle"). Whisper sobre el
        # audio de la frase recupera el comando real. Solo corre tras el wake-word.
        if audio:
            acc = self._whisper_cmd(audio)
            if acc:
                cmd = acc
        # Solo saludo o wake-word sin comando → acusar recibo (que sepas que oye)
        if not cmd or re.fullmatch(
                r"(hola|buenas|buen[oa]s?\s*(d[íi]as|tardes|noches)?|ey+|hey|"
                r"holis|qu[ée]\s+tal|c[óo]mo\s+est[áa]s?|che)\.?", cmd):
            saludo = "Hola. Te escucho, decime."
            self._speaking = True
            self._speak(saludo)
            self._speaking = False
            push_feed(cmd or "hola", saludo)
            return
        # --- VERIFICACIÓN DEL HABLANTE (solo tu voz) ---
        # Si hay huella entrenada y el modo "solo dueño" está activo, comparo el
        # audio de la frase contra la huella. Si no coincide → ignoro el comando.
        if self._owner_only and audio:
            try:
                from core import voiceprint
                if voiceprint.enrolled():
                    import numpy as np
                    f32 = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
                    ok, sim = voiceprint.verify_audio(f32, threshold=self.OWNER_MIN)
                    if sim >= 0 and not ok:  # sim<0 = no se pudo verificar → permito
                        self.genesis.log.debug(
                            f"[handsfree] voz ajena (sim={sim:.2f}) — ignoro: {cmd!r}")
                        return
            except Exception:
                pass  # ante cualquier fallo, no bloquear (fail-open)
        # apagar por voz
        if re.search(r"\b(dej[áa]\s+de\s+escuchar|apag[áa]\s+(la\s+)?escucha|"
                     r"basta|silencio|deten[ée]\s+la\s+escucha)\b", cmd):
            self._speaking = True
            self._speak("Listo, dejo de escuchar.")
            self._speaking = False
            self.running = False
            return
        # ejecutar el comando vía Genesis y responder por voz
        self._speaking = True
        try:
            resp = self.genesis.process_input(cmd)
        except Exception as e:
            resp = f"Hubo un error: {e}"
        push_feed(cmd, resp)  # mostrarlo en la cabina
        self._speak(resp)
        self._speaking = False
        self._last = cmd

    def _whisper_cmd(self, audio):
        """Transcribe el audio de la frase con Whisper (preciso) y devuelve el
        comando sin la palabra de activación. '' si no se pudo."""
        try:
            from core import stt
            if not stt.available():
                return ""
            txt = stt.transcribe(audio)
            if not txt:
                return ""
            try:
                self.genesis.log.debug(f"[handsfree] whisper: {txt!r}")
            except Exception:
                pass
            low = txt.lower().strip()
            # quitar el wake-word esté donde esté (al inicio, medio o final:
            # "hola genesis" → "hola", "genesis salida flip" → "salida flip")
            for w in self.WAKE:
                low = low.replace(w, " ")
            # Whisper agrega puntuación ("salida, flip") que rompe los regex de
            # los handlers → la normalizo a espacios.
            cmd = re.sub(r"[,.;:¿?¡!]+", " ", low)
            return re.sub(r"\s+", " ", cmd).strip()
        except Exception:
            return ""

    def _speak(self, text):
        """Voz lado servidor — suena por los parlantes aunque haya un juego en
        primer plano (no depende del navegador ni del foco). Usa la MISMA voz
        clonada que la cabina; si XTTS falla/OOM (p.ej. GPU ocupada por el
        juego) cae solo a pyttsx3."""
        try:
            from core import voice_clone
            voice_clone.speak_aloud(text)
        except Exception:
            pass


def get(genesis):
    global _listener
    if _listener is None or _listener.genesis is not genesis:
        _listener = HandsFree(genesis)
    return _listener
