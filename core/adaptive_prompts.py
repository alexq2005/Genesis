"""
GENESIS — Adaptive Prompts
Sistema de A/B testing y optimizacion de prompts basado en feedback.

Permite:
- Crear variantes de un prompt base
- Medir cual variante obtiene mejor feedback
- Auto-seleccionar la mejor variante despues de N muestras
- Trackear efectividad de instrucciones especificas

Cada "experimento" tiene:
- Prompt base (el original)
- Variantes (modificaciones a probar)
- Metricas por variante (positivo/negativo/total)
- Estado (running, concluded, archived)

Uso:
    ap = AdaptivePrompts(base_dir)
    ap.create_experiment("saludo", "Saluda al usuario.", [
        "Saluda al usuario de forma casual.",
        "Saluda al usuario de forma profesional.",
    ])
    variant = ap.get_variant("saludo")  # Retorna la mejor o una aleatoria
    ap.record_feedback("saludo", variant_index=0, positive=True)
    ap.record_feedback("saludo", variant_index=1, positive=False)
    best = ap.get_best("saludo")  # Retorna la variante ganadora
"""
import json
import time
import random
import os
from pathlib import Path
from typing import Optional, List


class PromptVariant:
    """Una variante de prompt dentro de un experimento."""

    def __init__(self, text: str, label: str = ""):
        self.text = text
        self.label = label or text[:50]
        self.positive = 0
        self.negative = 0
        self.total = 0
        self.created_at = time.time()

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.5  # Sin datos = neutral
        return self.positive / self.total

    def record(self, positive: bool):
        self.total += 1
        if positive:
            self.positive += 1
        else:
            self.negative += 1

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "label": self.label,
            "positive": self.positive,
            "negative": self.negative,
            "total": self.total,
            "success_rate": round(self.success_rate, 3),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PromptVariant":
        v = cls(text=d.get("text", ""), label=d.get("label", ""))
        v.positive = d.get("positive", 0)
        v.negative = d.get("negative", 0)
        v.total = d.get("total", 0)
        v.created_at = d.get("created_at", time.time())
        return v


class PromptExperiment:
    """
    Un experimento de A/B testing para un prompt.
    Contiene multiples variantes y decide cual es mejor.
    """

    def __init__(self, name: str, base_prompt: str, min_samples: int = 5):
        """
        Args:
            name: nombre del experimento
            base_prompt: prompt original (variante 0)
            min_samples: minimo de muestras antes de declarar ganador
        """
        self.name = name
        self.base_prompt = base_prompt
        self.min_samples = min_samples
        self.variants = [PromptVariant(text=base_prompt, label="original")]
        self.state = "running"  # running, concluded, archived
        self.winner_index = None
        self.created_at = time.time()
        self.concluded_at = None

    def add_variant(self, text: str, label: str = "") -> int:
        """Agrega una variante. Retorna su indice."""
        idx = len(self.variants)
        self.variants.append(PromptVariant(text=text, label=label or f"variant_{idx}"))
        return idx

    def get_variant(self, strategy: str = "epsilon_greedy", epsilon: float = 0.2) -> tuple:
        """
        Selecciona una variante para probar.

        Args:
            strategy: "random", "epsilon_greedy", "best"
            epsilon: probabilidad de explorar (solo para epsilon_greedy)

        Returns:
            (index, text) de la variante seleccionada
        """
        if self.state == "concluded" and self.winner_index is not None:
            v = self.variants[self.winner_index]
            return self.winner_index, v.text

        if not self.variants:
            return 0, self.base_prompt

        if strategy == "random":
            idx = random.randint(0, len(self.variants) - 1)
        elif strategy == "best":
            idx = max(range(len(self.variants)),
                      key=lambda i: self.variants[i].success_rate)
        else:
            # Epsilon-greedy: explora con prob epsilon, explota con 1-epsilon
            if random.random() < epsilon:
                idx = random.randint(0, len(self.variants) - 1)
            else:
                idx = max(range(len(self.variants)),
                          key=lambda i: self.variants[i].success_rate)

        return idx, self.variants[idx].text

    def record_feedback(self, variant_index: int, positive: bool):
        """Registra feedback para una variante."""
        if 0 <= variant_index < len(self.variants):
            self.variants[variant_index].record(positive)
            self._check_conclusion()

    def _check_conclusion(self):
        """Verifica si el experimento puede concluirse."""
        if self.state != "running":
            return

        # Todas las variantes deben tener al menos min_samples
        if all(v.total >= self.min_samples for v in self.variants):
            # Buscar ganador claro (>15% de diferencia con el segundo)
            rates = [(i, v.success_rate) for i, v in enumerate(self.variants)]
            rates.sort(key=lambda x: -x[1])

            if len(rates) >= 2:
                best_rate = rates[0][1]
                second_rate = rates[1][1]
                if best_rate - second_rate >= 0.15:
                    self.winner_index = rates[0][0]
                    self.state = "concluded"
                    self.concluded_at = time.time()

    def get_results(self) -> dict:
        """Retorna resultados del experimento."""
        return {
            "name": self.name,
            "state": self.state,
            "variants": [v.to_dict() for v in self.variants],
            "winner_index": self.winner_index,
            "winner_label": (self.variants[self.winner_index].label
                            if self.winner_index is not None else None),
        }

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "base_prompt": self.base_prompt,
            "min_samples": self.min_samples,
            "variants": [v.to_dict() for v in self.variants],
            "state": self.state,
            "winner_index": self.winner_index,
            "created_at": self.created_at,
            "concluded_at": self.concluded_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PromptExperiment":
        exp = cls(
            name=d.get("name", ""),
            base_prompt=d.get("base_prompt", ""),
            min_samples=d.get("min_samples", 5),
        )
        exp.variants = [PromptVariant.from_dict(v) for v in d.get("variants", [])]
        exp.state = d.get("state", "running")
        exp.winner_index = d.get("winner_index")
        exp.created_at = d.get("created_at", time.time())
        exp.concluded_at = d.get("concluded_at")
        return exp


