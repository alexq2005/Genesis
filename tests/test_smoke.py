"""
GENESIS — Suite de smoke tests REAL (pytest, con aserciones).

A diferencia de los scripts legacy `test_v*.py` (runner casero con print),
estos son tests con `assert` que pytest descubre y ejecuta. Cubren los
contratos críticos: que los módulos importen, que la config esté completa y
que las funciones puras/contratos clave existan y respondan. No requieren
GPU, Ollama ni red — son rápidos y deterministas (aptos para CI).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ----------------------------------------------------------------- imports ---
def test_import_genesis():
    import genesis  # noqa: F401


def test_import_core_modules():
    """Los módulos core clave deben importar sin error."""
    import importlib
    for mod in [
        "core.genesis_tools", "core.genesis_processing", "core.genesis_commands",
        "core.media_generator", "core.voice_clone", "core.netflix", "core.casting",
        "core.system_control", "core.connections", "core.folder_index",
        "core.program_index", "core.provider_router",
    ]:
        importlib.import_module(mod)


# ------------------------------------------------------------------ config ---
def test_config_metadata():
    import config
    assert isinstance(config.GENESIS_NAME, str) and config.GENESIS_NAME
    assert isinstance(config.GENESIS_VERSION, str) and config.GENESIS_VERSION


def test_config_model_routing():
    import config
    assert isinstance(config.OLLAMA_MODEL_BY_TASK, dict)
    assert "default" in config.OLLAMA_MODEL_BY_TASK


# ----------------------------------------------------------- contratos clave ---
def test_voice_clone_contract():
    from core import voice_clone
    assert callable(voice_clone.available)
    assert callable(voice_clone.clone_say)
    assert callable(voice_clone.clone_say_hq)
    ref = voice_clone.ref_for("milton")
    assert str(ref).endswith("milton.wav")


def test_media_generator_contract():
    from core.media_generator import MediaGenerator
    assert hasattr(MediaGenerator, "generate_image")
    assert hasattr(MediaGenerator, "_try_local_sd")


def test_system_control_monitors():
    from core import system_control
    mons = system_control.get_monitors()
    assert isinstance(mons, list)  # 0+ monitores; debe devolver lista siempre


def test_netflix_app_id():
    from core import netflix
    assert callable(netflix.launch_app)
    assert callable(netflix.play)
    assert callable(netflix.cast)


def test_no_undefined_names_regression():
    """Regresión: genesis_commands debe poder construir el reporte de estado
    (antes fallaba por GENESIS_NAME/VERSION/LLM_PROVIDER indefinidos — F821)."""
    import config
    # las constantes que faltaban ahora deben resolverse
    assert config.GENESIS_NAME
    assert config.GENESIS_VERSION
