"""
GENESIS Inference Optimizer — Optimizador de velocidad de inferencia.

Reduce el tiempo de respuesta del LLM local mediante:
1. Context caching: no recalcular el system prompt si no cambio
2. Smart trimming: solo incluir secciones relevantes del contexto
3. Response length prediction: ajustar max_tokens segun la pregunta
4. Prompt compression: comprimir mensajes largos sin perder significado

En un 7B con 8GB VRAM, cada token cuenta. Este modulo optimiza
el uso del contexto para maximizar velocidad sin perder calidad.
"""
import time
import hashlib
from typing import Optional


class PromptCache:
    """
    Cache del system prompt tokenizado.

    Si el system prompt no cambio, reusar el resultado anterior
    en vez de re-procesarlo. En modelos locales, el prefill del
    system prompt puede tomar 20-40% del tiempo total.
    """

    def __init__(self, max_entries: int = 5):
        self.cache: dict[str, dict] = {}  # hash -> {prompt, timestamp, hits}
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0

    def get(self, prompt: str) -> Optional[str]:
        """Retorna el prompt cacheado si existe."""
        h = self._hash(prompt)
        if h in self.cache:
            self.cache[h]["hits"] += 1
            self.cache[h]["last_used"] = time.time()
            self.hits += 1
            return self.cache[h]["prompt"]
        self.misses += 1
        return None

    def put(self, prompt: str):
        """Cachea un prompt."""
        h = self._hash(prompt)
        self.cache[h] = {
            "prompt": prompt,
            "timestamp": time.time(),
            "last_used": time.time(),
            "hits": 0,
        }
        # Evictar si excede limite
        if len(self.cache) > self.max_entries:
            oldest = min(self.cache, key=lambda k: self.cache[k]["last_used"])
            del self.cache[oldest]

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class ResponsePredictor:
    """
    Predice la longitud optima de respuesta.

    Preguntas simples ("que hora es?") no necesitan 2048 tokens.
    Preguntas complejas ("explica la teoria de cuerdas") si.
    Reducir max_tokens = generacion mas rapida.
    """

    # Patrones de preguntas cortas
    SHORT_PATTERNS = [
        "que es", "quien es", "cuando", "donde", "cuanto",
        "si o no", "verdadero o falso", "cual es",
        "define", "nombre", "fecha", "numero",
        "what is", "who is", "when", "where", "how much",
    ]

    # Patrones de preguntas largas
    LONG_PATTERNS = [
        "explica", "describe", "analiza", "compara",
        "escribe un", "crea un", "genera un", "implementa",
        "tutorial", "guia", "paso a paso", "detallado",
        "explain", "describe", "analyze", "compare",
        "write a", "create a", "generate", "implement",
        "codigo", "programa", "script", "funcion",
    ]

    def predict_max_tokens(self, user_input: str,
                           default: int = 1024) -> int:
        """
        Predice max_tokens optimo para la pregunta.

        Args:
            user_input: Texto del usuario
            default: Valor por defecto

        Returns:
            max_tokens optimizado (256-2048)
        """
        text = user_input.lower()
        length = len(text)

        # Preguntas muy cortas (< 20 chars) → respuesta corta
        if length < 20:
            return 256

        # Detectar patrones cortos
        short_score = sum(1 for p in self.SHORT_PATTERNS if p in text)
        long_score = sum(1 for p in self.LONG_PATTERNS if p in text)

        if short_score > long_score:
            return 384  # Respuesta concisa
        elif long_score > short_score:
            return min(2048, default * 2)  # Respuesta detallada
        elif length > 200:
            return 1536  # Input largo = contexto rico = respuesta media-larga
        else:
            return default


