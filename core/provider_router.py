"""
GENESIS ProviderRouter — Ruteo inteligente multi-provider con failover automatico.

Envuelve multiples instancias de Brain (ollama, gemini, openai, anthropic) y
decide cual usar en cada request segun:
  1. Disponibilidad (circuit breaker con cooldown automatico)
  2. Estrategia del usuario (local_first, quality_first, cost_first, speed_first)
  3. Clasificacion de la tarea (simple / coding / reasoning)

Diseno:
- Mismo contrato que Brain: think(), quick_think(), is_available(), get_stats()
- Drop-in replacement: el resto del codigo no cambia
- Telemetria: registra que provider atendio cada call

Filosofia: soberania progresiva. Por defecto usa ollama si esta corriendo.
Si no, cae a gemini (gratis). Si tampoco, openai/anthropic (pagos).

NOTA: distinto del ModelRouter (que enruta entre modelos GGUF locales).
Este ProviderRouter opera un nivel arriba — elige entre PROVIDERS.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from core.brain import Brain


# ==============================================================
# CIRCUIT BREAKER — evita reintentar providers caidos
# ==============================================================

class _CircuitBreaker:
    """
    Marca un provider como 'down' tras N fallos consecutivos.
    Tras cooldown, permite un request de prueba antes de volver a habilitarlo.
    """
    def __init__(self, failure_threshold: int = 3, cooldown_sec: int = 300):
        self.failure_threshold = failure_threshold
        self.cooldown_sec = cooldown_sec
        self._failures: dict[str, int] = {}
        self._down_until: dict[str, float] = {}

    def is_up(self, provider: str) -> bool:
        """True si el provider esta disponible (no en cooldown)."""
        down_ts = self._down_until.get(provider, 0)
        if down_ts == 0:
            return True
        if time.time() >= down_ts:
            # Cooldown expirado — dar una oportunidad mas
            self._failures[provider] = 0
            self._down_until[provider] = 0
            return True
        return False

    def record_success(self, provider: str):
        """Reset counter cuando un provider responde OK."""
        self._failures[provider] = 0
        self._down_until[provider] = 0

    def record_failure(self, provider: str):
        """Incrementa contador de fallos. Si supera umbral, marca down."""
        self._failures[provider] = self._failures.get(provider, 0) + 1
        if self._failures[provider] >= self.failure_threshold:
            self._down_until[provider] = time.time() + self.cooldown_sec

    def status(self) -> dict:
        """Estado actual del circuit breaker (para debug)."""
        now = time.time()
        return {
            p: {
                "failures": self._failures.get(p, 0),
                "down": self._down_until.get(p, 0) > now,
                "cooldown_remaining": max(0, int(self._down_until.get(p, 0) - now)),
            }
            for p in set(list(self._failures.keys()) + list(self._down_until.keys()))
        }


# ==============================================================
# TASK CLASSIFIER — clasifica requests para elegir provider
# ==============================================================

class _TaskClassifier:
    """
    Clasifica un prompt en una de tres categorias para elegir provider optimo.
    Heuristica simple basada en keywords y longitud — no usa LLM (seria recursivo).
    """
    _CODING_KW = ("python", "javascript", "codigo", "código", "funcion", "función",
                  "script", "refactor", "bug", "error", "stack trace", "exception",
                  "import", "class ", "def ", "const ", "let ", "var ", "async",
                  "html", "css", "sql", "query", "api", "endpoint", "regex")
    _REASONING_KW = ("analiza", "evalua", "evalúa", "compara", "propone", "propón",
                     "decide", "razona", "deduce", "explica por qué", "estrategia",
                     "auditoria", "auditoría", "plan completo", "arquitectura",
                     "diseña", "diseño de sistema", "pros y contras")

    @classmethod
    def classify(cls, messages: list[dict]) -> str:
        """
        Retorna: 'simple' | 'coding' | 'reasoning'
        Usado por el router para elegir provider segun estrategia.
        """
        text = " ".join(m.get("content", "") for m in messages).lower()
        if not text:
            return "simple"

        if any(k in text for k in cls._REASONING_KW) or len(text) > 3000:
            return "reasoning"
        if any(k in text for k in cls._CODING_KW):
            return "coding"
        return "simple"


# ==============================================================
# PROVIDER ROUTER — el Facade principal
# ==============================================================

class ProviderRouter:
    """
    Router multi-provider. Mismo contrato publico que Brain.

    Uso:
        router = ProviderRouter.from_config()
        response = router.think(system_prompt, messages)   # usa best provider
    """

    # Estrategias disponibles — ordenes de preferencia
    STRATEGIES = {
        "local_first": ["ollama", "gemini", "openai", "anthropic"],
        "quality_first": ["anthropic", "openai", "gemini", "ollama"],
        "cost_first": ["ollama", "gemini", "openai", "anthropic"],
        "speed_first": ["gemini", "ollama", "openai", "anthropic"],
    }

    def __init__(
        self,
        brains: dict[str, Brain],
        strategy: str = "local_first",
        enable_classifier: bool = True,
        ollama_model_by_task: Optional[dict] = None,
        ollama_url: str = "http://localhost:11434",
    ):
        """
        Args:
            brains: dict {provider_name: Brain_instance} de providers habilitados
            strategy: local_first | quality_first | cost_first | speed_first
            enable_classifier: si True, clasifica tareas para elegir provider
            ollama_model_by_task: dict {"coding": "qwen2.5-coder:7b", "default": "genesis"}
                Cuando el router elige ollama, usa el modelo correspondiente al task_type.
                None → usa siempre el modelo del Brain base.
            ollama_url: URL del servidor Ollama (usado para crear Brains on-demand).
        """
        if not brains:
            raise ValueError("ProviderRouter requiere al menos un Brain configurado")
        self.brains = brains
        self.strategy = strategy if strategy in self.STRATEGIES else "local_first"
        self.enable_classifier = enable_classifier
        self.breaker = _CircuitBreaker()
        # Multi-model Ollama
        self.ollama_model_by_task = ollama_model_by_task or {}
        self.ollama_url = ollama_url
        self._ollama_brain_cache: dict[str, Brain] = {}
        # Telemetria
        self.total_calls = 0
        self.calls_by_provider: dict[str, int] = {}
        self.calls_by_model: dict[str, int] = {}   # NEW: telemetria por modelo
        self.fallbacks_triggered = 0
        self._last_provider_used: Optional[str] = None
        self._last_model_used: Optional[str] = None

    # ------------------------------------------------------------
    # Factory — crea router desde config.py sin que genesis.py sepa
    # ------------------------------------------------------------
    @classmethod
    def from_config(cls) -> "ProviderRouter":
        """Construye router leyendo config.py. Incluye solo providers configurados."""
        from config import (
            LLM_MODELS, GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
            OLLAMA_URL,
        )
        brains: dict[str, Brain] = {}

        # Ollama: siempre intentamos construirlo (is_available detecta si esta corriendo)
        brains["ollama"] = Brain(
            provider="ollama",
            model=LLM_MODELS.get("ollama", "llama3.1"),
            ollama_url=OLLAMA_URL,
        )

        # Gemini: solo si hay API key
        if GOOGLE_API_KEY:
            brains["gemini"] = Brain(
                provider="gemini",
                model=LLM_MODELS.get("gemini", "gemini-2.0-flash"),
                google_key=GOOGLE_API_KEY,
            )

        # OpenAI: solo si hay API key
        if OPENAI_API_KEY:
            brains["openai"] = Brain(
                provider="openai",
                model=LLM_MODELS.get("openai", "gpt-4o"),
                openai_key=OPENAI_API_KEY,
            )

        # Anthropic: solo si hay API key
        if ANTHROPIC_API_KEY:
            brains["anthropic"] = Brain(
                provider="anthropic",
                model=LLM_MODELS.get("anthropic", "claude-sonnet-4-20250514"),
                anthropic_key=ANTHROPIC_API_KEY,
            )

        # Leer estrategia de config (opcional, default local_first)
        try:
            from config import LLM_STRATEGY
            strategy = LLM_STRATEGY
        except ImportError:
            strategy = "local_first"

        # Multi-model Ollama (opcional, default dict vacio = modelo unico)
        try:
            from config import OLLAMA_MODEL_BY_TASK
            ollama_model_by_task = OLLAMA_MODEL_BY_TASK
        except ImportError:
            ollama_model_by_task = {}

        return cls(
            brains,
            strategy=strategy,
            ollama_model_by_task=ollama_model_by_task,
            ollama_url=OLLAMA_URL,
        )

    # ------------------------------------------------------------
    # Multi-model Ollama: elige Brain segun task_type
    # ------------------------------------------------------------
    def _get_brain_for(self, provider: str, task_type: str) -> Brain:
        """
        Retorna el Brain a usar para un provider + task_type dados.

        Para Ollama con multi-model habilitado: elige modelo segun tarea
        (coding → qwen-coder, reasoning → genesis, etc.) y cachea la instancia.
        Para otros providers: retorna el Brain base tal cual.
        """
        base_brain = self.brains[provider]
        if provider != "ollama" or not self.ollama_model_by_task:
            return base_brain

        # Ollama con multi-model: pickear modelo segun task_type
        target_model = (
            self.ollama_model_by_task.get(task_type)
            or self.ollama_model_by_task.get("default")
            or base_brain.model
        )
        # Si el modelo es el mismo que el del Brain base, reusar esa instancia
        if target_model == base_brain.model:
            return base_brain
        # Cachear por nombre de modelo para no recrear Brain en cada request
        cache_key = target_model
        if cache_key not in self._ollama_brain_cache:
            self._ollama_brain_cache[cache_key] = Brain(
                provider="ollama",
                model=target_model,
                ollama_url=self.ollama_url,
            )
        return self._ollama_brain_cache[cache_key]

    # ------------------------------------------------------------
    # Core: decidir el orden de providers a probar
    # ------------------------------------------------------------
    def _pick_order(self, task_type: str) -> list[str]:
        """
        Retorna lista ordenada de providers a intentar, filtrada por:
          1. Disponibilidad fisica (circuit breaker UP)
          2. Estrategia del usuario
          3. Clasificacion de tarea (reasoning usa providers mejores)
        """
        # Estrategia base
        order = list(self.STRATEGIES.get(self.strategy, self.STRATEGIES["local_first"]))

        # Si es reasoning, priorizar providers mas potentes (anthropic, openai)
        if self.enable_classifier and task_type == "reasoning":
            premium = ["anthropic", "openai"]
            # Mover providers premium al frente si estan disponibles
            for p in reversed(premium):
                if p in order and p in self.brains:
                    order.remove(p)
                    order.insert(0, p)

        # Filtrar solo providers configurados Y con circuit breaker UP
        available = [
            p for p in order
            if p in self.brains and self.breaker.is_up(p)
        ]
        return available

    # ------------------------------------------------------------
    # API publica: misma firma que Brain.think()
    # ------------------------------------------------------------
    def think(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        stream_callback: Optional[Callable] = None,
    ) -> str:
        """
        Envia prompt al mejor provider disponible. Falla automaticamente al siguiente
        si el primero tiene error (timeout, 429, 500, etc.).
        """
        self.total_calls += 1
        task_type = (
            _TaskClassifier.classify(messages) if self.enable_classifier else "simple"
        )
        order = self._pick_order(task_type)

        if not order:
            return ("[ERROR] Ningun provider LLM disponible. Verifica que Ollama este "
                    "corriendo (ollama serve) o que haya alguna API key configurada.")

        last_error = None
        for i, provider in enumerate(order):
            # Seleccion de Brain (para ollama: usa modelo segun task_type)
            brain = self._get_brain_for(provider, task_type)
            # Healthcheck barato solo para ollama (HTTP ping local)
            # Providers con API key: no hacemos ping — costaria tokens
            if provider == "ollama" and not brain.is_available():
                self.breaker.record_failure(provider)
                continue
            try:
                response = brain.think(
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    stream_callback=stream_callback,
                )
                # Detectar errores retornados como string (patron de Brain)
                if isinstance(response, str) and response.startswith("[ERROR]"):
                    last_error = response
                    self.breaker.record_failure(provider)
                    if i < len(order) - 1:
                        self.fallbacks_triggered += 1
                    continue
                # Exito
                self.breaker.record_success(provider)
                self._last_provider_used = provider
                self._last_model_used = brain.model
                self.calls_by_provider[provider] = (
                    self.calls_by_provider.get(provider, 0) + 1
                )
                self.calls_by_model[brain.model] = (
                    self.calls_by_model.get(brain.model, 0) + 1
                )
                return response
            except Exception as e:
                last_error = f"[ERROR] {provider}: {e}"
                self.breaker.record_failure(provider)
                if i < len(order) - 1:
                    self.fallbacks_triggered += 1
                continue

        # Todos los providers fallaron
        return last_error or "[ERROR] Todos los providers fallaron sin mensaje especifico."

    def quick_think(
        self,
        prompt: str,
        system: str = "Responde de forma concisa.",
        temperature: float = 0.5,
    ) -> str:
        """Atajo compatible con Brain.quick_think()."""
        messages = [{"role": "user", "content": prompt}]
        return self.think(system, messages, temperature=temperature, max_tokens=512)

    def is_available(self) -> bool:
        """True si al menos un provider esta disponible."""
        for provider, brain in self.brains.items():
            if not self.breaker.is_up(provider):
                continue
            if provider == "ollama":
                if brain.is_available():
                    return True
            else:
                # Providers con API key: disponibles si la key existe
                if brain.is_available():
                    return True
        return False

    def get_stats(self) -> dict:
        """Telemetria: que providers atendieron cuantas calls."""
        return {
            "strategy": self.strategy,
            "total_calls": self.total_calls,
            "calls_by_provider": dict(self.calls_by_provider),
            "calls_by_model": dict(self.calls_by_model),
            "fallbacks_triggered": self.fallbacks_triggered,
            "last_provider_used": self._last_provider_used,
            "last_model_used": self._last_model_used,
            "circuit_breaker": self.breaker.status(),
            "providers_configured": list(self.brains.keys()),
            "ollama_model_by_task": dict(self.ollama_model_by_task),
            "ollama_models_cached": list(self._ollama_brain_cache.keys()),
        }

    # ------------------------------------------------------------
    # Pass-through: atributos que el resto del codigo accede en Brain
    # (provider, model, total_tokens_used)
    # ------------------------------------------------------------
    @property
    def provider(self) -> str:
        """Retorna el provider del ultimo call (o el primero si no hubo calls)."""
        return self._last_provider_used or next(iter(self.brains.keys()), "none")

    @property
    def model(self) -> str:
        """Retorna el modelo del provider activo."""
        p = self.provider
        if p in self.brains:
            return self.brains[p].model
        return "none"

    @property
    def total_tokens_used(self) -> int:
        """Suma de tokens usados por todos los providers."""
        return sum(b.total_tokens_used for b in self.brains.values())
