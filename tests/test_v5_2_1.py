"""
GENESIS Test Suite v5.2.1 — Voice/STT System Tests
Tests para la corrección del sistema de voz (STT + auto-send).

Cubre:
1. VoiceSystem initialization con modelo vosk
2. STTEngine availability check
3. TTSEngine basic functionality
4. Web UI STT endpoint structure
5. Vosk model file existence
6. Audio WAV header construction
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  ✓ {name}")
        passed += 1
    else:
        print(f"  ✗ {name}")
        failed += 1


# ============================================================
# 1. Voice Packages Installed
# ============================================================
print("\n--- Voice Packages ---")

test("vosk package importable", (lambda: (__import__('vosk'), True)[-1])() if True else False)
test("sounddevice package importable", (lambda: (__import__('sounddevice'), True)[-1])() if True else False)
test("pyttsx3 package importable", (lambda: (__import__('pyttsx3'), True)[-1])() if True else False)


# ============================================================
# 2. Vosk Model Existence
# ============================================================
print("\n--- Vosk Model ---")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(BASE, "models", "vosk-model-small-es")

test("vosk model directory exists", os.path.isdir(model_path))
test("vosk model has 'am' subdirectory", os.path.isdir(os.path.join(model_path, "am")))
test("vosk model has 'conf' subdirectory", os.path.isdir(os.path.join(model_path, "conf")))
test("vosk model has 'graph' subdirectory", os.path.isdir(os.path.join(model_path, "graph")))

# Test loading model
try:
    import vosk
    vosk.SetLogLevel(-1)
    model = vosk.Model(model_path)
    test("vosk model loads successfully", model is not None)
    rec = vosk.KaldiRecognizer(model, 16000)
    test("vosk recognizer creates with 16kHz", rec is not None)
except Exception as e:
    test(f"vosk model loads successfully (ERROR: {e})", False)
    test("vosk recognizer creates with 16kHz", False)


# ============================================================
# 3. VoiceSystem Initialization
# ============================================================
print("\n--- VoiceSystem ---")

from core.voice import VoiceSystem, STTEngine, TTSEngine

# Test STTEngine with model path
stt = STTEngine(model_path=model_path, lang="es")
test("STTEngine available with valid model path", stt.available)
test("STTEngine lang is 'es'", stt.lang == "es")
test("STTEngine model loaded", stt.model is not None)

# Test STTEngine without model path
stt_empty = STTEngine(model_path="", lang="es")
test("STTEngine NOT available without model path", not stt_empty.available)

# Test STTEngine with bad path
stt_bad = STTEngine(model_path="/nonexistent/path", lang="es")
test("STTEngine NOT available with bad path", not stt_bad.available)

# Test VoiceSystem full init
voice = VoiceSystem(vosk_model_path=model_path)
test("VoiceSystem STT available", voice.stt.available)
test("VoiceSystem enabled defaults to False", not voice.enabled)
test("VoiceSystem toggle works", voice.toggle() == "Voz ACTIVADA" and voice.enabled)
test("VoiceSystem toggle back", voice.toggle() == "Voz DESACTIVADA" and not voice.enabled)

# Test listen returns None when disabled
test("VoiceSystem listen returns None when disabled", voice.listen() is None)

# Test status output
status = voice.status()
test("VoiceSystem status includes STT info", "STT" in status)
test("VoiceSystem status includes TTS info", "TTS" in status)


# ============================================================
# 4. TTSEngine
# ============================================================
print("\n--- TTSEngine ---")

tts = TTSEngine()
test("TTSEngine initializes", tts is not None)
# On Windows with pyttsx3, should be available
test("TTSEngine available on Windows", tts.available)
test("TTSEngine default rate is 175", tts.rate == 175)
test("TTSEngine default volume is 0.9", tts.volume == 0.9)
test("TTSEngine has voices", len(tts.voices) > 0)
test("TTSEngine list_voices works", len(tts.list_voices()) > 0)

# Set rate/volume
tts.set_rate(200)
test("TTSEngine set_rate works", tts.rate == 200)
tts.set_volume(0.5)
test("TTSEngine set_volume works", tts.volume == 0.5)
tts.set_volume(1.5)  # Should clamp
test("TTSEngine set_volume clamps to 1.0", tts.volume == 1.0)

# Clean text for speech
voice_sys = VoiceSystem(vosk_model_path=model_path)
cleaned = voice_sys._clean_for_speech("# Titulo\n```python\nprint('hello')\n```\n**bold** text https://example.com")
test("Clean speech removes markdown headers", "#" not in cleaned)
test("Clean speech removes code blocks", "print" not in cleaned)
test("Clean speech removes URLs", "https" not in cleaned)
test("Clean speech removes bold markers", "**" not in cleaned)


# ============================================================
# 5. Genesis Voice Init with Model Path
# ============================================================
print("\n--- Genesis Voice Init ---")

genesis_path = os.path.join(BASE, "genesis.py")
with open(genesis_path, "r", encoding="utf-8") as f:
    genesis_src = f.read()

test("Genesis inits VoiceSystem with vosk model path",
     "vosk-model-small-es" in genesis_src and "vosk_model_path" in genesis_src)
test("Genesis references vosk_path variable",
     "vosk_path = str(BASE_DIR" in genesis_src)


# ============================================================
# 6. Web UI STT Endpoint
# ============================================================
print("\n--- Web UI STT Endpoint ---")

webui_path = os.path.join(BASE, "web_ui.py")
with open(webui_path, "r", encoding="utf-8") as f:
    webui_src = f.read()

test("Web UI has /api/stt endpoint", '"/api/stt"' in webui_src)
test("Web UI STT uses vosk", "vosk" in webui_src)
test("Web UI STT accepts POST", 'methods=["POST"]' in webui_src and "api_stt" in webui_src)
test("Web UI STT uses wave module", "wave.open" in webui_src)
test("Web UI STT caches vosk model", "_vosk_model" in webui_src)
test("Web UI STT reads audio from request.files", "request.files" in webui_src)
test("Web UI STT returns JSON text", '"text"' in webui_src)


# ============================================================
# 7. Web UI Frontend STT
# ============================================================
print("\n--- Frontend STT ---")

html_path = os.path.join(BASE, "templates", "index.html")
with open(html_path, "r", encoding="utf-8") as f:
    html_src = f.read()

test("Frontend has toggleSTT function", "function toggleSTT()" in html_src)
test("Frontend has startBrowserSTT", "function startBrowserSTT()" in html_src)
test("Frontend has startServerSTT", "async function startServerSTT()" in html_src)
test("Frontend has stopServerSTT", "async function stopServerSTT()" in html_src)
test("Frontend auto-sends after voice capture", "sendMessage()" in html_src and "sttAutoSend" in html_src)
test("Frontend continuous depends on hands-free", "continuous = handsFreeModeActive" in html_src or "handsFreeModeActive" in html_src)
test("Frontend has silence timer", "STT_SILENCE_MS" in html_src)
test("Frontend builds WAV header in JS", "writeStr(0, 'RIFF')" in html_src)
test("Frontend sends WAV to /api/stt", "'/api/stt'" in html_src)
test("Frontend captures PCM Int16", "Int16Array" in html_src)
test("Frontend has ScriptProcessor for audio capture", "createScriptProcessor" in html_src)
test("Frontend fallback to server on network error", "startServerSTT()" in html_src and "network" in html_src)
test("Frontend mic button exists", 'id="micBtn"' in html_src)
test("Frontend Ctrl+M shortcut", "Ctrl+M" in html_src or "key === 'm'" in html_src)

# Hands-free mode tests
test("Frontend has toggleHandsFree function", "function toggleHandsFree()" in html_src)
test("Frontend has handsFreeStartListening", "function handsFreeStartListening()" in html_src)
test("Frontend has handsFreeOnResponseComplete", "function handsFreeOnResponseComplete()" in html_src)
test("Frontend handsFreeModeActive variable", "let handsFreeModeActive = false" in html_src)
test("Frontend calls handsFreeOnResponseComplete after response", "handsFreeOnResponseComplete()" in html_src)
test("Frontend long-press activates hands-free", "micLongPressTimer" in html_src and "toggleHandsFree()" in html_src)
test("Frontend Ctrl+Shift+M shortcut", "Ctrl+Shift+M" in html_src or "e.shiftKey" in html_src)
test("Frontend hands-free CSS class", ".mic-btn.handsfree" in html_src)
test("Frontend hands-free LIVE badge", "content: 'LIVE'" in html_src)
test("Frontend continuous uses handsFreeModeActive", "recognition.continuous = handsFreeModeActive" in html_src)
test("Frontend auto-restarts listening in hands-free", "handsFreeStartListening()" in html_src)


# ============================================================
# 8. Audio Processing Validation
# ============================================================
print("\n--- Audio Processing ---")

import struct
import io
import wave

# Test creating a WAV file with vosk-compatible format
sample_rate = 16000
duration_s = 1
n_samples = sample_rate * duration_s

# Generate silence (all zeros) as Int16
pcm_data = b'\x00\x00' * n_samples

# Create WAV in memory
wav_buffer = io.BytesIO()
with wave.open(wav_buffer, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(pcm_data)

wav_buffer.seek(0)
test("WAV file created in memory", wav_buffer.getbuffer().nbytes > 44)

# Read back and verify
with wave.open(wav_buffer, 'rb') as wf:
    test("WAV channels = 1 (mono)", wf.getnchannels() == 1)
    test("WAV sample width = 2 (16-bit)", wf.getsampwidth() == 2)
    test("WAV framerate = 16000", wf.getframerate() == 16000)
    test("WAV frames = expected", wf.getnframes() == n_samples)

# Test vosk recognizer with silence (should return empty text)
wav_buffer.seek(0)
with wave.open(wav_buffer, 'rb') as wf:
    import vosk, json as _json
    vosk.SetLogLevel(-1)
    rec = vosk.KaldiRecognizer(vosk.Model(model_path), wf.getframerate())
    data = wf.readframes(wf.getnframes())
    rec.AcceptWaveform(data)
    result = _json.loads(rec.FinalResult())
    test("Vosk returns empty text for silence", result.get("text", "").strip() == "")


# ============================================================
print(f"\n{'='*60}")
print(f"RESULTADOS: {passed}/{passed+failed} passed, {failed} failed")
print(f"{'='*60}")

if failed > 0:
    sys.exit(1)
