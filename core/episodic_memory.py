"""
GENESIS — Episodic Memory (v2.4)

Memoria episódica: Genesis recuerda CUÁNDO pasaron las cosas,
QUÉ temas se trataron, y el CONTEXTO emocional de cada sesión.

Componentes:
- Episode: un episodio (sesión o segmento de conversación)
- EpisodeBuilder: construye episodios desde historial de conversación
- TimelineIndex: índice temporal para queries por fecha/rango
- EpisodicMemory: coordinador principal con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta


class Episode:
    """Un episodio: segmento de conversación con contexto temporal."""

    def __init__(self, episode_id: str = None, timestamp: float = None):
        self.episode_id = episode_id or hashlib.md5(
            f"ep_{time.time()}".encode()
        ).hexdigest()[:10]
        self.timestamp = timestamp or time.time()
        self.ended_at = 0
        self.topics = []           # Lista de temas detectados
        self.summary = ""          # Resumen del episodio
        self.emotional_tone = "neutral"  # neutral, positive, negative, curious, frustrated
        self.key_facts = []        # Hechos clave extraídos
        self.message_count = 0     # Mensajes en este episodio
        self.user_queries = []     # Queries del usuario (max 10)
        self.tags = []             # Tags del contenido

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or time.time()
        return max(0, end - self.timestamp)

    @property
    def date_str(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M")

    @property
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600

    def to_text(self) -> str:
        """Representación textual para inyectar en prompts."""
        lines = [f"[Episodio {self.date_str}]"]
        if self.topics:
            lines.append(f"  Temas: {', '.join(self.topics[:5])}")
        if self.summary:
            lines.append(f"  Resumen: {self.summary[:200]}")
        if self.key_facts:
            for fact in self.key_facts[:3]:
                lines.append(f"  - {fact[:100]}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.episode_id,
            "timestamp": self.timestamp,
            "ended_at": self.ended_at,
            "topics": self.topics[:20],
            "summary": self.summary[:500],
            "emotional_tone": self.emotional_tone,
            "key_facts": self.key_facts[:20],
            "message_count": self.message_count,
            "user_queries": self.user_queries[:10],
            "tags": self.tags[:15],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Episode":
        ep = cls(
            episode_id=data.get("id"),
            timestamp=data.get("timestamp", time.time()),
        )
        ep.ended_at = data.get("ended_at", 0)
        ep.topics = data.get("topics", [])
        ep.summary = data.get("summary", "")
        ep.emotional_tone = data.get("emotional_tone", "neutral")
        ep.key_facts = data.get("key_facts", [])
        ep.message_count = data.get("message_count", 0)
        ep.user_queries = data.get("user_queries", [])
        ep.tags = data.get("tags", [])
        return ep


class EpisodeBuilder:
    """Construye episodios desde interacciones de conversación."""

    # Palabras clave por categoría para detección de temas
    TOPIC_KEYWORDS = {
        "programacion": ["codigo", "funcion", "variable", "python", "javascript",
                         "programa", "script", "compilar", "debugger", "algorithm"],
        "seguridad": ["hack", "exploit", "vulnerabilidad", "password", "cifrado",
                      "firewall", "pentest", "osint", "malware", "encrypt"],
        "ia_ml": ["modelo", "neural", "training", "dataset", "embeddings",
                  "transformer", "llm", "machine learning", "deep learning", "gpu"],
        "web": ["html", "css", "api", "servidor", "frontend", "backend",
                "react", "flask", "django", "http"],
        "sistema": ["linux", "windows", "docker", "kubernetes", "deploy",
                    "servidor", "terminal", "bash", "proceso", "servicio"],
        "datos": ["database", "sql", "json", "csv", "tabla", "query",
                  "mongodb", "redis", "cache", "indice"],
        "general": ["ayuda", "explica", "como", "que es", "por que",
                    "tutorial", "ejemplo", "documentacion"],
    }

    # Indicadores de tono emocional
    TONE_INDICATORS = {
        "positive": ["gracias", "excelente", "perfecto", "genial", "increible",
                     "bien", "bueno", "funciona", "resuelto", "listo"],
        "negative": ["error", "fallo", "no funciona", "problema", "bug",
                     "mal", "roto", "crashea", "imposible"],
        "curious": ["como", "por que", "que pasa", "interesante", "curioso",
                    "investigar", "explorar", "aprender"],
        "frustrated": ["no entiendo", "otra vez", "sigue sin", "no puede ser",
                       "ya intente", "no sirve"],
    }

    def build_episode(self, messages: list, max_queries: int = 10) -> Episode:
        """
        Construye un episodio desde una lista de mensajes.
        Cada mensaje es dict con 'role' y 'content'.
        """
        ep = Episode()
        ep.message_count = len(messages)

        all_text = ""
        for msg in messages:
            content = msg.get("content", "")
            all_text += f" {content}"
            if msg.get("role") == "user" and len(ep.user_queries) < max_queries:
                ep.user_queries.append(content[:200])

        # Detectar temas
        ep.topics = self._detect_topics(all_text)

        # Detectar tono
        ep.emotional_tone = self._detect_tone(all_text)

        # Extraer hechos clave
        ep.key_facts = self._extract_facts(messages)

        # Generar resumen básico
        ep.summary = self._generate_summary(messages, ep.topics)

        # Tags
        ep.tags = self._extract_tags(all_text)

        return ep

    def _detect_topics(self, text: str) -> list:
        """Detecta temas principales del texto."""
        text_lower = text.lower()
        scored = {}

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count >= 2:
                scored[topic] = count

        # Ordenar por frecuencia
        sorted_topics = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_topics[:5]]

    def _detect_tone(self, text: str) -> str:
        """Detecta el tono emocional predominante."""
        text_lower = text.lower()
        scores = {}

        for tone, indicators in self.TONE_INDICATORS.items():
            scores[tone] = sum(1 for ind in indicators if ind in text_lower)

        if not any(scores.values()):
            return "neutral"

        return max(scores, key=scores.get)

    def _extract_facts(self, messages: list, max_facts: int = 10) -> list:
        """Extrae hechos clave de la conversación."""
        facts = []
        for msg in messages:
            content = msg.get("content", "")
            if msg.get("role") == "assistant" and len(content) > 50:
                # Buscar oraciones que parecen hechos definitorios
                sentences = re.split(r'[.!]\s+', content)
                for sent in sentences:
                    sent = sent.strip()
                    if 20 < len(sent) < 200:
                        # Oraciones con patrones de definición o explicación
                        if any(p in sent.lower() for p in
                               ["es un", "es una", "permite", "sirve para",
                                "se usa", "funciona", "significa", "consiste"]):
                            facts.append(sent)
                            if len(facts) >= max_facts:
                                return facts
        return facts

    def _generate_summary(self, messages: list, topics: list) -> str:
        """Genera un resumen básico del episodio."""
        user_msgs = [m["content"][:100] for m in messages
                     if m.get("role") == "user"]
        if not user_msgs:
            return "Sesión sin interacciones del usuario."

        topic_str = ", ".join(topics[:3]) if topics else "varios temas"
        n = len(user_msgs)
        first = user_msgs[0][:80]

        summary = f"Conversación de {n} mensajes sobre {topic_str}. "
        summary += f"Inicio: \"{first}\""
        return summary[:300]

    def _extract_tags(self, text: str) -> list:
        """Extrae tags del contenido."""
        text_lower = text.lower()
        tags = set()

        tech_terms = [
            "python", "javascript", "docker", "git", "linux", "api",
            "react", "flask", "django", "sql", "html", "css",
            "tensorflow", "pytorch", "cuda", "nginx", "redis",
        ]
        for term in tech_terms:
            if term in text_lower:
                tags.add(term)

        return list(tags)[:15]


class TimelineIndex:
    """Índice temporal para búsquedas por fecha/rango."""

    def __init__(self):
        self.episodes = []  # Ordenados por timestamp

    def add(self, episode: Episode):
        """Agrega un episodio manteniendo orden temporal."""
        self.episodes.append(episode)
        self.episodes.sort(key=lambda e: e.timestamp)

    def query_range(self, start_ts: float, end_ts: float) -> list:
        """Episodios dentro de un rango de timestamps."""
        return [e for e in self.episodes
                if start_ts <= e.timestamp <= end_ts]

    def query_last_n(self, n: int) -> list:
        """Últimos N episodios."""
        return self.episodes[-n:] if self.episodes else []

    def query_last_hours(self, hours: float) -> list:
        """Episodios de las últimas N horas."""
        cutoff = time.time() - (hours * 3600)
        return [e for e in self.episodes if e.timestamp >= cutoff]

    def query_by_topic(self, topic: str) -> list:
        """Episodios que contienen un tema específico."""
        topic_lower = topic.lower()
        return [e for e in self.episodes
                if any(topic_lower in t.lower() for t in e.topics)]

    def query_by_keyword(self, keyword: str) -> list:
        """Episodios que mencionan una keyword en queries o facts."""
        kw_lower = keyword.lower()
        results = []
        for ep in self.episodes:
            text = " ".join(ep.user_queries + ep.key_facts + ep.topics).lower()
            if kw_lower in text:
                results.append(ep)
        return results

    @property
    def count(self) -> int:
        return len(self.episodes)

    def to_list(self) -> list:
        return [e.to_dict() for e in self.episodes]

    def load_list(self, data: list):
        self.episodes = [Episode.from_dict(d) for d in data]
        self.episodes.sort(key=lambda e: e.timestamp)


class EpisodicMemory:
    """
    Coordinador de memoria episódica.
    Gestiona episodios con persistencia y queries temporales.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/episodic_memory")
        self.data_file = self.base_dir / "episodes.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.timeline = TimelineIndex()
        self.builder = EpisodeBuilder()
        self.current_episode = None
        self.max_episodes = 500
        self.total_episodes = 0
        self.total_queries = 0
        self.enabled = True

        self._load()

    def start_episode(self) -> Episode:
        """Inicia un nuevo episodio (nueva sesión)."""
        if self.current_episode:
            self.end_episode()

        self.current_episode = Episode()
        return self.current_episode

    def end_episode(self, messages: list = None):
        """Finaliza el episodio actual y lo almacena."""
        if not self.current_episode:
            return

        self.current_episode.ended_at = time.time()

        # Si hay mensajes, enriquecer el episodio
        if messages and len(messages) >= 2:
            built = self.builder.build_episode(messages)
            self.current_episode.topics = built.topics
            self.current_episode.summary = built.summary
            self.current_episode.emotional_tone = built.emotional_tone
            self.current_episode.key_facts = built.key_facts
            self.current_episode.message_count = built.message_count
            self.current_episode.user_queries = built.user_queries
            self.current_episode.tags = built.tags

        # Almacenar en timeline
        self.timeline.add(self.current_episode)
        self.total_episodes += 1

        # Evicción si excede máximo
        if self.timeline.count > self.max_episodes:
            self._evict()

        self.current_episode = None

    def record_message(self, role: str, content: str):
        """Registra un mensaje en el episodio actual."""
        if not self.current_episode:
            self.start_episode()

        self.current_episode.message_count += 1
        if role == "user" and len(self.current_episode.user_queries) < 10:
            self.current_episode.user_queries.append(content[:200])

    def recall_recent(self, n: int = 5) -> list:
        """Recuerda los últimos N episodios."""
        self.total_queries += 1
        return self.timeline.query_last_n(n)

    def recall_by_topic(self, topic: str) -> list:
        """Recuerda episodios sobre un tema."""
        self.total_queries += 1
        return self.timeline.query_by_topic(topic)

    def recall_by_keyword(self, keyword: str) -> list:
        """Recuerda episodios que mencionan una keyword."""
        self.total_queries += 1
        return self.timeline.query_by_keyword(keyword)

    def recall_last_hours(self, hours: float = 24) -> list:
        """Episodios de las últimas N horas."""
        self.total_queries += 1
        return self.timeline.query_last_hours(hours)

    def get_context_for_prompt(self, user_input: str, max_chars: int = 600) -> str:
        """
        Genera contexto temporal para inyectar en el prompt.
        Busca episodios relevantes al input actual.
        """
        if not self.enabled or not self.timeline.episodes:
            return ""

        # Buscar episodios relevantes por keywords del input
        input_words = set(
            w for w in re.findall(r'\b\w+\b', user_input.lower()) if len(w) > 3
        )

        relevant = []
        for ep in reversed(self.timeline.episodes[-20:]):  # Últimos 20
            ep_text = " ".join(ep.topics + ep.user_queries + ep.tags).lower()
            ep_words = set(re.findall(r'\b\w+\b', ep_text))
            overlap = len(input_words & ep_words)
            if overlap >= 2:
                relevant.append((overlap, ep))

        if not relevant:
            return ""

        relevant.sort(key=lambda x: x[0], reverse=True)

        lines = ["[CONTEXTO DE EPISODIOS ANTERIORES]"]
        total_chars = 0
        for _, ep in relevant[:3]:
            text = ep.to_text()
            if total_chars + len(text) > max_chars:
                break
            lines.append(text)
            total_chars += len(text)

        return "\n".join(lines) if len(lines) > 1 else ""

    def get_temporal_summary(self) -> str:
        """Resumen temporal: cuándo fue la última sesión, frecuencia, etc."""
        if not self.timeline.episodes:
            return "Sin episodios registrados."

        last = self.timeline.episodes[-1]
        hours_ago = last.age_hours

        if hours_ago < 1:
            time_str = f"hace {int(hours_ago * 60)} minutos"
        elif hours_ago < 24:
            time_str = f"hace {int(hours_ago)} horas"
        else:
            days = int(hours_ago / 24)
            time_str = f"hace {days} día{'s' if days > 1 else ''}"

        last_24h = len(self.timeline.query_last_hours(24))
        last_7d = len(self.timeline.query_last_hours(168))

        return (f"Último episodio: {time_str}. "
                f"Últimas 24h: {last_24h} episodios. "
                f"Última semana: {last_7d} episodios.")

    def get_stats(self) -> dict:
        """Estadísticas de memoria episódica."""
        return {
            "total_episodes": self.total_episodes,
            "stored_episodes": self.timeline.count,
            "total_queries": self.total_queries,
            "current_episode_active": self.current_episode is not None,
            "temporal_summary": self.get_temporal_summary(),
        }

    def status(self) -> str:
        """Status de una línea."""
        return (f"Episodios: {self.timeline.count} almacenados | "
                f"Total: {self.total_episodes} | "
                f"Queries: {self.total_queries}")

    def generate_report(self) -> str:
        """Reporte detallado."""
        lines = ["=== EPISODIC MEMORY REPORT ==="]
        lines.append(f"Total episodios creados: {self.total_episodes}")
        lines.append(f"Episodios almacenados: {self.timeline.count}")
        lines.append(f"Total queries: {self.total_queries}")
        lines.append(f"Max episodios: {self.max_episodes}")
        lines.append(f"Temporal: {self.get_temporal_summary()}")

        if self.timeline.episodes:
            lines.append("\nÚltimos 5 episodios:")
            for ep in self.timeline.query_last_n(5):
                topics = ", ".join(ep.topics[:3]) if ep.topics else "sin temas"
                lines.append(f"  [{ep.date_str}] {topics} ({ep.message_count} msgs)")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado a disco."""
        data = {
            "total_episodes": self.total_episodes,
            "total_queries": self.total_queries,
            "episodes": self.timeline.to_list(),
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        """Carga estado desde disco."""
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_episodes = data.get("total_episodes", 0)
            self.total_queries = data.get("total_queries", 0)
            self.timeline.load_list(data.get("episodes", []))
        except Exception:
            pass

    def clear(self):
        """Limpia toda la memoria episódica."""
        self.timeline = TimelineIndex()
        self.current_episode = None
        self.total_episodes = 0
        self.total_queries = 0

    def _evict(self):
        """Elimina episodios más antiguos cuando se excede el máximo."""
        while self.timeline.count > self.max_episodes:
            if self.timeline.episodes:
                self.timeline.episodes.pop(0)