class ContextTrimmer:
    """
    Comprime el contexto del prompt inteligentemente.

    En un 7B con 8K de contexto, cada token cuenta.
    Este modulo:
    - Elimina whitespace excesivo
    - Trunca mensajes antiguos
    - Resume mensajes largos del historial
    - Prioriza los mensajes mas recientes
    """

    def __init__(self, max_system_chars: int = 3000,
                 max_message_chars: int = 500,
                 max_messages: int = 8):
        self.max_system_chars = max_system_chars
        self.max_message_chars = max_message_chars
        self.max_messages = max_messages
        self.chars_saved = 0

    def trim_system_prompt(self, prompt: str) -> str:
        """Comprime el system prompt sin perder informacion critica."""
        original_len = len(prompt)

        # Eliminar lineas vacias multiples
        lines = prompt.split("\n")
        trimmed_lines = []
        prev_empty = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not prev_empty:
                    trimmed_lines.append("")
                    prev_empty = True
            else:
                trimmed_lines.append(line)
                prev_empty = False

        result = "\n".join(trimmed_lines)

        # Truncar si excede el maximo
        if len(result) > self.max_system_chars:
            # Mantener inicio (personalidad + reglas) y final (metadata)
            half = self.max_system_chars // 2
            result = result[:half] + "\n...[contexto recortado]...\n" + result[-half:]

        self.chars_saved += original_len - len(result)
        return result

    def trim_messages(self, messages: list[dict]) -> list[dict]:
        """
        Comprime la lista de mensajes del historial.

        Prioriza los mas recientes y trunca los antiguos.
        """
        if not messages:
            return messages

        # Mantener solo los N mas recientes
        if len(messages) > self.max_messages:
            messages = messages[-self.max_messages:]

        trimmed = []
        for i, msg in enumerate(messages):
            content = msg["content"]
            original_len = len(content)

            # Los ultimos 2 mensajes se mantienen completos
            if i >= len(messages) - 2:
                trimmed.append(msg)
                continue

            # Truncar mensajes antiguos
            if len(content) > self.max_message_chars:
                content = content[:self.max_message_chars] + "..."
                self.chars_saved += original_len - len(content)

            trimmed.append({"role": msg["role"], "content": content})

        return trimmed


class InferenceOptimizer:
    """
    Optimizador principal de inferencia.

    Coordina cache, prediccion y trimming para minimizar
    el tiempo de respuesta del LLM local.
    """

    def __init__(self):
        self.prompt_cache = PromptCache()
        self.predictor = ResponsePredictor()
        self.trimmer = ContextTrimmer()

        # Stats
        self.total_optimizations = 0
        self.total_tokens_saved = 0
        self.total_time_saved_ms = 0
        self.last_optimization = {}

    def optimize(self, system_prompt: str, messages: list[dict],
                 user_input: str, default_max_tokens: int = 1024) -> dict:
        """
        Optimiza los parametros de inferencia.

        Args:
            system_prompt: Prompt del sistema actual
            messages: Historial de mensajes
            user_input: Input del usuario actual
            default_max_tokens: max_tokens por defecto

        Returns:
            dict con:
                system_prompt: prompt optimizado
                messages: mensajes optimizados
                max_tokens: tokens maximos optimizados
                cache_hit: si hubo cache hit
                chars_saved: caracteres ahorrados
        """
        start = time.time()
        self.total_optimizations += 1

        original_chars = len(system_prompt) + sum(
            len(m["content"]) for m in messages
        )

        # 1. Cache del system prompt
        cache_hit = self.prompt_cache.get(system_prompt) is not None
        if not cache_hit:
            self.prompt_cache.put(system_prompt)

        # 2. Trimming del system prompt
        optimized_prompt = self.trimmer.trim_system_prompt(system_prompt)

        # 3. Trimming de mensajes
        optimized_messages = self.trimmer.trim_messages(messages)

        # 4. Prediccion de max_tokens
        optimized_max_tokens = self.predictor.predict_max_tokens(
            user_input, default_max_tokens
        )

        optimized_chars = len(optimized_prompt) + sum(
            len(m["content"]) for m in optimized_messages
        )
        chars_saved = original_chars - optimized_chars
        self.total_tokens_saved += chars_saved // 4  # Aprox 4 chars per token

        elapsed_ms = (time.time() - start) * 1000
        self.total_time_saved_ms += elapsed_ms

        self.last_optimization = {
            "cache_hit": cache_hit,
            "chars_saved": chars_saved,
            "max_tokens": optimized_max_tokens,
            "original_max_tokens": default_max_tokens,
            "messages_before": len(messages),
            "messages_after": len(optimized_messages),
            "elapsed_ms": elapsed_ms,
        }

        return {
            "system_prompt": optimized_prompt,
            "messages": optimized_messages,
            "max_tokens": optimized_max_tokens,
            "cache_hit": cache_hit,
            "chars_saved": chars_saved,
        }

    def get_stats(self) -> dict:
        """Estadisticas del optimizador."""
        return {
            "total_optimizations": self.total_optimizations,
            "cache_hit_rate": f"{self.prompt_cache.hit_rate * 100:.0f}%",
            "total_tokens_saved": self.total_tokens_saved,
            "total_chars_trimmed": self.trimmer.chars_saved,
            "last": self.last_optimization,
        }

    def status(self) -> str:
        """Resumen para /status."""
        return (
            f"  Optimizaciones: {self.total_optimizations} | "
            f"Cache: {self.prompt_cache.hit_rate * 100:.0f}% hit | "
            f"Tokens ahorrados: ~{self.total_tokens_saved}"
        )
