"""
GENESIS Memory — Sistema de memoria multi-nivel.

3 niveles inspirados en el cerebro humano:
- Corto plazo: Conversacion actual (como la memoria de trabajo)
- Largo plazo: Hechos persistentes entre sesiones (como el hipocampo)
- Emocional: Recuerdos con peso emocional (como la amigdala)

Incluye busqueda semantica con TF-IDF (inspirado en Aetherius).
"""
import json
import math
import time
import re
from pathlib import Path
from typing import Optional
from collections import Counter

from core.safe_io import safe_write_json


# ============================================================
# Motor de busqueda semantica TF-IDF
# ============================================================

class TFIDFSearch:
    """
    Busqueda semantica ligera usando TF-IDF.
    No requiere dependencias externas — implementacion pura en Python.

    Inspirado en Aetherius: busca memorias por similitud conceptual,
    no solo por coincidencia exacta de texto.
    """

    # Stopwords en español e ingles
    STOPWORDS = {
        "de", "la", "el", "en", "y", "a", "los", "del", "las", "un",
        "por", "con", "una", "su", "para", "es", "al", "lo", "como",
        "mas", "pero", "sus", "le", "ya", "o", "fue", "este", "ha",
        "si", "porque", "esta", "son", "entre", "cuando", "muy", "sin",
        "sobre", "ser", "tambien", "me", "hasta", "hay", "donde", "quien",
        "desde", "nos", "durante", "todo", "eso", "esos", "que", "no",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "it", "this", "that", "these", "those", "i", "you", "he",
        "she", "we", "they", "my", "your", "his", "her", "its",
        "and", "but", "or", "not", "so", "if", "then", "than",
    }

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokeniza texto: minusculas, elimina puntuacion, filtra stopwords."""
        text = text.lower()
        # Reemplazar caracteres no alfanumericos con espacio
        text = re.sub(r'[^a-záéíóúüñ0-9\s]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if t not in TFIDFSearch.STOPWORDS and len(t) > 2]

    @staticmethod
    def compute_tf(tokens: list[str]) -> dict[str, float]:
        """Calcula Term Frequency para un documento."""
        counts = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {term: count / total for term, count in counts.items()}

    @staticmethod
    def compute_idf(documents: list[list[str]]) -> dict[str, float]:
        """Calcula Inverse Document Frequency sobre un corpus."""
        n_docs = len(documents)
        if n_docs == 0:
            return {}

        # Contar en cuantos documentos aparece cada termino
        doc_freq = Counter()
        for doc_tokens in documents:
            unique_terms = set(doc_tokens)
            for term in unique_terms:
                doc_freq[term] += 1

        # IDF = log(N / df) + 1 (suavizado)
        return {
            term: math.log(n_docs / df) + 1
            for term, df in doc_freq.items()
        }

    @staticmethod
    def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        """Calcula similitud coseno entre dos vectores TF-IDF."""
        # Producto punto
        common_terms = set(vec_a.keys()) & set(vec_b.keys())
        if not common_terms:
            return 0.0

        dot = sum(vec_a[t] * vec_b[t] for t in common_terms)

        # Magnitudes
        mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
        mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)

    # Cache para IDF pre-computado (evita recalcular en cada busqueda)
    _idf_cache: dict[int, dict[str, float]] = {}
    _idf_cache_hash: int = 0

    @staticmethod
    def search(query: str, documents: list[str], top_k: int = 10) -> list[tuple[int, float]]:
        """
        Busca los documentos mas similares a la query.
        Usa cache de IDF para evitar recalcular en busquedas consecutivas.

        Args:
            query: Texto de busqueda
            documents: Lista de textos (documentos)
            top_k: Cuantos resultados retornar

        Returns:
            Lista de (indice, score) ordenada por relevancia
        """
        if not documents:
            return []

        # Tokenizar todos los documentos + la query
        doc_tokens = [TFIDFSearch.tokenize(doc) for doc in documents]
        query_tokens = TFIDFSearch.tokenize(query)

        if not query_tokens:
            return []

        # Verificar si el corpus cambio (cache de IDF)
        corpus_hash = hash(tuple(len(d) for d in documents))
        if corpus_hash != TFIDFSearch._idf_cache_hash:
            # Recalcular IDF
            TFIDFSearch._idf_cache_hash = corpus_hash
            TFIDFSearch._idf_cache = TFIDFSearch.compute_idf(doc_tokens)

        idf = TFIDFSearch._idf_cache
        # Agregar terminos de la query al IDF si no estan
        query_unique = set(query_tokens)
        n_docs = len(doc_tokens)
        for term in query_unique:
            if term not in idf:
                idf[term] = math.log(n_docs + 1) + 1

        # Vector TF-IDF de la query
        query_tf = TFIDFSearch.compute_tf(query_tokens)
        query_tfidf = {t: tf * idf.get(t, 0) for t, tf in query_tf.items()}

        # Calcular similitud con cada documento
        scores = []
        for idx, tokens in enumerate(doc_tokens):
            if not tokens:
                scores.append((idx, 0.0))
                continue
            doc_tf = TFIDFSearch.compute_tf(tokens)
            doc_tfidf = {t: tf * idf.get(t, 0) for t, tf in doc_tf.items()}
            sim = TFIDFSearch.cosine_similarity(query_tfidf, doc_tfidf)
            scores.append((idx, sim))

        # Ordenar por score descendente y filtrar zeros
        scores.sort(key=lambda x: x[1], reverse=True)
        return [(idx, score) for idx, score in scores[:top_k] if score > 0.0]


class ShortTermMemory:
    """Memoria de corto plazo — contexto de conversacion actual."""

    def __init__(self, max_messages: int = 20):
        self.messages: list[dict] = []
        self.max_messages = max_messages

    def __len__(self) -> int:
        """Cantidad de mensajes en memoria de corto plazo.

        Necesario porque varios call-sites (dashboards, health_monitor,
        proactive) hacen len(memory.short_term) directamente.
        """
        return len(self.messages)

    def add(self, role: str, content: str):
        """Agrega un mensaje a la memoria."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        # Mantener solo los ultimos N mensajes
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_context(self) -> list[dict]:
        """Retorna mensajes formateados para el LLM."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def get_last(self, n: int = 5) -> list[dict]:
        """Retorna los ultimos N mensajes."""
        return self.messages[-n:]

    def clear(self):
        """Limpia la memoria de corto plazo."""
        self.messages.clear()

    def summary(self) -> str:
        """Resume el estado actual."""
        return f"[Corto plazo: {len(self.messages)}/{self.max_messages} mensajes]"


class LongTermMemory:
    """Memoria de largo plazo — hechos persistentes entre sesiones."""

    MAX_MEMORIES = 500  # Limite de memorias para evitar crecimiento infinito

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.memories: list[dict] = self._load()

    def _load(self) -> list[dict]:
        """Carga memorias desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save(self):
        """Persiste memorias a disco de forma atomica y thread-safe.

        Usa safe_write_json (tmp + rename + lock) porque la memoria de largo
        plazo la escriben varios threads daemon (heartbeat, curiosity-gen) y
        los workers de Flask. La escritura directa con open(w) corrompia el
        JSON ante escrituras concurrentes. create_backup=False: el backup
        periodico de backup_all ya cubre el disaster-recovery y recall()
        escribe en cada lectura.
        """
        safe_write_json(self.filepath, self.memories, create_backup=False)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def remember(self, fact: str, category: str = "general", source: str = "conversation"):
        """Almacena un hecho en la memoria de largo plazo."""
        # Evitar duplicados
        for m in self.memories:
            if m["fact"].lower() == fact.lower():
                m["access_count"] += 1
                m["last_accessed"] = time.time()
                self._save()
                return

        self.memories.append({
            "fact": fact,
            "category": category,
            "source": source,
            "created": time.time(),
            "last_accessed": time.time(),
            "access_count": 1,
        })

        # Aplicar limite de memorias
        if len(self.memories) > self.MAX_MEMORIES:
            # Eliminar las menos accedidas y mas viejas
            self.memories.sort(
                key=lambda m: (m["access_count"], m["last_accessed"])
            )
            self.memories = self.memories[-self.MAX_MEMORIES:]

        self._save()

    def recall(self, query: str = "", category: str = "", limit: int = 10,
               semantic: bool = True) -> list[dict]:
        """
        Busca en la memoria de largo plazo.

        Con semantic=True usa TF-IDF para encontrar memorias conceptualmente
        relacionadas, no solo coincidencias textuales.
        """
        results = self.memories

        if category:
            results = [m for m in results if m["category"] == category]

        if query:
            if semantic and len(results) > 1:
                # Busqueda semantica con TF-IDF
                documents = [m["fact"] for m in results]
                scored = TFIDFSearch.search(query, documents, top_k=limit)

                if scored:
                    semantic_results = []
                    for idx, score in scored:
                        mem = results[idx].copy()
                        mem["_relevance"] = round(score, 3)
                        semantic_results.append(mem)
                    results = semantic_results
                else:
                    # Fallback a busqueda por substring
                    query_lower = query.lower()
                    results = [m for m in results if query_lower in m["fact"].lower()]
            else:
                # Busqueda simple por substring
                query_lower = query.lower()
                results = [m for m in results if query_lower in m["fact"].lower()]

        if not query:
            # Sin query: ordenar por frecuencia de acceso
            results.sort(key=lambda x: x["access_count"], reverse=True)

        # Actualizar last_accessed
        for m in results[:limit]:
            # Buscar la memoria original y actualizar
            for original in self.memories:
                if original["fact"] == m["fact"]:
                    original["last_accessed"] = time.time()
                    original["access_count"] += 1
                    break
        self._save()

        return results[:limit]

    def forget(self, fact: str) -> bool:
        """Olvida un hecho especifico."""
        before = len(self.memories)
        self.memories = [m for m in self.memories if m["fact"].lower() != fact.lower()]
        if len(self.memories) < before:
            self._save()
            return True
        return False

    def get_all_formatted(self) -> str:
        """Retorna todas las memorias formateadas como texto."""
        if not self.memories:
            return "No hay memorias de largo plazo."
        lines = []
        for m in self.memories:
            lines.append(f"- [{m['category']}] {m['fact']}")
        return "\n".join(lines)

    def summary(self) -> str:
        """Resume el estado actual."""
        categories = set(m["category"] for m in self.memories)
        return f"[Largo plazo: {len(self.memories)} hechos en {len(categories)} categorias]"


