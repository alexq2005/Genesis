"""
GENESIS — Pattern Predictor (v2.7)

Predicción de patrones de uso: cadenas de Markov de intents,
patrones temporales, secuencias de topics. Genesis anticipa
qué necesitará el usuario antes de que lo pida.

Componentes:
- TransitionMatrix: cadena de Markov de primer orden
- TemporalPattern: patrones por hora del día / día de semana
- SequencePredictor: predicción basada en secuencias recientes
- PatternPredictor: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class TransitionMatrix:
    """Cadena de Markov de primer orden para transiciones de estados."""

    def __init__(self):
        self.transitions = defaultdict(lambda: defaultdict(int))
        self.totals = defaultdict(int)

    def record(self, from_state: str, to_state: str):
        """Registra una transición."""
        self.transitions[from_state][to_state] += 1
        self.totals[from_state] += 1

    def predict(self, current_state: str, top_n: int = 3) -> list:
        """Predice los próximos estados más probables."""
        if current_state not in self.transitions:
            return []
        total = self.totals[current_state]
        if total == 0:
            return []
        probs = []
        for next_state, count in self.transitions[current_state].items():
            probs.append((next_state, count / total))
        probs.sort(key=lambda x: x[1], reverse=True)
        return probs[:top_n]

    def get_probability(self, from_state: str, to_state: str) -> float:
        """Probabilidad de transición específica."""
        total = self.totals.get(from_state, 0)
        if total == 0:
            return 0.0
        return self.transitions[from_state].get(to_state, 0) / total

    @property
    def state_count(self) -> int:
        return len(self.transitions)

    @property
    def transition_count(self) -> int:
        return sum(sum(v.values()) for v in self.transitions.values())

    def to_dict(self) -> dict:
        return {
            "transitions": {k: dict(v) for k, v in self.transitions.items()},
            "totals": dict(self.totals),
        }

    def load_dict(self, data: dict):
        self.transitions = defaultdict(lambda: defaultdict(int))
        self.totals = defaultdict(int)
        for k, v in data.get("transitions", {}).items():
            for k2, count in v.items():
                self.transitions[k][k2] = count
        for k, v in data.get("totals", {}).items():
            self.totals[k] = v


class TemporalPattern:
    """Patrones de uso por hora del día y día de semana."""

    def __init__(self):
        self.hourly = defaultdict(lambda: defaultdict(int))   # hour -> intent -> count
        self.daily = defaultdict(lambda: defaultdict(int))    # weekday -> intent -> count
        self.total_records = 0

    def record(self, intent: str, timestamp: float = None):
        """Registra un intent con su timestamp."""
        t = time.localtime(timestamp or time.time())
        hour = t.tm_hour
        weekday = t.tm_wday  # 0=Monday
        self.hourly[hour][intent] += 1
        self.daily[weekday][intent] += 1
        self.total_records += 1

    def predict_by_hour(self, hour: int = None, top_n: int = 3) -> list:
        """Predice intents más probables para esta hora."""
        if hour is None:
            hour = time.localtime().tm_hour
        if hour not in self.hourly:
            return []
        total = sum(self.hourly[hour].values())
        if total == 0:
            return []
        probs = [(intent, count / total) for intent, count in self.hourly[hour].items()]
        probs.sort(key=lambda x: x[1], reverse=True)
        return probs[:top_n]

    def predict_by_day(self, weekday: int = None, top_n: int = 3) -> list:
        """Predice intents más probables para este día."""
        if weekday is None:
            weekday = time.localtime().tm_wday
        if weekday not in self.daily:
            return []
        total = sum(self.daily[weekday].values())
        if total == 0:
            return []
        probs = [(intent, count / total) for intent, count in self.daily[weekday].items()]
        probs.sort(key=lambda x: x[1], reverse=True)
        return probs[:top_n]

    def to_dict(self) -> dict:
        return {
            "hourly": {str(k): dict(v) for k, v in self.hourly.items()},
            "daily": {str(k): dict(v) for k, v in self.daily.items()},
            "total_records": self.total_records,
        }

    def load_dict(self, data: dict):
        self.hourly = defaultdict(lambda: defaultdict(int))
        self.daily = defaultdict(lambda: defaultdict(int))
        for k, v in data.get("hourly", {}).items():
            for intent, count in v.items():
                self.hourly[int(k)][intent] = count
        for k, v in data.get("daily", {}).items():
            for intent, count in v.items():
                self.daily[int(k)][intent] = count
        self.total_records = data.get("total_records", 0)


class SequencePredictor:
    """Predicción basada en secuencias recientes (n-gramas)."""

    def __init__(self, window_size: int = 3):
        self.window_size = window_size
        self.sequences = defaultdict(lambda: defaultdict(int))
        self.history = []      # Últimos N intents
        self.max_history = 100

    def record(self, intent: str):
        """Registra un intent en la secuencia."""
        self.history.append(intent)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Registrar n-gramas
        if len(self.history) >= 2:
            for n in range(2, min(self.window_size + 1, len(self.history) + 1)):
                key = tuple(self.history[-n:-1])
                self.sequences[key][intent] += 1

    def predict(self, top_n: int = 3) -> list:
        """Predice el próximo intent basado en la secuencia reciente."""
        if len(self.history) < 1:
            return []

        predictions = defaultdict(float)

        # Probar n-gramas de mayor a menor (mayor peso a secuencias más largas)
        for n in range(min(self.window_size, len(self.history)), 0, -1):
            key = tuple(self.history[-n:])
            if key in self.sequences:
                total = sum(self.sequences[key].values())
                weight = n / self.window_size  # Más peso a secuencias largas
                for intent, count in self.sequences[key].items():
                    predictions[intent] += (count / total) * weight

        if not predictions:
            return []

        result = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        return result[:top_n]

    def to_dict(self) -> dict:
        seq_dict = {}
        for key, vals in self.sequences.items():
            str_key = "|".join(key)
            seq_dict[str_key] = dict(vals)
        return {
            "sequences": seq_dict,
            "history": self.history[-self.max_history:],
        }

    def load_dict(self, data: dict):
        self.sequences = defaultdict(lambda: defaultdict(int))
        for str_key, vals in data.get("sequences", {}).items():
            key = tuple(str_key.split("|"))
            for intent, count in vals.items():
                self.sequences[key][intent] = count
        self.history = data.get("history", [])


class PatternPredictor:
    """
    Coordinador de predicción de patrones.
    Combina Markov chains, patrones temporales y secuencias
    para anticipar las necesidades del usuario.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/predictor")
        self.data_file = self.base_dir / "predictor_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.markov = TransitionMatrix()
        self.temporal = TemporalPattern()
        self.sequence = SequencePredictor(window_size=3)
        self.last_intent = ""
        self.total_predictions = 0
        self.correct_predictions = 0
        self.enabled = True

        self._load()

    def record_intent(self, intent: str):
        """Registra un intent en todos los predictores."""
        if not self.enabled or not intent:
            return

        # Markov: transición desde el último intent
        if self.last_intent:
            self.markov.record(self.last_intent, intent)

        # Temporal
        self.temporal.record(intent)

        # Secuencia
        self.sequence.record(intent)

        self.last_intent = intent

    def predict(self, top_n: int = 3) -> list:
        """
        Predice los próximos intents combinando los 3 predictores.
        Retorna lista de (intent, confidence).
        """
        if not self.enabled:
            return []

        combined = defaultdict(float)

        # Markov (peso 0.4)
        markov_preds = self.markov.predict(self.last_intent, top_n=5)
        for intent, prob in markov_preds:
            combined[intent] += prob * 0.4

        # Temporal (peso 0.3)
        hour_preds = self.temporal.predict_by_hour(top_n=5)
        for intent, prob in hour_preds:
            combined[intent] += prob * 0.3

        # Secuencia (peso 0.3)
        seq_preds = self.sequence.predict(top_n=5)
        for intent, prob in seq_preds:
            combined[intent] += prob * 0.3

        if not combined:
            return []

        self.total_predictions += 1
        result = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        return result[:top_n]

    def verify_prediction(self, actual_intent: str):
        """Verifica si la predicción anterior fue correcta."""
        predictions = self.predict(top_n=1)
        if predictions and predictions[0][0] == actual_intent:
            self.correct_predictions += 1

    @property
    def accuracy(self) -> float:
        if self.total_predictions == 0:
            return 0.0
        return self.correct_predictions / self.total_predictions

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto predictivo para inyectar en prompt."""
        if not self.enabled:
            return ""
        predictions = self.predict(top_n=3)
        if not predictions:
            return ""

        top_pred = predictions[0]
        if top_pred[1] < 0.2:  # Confianza mínima
            return ""

        lines = ["[PREDICCIÓN DE CONTEXTO]"]
        lines.append(f"Probable próximo intent: {top_pred[0]} ({top_pred[1]:.0%})")
        if len(predictions) > 1:
            alts = ", ".join(f"{p[0]} ({p[1]:.0%})" for p in predictions[1:])
            lines.append(f"Alternativas: {alts}")

        return "\n".join(lines)[:max_chars]

    def get_stats(self) -> dict:
        return {
            "markov_states": self.markov.state_count,
            "markov_transitions": self.markov.transition_count,
            "temporal_records": self.temporal.total_records,
            "sequence_history": len(self.sequence.history),
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "accuracy": round(self.accuracy, 3),
        }

    def status(self) -> str:
        return (f"Markov: {self.markov.state_count} estados | "
                f"Temporal: {self.temporal.total_records} registros | "
                f"Accuracy: {self.accuracy:.0%} ({self.correct_predictions}/{self.total_predictions})")

    def generate_report(self) -> str:
        lines = ["=== PATTERN PREDICTOR REPORT ==="]
        lines.append(f"Estados Markov: {self.markov.state_count}")
        lines.append(f"Transiciones: {self.markov.transition_count}")
        lines.append(f"Registros temporales: {self.temporal.total_records}")
        lines.append(f"Historial secuencias: {len(self.sequence.history)}")
        lines.append(f"Predicciones: {self.total_predictions}")
        lines.append(f"Correctas: {self.correct_predictions}")
        lines.append(f"Accuracy: {self.accuracy:.1%}")

        # Predicción actual
        preds = self.predict(top_n=5)
        if preds:
            lines.append(f"\nPredicción actual:")
            for intent, prob in preds:
                bar = "█" * int(prob * 20)
                lines.append(f"  {intent:15s} {bar} {prob:.0%}")

        # Patrones por hora
        hour = time.localtime().tm_hour
        hour_preds = self.temporal.predict_by_hour(hour, top_n=3)
        if hour_preds:
            lines.append(f"\nPatrón hora {hour}:00:")
            for intent, prob in hour_preds:
                lines.append(f"  {intent}: {prob:.0%}")

        return "\n".join(lines)

    def save(self):
        data = {
            "last_intent": self.last_intent,
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "markov": self.markov.to_dict(),
            "temporal": self.temporal.to_dict(),
            "sequence": self.sequence.to_dict(),
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.last_intent = data.get("last_intent", "")
            self.total_predictions = data.get("total_predictions", 0)
            self.correct_predictions = data.get("correct_predictions", 0)
            self.markov.load_dict(data.get("markov", {}))
            self.temporal.load_dict(data.get("temporal", {}))
            self.sequence.load_dict(data.get("sequence", {}))
        except Exception:
            pass

    def clear(self):
        self.markov = TransitionMatrix()
        self.temporal = TemporalPattern()
        self.sequence = SequencePredictor(window_size=3)
        self.last_intent = ""
        self.total_predictions = 0
        self.correct_predictions = 0
