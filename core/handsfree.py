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

    def __init__(self, genesis):
        self.genesis = genesis
        self.running = False
        self._thread = None
        self._speaking = False
        self._last = ""

    def status(self):
        return ("🎙️ Escucha manos libres: " + ("ACTIVA" if self.running else "apagada")
                + (" · esperando «genesis ...»" if self.running else ""))

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
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                                   channels=1) as stream:
                while self.running:
                    data, _ = stream.read(4000)
                    if self._speaking:
                        continue  # no escucharse a sí mismo
                    if rec.AcceptWaveform(bytes(data)):
                        txt = json.loads(rec.Result()).get("text", "").strip()
                        if txt:
                            self._handle(txt)
        except Exception as e:
            self.running = False
            try:
                self.genesis.log.error(f"HandsFree loop error: {e}")
            except Exception:
                pass

    def _handle(self, txt):
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
        if not cmd:
            return
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
        self._speak(resp)
        self._speaking = False
        self._last = cmd

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