class EmotionalMemory:
    """Memoria emocional — recuerdos con peso/importancia emocional."""

    DECAY_RATE = 0.02  # Cuanto decae el peso por dia
    MAX_MEMORIES = 200  # Limite de recuerdos emocionales

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.memories: list[dict] = self._load()

    def _load(self) -> list[dict]:
        """Carga memorias desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save(self):
        """Persiste memorias emocionales a disco de forma atomica y thread-safe.

        Misma razon que LongTermMemory._save: escritura concurrente desde
        threads daemon. Ver nota alli.
        """
        safe_write_json(self.filepath, self.memories, create_backup=False)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def imprint(self, memory: str, emotion: str, weight: float,
                context: str = ""):
        """
        Imprime un recuerdo con carga emocional.

        Args:
            memory: El contenido del recuerdo
            emotion: Tipo de emocion (curiosidad, satisfaccion, frustracion, etc)
            weight: Importancia 0.0 (trivial) a 1.0 (critico)
            context: Contexto adicional
        """
        weight = max(0.0, min(1.0, weight))

        self.memories.append({
            "memory": memory,
            "emotion": emotion,
            "weight": weight,
            "context": context,
            "created": time.time(),
            "last_recalled": time.time(),
            "recall_count": 0,
        })

        # Aplicar limite
        if len(self.memories) > self.MAX_MEMORIES:
            # Eliminar los de menor peso
            self.memories.sort(key=lambda m: m["weight"])
            self.memories = self.memories[-self.MAX_MEMORIES:]

        self._save()

    def recall_strongest(self, n: int = 5) -> list[dict]:
        """Retorna los N recuerdos con mayor peso emocional (aplicando decay)."""
        self._apply_decay()
        sorted_mems = sorted(self.memories, key=lambda x: x["weight"], reverse=True)
        return sorted_mems[:n]

    def recall_by_emotion(self, emotion: str) -> list[dict]:
        """Retorna recuerdos filtrados por tipo de emocion."""
        return [m for m in self.memories if m["emotion"] == emotion]

    def _apply_decay(self):
        """Aplica decaimiento temporal — los recuerdos pierden peso con el tiempo."""
        now = time.time()
        changed = False
        surviving = []

        for m in self.memories:
            days_old = (now - m["created"]) / 86400
            decay = self.DECAY_RATE * days_old
            m["weight"] = max(0.0, m["weight"] - decay)

            # Olvidar recuerdos con peso casi nulo
            if m["weight"] > 0.01:
                surviving.append(m)
            else:
                changed = True

        if changed or len(surviving) != len(self.memories):
            self.memories = surviving
            self._save()

    def get_emotional_context(self) -> str:
        """Genera un resumen emocional para inyectar en el prompt."""
        if not self.memories:
            return ""

        strongest = self.recall_strongest(5)
        if not strongest:
            return ""

        lines = ["[MEMORIA EMOCIONAL — Recuerdos con mayor peso:]"]
        for m in strongest:
            lines.append(f"  - ({m['emotion']}, peso={m['weight']:.2f}) {m['memory']}")
        return "\n".join(lines)

    def summary(self) -> str:
        """Resume el estado actual."""
        if not self.memories:
            return "[Emocional: vacia]"
        emotions = {}
        for m in self.memories:
            emotions[m["emotion"]] = emotions.get(m["emotion"], 0) + 1
        emo_str = ", ".join(f"{k}:{v}" for k, v in emotions.items())
        return f"[Emocional: {len(self.memories)} recuerdos — {emo_str}]"


class MemorySystem:
    """Sistema unificado de memoria multi-nivel."""

    def __init__(self, long_term_path: Path, emotional_path: Path,
                 short_term_limit: int = 20):
        self.short_term = ShortTermMemory(max_messages=short_term_limit)
        self.long_term = LongTermMemory(filepath=long_term_path)
        self.emotional = EmotionalMemory(filepath=emotional_path)

    def get_full_context(self) -> str:
        """Genera el contexto completo de memoria para inyectar en el prompt."""
        parts = []

        # Memorias de largo plazo
        lt_memories = self.long_term.get_all_formatted()
        if lt_memories != "No hay memorias de largo plazo.":
            parts.append(f"[MEMORIA DE LARGO PLAZO]\n{lt_memories}")

        # Memorias emocionales
        emotional_ctx = self.emotional.get_emotional_context()
        if emotional_ctx:
            parts.append(emotional_ctx)

        return "\n\n".join(parts)

    def get_conversation_messages(self) -> list[dict]:
        """Retorna los mensajes de conversacion para el LLM."""
        return self.short_term.get_context()

    def status(self) -> str:
        """Retorna un resumen de estado de toda la memoria."""
        return (f"  {self.short_term.summary()}\n"
                f"  {self.long_term.summary()}\n"
                f"  {self.emotional.summary()}")
