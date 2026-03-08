"""
GENESIS Semantic Memory — Memoria semantica persistente.

Cada conversacion se indexa automaticamente en embeddings.
Genesis recuerda TODO lo que hablaste, busca por significado
(no por texto exacto) y consolida conocimiento automaticamente.

Flujo:
1. process_input() genera respuesta
2. post_process() indexa la interaccion en embeddings
3. Proximo input: busca interacciones semanticamente similares
4. Inyecta contexto relevante en el prompt

Esto es MEMORIA REAL — no chat history raw, sino conocimiento
destilado y recuperable por significado.
"""
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime


class ConversationEntry:
    """Una entrada de conversacion indexada."""

    def __init__(self, user_input: str, response: str,
                 intent: str = "chat", timestamp: float = 0.0,
                 tags: list = None, quality: float = 0.5):
        self.user_input = user_input
        self.response = response
        self.intent = intent
        self.timestamp = timestamp or time.time()
        self.tags = tags or []
        self.quality = quality  # 0.0-1.0 basado en feedback
        self.entry_id = self._generate_id()

    def _generate_id(self) -> str:
        """Genera un ID unico para la entrada."""
        content = f"{self.user_input}:{self.timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def to_text(self) -> str:
        """Convierte a texto para embedding."""
        return f"Pregunta: {self.user_input}\nRespuesta: {self.response[:500]}"

    def to_dict(self) -> dict:
        return {
            "id": self.entry_id,
            "user_input": self.user_input,
            "response": self.response[:1000],  # Limitar para no explotar el storage
            "intent": self.intent,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "quality": self.quality,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationEntry":
        entry = cls(
            user_input=data["user_input"],
            response=data.get("response", ""),
            intent=data.get("intent", "chat"),
            timestamp=data.get("timestamp", 0),
            tags=data.get("tags", []),
            quality=data.get("quality", 0.5),
        )
        entry.entry_id = data.get("id", entry.entry_id)
        return entry


class SemanticMemory:
    """
    Memoria semantica persistente para Genesis.

    Indexa conversaciones en embeddings y las recupera
    por similitud semantica cuando son relevantes.
    """

    def __init__(self, embeddings_engine=None, base_dir: str = "."):
        """
        Args:
            embeddings_engine: Instancia de EmbeddingsEngine para vectores
            base_dir: Directorio base para persistencia
        """
        self.embeddings = embeddings_engine
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data" / "semantic_memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Metadata de entradas (ligero, en JSON)
        self.entries: dict[str, ConversationEntry] = {}
        self.metadata_file = self.data_dir / "entries.json"

        # Stats
        self.total_indexed = 0
        self.total_recalls = 0
        self.total_hits = 0  # Recalls que retornaron resultados

        # Config
        self.auto_index = True  # Indexar automaticamente cada conversacion
        self.min_input_length = 10  # Ignorar inputs muy cortos
        self.min_response_length = 20  # Ignorar respuestas muy cortas
        self.max_entries = 10000  # Limite de entradas
        self.recall_top_k = 3  # Cuantos resultados traer por recall
        self.recall_min_score = 0.15  # Score minimo para considerar relevante
        self.dedup_threshold = 0.92  # Umbral para considerar duplicado

        # Cargar estado persistido
        self._load()

    def index(self, user_input: str, response: str,
              intent: str = "chat", tags: list = None,
              quality: float = 0.5) -> Optional[str]:
        """
        Indexa una interaccion en la memoria semantica.

        Args:
            user_input: Lo que dijo el usuario
            response: Lo que respondio Genesis
            intent: Tipo de intencion (chat, code, research, etc.)
            tags: Tags opcionales
            quality: Calidad de la interaccion (0.0-1.0)

        Returns:
            ID de la entrada, o None si no se indexo
        """
        if not self.auto_index:
            return None

        # Filtrar interacciones triviales
        if len(user_input.strip()) < self.min_input_length:
            return None
        if len(response.strip()) < self.min_response_length:
            return None
        if response.startswith("[ERROR]") or response.startswith("[TIMEOUT]"):
            return None

        # Crear entrada
        entry = ConversationEntry(
            user_input=user_input,
            response=response,
            intent=intent,
            tags=tags or [],
            quality=quality,
        )

        # Verificar duplicados via embeddings
        if self.embeddings and len(self.entries) > 0:
            similar = self.embeddings.search(entry.to_text(), top_k=1)
            if similar and similar[0]["score"] >= self.dedup_threshold:
                # Actualizar entrada existente en vez de duplicar
                existing_key = similar[0].get("key", "")
                if existing_key in self.entries:
                    old = self.entries[existing_key]
                    # Mantener la de mejor calidad
                    if quality > old.quality:
                        self.entries[existing_key] = entry
                        entry.entry_id = existing_key
                    return None  # No indexar duplicado

        # Indexar en embeddings
        if self.embeddings:
            self.embeddings.add_text(
                key=entry.entry_id,
                text=entry.to_text(),
                metadata={
                    "type": "conversation",
                    "intent": intent,
                    "timestamp": entry.timestamp,
                },
            )

        # Guardar metadata
        self.entries[entry.entry_id] = entry
        self.total_indexed += 1

        # Limitar tamanio
        if len(self.entries) > self.max_entries:
            self._evict_oldest()

        # Persistir periodicamente (cada 10 indexaciones)
        if self.total_indexed % 10 == 0:
            self._save()

        return entry.entry_id

    def recall(self, query: str, top_k: int = 0,
               intent_filter: str = "") -> list[dict]:
        """
        Busca conversaciones pasadas semanticamente similares.

        Args:
            query: Texto de busqueda
            top_k: Cuantos resultados (0 = usar default)
            intent_filter: Filtrar por tipo de intent

        Returns:
            Lista de dicts con user_input, response, score, timestamp
        """
        self.total_recalls += 1
        k = top_k or self.recall_top_k

        if not self.embeddings or len(self.entries) == 0:
            return []

        # Buscar en embeddings
        results = self.embeddings.search(query, top_k=k * 2)  # Pedir mas para filtrar

        recalled = []
        for r in results:
            if r["score"] < self.recall_min_score:
                continue

            entry_id = r.get("key", "")
            entry = self.entries.get(entry_id)
            if not entry:
                continue

            # Filtrar por intent si se especifica
            if intent_filter and entry.intent != intent_filter:
                continue

            recalled.append({
                "user_input": entry.user_input,
                "response": entry.response[:500],
                "intent": entry.intent,
                "score": r["score"],
                "timestamp": entry.timestamp,
                "quality": entry.quality,
                "tags": entry.tags,
                "age_hours": (time.time() - entry.timestamp) / 3600,
            })

            if len(recalled) >= k:
                break

        if recalled:
            self.total_hits += 1

        return recalled

    def get_context_for_prompt(self, user_input: str,
                                max_chars: int = 1500) -> str:
        """
        Genera contexto de memoria semantica para inyectar en el prompt.

        Busca interacciones pasadas relevantes y las formatea
        como contexto adicional para el LLM.
        """
        recalled = self.recall(user_input)
        if not recalled:
            return ""

        parts = ["[MEMORIA SEMANTICA — Conversaciones pasadas relevantes:]"]
        total_chars = len(parts[0])

        for r in recalled:
            age = r["age_hours"]
            if age < 1:
                age_str = f"hace {age * 60:.0f}min"
            elif age < 24:
                age_str = f"hace {age:.0f}h"
            else:
                age_str = f"hace {age / 24:.0f} dias"

            snippet = (
                f"\n- [{age_str}, {r['intent']}] "
                f"Usuario: {r['user_input'][:100]} | "
                f"Tu respuesta: {r['response'][:200]}"
            )

            if total_chars + len(snippet) > max_chars:
                break

            parts.append(snippet)
            total_chars += len(snippet)

        if len(parts) <= 1:
            return ""

        parts.append(
            "\n[Usa estas memorias como contexto si son relevantes. "
            "NO repitas respuestas anteriores.]"
        )
        return "\n".join(parts)

    def update_quality(self, entry_id: str, quality: float):
        """Actualiza la calidad de una entrada (post-feedback)."""
        if entry_id in self.entries:
            self.entries[entry_id].quality = quality

    def get_stats(self) -> dict:
        """Estadisticas de la memoria semantica."""
        return {
            "total_entries": len(self.entries),
            "total_indexed": self.total_indexed,
            "total_recalls": self.total_recalls,
            "total_hits": self.total_hits,
            "hit_rate": (
                f"{self.total_hits / self.total_recalls * 100:.0f}%"
                if self.total_recalls > 0 else "N/A"
            ),
            "auto_index": self.auto_index,
        }

    def status(self) -> str:
        """Resumen para /status."""
        s = self.get_stats()
        return (
            f"  Entradas: {s['total_entries']} | "
            f"Indexadas: {s['total_indexed']} | "
            f"Recalls: {s['total_recalls']} (hits: {s['hit_rate']})"
        )

    def _evict_oldest(self):
        """Elimina las entradas mas antiguas y de menor calidad."""
        if len(self.entries) <= self.max_entries:
            return

        # Ordenar por (quality ASC, timestamp ASC) — eliminar las peores/viejas
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (e.quality, e.timestamp),
        )

        # Eliminar 10% mas antiguas/peores
        to_remove = len(self.entries) - self.max_entries + int(self.max_entries * 0.1)
        for entry in sorted_entries[:to_remove]:
            del self.entries[entry.entry_id]
            if self.embeddings:
                self.embeddings.remove(entry.entry_id)

    def _save(self):
        """Persiste metadata a disco."""
        try:
            data = {
                "entries": {k: v.to_dict() for k, v in self.entries.items()},
                "stats": {
                    "total_indexed": self.total_indexed,
                    "total_recalls": self.total_recalls,
                    "total_hits": self.total_hits,
                },
            }
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # No crashear por persistencia

    def _load(self):
        """Carga metadata desde disco."""
        if not self.metadata_file.exists():
            return

        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry_id, entry_data in data.get("entries", {}).items():
                self.entries[entry_id] = ConversationEntry.from_dict(entry_data)

            stats = data.get("stats", {})
            self.total_indexed = stats.get("total_indexed", len(self.entries))
            self.total_recalls = stats.get("total_recalls", 0)
            self.total_hits = stats.get("total_hits", 0)

        except Exception:
            pass  # No crashear por persistencia corrupta

    def save(self):
        """Guardar estado (public interface)."""
        self._save()
        if self.embeddings:
            self.embeddings.save()

    def clear(self):
        """Limpia toda la memoria semantica."""
        self.entries.clear()
        self.total_indexed = 0
        if self.metadata_file.exists():
            self.metadata_file.unlink()

    def generate_report(self) -> str:
        """Reporte completo de la memoria semantica."""
        lines = [
            "=== MEMORIA SEMANTICA ===",
            f"  Entradas indexadas: {len(self.entries)}",
            f"  Total indexaciones: {self.total_indexed}",
            f"  Total recalls: {self.total_recalls}",
            f"  Hits: {self.total_hits}",
            f"  Auto-index: {'ON' if self.auto_index else 'OFF'}",
        ]

        if self.entries:
            # Mostrar ultimas 5 entradas
            recent = sorted(
                self.entries.values(),
                key=lambda e: e.timestamp,
                reverse=True,
            )[:5]

            lines.append(f"\n  RECIENTES:")
            for entry in recent:
                ts = datetime.fromtimestamp(entry.timestamp).strftime("%d/%m %H:%M")
                lines.append(
                    f"    [{ts}] {entry.intent:8s} | "
                    f"{entry.user_input[:60]}"
                )

            # Distribucion de intents
            intent_counts = {}
            for e in self.entries.values():
                intent_counts[e.intent] = intent_counts.get(e.intent, 0) + 1
            lines.append(f"\n  DISTRIBUCION:")
            for intent, count in sorted(intent_counts.items(),
                                         key=lambda x: -x[1]):
                lines.append(f"    {intent}: {count}")

        return "\n".join(lines)
