"""
GENESIS — Voice I/O
Sistema de entrada/salida por voz 100% local.

TTS (Text-to-Speech): pyttsx3 — motor local de Windows/Linux/macOS
STT (Speech-to-Text): Opcion 1: vosk (offline), Opcion 2: whisper.cpp (futuro)

Ambos funcionan sin conexion a internet.

Dependencias opcionales:
    pip install pyttsx3       # TTS — usa SAPI5 (Windows) o espeak (Linux)
    pip install vosk           # STT — reconocimiento offline
    pip install sounddevice    # Captura de audio del microfono

Uso:
    voice = VoiceSystem()
    voice.speak("Hola, soy Genesis")
    texto = voice.listen(timeout=10)  # Escucha 10 segundos
"""
import threading
import time
import queue
from typing import Optional


# ============================================================
# TTS Engine — Text to Speech
# ============================================================
class TTSEngine:
    """Motor de texto a voz local usando pyttsx3."""

    def __init__(self, rate: int = 175, volume: float = 0.9, voice_id: int = 0):
        """
        Args:
            rate: velocidad de habla (palabras por minuto, default 175)
            volume: volumen 0.0 a 1.0
            voice_id: indice de la voz a usar (0 = primera disponible)
        """
        self.engine = None
        self.available = False
        self.rate = rate
        self.volume = volume
        self.voice_id = voice_id
        self.voices = []
        self._speaking = False
        self._lock = threading.Lock()

        self._init_engine()

    def _init_engine(self):
        """Inicializa pyttsx3 si esta disponible."""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", self.rate)
            self.engine.setProperty("volume", self.volume)

            # Listar voces disponibles
            self.voices = self.engine.getProperty("voices")
            if self.voices and self.voice_id < len(self.voices):
                self.engine.setProperty("voice", self.voices[self.voice_id].id)

            self.available = True
        except ImportError:
            self.available = False
        except Exception:
            self.available = False

    def speak(self, text: str, block: bool = True) -> bool:
        """
        Habla el texto dado.

        Args:
            text: texto a hablar
            block: True = espera a que termine, False = habla en background

        Returns:
            True si se inicio/completo correctamente
        """
        if not self.available or not text:
            return False

        if block:
            return self._speak_sync(text)
        else:
            t = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            t.start()
            return True

    def _speak_sync(self, text: str) -> bool:
        """Habla sincronamente con lock para thread safety."""
        with self._lock:
            try:
                self._speaking = True
                self.engine.say(text)
                self.engine.runAndWait()
                self._speaking = False
                return True
            except Exception:
                self._speaking = False
                return False

    def stop(self):
        """Detiene el habla actual."""
        if self.engine and self._speaking:
            try:
                self.engine.stop()
            except Exception:
                pass
            self._speaking = False

    def set_rate(self, rate: int):
        """Ajusta velocidad de habla."""
        self.rate = rate
        if self.engine:
            self.engine.setProperty("rate", rate)

    def set_volume(self, volume: float):
        """Ajusta volumen (0.0 a 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        if self.engine:
            self.engine.setProperty("volume", self.volume)

    def set_voice(self, voice_id: int) -> str:
        """Cambia la voz por indice."""
        if not self.voices:
            return "No hay voces disponibles"
        if voice_id < 0 or voice_id >= len(self.voices):
            return f"ID invalido. Rango: 0 a {len(self.voices) - 1}"
        self.voice_id = voice_id
        if self.engine:
            self.engine.setProperty("voice", self.voices[voice_id].id)
        return f"Voz cambiada a: {self.voices[voice_id].name}"

    def list_voices(self) -> list:
        """Lista voces disponibles."""
        result = []
        for i, v in enumerate(self.voices):
            result.append({
                "id": i,
                "name": v.name,
                "lang": getattr(v, "languages", ["?"]),
            })
        return result

    @property
    def is_speaking(self) -> bool:
        return self._speaking


# ============================================================
# STT Engine — Speech to Text
# ============================================================
class STTEngine:
    """Motor de reconocimiento de voz offline usando vosk."""

    def __init__(self, model_path: str = "", lang: str = "es"):
        """
        Args:
            model_path: ruta al modelo vosk (si vacio, intenta descargar)
            lang: idioma (es, en)
        """
        self.available = False
        self.model = None
        self.recognizer = None
        self.lang = lang
        self.model_path = model_path
        self._listening = False

        self._init_engine()

    def _init_engine(self):
        """Inicializa vosk si esta disponible."""
        try:
            import vosk
            import sounddevice
            vosk.SetLogLevel(-1)  # Silenciar logs de vosk

            if self.model_path and __import__('os').path.isdir(self.model_path):
                self.model = vosk.Model(self.model_path)
                self.available = True
            else:
                # Sin modelo, queda como no disponible
                self.available = False
        except ImportError:
            self.available = False
        except Exception:
            self.available = False

    def listen(self, timeout: int = 10, sample_rate: int = 16000) -> Optional[str]:
        """
        Escucha del microfono y retorna texto reconocido.

        Args:
            timeout: segundos maximos de escucha
            sample_rate: frecuencia de muestreo

        Returns:
            Texto reconocido o None si falla
        """
        if not self.available:
            return None

        try:
            import vosk
            import sounddevice as sd
            import json as _json

            recognizer = vosk.KaldiRecognizer(self.model, sample_rate)
            result_queue = queue.Queue()
            self._listening = True

            def audio_callback(indata, frames, time_info, status):
                if status:
                    pass  # Ignorar warnings de audio
                result_queue.put(bytes(indata))

            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                start = time.time()
                text_parts = []

                while time.time() - start < timeout and self._listening:
                    try:
                        data = result_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if recognizer.AcceptWaveform(data):
                        result = _json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            text_parts.append(text)
                            break  # Frase completa detectada

                # Resultado final parcial
                if not text_parts:
                    final = _json.loads(recognizer.FinalResult())
                    text = final.get("text", "").strip()
                    if text:
                        text_parts.append(text)

                self._listening = False
                return " ".join(text_parts) if text_parts else None

        except Exception:
            self._listening = False
            return None

    def stop_listening(self):
        """Detiene la escucha activa."""
        self._listening = False

    @property
    def is_listening(self) -> bool:
        return self._listening


# ============================================================
# Voice System — integra TTS + STT
# ============================================================
class VoiceSystem:
    """Sistema de voz completo: habla y escucha."""

    def __init__(self, vosk_model_path: str = ""):
        self.tts = TTSEngine()
        self.stt = STTEngine(model_path=vosk_model_path)
        self.enabled = False
        self.tts_enabled = True
        self.stt_enabled = True

    def toggle(self) -> str:
        """Alterna voz on/off."""
        self.enabled = not self.enabled
        return f"Voz {'ACTIVADA' if self.enabled else 'DESACTIVADA'}"

    def speak(self, text: str, block: bool = False) -> bool:
        """Habla texto si la voz esta habilitada."""
        if not self.enabled or not self.tts_enabled:
            return False
        if not self.tts.available:
            return False
        # Limpiar texto para habla (quitar markdown, codigo, etc.)
        clean = self._clean_for_speech(text)
        if not clean:
            return False
        return self.tts.speak(clean, block=block)

    def listen(self, timeout: int = 10) -> Optional[str]:
        """Escucha del microfono si STT esta habilitado."""
        if not self.enabled or not self.stt_enabled:
            return None
        if not self.stt.available:
            return None
        return self.stt.listen(timeout=timeout)

    def status(self) -> str:
        """Estado del sistema de voz."""
        lines = [
            "=== Voice System ===",
            f"  Habilitado: {'SI' if self.enabled else 'NO'}",
            f"  TTS (pyttsx3): {'disponible' if self.tts.available else 'NO instalado (pip install pyttsx3)'}",
            f"    Voces: {len(self.tts.voices)}",
            f"    Rate: {self.tts.rate} | Vol: {self.tts.volume}",
            f"  STT (vosk): {'disponible' if self.stt.available else 'NO instalado (pip install vosk sounddevice)'}",
            f"    Idioma: {self.stt.lang}",
        ]
        return "\n".join(lines)

    def _clean_for_speech(self, text: str) -> str:
        """Limpia texto para que suene natural al hablarlo."""
        import re
        # Remover bloques de codigo
        text = re.sub(r'```[\s\S]*?```', ' codigo omitido ', text)
        # Remover inline code
        text = re.sub(r'`[^`]+`', '', text)
        # Remover URLs
        text = re.sub(r'https?://\S+', ' enlace ', text)
        # Remover markdown headers
        text = re.sub(r'#{1,6}\s*', '', text)
        # Remover bold/italic
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        # Remover separadores
        text = re.sub(r'[-=]{3,}', '', text)
        # Remover multiples espacios
        text = re.sub(r'\s+', ' ', text).strip()
        # Limitar longitud (no hablar textos enormes)
        if len(text) > 500:
            # Cortar en punto o coma cercano
            cut = text[:500].rfind('.')
            if cut > 200:
                text = text[:cut + 1]
            else:
                text = text[:500] + "..."
        return text
