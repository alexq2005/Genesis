"""
GENESIS — Clonación de voz (XTTS-v2 / Coqui, local en GPU).

Clona una voz a partir de una muestra de referencia (`speaker_wav`) y sintetiza
texto en español con ese timbre. 100% local (tras bajar el modelo ~1.8GB la
primera vez). Pensado para uso PERSONAL — XTTS-v2 usa licencia CPML (no comercial)
y clonar una voz real solo es aceptable para uso privado, NO para distribuir.

Uso:
    from core import voice_clone
    voice_clone.clone_say("Hola, señor.", "data/voices/milton.wav", "out.wav")
"""
import os
from pathlib import Path

# Aceptar la licencia CPML de XTTS sin prompt interactivo (uso personal).
os.environ.setdefault("COQUI_TOS_AGREED", "1")

_BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VOICES_DIR = _BASE / "data" / "voices"
_VOICES_DIR.mkdir(parents=True, exist_ok=True)

_XTTS = None  # pipeline cacheado (se carga 1 vez en VRAM)
_PATCHED = False


def _patch_transformers():
    """coqui-tts importa `isin_mps_friendly` de transformers.pytorch_utils, que
    transformers 5.x eliminó. Inyectamos el símbolo (shim) para no downgradear
    transformers y NO romper SD/embeddings."""
    global _PATCHED
    if _PATCHED:
        return
    try:
        import transformers.pytorch_utils as ptu
        if not hasattr(ptu, "isin_mps_friendly"):
            def isin_mps_friendly(elements, test_elements):
                import torch
                if getattr(elements, "device", None) is not None and elements.device.type == "mps":
                    test_elements = test_elements.to(elements.device)
                    return (elements.tile(test_elements.shape[0], 1)
                            .eq(test_elements.unsqueeze(1)).sum(dim=0).bool().squeeze())
                return torch.isin(elements, test_elements)
            ptu.isin_mps_friendly = isin_mps_friendly
        _PATCHED = True
    except Exception:
        pass


def available() -> bool:
    """True si XTTS (coqui-tts) está instalado y se puede importar."""
    _patch_transformers()
    try:
        import TTS  # noqa: F401
        return True
    except Exception:
        return False


def _load():
    """Carga XTTS-v2 (en GPU si hay, si no CPU). Cacheado."""
    global _XTTS
    if _XTTS is not None:
        return _XTTS
    _patch_transformers()
    from TTS.api import TTS
    try:
        import torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        dev = "cpu"
    _XTTS = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(dev)
    return _XTTS


def clone_say(text: str, speaker_wav: str, out_path: str,
              language: str = "es") -> dict:
    """Sintetiza `text` con el timbre de `speaker_wav`. Devuelve dict con path/ok."""
    if not available():
        return {"ok": False, "error": "XTTS (coqui-tts) no está instalado."}
    ref = Path(speaker_wav)
    if not ref.exists():
        return {"ok": False, "error": f"No encuentro la muestra de voz: {speaker_wav}"}
    try:
        import time
        t = time.time()
        tts = _load()
        tts.tts_to_file(text=text, speaker_wav=str(ref),
                        language=language, file_path=str(out_path))
        return {"ok": True, "path": str(out_path),
                "time_s": round(time.time() - t, 1),
                "method": "xtts-v2-clone (GPU)"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def clone_say_hq(text: str, speaker_wav: str, out_path: str, language: str = "es",
                 temperature: float = 0.65, gpt_cond_len: int = 30) -> dict:
    """Clonación de ALTA FIDELIDAD: API de bajo nivel de XTTS.
    Usa TODA la muestra para condicionar (gpt_cond_len grande) y temperatura
    ajustable (más baja = más fiel/estable). Mejor que clone_say (defaults)."""
    if not available():
        return {"ok": False, "error": "XTTS no está instalado."}
    if not Path(speaker_wav).exists():
        return {"ok": False, "error": f"No encuentro la muestra: {speaker_wav}"}
    try:
        import time
        import torch
        import torchaudio
        t = time.time()
        tts = _load()
        model = tts.synthesizer.tts_model  # instancia Xtts
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=[speaker_wav], gpt_cond_len=gpt_cond_len,
            max_ref_length=gpt_cond_len)
        out = model.inference(
            text, language, gpt_cond_latent, speaker_embedding,
            temperature=temperature, repetition_penalty=5.0,
            length_penalty=1.0, enable_text_splitting=True)
        wav = torch.tensor(out["wav"]).unsqueeze(0)
        torchaudio.save(str(out_path), wav, 24000)
        return {"ok": True, "path": str(out_path), "time_s": round(time.time() - t, 1),
                "method": f"xtts-hq (cond={gpt_cond_len}s, temp={temperature})"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ref_for(name: str) -> Path:
    """Ruta esperada de la muestra de una voz por nombre (ej: 'milton')."""
    return _VOICES_DIR / f"{name}.wav"
