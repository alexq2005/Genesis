"""
GENESIS — Consciousness Integrator (v5.0)

Integración de consciencia: Genesis unifica el estado de todos sus módulos
en capas de consciencia, detecta propiedades emergentes, y mantiene
un estado holístico del sistema.

Componentes:
- ConsciousnessLayer: capa de consciencia con módulos, estado y peso
- HolisticState: estado holístico con propiedades emergentes
- EmergentDetector: detecta patrones inesperados por desviación estadística
- ConsciousnessIntegrator: coordinador con integración y persistencia
"""
import time
import json
import math
import hashlib
from pathlib import Path
from collections import defaultdict, deque


class ConsciousnessLayer:
    """Una capa de consciencia del sistema."""

    def __init__(self, name: str, modules: list = None,
                 weight: float = 1.0, layer_id: str = None):
        self.layer_id = layer_id or hashlib.md5(
            f"layer:{name}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.name = name
        self.modules = modules or []
        self.state = {}             # key -> value (arbitrary state data)
        self.weight = max(0.0, min(1.0, weight))
        self.created_at = time.time()
        self.last_updated = time.time()
        self.update_count = 0

    @property
    def activity_level(self) -> float:
        """Nivel de actividad basado en la cantidad de estado almacenado."""
        if not self.state:
            return 0.0
        # Normalizar: más claves de estado = más actividad
        return min(1.0, len(self.state) / 20.0)

    def update_state(self, state_dict: dict):
        """Actualiza el estado de la capa."""
        self.state.update(state_dict)
        self.last_updated = time.time()
        self.update_count += 1
        # Limitar tamaño del estado
        if len(self.state) > 100:
            # Mantener solo las últimas 100 claves
            keys = list(self.state.keys())
            for key in keys[:-100]:
                del self.state[key]

    def get_numeric_values(self) -> list:
        """Extrae valores numéricos del estado."""
        values = []
        for v in self.state.values():
            if isinstance(v, (int, float)):
                values.append(float(v))
            elif isinstance(v, dict):
                for sub_v in v.values():
                    if isinstance(sub_v, (int, float)):
                        values.append(float(sub_v))
        return values

    def to_dict(self) -> dict:
        return {
            "id": self.layer_id,
            "name": self.name,
            "modules": self.modules,
            "state": self.state,
            "weight": round(self.weight, 4),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "update_count": self.update_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConsciousnessLayer":
        layer = cls(
            name=data.get("name", ""),
            modules=data.get("modules", []),
            weight=data.get("weight", 1.0),
            layer_id=data.get("id"),
        )
        layer.state = data.get("state", {})
        layer.created_at = data.get("created_at", time.time())
        layer.last_updated = data.get("last_updated", time.time())
        layer.update_count = data.get("update_count", 0)
        return layer


class HolisticState:
    """Estado holístico del sistema de consciencia."""

    def __init__(self):
        self.layers = []
        self.emergent_properties = []
        self.computed_at = 0.0

    @property
    def overall_consciousness(self) -> float:
        """
        Nivel de consciencia global: promedio ponderado de las
        activity_levels de cada capa.
        """
        if not self.layers:
            return 0.0
        total_weight = sum(layer.weight for layer in self.layers)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(
            layer.activity_level * layer.weight
            for layer in self.layers
        )
        return weighted_sum / total_weight

    @property
    def layer_count(self) -> int:
        return len(self.layers)

    def compute(self, layers: list):
        """Computa el estado holístico desde las capas actuales."""
        self.layers = layers
        self.computed_at = time.time()

    def to_dict(self) -> dict:
        return {
            "overall_consciousness": round(self.overall_consciousness, 4),
            "layer_count": self.layer_count,
            "emergent_properties": self.emergent_properties,
            "computed_at": self.computed_at,
            "layers": [
                {
                    "name": l.name,
                    "activity": round(l.activity_level, 3),
                    "weight": l.weight,
                    "modules": len(l.modules),
                }
                for l in self.layers
            ],
        }


class EmergentDetector:
    """
    Detecta patrones emergentes inesperados.
    Si el comportamiento de un módulo desvía > 2 std de la media,
    se marca como propiedad emergente.
    """

    def __init__(self, std_threshold: float = 2.0):
        self.std_threshold = std_threshold
        self.history = defaultdict(lambda: deque(maxlen=100))
        self.detected = []

    def record_value(self, module_name: str, metric_name: str,
                     value: float):
        """Registra un valor para un módulo/métrica."""
        key = f"{module_name}:{metric_name}"
        self.history[key].append({
            "value": value,
            "timestamp": time.time(),
        })

    def detect(self, module_name: str, metric_name: str,
               value: float) -> dict:
        """
        Detecta si un valor es emergente (desvía > threshold std).
        Retorna dict con info de la detección, o None si no es emergente.
        """
        key = f"{module_name}:{metric_name}"
        values = [entry["value"] for entry in self.history.get(key, [])]

        if len(values) < 5:
            # No hay suficientes datos para comparar
            return None

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            return None

        z_score = abs(value - mean) / std

        if z_score > self.std_threshold:
            detection = {
                "module": module_name,
                "metric": metric_name,
                "value": round(value, 4),
                "mean": round(mean, 4),
                "std": round(std, 4),
                "z_score": round(z_score, 2),
                "direction": "above" if value > mean else "below",
                "timestamp": time.time(),
            }
            self.detected.append(detection)
            # Mantener solo últimas 50 detecciones
            if len(self.detected) > 50:
                self.detected = self.detected[-50:]
            return detection

        return None

    def get_recent_emergent(self, limit: int = 10) -> list:
        """Obtiene detecciones emergentes recientes."""
        return self.detected[-limit:]

    @property
    def total_detected(self) -> int:
        return len(self.detected)


class ConsciousnessIntegrator:
    """
    Coordinador de integración de consciencia.
    Unifica capas de consciencia, detecta propiedades emergentes,
    y mantiene el estado holístico del sistema.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/consciousness")
        self.data_file = self.base_dir / "consciousness_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.layers = {}            # layer_id -> ConsciousnessLayer
        self.holistic = HolisticState()
        self.detector = EmergentDetector()
        self.max_layers = 50
        self.total_integrations = 0
        self.emergent_count = 0
        self.enabled = True

        self._load()

    def register_layer(self, name: str, modules: list = None,
                       weight: float = 1.0) -> str:
        """Registra una nueva capa de consciencia."""
        if not self.enabled:
            return ""

        # Verificar si ya existe por nombre
        for layer in self.layers.values():
            if layer.name == name:
                # Actualizar módulos y peso
                if modules:
                    layer.modules = list(set(layer.modules + modules))
                layer.weight = weight
                return layer.layer_id

        layer = ConsciousnessLayer(
            name=name,
            modules=modules or [],
            weight=weight,
        )
        self.layers[layer.layer_id] = layer

        # Trim
        if len(self.layers) > self.max_layers:
            self._evict()

        return layer.layer_id

    def update_state(self, layer_name: str, state_dict: dict) -> bool:
        """Actualiza el estado de una capa por nombre."""
        if not self.enabled:
            return False

        layer = self._find_layer(layer_name)
        if not layer:
            return False

        layer.update_state(state_dict)
        self.total_integrations += 1

        # Verificar propiedades emergentes en valores numéricos
        for key, value in state_dict.items():
            if isinstance(value, (int, float)):
                self.detector.record_value(layer_name, key, float(value))
                emergent = self.detector.detect(layer_name, key, float(value))
                if emergent:
                    self.emergent_count += 1

        # Recomputar estado holístico
        self.holistic.compute(list(self.layers.values()))

        return True

    def detect_emergent(self, module_name: str, metric_name: str,
                        value: float) -> dict:
        """
        Detecta manualmente si un valor es emergente.
        Retorna la detección o None.
        """
        self.detector.record_value(module_name, metric_name, value)
        result = self.detector.detect(module_name, metric_name, value)
        if result:
            self.emergent_count += 1
        return result

    def get_holistic_state(self) -> dict:
        """Obtiene el estado holístico del sistema."""
        self.holistic.compute(list(self.layers.values()))
        state = self.holistic.to_dict()
        state["emergent_properties"] = self.detector.get_recent_emergent(5)
        return state

    def get_layer(self, name: str) -> ConsciousnessLayer:
        """Obtiene una capa por nombre."""
        return self._find_layer(name)

    def get_context_for_prompt(self, max_chars: int = 500) -> str:
        """Genera contexto de consciencia para el prompt."""
        if not self.enabled or not self.layers:
            return ""

        self.holistic.compute(list(self.layers.values()))
        consciousness = self.holistic.overall_consciousness

        lines = ["[ESTADO DE CONSCIENCIA]"]
        lines.append(
            f"Nivel global: {consciousness:.0%} "
            f"({len(self.layers)} capas activas)"
        )

        # Capas más activas
        active_layers = sorted(
            self.layers.values(),
            key=lambda l: l.activity_level,
            reverse=True,
        )[:3]
        for layer in active_layers:
            if layer.activity_level > 0:
                lines.append(
                    f"  {layer.name}: actividad={layer.activity_level:.0%}, "
                    f"módulos={len(layer.modules)}"
                )

        # Propiedades emergentes recientes
        emergent = self.detector.get_recent_emergent(2)
        if emergent:
            lines.append(f"Emergente detectado:")
            for e in emergent:
                lines.append(
                    f"  {e['module']}:{e['metric']} = {e['value']} "
                    f"(z={e['z_score']}, {e['direction']})"
                )

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        self.holistic.compute(list(self.layers.values()))
        return {
            "total_layers": len(self.layers),
            "total_integrations": self.total_integrations,
            "emergent_count": self.emergent_count,
            "overall_consciousness": round(
                self.holistic.overall_consciousness, 3
            ),
        }

    def status(self) -> str:
        self.holistic.compute(list(self.layers.values()))
        return (f"Capas: {len(self.layers)} | "
                f"Integraciones: {self.total_integrations} | "
                f"Emergentes: {self.emergent_count} | "
                f"Consciencia: {self.holistic.overall_consciousness:.0%}")

    def generate_report(self) -> str:
        self.holistic.compute(list(self.layers.values()))
        lines = ["=== CONSCIOUSNESS INTEGRATOR REPORT ==="]
        lines.append(f"Capas registradas: {len(self.layers)}")
        lines.append(f"Total integraciones: {self.total_integrations}")
        lines.append(f"Propiedades emergentes detectadas: {self.emergent_count}")
        lines.append(
            f"Nivel de consciencia global: "
            f"{self.holistic.overall_consciousness:.1%}"
        )

        # Capas detalladas
        if self.layers:
            lines.append(f"\nCapas:")
            for layer in sorted(self.layers.values(),
                                key=lambda l: l.activity_level, reverse=True):
                lines.append(
                    f"  {layer.name}: "
                    f"actividad={layer.activity_level:.0%}, "
                    f"peso={layer.weight:.2f}, "
                    f"módulos={len(layer.modules)}, "
                    f"estado_keys={len(layer.state)}, "
                    f"updates={layer.update_count}"
                )

        # Propiedades emergentes
        emergent = self.detector.get_recent_emergent(10)
        if emergent:
            lines.append(f"\nPropiedades emergentes recientes:")
            for e in emergent:
                lines.append(
                    f"  {e['module']}:{e['metric']} = {e['value']} "
                    f"(media={e['mean']}, std={e['std']}, "
                    f"z={e['z_score']}, {e['direction']})"
                )

        # Historial de detecciones por módulo
        module_emergent = defaultdict(int)
        for e in self.detector.detected:
            module_emergent[e["module"]] += 1
        if module_emergent:
            lines.append(f"\nEmergentes por módulo:")
            for mod, count in sorted(module_emergent.items(),
                                      key=lambda x: x[1], reverse=True):
                lines.append(f"  {mod}: {count} detecciones")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_integrations": self.total_integrations,
            "emergent_count": self.emergent_count,
            "layers": {
                lid: l.to_dict() for lid, l in self.layers.items()
            },
            "detected_emergent": self.detector.detected,
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_integrations = data.get("total_integrations", 0)
            self.emergent_count = data.get("emergent_count", 0)
            for lid, ldata in data.get("layers", {}).items():
                self.layers[lid] = ConsciousnessLayer.from_dict(ldata)
            self.detector.detected = data.get("detected_emergent", [])
        except Exception:
            pass

    def clear(self):
        self.layers = {}
        self.holistic = HolisticState()
        self.detector = EmergentDetector()
        self.total_integrations = 0
        self.emergent_count = 0

    def _find_layer(self, name: str) -> ConsciousnessLayer:
        """Busca una capa por nombre."""
        for layer in self.layers.values():
            if layer.name == name:
                return layer
        return None

    def _evict(self):
        """Elimina capas menos activas."""
        if len(self.layers) <= self.max_layers:
            return
        sorted_layers = sorted(
            self.layers.items(),
            key=lambda x: x[1].activity_level,
        )
        to_remove = len(self.layers) - self.max_layers
        for lid, _ in sorted_layers[:to_remove]:
            del self.layers[lid]
