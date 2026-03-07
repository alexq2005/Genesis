"""
GENESIS — Conversation Analytics
Analiza patrones de conversacion para generar insights actionables.

Trackea:
- Topicos frecuentes y tendencias
- Metricas de engagement (largo de sesiones, frecuencia)
- Distribucion temporal (hora del dia, dia de la semana)
- Gaps de conocimiento (preguntas sin respuesta satisfactoria)
- Complejidad de queries a lo largo del tiempo

Uso:
    analytics = ConversationAnalytics(base_dir)
    analytics.track_message("user", "como funciona un transformer?", tags=["ml", "nlp"])
    analytics.track_response(agent="researcher", feedback=1, response_time=2.5)
    report = analytics.generate_report()
"""
import json
import time
import os
from pathlib import Path
from typing import Optional, List
from collections import defaultdict, Counter


class TopicTracker:
    """Detecta y trackea topicos de conversacion."""

    # Topicos predefinidos con keywords
    TOPIC_KEYWORDS = {
        "programacion": ["codigo", "funcion", "clase", "python", "javascript", "programa",
                         "variable", "loop", "array", "bug", "debug", "error", "api",
                         "framework", "libreria", "modulo", "git", "docker"],
        "seguridad": ["seguridad", "vulnerabilidad", "hack", "malware", "cifrado",
                      "password", "firewall", "pentest", "exploit", "cve", "owasp"],
        "datos": ["datos", "base de datos", "sql", "json", "csv", "analisis",
                  "estadistica", "grafico", "tabla", "query", "pandas", "dataframe"],
        "ia_ml": ["machine learning", "inteligencia artificial", "modelo", "neuronal",
                  "entrenamiento", "dataset", "tensorflow", "pytorch", "transformer",
                  "embedding", "nlp", "gpt", "llm"],
        "web": ["html", "css", "web", "servidor", "http", "rest", "frontend",
                "backend", "react", "flask", "django", "url", "dominio"],
        "sistema": ["linux", "windows", "terminal", "proceso", "memoria", "disco",
                    "red", "puerto", "servicio", "instalacion", "configuracion"],
        "creative": ["historia", "poema", "cuento", "creativo", "escribe", "inventa",
                     "nombre", "slogan", "idea", "brainstorm"],
        "general": ["explica", "que es", "como funciona", "diferencia", "ejemplo",
                    "tutorial", "ayuda", "resumen"],
    }

    def __init__(self):
        self.topic_counts = Counter()
        self.topic_timeline = []  # (timestamp, topic)
        self.max_timeline = 500

    def detect_topics(self, text: str) -> list:
        """Detecta topicos en un texto."""
        text_lower = text.lower()
        detected = []
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score >= 1:
                detected.append((topic, score))
        # Ordenar por score descendente
        detected.sort(key=lambda x: -x[1])
        return [t[0] for t in detected[:3]]  # Top 3 topicos

    def record(self, text: str):
        """Registra topicos de un mensaje."""
        topics = self.detect_topics(text)
        for topic in topics:
            self.topic_counts[topic] += 1
        if topics:
            self.topic_timeline.append((time.time(), topics[0]))
            if len(self.topic_timeline) > self.max_timeline:
                self.topic_timeline = self.topic_timeline[-self.max_timeline:]

    def get_top_topics(self, limit: int = 10) -> list:
        """Retorna los topicos mas frecuentes."""
        return self.topic_counts.most_common(limit)

    def get_recent_trend(self, window: int = 20) -> dict:
        """Analiza tendencias recientes."""
        recent = self.topic_timeline[-window:]
        if not recent:
            return {}
        return dict(Counter(t[1] for t in recent))

    def to_dict(self) -> dict:
        return {
            "topic_counts": dict(self.topic_counts),
            "topic_timeline": self.topic_timeline[-200:],
        }

    def from_dict(self, data: dict):
        self.topic_counts = Counter(data.get("topic_counts", {}))
        self.topic_timeline = data.get("topic_timeline", [])


