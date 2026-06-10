"""
Tests para ProviderRouter — Phase 0 Multi-provider routing
Cubre: circuit breaker, task classifier, failover automatico, from_config.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.provider_router import ProviderRouter, _CircuitBreaker, _TaskClassifier

passed = 0
failed = 0
errors = []

def test(name, condition):
    global passed, failed, errors
    try:
        if condition:
            passed += 1
        else:
            failed += 1
            errors.append(f"FAIL: {name}")
            print(f"  FAIL: {name}")
    except Exception as e:
        failed += 1
        errors.append(f"ERROR: {name}: {e}")
        print(f"  ERROR: {name}: {e}")


# ============================================================
# FakeBrain — stub para simular providers sin hacer HTTP
# ============================================================

class FakeBrain:
    """Stub que imita la interfaz de Brain para tests aislados."""
    def __init__(self, provider="fake", model="fake-model",
                 fail=False, fail_count=0, delay=0.0, available=True):
        self.provider = provider
        self.model = model
        self.fail = fail
        self.fail_count = fail_count  # falla las primeras N veces
        self.calls = 0
        self.delay = delay
        self._available = available
        self.total_tokens_used = 0

    def is_available(self):
        return self._available

    def think(self, system_prompt, messages, temperature=0.7,
              max_tokens=2048, stream=False, stream_callback=None):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            return f"[ERROR] {self.provider} caido"
        if self.fail_count > 0:
            self.fail_count -= 1
            return f"[ERROR] {self.provider} intermitente"
        self.total_tokens_used += 10
        return f"OK desde {self.provider}"

    def quick_think(self, prompt, system="", temperature=0.5):
        return self.think(system, [{"role": "user", "content": prompt}])

    def get_stats(self):
        return {"provider": self.provider, "calls": self.calls}


# ============================================================
# 1. CircuitBreaker
# ============================================================

print("\n[1/4] CircuitBreaker...")
cb = _CircuitBreaker(failure_threshold=3, cooldown_sec=1)
test("Nuevo provider arranca UP", cb.is_up("ollama") is True)

cb.record_failure("ollama")
cb.record_failure("ollama")
test("Tras 2 fallos sigue UP", cb.is_up("ollama") is True)

cb.record_failure("ollama")
test("Tras 3 fallos pasa a DOWN", cb.is_up("ollama") is False)

status = cb.status()
test("Status reporta failures correctamente", status["ollama"]["failures"] == 3)
test("Status reporta down=True", status["ollama"]["down"] is True)

cb.record_success("gemini")
test("record_success no activa DOWN en otros providers", cb.is_up("gemini") is True)

# Cooldown
time.sleep(1.1)
test("Tras cooldown vuelve a UP automaticamente", cb.is_up("ollama") is True)

# Reset de counter tras éxito
cb.record_failure("openai")
cb.record_failure("openai")
cb.record_success("openai")
test("record_success resetea contador", cb.status().get("openai", {}).get("failures", -1) == 0)


# ============================================================
# 2. TaskClassifier
# ============================================================

print("\n[2/4] TaskClassifier...")

def msgs(text):
    return [{"role": "user", "content": text}]

test("Texto vacio → simple",
     _TaskClassifier.classify([]) == "simple")
test("'hola que tal' → simple",
     _TaskClassifier.classify(msgs("hola que tal")) == "simple")
test("'dame un script de python' → coding",
     _TaskClassifier.classify(msgs("dame un script de python")) == "coding")
test("'hay un bug en mi funcion' → coding",
     _TaskClassifier.classify(msgs("hay un bug en mi funcion")) == "coding")
test("'analiza los pros y contras' → reasoning",
     _TaskClassifier.classify(msgs("analiza los pros y contras de migrar a Rust")) == "reasoning")
test("'diseña la arquitectura del sistema' → reasoning",
     _TaskClassifier.classify(msgs("diseña la arquitectura del sistema completo")) == "reasoning")
test("Texto muy largo (>3000) → reasoning",
     _TaskClassifier.classify(msgs("x " * 2000)) == "reasoning")


# ============================================================
# 3. ProviderRouter — failover automatico
# ============================================================

print("\n[3/4] ProviderRouter failover...")

# Caso 1: Ollama cae, Gemini responde
ollama = FakeBrain(provider="ollama", fail=True)
gemini = FakeBrain(provider="gemini")
router = ProviderRouter(
    brains={"ollama": ollama, "gemini": gemini},
    strategy="local_first",
    enable_classifier=False,
)
response = router.think("sys", msgs("hola"))
test("Failover: ollama caido → gemini responde",
     response == "OK desde gemini")
test("Ollama fue intentado primero", ollama.calls == 1)
test("Gemini fue segundo intento", gemini.calls == 1)
test("fallbacks_triggered incrementado",
     router.fallbacks_triggered >= 1)
test("last_provider_used = gemini",
     router._last_provider_used == "gemini")

# Caso 2: todos caidos → error explicito
ollama2 = FakeBrain(provider="ollama", fail=True)
gemini2 = FakeBrain(provider="gemini", fail=True)
router2 = ProviderRouter(
    brains={"ollama": ollama2, "gemini": gemini2},
    strategy="local_first",
    enable_classifier=False,
)
resp2 = router2.think("sys", msgs("hola"))
test("Todos caidos → respuesta [ERROR]",
     resp2.startswith("[ERROR]"))

# Caso 3: provider intermitente (falla 2, ok 3ra)
intermit = FakeBrain(provider="ollama", fail_count=5)
# circuit breaker: 3 fallos → down. Probamos que se cae.
router3 = ProviderRouter(
    brains={"ollama": intermit, "gemini": FakeBrain(provider="gemini")},
    strategy="local_first",
    enable_classifier=False,
)
# Primera call: ollama falla, gemini responde
router3.think("sys", msgs("test 1"))
# Segunda: ollama falla otra vez
router3.think("sys", msgs("test 2"))
# Tercera: ollama deberia estar DOWN tras 3 failures, router salta directo a gemini
router3.think("sys", msgs("test 3"))
router3.think("sys", msgs("test 4"))
# Tras 3 fallos consecutivos de ollama, el breaker deberia marcarlo down
cb_status = router3.breaker.status()
test("Circuit breaker registra fallos de ollama",
     cb_status.get("ollama", {}).get("failures", 0) >= 3 or
     cb_status.get("ollama", {}).get("down", False) is True)


# ============================================================
# 4. ProviderRouter — estrategias y stats
# ============================================================

print("\n[4/4] ProviderRouter estrategias...")

# quality_first deberia probar anthropic primero
brains = {
    "ollama": FakeBrain(provider="ollama"),
    "gemini": FakeBrain(provider="gemini"),
    "anthropic": FakeBrain(provider="anthropic"),
}
router_q = ProviderRouter(brains=brains, strategy="quality_first",
                          enable_classifier=False)
r = router_q.think("sys", msgs("hola"))
test("quality_first: anthropic responde primero",
     r == "OK desde anthropic")
test("quality_first: ollama no fue llamado",
     brains["ollama"].calls == 0)

# speed_first deberia probar gemini primero
brains2 = {
    "ollama": FakeBrain(provider="ollama"),
    "gemini": FakeBrain(provider="gemini"),
}
router_s = ProviderRouter(brains=brains2, strategy="speed_first",
                          enable_classifier=False)
r2 = router_s.think("sys", msgs("hola"))
test("speed_first: gemini responde primero",
     r2 == "OK desde gemini")

# Stats
stats = router_s.get_stats()
test("get_stats retorna strategy", stats["strategy"] == "speed_first")
test("get_stats retorna total_calls", stats["total_calls"] == 1)
test("get_stats retorna calls_by_provider",
     stats["calls_by_provider"].get("gemini") == 1)

# Task classifier prioriza premium para reasoning
brains3 = {
    "ollama": FakeBrain(provider="ollama"),
    "gemini": FakeBrain(provider="gemini"),
    "anthropic": FakeBrain(provider="anthropic"),
}
router_c = ProviderRouter(brains=brains3, strategy="local_first",
                          enable_classifier=True)
r3 = router_c.think("sys", msgs("analiza los pros y contras de esta arquitectura"))
test("Classifier: reasoning → anthropic primero aunque strategy=local_first",
     r3 == "OK desde anthropic")

# is_available con todos down
brains4 = {"ollama": FakeBrain(provider="ollama", available=False)}
router_x = ProviderRouter(brains=brains4, strategy="local_first")
test("is_available: ollama no corriendo → False",
     router_x.is_available() is False)

# Validacion: ProviderRouter con brains vacio explota
try:
    ProviderRouter(brains={})
    test("Brains vacio debe lanzar ValueError", False)
except ValueError:
    test("Brains vacio lanza ValueError", True)

# Pass-through properties
router_p = ProviderRouter(brains={"ollama": FakeBrain(provider="ollama", model="genesis")},
                          strategy="local_first")
router_p.think("sys", msgs("hola"))
test("Property provider retorna ultimo usado",
     router_p.provider == "ollama")
test("Property model retorna modelo del provider activo",
     router_p.model == "genesis")
test("Property total_tokens_used suma tokens",
     router_p.total_tokens_used == 10)


# ============================================================
# 5. Multi-model Ollama (Phase 1)
# ============================================================

print("\n[5/5] Multi-model Ollama...")

# Caso 1: sin ollama_model_by_task → usa modelo base
base_brain = FakeBrain(provider="ollama", model="genesis")
router_mm = ProviderRouter(
    brains={"ollama": base_brain},
    strategy="local_first",
    enable_classifier=False,
)
chosen = router_mm._get_brain_for("ollama", "coding")
test("Sin multi-model config: usa Brain base",
     chosen is base_brain)

# Caso 2: con ollama_model_by_task → cachea brains por modelo
# Monkeypatch Brain constructor a FakeBrain para no hacer HTTP real
import core.provider_router as pr
original_Brain = pr.Brain

class FakeBrainCompat(FakeBrain):
    def __init__(self, provider="ollama", model="genesis",
                 ollama_url="http://localhost:11434", **kw):
        super().__init__(provider=provider, model=model)
        self.ollama_url = ollama_url

pr.Brain = FakeBrainCompat

try:
    router_mm2 = ProviderRouter(
        brains={"ollama": FakeBrain(provider="ollama", model="genesis")},
        strategy="local_first",
        enable_classifier=True,
        ollama_model_by_task={
            "coding": "qwen2.5-coder:7b",
            "reasoning": "genesis",
            "default": "genesis",
        },
        ollama_url="http://localhost:11434",
    )
    b_coding = router_mm2._get_brain_for("ollama", "coding")
    b_default = router_mm2._get_brain_for("ollama", "default")
    b_reason = router_mm2._get_brain_for("ollama", "reasoning")

    test("Multi-model: coding usa qwen-coder",
         b_coding.model == "qwen2.5-coder:7b")
    test("Multi-model: default usa genesis",
         b_default.model == "genesis")
    test("Multi-model: reasoning usa genesis (misma instancia base)",
         b_reason.model == "genesis")
    test("Multi-model: cache registra qwen-coder",
         "qwen2.5-coder:7b" in router_mm2._ollama_brain_cache)
    test("Multi-model: NO cachea genesis (reusa Brain base)",
         "genesis" not in router_mm2._ollama_brain_cache)

    # Cacheo: pedir dos veces → misma instancia
    b_coding2 = router_mm2._get_brain_for("ollama", "coding")
    test("Cache: segunda llamada retorna misma instancia",
         b_coding is b_coding2)

    # Task desconocido → usa default
    b_unknown = router_mm2._get_brain_for("ollama", "tarea_inexistente")
    test("Task desconocido cae a 'default'",
         b_unknown.model == "genesis")

    # think() integrado: prompt de coding usa qwen-coder
    router_mm3 = ProviderRouter(
        brains={"ollama": FakeBrain(provider="ollama", model="genesis")},
        strategy="local_first",
        enable_classifier=True,
        ollama_model_by_task={
            "coding": "qwen2.5-coder:7b",
            "default": "genesis",
        },
        ollama_url="http://localhost:11434",
    )
    router_mm3.think("sys", msgs("tengo un bug en mi funcion de python"))
    test("think(coding prompt) registra calls_by_model en qwen-coder",
         router_mm3.calls_by_model.get("qwen2.5-coder:7b") == 1)
    test("think(coding prompt) setea last_model_used",
         router_mm3._last_model_used == "qwen2.5-coder:7b")

    # Prompt general usa genesis
    router_mm3.think("sys", msgs("como estas hoy"))
    test("think(general prompt) registra calls_by_model en genesis",
         router_mm3.calls_by_model.get("genesis") == 1)

    # get_stats expone todo
    stats_mm = router_mm3.get_stats()
    test("Stats expone calls_by_model",
         "calls_by_model" in stats_mm)
    test("Stats expone last_model_used",
         stats_mm["last_model_used"] == "genesis")
    test("Stats expone ollama_model_by_task",
         stats_mm["ollama_model_by_task"]["coding"] == "qwen2.5-coder:7b")
finally:
    pr.Brain = original_Brain


# ============================================================
# Reporte final
# ============================================================

print("\n" + "=" * 60)
print(f"  PASSED: {passed}")
print(f"  FAILED: {failed}")
if errors:
    print("\nErrores:")
    for e in errors:
        print(f"  - {e}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