class AdaptivePrompts:
    """
    Sistema de A/B testing para prompts.
    Gestiona experimentos, trackea resultados y auto-selecciona ganadores.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "memory_data" / "adaptive_prompts"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.experiments = {}  # name -> PromptExperiment
        self.active_selections = {}  # name -> (variant_index, timestamp)

        # Cargar datos
        self._load()

    def create_experiment(self, name: str, base_prompt: str,
                          variants: list = None,
                          min_samples: int = 5) -> str:
        """
        Crea un nuevo experimento de A/B testing.

        Args:
            name: nombre unico del experimento
            base_prompt: prompt original
            variants: lista de textos alternativos a probar
            min_samples: minimo de muestras por variante

        Returns:
            Mensaje de confirmacion
        """
        if name in self.experiments:
            return f"Experimento '{name}' ya existe."

        exp = PromptExperiment(name=name, base_prompt=base_prompt,
                               min_samples=min_samples)
        for variant_text in (variants or []):
            exp.add_variant(variant_text)

        self.experiments[name] = exp
        self._save()

        n_variants = len(exp.variants)
        return (f"Experimento '{name}' creado con {n_variants} variantes "
                f"(min {min_samples} muestras por variante).")

    def get_variant(self, name: str) -> Optional[str]:
        """
        Obtiene la variante a usar para un experimento.
        Usa epsilon-greedy: mayormente la mejor, a veces explora.

        Returns:
            Texto de la variante seleccionada, o None si no existe.
        """
        if name not in self.experiments:
            return None

        idx, text = self.experiments[name].get_variant()
        self.active_selections[name] = (idx, time.time())
        return text

    def record_feedback(self, name: str, positive: bool,
                        variant_index: int = None) -> str:
        """
        Registra feedback para el ultimo variant seleccionado.

        Args:
            name: nombre del experimento
            positive: True = bueno, False = malo
            variant_index: indice explicito (si no, usa el ultimo seleccionado)

        Returns:
            Mensaje de estado
        """
        if name not in self.experiments:
            return f"Experimento '{name}' no encontrado."

        exp = self.experiments[name]

        if variant_index is None:
            # Usar la ultima seleccion
            selection = self.active_selections.get(name)
            if selection is None:
                return "No hay seleccion activa para este experimento."
            variant_index = selection[0]

        exp.record_feedback(variant_index, positive)

        msg = f"Feedback registrado para variante {variant_index}"
        if exp.state == "concluded":
            winner = exp.variants[exp.winner_index]
            msg += f"\n Experimento concluido! Ganador: '{winner.label}' ({winner.success_rate*100:.0f}%)"
            self._save()

        return msg

    def get_best(self, name: str) -> Optional[str]:
        """Retorna la mejor variante de un experimento."""
        if name not in self.experiments:
            return None
        exp = self.experiments[name]
        if exp.winner_index is not None:
            return exp.variants[exp.winner_index].text
        # Sin ganador, retorna la de mayor tasa
        best = max(exp.variants, key=lambda v: v.success_rate)
        return best.text

    def delete_experiment(self, name: str) -> str:
        """Elimina un experimento."""
        if name not in self.experiments:
            return f"Experimento '{name}' no encontrado."
        del self.experiments[name]
        self.active_selections.pop(name, None)
        self._save()
        return f"Experimento '{name}' eliminado."

    def list_experiments(self) -> str:
        """Lista todos los experimentos."""
        if not self.experiments:
            return "Sin experimentos activos."

        lines = ["=== Experimentos de Prompt ==="]
        for name, exp in sorted(self.experiments.items()):
            state_icon = {"running": "~", "concluded": "+", "archived": "-"}.get(exp.state, "?")
            lines.append(f"\n  [{state_icon}] {exp.name} ({exp.state})")
            for i, v in enumerate(exp.variants):
                winner = " [WINNER]" if i == exp.winner_index else ""
                lines.append(
                    f"    v{i}: {v.label} — {v.success_rate*100:.0f}% "
                    f"({v.positive}+/{v.negative}-/{v.total} total){winner}"
                )
        return "\n".join(lines)

    def get_active_experiments(self) -> list:
        """Retorna nombres de experimentos activos (running)."""
        return [name for name, exp in self.experiments.items()
                if exp.state == "running"]

    def status(self) -> str:
        """Estado resumido."""
        total = len(self.experiments)
        running = sum(1 for e in self.experiments.values() if e.state == "running")
        concluded = sum(1 for e in self.experiments.values() if e.state == "concluded")
        return (
            f"AdaptivePrompts: {total} experimentos | "
            f"Activos: {running} | Concluidos: {concluded}"
        )

    # --- Persistencia ---

    def _save(self):
        """Guarda a disco."""
        try:
            data = {
                "experiments": {
                    name: exp.to_dict()
                    for name, exp in self.experiments.items()
                },
                "saved_at": time.time(),
            }
            filepath = self.data_dir / "adaptive_prompts.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        """Carga desde disco."""
        try:
            filepath = self.data_dir / "adaptive_prompts.json"
            if not filepath.exists():
                return
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, exp_data in data.get("experiments", {}).items():
                self.experiments[name] = PromptExperiment.from_dict(exp_data)
        except Exception:
            pass

    def save(self):
        """Save forzado."""
        self._save()