class EngagementMetrics:
    """Trackea metricas de engagement y uso."""

    def __init__(self):
        self.session_lengths = []  # duracion de sesiones en mensajes
        self.response_times = []   # tiempos de respuesta
        self.messages_per_hour = defaultdict(int)  # distribucion horaria
        self.messages_per_day = defaultdict(int)    # distribucion por dia
        self.total_messages = 0
        self.total_sessions = 0
        self.current_session_msgs = 0
        self.session_start = time.time()
        self.query_lengths = []    # largo de queries

    def track_message(self, role: str, content: str):
        """Registra un mensaje para metricas."""
        self.total_messages += 1
        self.current_session_msgs += 1

        # Distribucion temporal
        now = time.localtime()
        hour_key = f"{now.tm_hour:02d}:00"
        self.messages_per_hour[hour_key] += 1
        day_names = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
        day_key = day_names[now.tm_wday]
        self.messages_per_day[day_key] += 1

        # Largo de query
        if role == "user":
            self.query_lengths.append(len(content))
            if len(self.query_lengths) > 500:
                self.query_lengths = self.query_lengths[-500:]

    def track_response_time(self, seconds: float):
        """Registra tiempo de respuesta."""
        self.response_times.append(seconds)
        if len(self.response_times) > 500:
            self.response_times = self.response_times[-500:]

    def end_session(self):
        """Marca fin de sesion."""
        if self.current_session_msgs > 0:
            self.session_lengths.append(self.current_session_msgs)
            self.total_sessions += 1
            self.current_session_msgs = 0
            if len(self.session_lengths) > 100:
                self.session_lengths = self.session_lengths[-100:]

    def get_avg_session_length(self) -> float:
        """Largo promedio de sesion en mensajes."""
        if not self.session_lengths:
            return 0.0
        return sum(self.session_lengths) / len(self.session_lengths)

    def get_avg_response_time(self) -> float:
        """Tiempo de respuesta promedio."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_avg_query_length(self) -> float:
        """Largo promedio de queries."""
        if not self.query_lengths:
            return 0.0
        return sum(self.query_lengths) / len(self.query_lengths)

    def get_peak_hours(self, limit: int = 3) -> list:
        """Horas pico de uso."""
        return sorted(self.messages_per_hour.items(), key=lambda x: -x[1])[:limit]

    def to_dict(self) -> dict:
        return {
            "session_lengths": self.session_lengths[-50:],
            "response_times": self.response_times[-100:],
            "messages_per_hour": dict(self.messages_per_hour),
            "messages_per_day": dict(self.messages_per_day),
            "total_messages": self.total_messages,
            "total_sessions": self.total_sessions,
            "query_lengths": self.query_lengths[-100:],
        }

    def from_dict(self, data: dict):
        self.session_lengths = data.get("session_lengths", [])
        self.response_times = data.get("response_times", [])
        self.messages_per_hour = defaultdict(int, data.get("messages_per_hour", {}))
        self.messages_per_day = defaultdict(int, data.get("messages_per_day", {}))
        self.total_messages = data.get("total_messages", 0)
        self.total_sessions = data.get("total_sessions", 0)
        self.query_lengths = data.get("query_lengths", [])


class KnowledgeGapDetector:
    """Detecta gaps de conocimiento — preguntas sin buenas respuestas."""

    def __init__(self):
        self.pending_query = None  # Query actual esperando feedback
        self.gaps = []             # Queries con feedback negativo
        self.max_gaps = 100
        self.resolved = []         # Gaps resueltos
        self.max_resolved = 50

    def track_query(self, query: str, tags: list = None):
        """Registra una query pendiente de feedback."""
        self.pending_query = {
            "query": query[:200],
            "tags": tags or [],
            "timestamp": time.time(),
        }

    def track_feedback(self, feedback: int):
        """Registra feedback para la query pendiente."""
        if self.pending_query is None:
            return

        if feedback < 0:
            # Gap detectado
            self.gaps.append(self.pending_query)
            if len(self.gaps) > self.max_gaps:
                self.gaps = self.gaps[-self.max_gaps:]
        elif feedback > 0:
            # Si era un gap previo, marcarlo como resuelto
            query_text = self.pending_query["query"]
            for i, gap in enumerate(self.gaps):
                if gap["query"] == query_text:
                    self.resolved.append(self.gaps.pop(i))
                    if len(self.resolved) > self.max_resolved:
                        self.resolved = self.resolved[-self.max_resolved:]
                    break

        self.pending_query = None

    def get_gaps(self, limit: int = 10) -> list:
        """Retorna los gaps mas recientes."""
        return self.gaps[-limit:]

    def get_gap_topics(self) -> dict:
        """Agrupa gaps por tag."""
        topics = Counter()
        for gap in self.gaps:
            for tag in gap.get("tags", []):
                topics[tag] += 1
        return dict(topics.most_common(10))

    def to_dict(self) -> dict:
        return {
            "gaps": self.gaps[-50:],
            "resolved": self.resolved[-20:],
        }

    def from_dict(self, data: dict):
        self.gaps = data.get("gaps", [])
        self.resolved = data.get("resolved", [])


class ConversationAnalytics:
    """
    Motor de analytics para conversaciones.
    Integra topic tracking, engagement metrics y knowledge gap detection.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "memory_data" / "analytics"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.topics = TopicTracker()
        self.engagement = EngagementMetrics()
        self.gaps = KnowledgeGapDetector()

        # Cargar datos persistidos
        self._load()

    def track_message(self, role: str, content: str, tags: list = None):
        """
        Registra un mensaje para analytics.

        Args:
            role: "user" o "assistant"
            content: contenido del mensaje
            tags: etiquetas opcionales
        """
        # Engagement
        self.engagement.track_message(role, content)

        # Topics (solo mensajes del usuario)
        if role == "user":
            self.topics.record(content)
            self.gaps.track_query(content, tags)

    def track_response(self, agent: str = "", feedback: int = 0,
                       response_time: float = 0.0):
        """
        Registra metricas de respuesta.

        Args:
            agent: agente que respondio
            feedback: +1/-1/0
            response_time: tiempo de respuesta
        """
        if response_time > 0:
            self.engagement.track_response_time(response_time)

        if feedback != 0:
            self.gaps.track_feedback(feedback)

    def end_session(self):
        """Marca fin de sesion y guarda datos."""
        self.engagement.end_session()
        self._save()

    def generate_report(self) -> str:
        """Genera un reporte completo de analytics."""
        lines = ["=== Reporte de Conversacion ==="]

        # Resumen general
        lines.append(f"\nMensajes totales: {self.engagement.total_messages}")
        lines.append(f"Sesiones: {self.engagement.total_sessions}")
        avg_len = self.engagement.get_avg_session_length()
        if avg_len > 0:
            lines.append(f"Promedio sesion: {avg_len:.1f} mensajes")
        avg_time = self.engagement.get_avg_response_time()
        if avg_time > 0:
            lines.append(f"Tiempo respuesta promedio: {avg_time:.1f}s")
        avg_query = self.engagement.get_avg_query_length()
        if avg_query > 0:
            lines.append(f"Largo promedio de query: {avg_query:.0f} chars")

        # Topicos
        top_topics = self.topics.get_top_topics(8)
        if top_topics:
            lines.append("\nTopicos mas frecuentes:")
            for topic, count in top_topics:
                bar = "#" * min(count, 20)
                lines.append(f"  {topic}: {count} {bar}")

        # Tendencia reciente
        trend = self.topics.get_recent_trend()
        if trend:
            lines.append("\nTendencia reciente (ultimos 20 msgs):")
            for topic, count in sorted(trend.items(), key=lambda x: -x[1]):
                lines.append(f"  {topic}: {count}")

        # Horas pico
        peaks = self.engagement.get_peak_hours()
        if peaks:
            lines.append("\nHoras pico de uso:")
            for hour, count in peaks:
                lines.append(f"  {hour}: {count} mensajes")

        # Distribucion por dia
        if self.engagement.messages_per_day:
            lines.append("\nUso por dia:")
            day_order = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
            for day in day_order:
                count = self.engagement.messages_per_day.get(day, 0)
                if count > 0:
                    bar = "#" * min(count, 20)
                    lines.append(f"  {day}: {count} {bar}")

        # Knowledge gaps
        gaps = self.gaps.get_gaps(5)
        if gaps:
            lines.append("\nGaps de conocimiento (respuestas insatisfactorias):")
            for gap in gaps:
                lines.append(f"  - {gap['query'][:80]}")
            gap_topics = self.gaps.get_gap_topics()
            if gap_topics:
                lines.append(f"  Areas con mas gaps: {', '.join(gap_topics.keys())}")

        return "\n".join(lines)

    def status(self) -> str:
        """Estado resumido."""
        top = self.topics.get_top_topics(3)
        top_str = ", ".join(f"{t[0]}({t[1]})" for t in top) if top else "sin datos"
        return (
            f"Analytics: {self.engagement.total_messages} msgs | "
            f"Top: {top_str} | "
            f"Gaps: {len(self.gaps.gaps)}"
        )

    # --- Persistencia ---

    def _save(self):
        """Guarda datos a disco."""
        try:
            data = {
                "topics": self.topics.to_dict(),
                "engagement": self.engagement.to_dict(),
                "gaps": self.gaps.to_dict(),
                "saved_at": time.time(),
            }
            filepath = self.data_dir / "conversation_analytics.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        """Carga datos desde disco."""
        try:
            filepath = self.data_dir / "conversation_analytics.json"
            if not filepath.exists():
                return
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.topics.from_dict(data.get("topics", {}))
            self.engagement.from_dict(data.get("engagement", {}))
            self.gaps.from_dict(data.get("gaps", {}))
        except Exception:
            pass

    def save(self):
        """Save forzado."""
        self._save()
