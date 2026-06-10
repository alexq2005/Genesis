from __future__ import annotations
"""
GENESIS Rate Limiter — Control de uso de recursos con Token Bucket.

Problema:
Sin control de tasa, un bucle de auto-evolucion o tool execution puede
consumir toda la GPU/RAM en segundos. Tambien previene abuso cuando
Genesis corre como servicio (Web UI).

Solucion:
Token Bucket algorithm para cada recurso (inferencia LLM, tool exec,
API calls). Cada bucket se llena a tasa constante y se consume por uso.
Si no hay tokens disponibles, la accion se rechaza o se espera.

Uso:
    limiter = RateLimiter()
    if limiter.allow("inference"):
        # Hacer inferencia
        limiter.consume("inference")
    else:
        # Rate limited
        wait_time = limiter.wait_time("inference")
"""
import time
from typing import Optional
from pathlib import Path


class TokenBucket:
    """
    Token Bucket para rate limiting.

    El bucket se llena a una tasa constante (tokens_per_second).
    Cada accion consume tokens. Si el bucket esta vacio, se rechaza.
    """

    def __init__(self, capacity: int, refill_rate: float,
                 name: str = "default"):
        """
        Args:
            capacity: Tokens maximos en el bucket
            refill_rate: Tokens que se agregan por segundo
            name: Nombre identificador del bucket
        """
        self.name = name
        self.capacity = max(1, capacity)
        self.refill_rate = max(0.01, refill_rate)
        self.tokens = float(capacity)  # Empieza lleno
        self.last_refill = time.time()

        # Stats
        self.total_consumed = 0
        self.total_rejected = 0

    def _refill(self):
        """Rellena tokens segun el tiempo transcurrido."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate,
        )
        self.last_refill = now

    def allow(self, cost: int = 1) -> bool:
        """Verifica si hay tokens disponibles sin consumir."""
        self._refill()
        return self.tokens >= cost

    def consume(self, cost: int = 1) -> bool:
        """
        Consume tokens si estan disponibles.

        Returns:
            True si se consumieron, False si no hay suficientes
        """
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            self.total_consumed += cost
            return True
        self.total_rejected += 1
        return False

    def wait_time(self, cost: int = 1) -> float:
        """Tiempo en segundos para que haya suficientes tokens."""
        self._refill()
        if self.tokens >= cost:
            return 0.0
        deficit = cost - self.tokens
        return deficit / self.refill_rate

    def reset(self):
        """Resetea el bucket a capacidad completa."""
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def get_stats(self) -> dict:
        """Estadisticas del bucket."""
        self._refill()
        return {
            "name": self.name,
            "tokens": round(self.tokens, 1),
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "total_consumed": self.total_consumed,
            "total_rejected": self.total_rejected,
            "fill_percent": round((self.tokens / self.capacity) * 100, 1),
        }


class CooldownTracker:
    """
    Tracker de cooldowns para acciones especificas.

    Previene acciones repetidas muy rapido (ej: auto-evolucion
    no deberia correr mas de 1 vez por minuto).
    """

    def __init__(self):
        self._cooldowns: dict[str, float] = {}  # {action: expiry_time}
        self._durations: dict[str, float] = {}  # {action: cooldown_secs}

    def set_cooldown(self, action: str, seconds: float):
        """Configura el cooldown para una accion."""
        self._durations[action] = seconds

    def start_cooldown(self, action: str, seconds: float = 0):
        """Inicia el cooldown para una accion."""
        if seconds <= 0:
            seconds = self._durations.get(action, 60.0)
        self._cooldowns[action] = time.time() + seconds

    def is_ready(self, action: str) -> bool:
        """Verifica si una accion puede ejecutarse (cooldown expirado)."""
        if action not in self._cooldowns:
            return True
        return time.time() >= self._cooldowns[action]

    def remaining(self, action: str) -> float:
        """Segundos restantes de cooldown."""
        if action not in self._cooldowns:
            return 0.0
        r = self._cooldowns[action] - time.time()
        return max(0.0, r)

    def clear(self, action: str = ""):
        """Limpia cooldown de una accion o todas."""
        if action:
            self._cooldowns.pop(action, None)
        else:
            self._cooldowns.clear()

    def get_active(self) -> dict[str, float]:
        """Cooldowns activos con tiempo restante."""
        now = time.time()
        active = {}
        for action, expiry in self._cooldowns.items():
            if expiry > now:
                active[action] = round(expiry - now, 1)
        return active


class UsageTracker:
    """
    Tracker de uso por periodo (hora, dia).

    Permite ver cuanto se usa cada recurso en ventanas de tiempo
    para analytics y limites diarios.
    """

    def __init__(self):
        self._hourly: dict[str, list[float]] = {}  # {resource: [timestamps]}
        self._window = 3600  # 1 hora por defecto

    def record(self, resource: str):
        """Registra un uso del recurso."""
        if resource not in self._hourly:
            self._hourly[resource] = []
        self._hourly[resource].append(time.time())
        # Limpiar registros viejos
        self._cleanup(resource)

    def _cleanup(self, resource: str):
        """Elimina registros fuera de la ventana."""
        cutoff = time.time() - self._window
        self._hourly[resource] = [
            t for t in self._hourly[resource] if t > cutoff
        ]

    def count_in_window(self, resource: str, window_secs: float = 0) -> int:
        """Cuenta usos en la ventana de tiempo."""
        if resource not in self._hourly:
            return 0
        if window_secs <= 0:
            window_secs = self._window
        cutoff = time.time() - window_secs
        return sum(1 for t in self._hourly[resource] if t > cutoff)

    def get_rates(self) -> dict[str, dict]:
        """Tasas de uso por recurso."""
        rates = {}
        for resource in self._hourly:
            self._cleanup(resource)
            per_min = self.count_in_window(resource, 60)
            per_hour = self.count_in_window(resource, 3600)
            rates[resource] = {
                "per_minute": per_min,
                "per_hour": per_hour,
            }
        return rates


class RateLimiter:
    """
    Rate Limiter principal de Genesis.

    Maneja multiples Token Buckets para diferentes recursos,
    cooldowns para acciones especificas, y tracking de uso.
    """

    def __init__(self):
        # Token Buckets para cada recurso
        self.buckets: dict[str, TokenBucket] = {}

        # Cooldowns para acciones
        self.cooldowns = CooldownTracker()

        # Tracking de uso
        self.usage = UsageTracker()

        # Estado global
        self.enabled = True
        self.total_limited = 0

        # Configurar buckets predefinidos
        self._setup_default_buckets()
        self._setup_default_cooldowns()

    def _setup_default_buckets(self):
        """Configura buckets por defecto para Genesis."""
        # Inferencia LLM: 10 por minuto, max 15 acumulado
        self.add_bucket("inference", capacity=15, refill_rate=10/60)

        # Ejecucion de tools: 20 por minuto, max 30 acumulado
        self.add_bucket("tools", capacity=30, refill_rate=20/60)

        # Auto-modificacion: 3 por hora, max 5 acumulado
        self.add_bucket("self_modify", capacity=5, refill_rate=3/3600)

        # Escritura a disco: 60 por minuto, max 100 acumulado
        self.add_bucket("disk_write", capacity=100, refill_rate=1.0)

        # API external (si aplica): 30 por minuto
        self.add_bucket("api_external", capacity=30, refill_rate=0.5)

    def _setup_default_cooldowns(self):
        """Configura cooldowns por defecto."""
        self.cooldowns.set_cooldown("evolution", 60.0)      # 1 min entre evoluciones
        self.cooldowns.set_cooldown("backup", 300.0)         # 5 min entre backups
        self.cooldowns.set_cooldown("health_check", 30.0)    # 30s entre health checks
        self.cooldowns.set_cooldown("rag_reindex", 120.0)    # 2 min entre reindexaciones

    def add_bucket(self, name: str, capacity: int, refill_rate: float):
        """Agrega un nuevo bucket de rate limiting."""
        self.buckets[name] = TokenBucket(
            capacity=capacity,
            refill_rate=refill_rate,
            name=name,
        )

    def remove_bucket(self, name: str) -> bool:
        """Elimina un bucket."""
        if name in self.buckets:
            del self.buckets[name]
            return True
        return False

    def allow(self, resource: str, cost: int = 1) -> bool:
        """
        Verifica si una accion esta permitida.

        Args:
            resource: Nombre del recurso (debe tener bucket)
            cost: Tokens a consumir

        Returns:
            True si hay tokens disponibles
        """
        if not self.enabled:
            return True

        if resource not in self.buckets:
            return True  # Sin bucket = sin limite

        return self.buckets[resource].allow(cost)

    def consume(self, resource: str, cost: int = 1) -> bool:
        """
        Consume tokens y registra el uso.

        Returns:
            True si se consumio exitosamente
        """
        if not self.enabled:
            self.usage.record(resource)
            return True

        if resource not in self.buckets:
            self.usage.record(resource)
            return True

        success = self.buckets[resource].consume(cost)
        if success:
            self.usage.record(resource)
        else:
            self.total_limited += 1
        return success

    def wait_time(self, resource: str, cost: int = 1) -> float:
        """Tiempo de espera para que el recurso este disponible."""
        if not self.enabled or resource not in self.buckets:
            return 0.0
        return self.buckets[resource].wait_time(cost)

    def reset(self, resource: str = ""):
        """Resetea un bucket o todos."""
        if resource:
            if resource in self.buckets:
                self.buckets[resource].reset()
        else:
            for bucket in self.buckets.values():
                bucket.reset()

    def toggle(self) -> bool:
        """Activa/desactiva el rate limiter."""
        self.enabled = not self.enabled
        return self.enabled

    def get_usage_report(self) -> str:
        """Reporte de uso de recursos."""
        lines = ["=== RATE LIMITER REPORT ==="]
        lines.append(f"Estado: {'ACTIVO' if self.enabled else 'DESACTIVADO'}")
        lines.append(f"Rechazos totales: {self.total_limited}")
        lines.append("")

        # Buckets
        lines.append("  BUCKETS:")
        for name, bucket in sorted(self.buckets.items()):
            stats = bucket.get_stats()
            bar_len = 20
            fill = int(stats["fill_percent"] / 100 * bar_len)
            bar = "#" * fill + "-" * (bar_len - fill)
            lines.append(
                f"    {name:15s} [{bar}] {stats['tokens']:.0f}/{stats['capacity']} "
                f"(consumed: {stats['total_consumed']}, rejected: {stats['total_rejected']})"
            )

        # Cooldowns activos
        active_cd = self.cooldowns.get_active()
        if active_cd:
            lines.append("\n  COOLDOWNS ACTIVOS:")
            for action, remaining in sorted(active_cd.items()):
                lines.append(f"    {action:15s} {remaining:.0f}s restantes")

        # Tasas de uso
        rates = self.usage.get_rates()
        if rates:
            lines.append("\n  TASAS DE USO:")
            for resource, rate in sorted(rates.items()):
                lines.append(
                    f"    {resource:15s} {rate['per_minute']}/min, {rate['per_hour']}/hora"
                )

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen breve para /status."""
        state = "ON" if self.enabled else "OFF"
        n_buckets = len(self.buckets)
        active_cd = len(self.cooldowns.get_active())
        return (
            f"  Estado: {state} | Buckets: {n_buckets} | "
            f"Rechazos: {self.total_limited} | Cooldowns: {active_cd}"
        )
