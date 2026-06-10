"""
Test end-to-end con Ollama REAL (requiere Qwen 2.5 Coder + Genesis instalados).

Valida que:
  - Prompt de coding ruta a qwen2.5-coder:7b
  - Prompt general ruta a genesis (llama 3.1 custom)
  - Stats reflejan el cambio de modelo

Uso: python tests/test_qwen_e2e.py
Prerequisitos:
  - ollama serve corriendo
  - ollama pull qwen2.5-coder:7b
  - ollama pull genesis (o cualquier modelo definido en OLLAMA_MODEL_BY_TASK)
"""
import sys, os, time, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.provider_router import ProviderRouter


def list_ollama_models():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            data = json.loads(r.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception as e:
        return []


def main():
    print("=" * 60)
    print(" GENESIS Phase 1 — E2E Test: Multi-Model Ollama")
    print("=" * 60)

    models = list_ollama_models()
    print(f"\n[SETUP] Modelos en Ollama: {models}")

    qwen_present = any("qwen2.5-coder" in m for m in models)
    genesis_present = any(m.startswith("genesis") for m in models)
    if not qwen_present:
        print("[SKIP] qwen2.5-coder:7b no esta descargado. Run: ollama pull qwen2.5-coder:7b")
        return 2
    if not genesis_present:
        print("[SKIP] genesis no esta descargado. Run: ollama pull llama3.1 && tag as genesis")
        return 2

    print("\n[1] Instanciando router...")
    r = ProviderRouter.from_config()
    print(f"    Providers: {list(r.brains.keys())}")
    print(f"    Model by task: {r.ollama_model_by_task}")

    print("\n[2] Prompt de CODING (deberia usar qwen-coder)...")
    t0 = time.time()
    resp_code = r.think(
        system_prompt="Eres un asistente de codigo. Responde solo con codigo, sin explicacion.",
        messages=[{"role": "user",
                   "content": "Escribe una funcion Python llamada factorial(n) que calcule el factorial iterativo. Solo codigo."}],
        temperature=0.1,
        max_tokens=200,
    )
    dt_code = time.time() - t0
    print(f"    Modelo usado: {r._last_model_used}")
    print(f"    Latencia: {dt_code:.1f}s")
    print(f"    Respuesta (primeros 200 chars):\n      {resp_code[:200]!r}")

    print("\n[3] Prompt GENERAL (deberia usar genesis)...")
    t0 = time.time()
    resp_gen = r.think(
        system_prompt="Eres Genesis. Responde breve.",
        messages=[{"role": "user", "content": "Que es la soberania digital en 1 oracion?"}],
        temperature=0.5,
        max_tokens=100,
    )
    dt_gen = time.time() - t0
    print(f"    Modelo usado: {r._last_model_used}")
    print(f"    Latencia: {dt_gen:.1f}s")
    print(f"    Respuesta (primeros 200 chars):\n      {resp_gen[:200]!r}")

    print("\n[4] Stats finales:")
    stats = r.get_stats()
    for k in ("strategy", "total_calls", "calls_by_provider", "calls_by_model",
              "last_model_used", "ollama_models_cached"):
        print(f"    {k}: {stats.get(k)}")

    # Validaciones (substring match sobre keys del dict)
    print("\n[VALIDACION]")
    ok = True
    models_called = list((r.calls_by_model or {}).keys())
    used_qwen = any("qwen" in m for m in models_called)
    used_genesis = any("genesis" in m or "llama" in m for m in models_called)
    if not used_qwen:
        print(f"    FAIL: coding prompt no uso qwen. models_called={models_called}")
        ok = False
    else:
        print("    OK: coding prompt ruto a qwen2.5-coder")
    if not used_genesis:
        print(f"    FAIL: general prompt no uso genesis. models_called={models_called}")
        ok = False
    else:
        print("    OK: general prompt ruto a genesis")

    print("\n" + "=" * 60)
    print(" RESULT:", "PASS" if ok else "FAIL")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
