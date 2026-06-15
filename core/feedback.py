"""
GENESIS Feedback — Sistema de aprendizaje por refuerzo humano.

El usuario califica las respuestas de Genesis con + (buena) o - (mala).
Esto alimenta:
- La evolucion (fitness real basado en datos, no auto-evaluacion)
- El perfil de aprendizaje (que tipo de respuestas funcionan)
- La adaptacion de comportamiento (ajustar estilo segun preferencias)

Inspirado en RLHF (Reinforcement Learning from Human Feedback)
pero simplificado para correr local sin entrenamiento de modelo.
"""
import json
import time
from pathlib import Path
from collections import Counter


class FeedbackSystem:
    """Sistema de feedback que permite al usuario calificar respuestas."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = self._load()
        # Buffer de la ultima interaccion (para calificar)
        self.last_interaction: dict = {}

    def _load(self) -> dict:
        """Carga historial de feedback desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "ratings": [],           # Historial completo de ratings
            "positive_count": 0,     # Total de respuestas positivas
            "negative_count": 0,     # Total de respuestas negativas
            "patterns": {            # Patrones aprendidos
                "liked_topics": {},      # Temas que gustan: {tema: conteo}
                "disliked_topics": {},   # Temas que no gustan
                "liked_styles": [],      # Estilos que funcionan
                "disliked_styles": [],   # Estilos que no funcionan
            },
            "streak": 0,             # Racha actual (positiva o negativa)
            "best_streak": 0,        # Mejor racha positiva
            "created": time.time(),
        }

    def _save(self):
        """Persiste feedback a disco."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def clear(self):
        """Resetea todos los datos de feedback y elimina el archivo."""
        self.data = {
            "ratings": [],
            "positive_count": 0,
            "negative_count": 0,
            "patterns": {
                "liked_topics": {},
                "disliked_topics": {},
                "liked_styles": [],
                "disliked_styles": [],
            },
            "streak": 0,
            "best_streak": 0,
            "created": time.time(),
        }
        self.last_interaction = {}
        if self.filepath.exists():
            self.filepath.unlink()

    def set_last_interaction(self, user_input: str, response: str,
                             category: str = "general"):
        """Registra la ultima interaccion para poder calificarla."""
        self.last_interaction = {
            "user_input": user_input[:300],
            "response": response[:500],
            "category": category,
            "timestamp": time.time(),
        }

    def rate(self, positive: bool) -> str:
        """
        Califica la ultima respuesta.

        Args:
            positive: True = buena respuesta, False = mala

        Returns:
            Mensaje de confirmacion
        """
        if not self.last_interaction:
            return "No hay respuesta que calificar."

        rating = {
            "positive": positive,
            "user_input": self.last_interaction["user_input"],
            "response_preview": self.last_interaction["response"][:200],
            "category": self.last_interaction["category"],
            "timestamp": time.time(),
        }

        self.data["ratings"].append(rating)

        if positive:
            self.data["positive_count"] += 1
            if self.data["streak"] >= 0:
                self.data["streak"] += 1
            else:
                self.data["streak"] = 1
            self.data["best_streak"] = max(
                self.data["best_streak"], self.data["streak"]
            )
        else:
            self.data["negative_count"] += 1
            if self.data["streak"] <= 0:
                self.data["streak"] -= 1
            else:
                self.data["streak"] = -1

        # Aprender patrones
        self._learn_pattern(rating)

        # Limitar historial (max 500 ratings)
        if len(self.data["ratings"]) > 500:
            self.data["ratings"] = self.data["ratings"][-500:]

        self._save()

        total = self.data["positive_count"] + self.data["negative_count"]
        ratio = self.data["positive_count"] / total * 100 if total > 0 else 0

        emoji = "👍" if positive else "👎"
        streak_info = ""
        if abs(self.data["streak"]) >= 3:
            if self.data["streak"] > 0:
                streak_info = f" | Racha positiva: {self.data['streak']}🔥"
            else:
                streak_info = f" | Racha negativa: {abs(self.data['streak'])}⚠️"

        return (
            f"{emoji} Registrado. "
            f"Aprobacion: {ratio:.0f}% ({self.data['positive_count']}/{total})"
            f"{streak_info}"
        )

    def _learn_pattern(self, rating: dict):
        """Extrae patrones de la interaccion calificada."""
        user_input = rating["user_input"].lower()
        category = rating["category"]

        # Detectar temas
        topic_keywords = {
            "codigo": ["programa", "codigo", "script", "funcion", "python", "code"],
            "investigacion": ["investiga", "busca", "informacion", "explica"],
            "creatividad": ["crea", "imagina", "inventa", "historia", "genera"],
            "tecnico": ["como funciona", "arquitectura", "sistema", "red", "hardware"],
            "seguridad": ["hack", "seguridad", "malware", "exploit", "vulnerabilidad"],
            "general": [],
        }

        detected_topic = category
        for topic, keywords in topic_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_topic = topic
                break

        target = "liked_topics" if rating["positive"] else "disliked_topics"
        topics = self.data["patterns"][target]
        topics[detected_topic] = topics.get(detected_topic, 0) + 1

        # Detectar estilo de respuesta
        response = rating["response_preview"].lower()
        style_hints = []

        if len(response) > 300:
            style_hints.append("detallada")
        elif len(response) < 100:
            style_hints.append("concisa")

        if "```" in response or "[TOOL:" in response:
            style_hints.append("con_codigo")
        if any(w in response for w in ["ejemplo", "por ejemplo", "como esto"]):
            style_hints.append("con_ejemplos")
        if any(w in response for w in ["paso 1", "primero", "1.", "1)"]):
            style_hints.append("paso_a_paso")

        target_styles = "liked_styles" if rating["positive"] else "disliked_styles"
        self.data["patterns"][target_styles].extend(style_hints)

        # Limitar listas de estilos
        for key in ["liked_styles", "disliked_styles"]:
            if len(self.data["patterns"][key]) > 100:
                self.data["patterns"][key] = self.data["patterns"][key][-100:]

    def get_satisfaction_rate(self) -> float:
        """Retorna tasa de satisfaccion (0.0 a 1.0)."""
        total = self.data["positive_count"] + self.data["negative_count"]
        if total == 0:
            return 0.5  # Neutral si no hay datos
        return self.data["positive_count"] / total

    def get_fitness_from_feedback(self) -> int:
        """
        Calcula fitness basado en feedback real del usuario.
        Retorna 0-100.
        """
        total = self.data["positive_count"] + self.data["negative_count"]
        if total < 3:
            return 50  # Sin datos suficientes

        # Tasa de aprobacion base (pesa 60%)
        approval = self.get_satisfaction_rate() * 100

        # Tendencia reciente (pesa 40%) — ultimos 10 ratings
        recent = self.data["ratings"][-10:]
        if recent:
            recent_positive = sum(1 for r in recent if r["positive"])
            recent_rate = recent_positive / len(recent) * 100
        else:
            recent_rate = 50

        fitness = int(approval * 0.6 + recent_rate * 0.4)
        return max(0, min(100, fitness))

    def get_learning_context(self) -> str:
        """
        Genera contexto de aprendizaje para inyectar en el system prompt.
        Le dice a Genesis que le gusta y que no le gusta al usuario.
        """
        total = self.data["positive_count"] + self.data["negative_count"]
        if total < 2:
            return ""

        lines = ["[PREFERENCIAS DEL USUARIO — Aprendidas de su feedback:]"]

        # Temas que gustan
        liked = self.data["patterns"]["liked_topics"]
        if liked:
            top_liked = sorted(liked.items(), key=lambda x: x[1], reverse=True)[:3]
            temas = ", ".join(f"{t[0]}({t[1]})" for t in top_liked)
            lines.append(f"- Temas preferidos: {temas}")

        # Temas que no gustan
        disliked = self.data["patterns"]["disliked_topics"]
        if disliked:
            top_disliked = sorted(disliked.items(), key=lambda x: x[1], reverse=True)[:3]
            temas = ", ".join(f"{t[0]}({t[1]})" for t in top_disliked)
            lines.append(f"- Temas a mejorar: {temas}")

        # Estilos preferidos
        liked_styles = self.data["patterns"]["liked_styles"]
        if liked_styles:
            style_counts = Counter(liked_styles)
            top_styles = style_counts.most_common(3)
            estilos = ", ".join(f"{s[0]}" for s in top_styles)
            lines.append(f"- Estilos que funcionan: {estilos}")

        # Estilos a evitar
        disliked_styles = self.data["patterns"]["disliked_styles"]
        if disliked_styles:
            style_counts = Counter(disliked_styles)
            top_styles = style_counts.most_common(3)
            estilos = ", ".join(f"{s[0]}" for s in top_styles)
            lines.append(f"- Estilos a evitar: {estilos}")

        # Tasa de aprobacion
        rate = self.get_satisfaction_rate() * 100
        lines.append(f"- Aprobacion general: {rate:.0f}%")

        if len(lines) <= 1:
            return ""

        return "\n".join(lines)

    def get_recent_failures(self, n: int = 5) -> list[dict]:
        """Retorna las ultimas respuestas negativas para analisis."""
        negatives = [r for r in self.data["ratings"] if not r["positive"]]
        return negatives[-n:] if len(negatives) >= n else negatives

    def format_stats(self) -> str:
        """Formatea estadisticas para mostrar al usuario."""
        total = self.data["positive_count"] + self.data["negative_count"]
        if total == 0:
            return "  Sin ratings aun. Usa + o - para calificar respuestas."

        rate = self.data["positive_count"] / total * 100
        lines = [
            f"  Total ratings: {total}",
            f"  Positivos: {self.data['positive_count']} 👍",
            f"  Negativos: {self.data['negative_count']} 👎",
            f"  Aprobacion: {rate:.1f}%",
            f"  Racha actual: {self.data['streak']}",
            f"  Mejor racha: {self.data['best_streak']}",
        ]

        # Fitness calculado
        fitness = self.get_fitness_from_feedback()
        lines.append(f"  Fitness (de feedback): {fitness}/100")

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen corto para /status."""
        total = self.data["positive_count"] + self.data["negative_count"]
        if total == 0:
            return "  Sin feedback (usa + o - despues de una respuesta)"
        rate = self.data["positive_count"] / total * 100
        return (
            f"  Aprobacion: {rate:.0f}% "
            f"({self.data['positive_count']}👍 / {self.data['negative_count']}👎) "
            f"| Racha: {self.data['streak']}"
        )
