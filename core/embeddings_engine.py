"""
GENESIS Embeddings Engine — Embeddings locales para busqueda semantica.

Problema:
El RAG actual usa TF-IDF (bag-of-words). No entiende sinonimos,
contexto, ni significado. "auto" y "coche" son palabras distintas
para TF-IDF pero semanticamente identicas.

Solucion:
Un motor de embeddings local que:
1. Genera vectores densos con sentence-transformers (o fallback a TF-IDF)
2. Almacena embeddings en disco para persistencia
3. Busca por similitud coseno (busqueda semantica real)
4. Se integra con el RAG existente como backend mejorado

Hardware: RTX 3060 Ti (8GB VRAM) — sentence-transformers corre en GPU.
Modelo por defecto: all-MiniLM-L6-v2 (80MB, 384 dims, rapido).

Uso:
    engine = EmbeddingsEngine(base_dir=str(BASE_DIR))
    engine.add_text("id1", "Los coches electricos son el futuro")
    results = engine.search("vehiculos del futuro", top_k=5)
"""
import os
import json
import math
import time
import hashlib
import numpy as np
from pathlib import Path
from typing import Optional


class VectorStore:
    """
    Almacen de vectores con busqueda por similitud coseno.

    Almacena embeddings como arrays numpy con metadata asociada.
    Persistencia en disco como JSON + numpy binary.
    """

    def __init__(self, store_path: str = ""):
        self.vectors: dict[str, np.ndarray] = {}  # {id: embedding}
        self.metadata: dict[str, dict] = {}  # {id: {text, source, ...}}
        self.dimension: int = 0
        self.store_path = store_path

        if store_path:
            self._load()

    def add(self, doc_id: str, embedding: np.ndarray, metadata: dict = None):
        """Agrega un vector al store."""
        if self.dimension == 0:
            self.dimension = len(embedding)
        elif len(embedding) != self.dimension:
            raise ValueError(
                f"Dimension mismatch: esperado {self.dimension}, "
                f"recibido {len(embedding)}"
            )

        self.vectors[doc_id] = embedding
        self.metadata[doc_id] = metadata or {}

    def remove(self, doc_id: str) -> bool:
        """Elimina un vector del store."""
        if doc_id in self.vectors:
            del self.vectors[doc_id]
            self.metadata.pop(doc_id, None)
            return True
        return False

    def search(self, query_embedding: np.ndarray, top_k: int = 5,
               min_score: float = 0.0) -> list[dict]:
        """
        Busca los vectores mas similares al query.

        Args:
            query_embedding: Vector de consulta
            top_k: Numero maximo de resultados
            min_score: Score minimo para incluir resultado

        Returns:
            Lista de {id, score, metadata} ordenada por score desc
        """
        if not self.vectors:
            return []

        results = []
        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0:
            return []

        for doc_id, vec in self.vectors.items():
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            # Similitud coseno
            score = float(np.dot(query_embedding, vec) / (query_norm * vec_norm))
            if score >= min_score:
                results.append({
                    "id": doc_id,
                    "score": round(score, 4),
                    "metadata": self.metadata.get(doc_id, {}),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get(self, doc_id: str) -> Optional[np.ndarray]:
        """Obtiene un vector por ID."""
        return self.vectors.get(doc_id)

    def count(self) -> int:
        return len(self.vectors)

    def _save(self):
        """Persiste el store a disco."""
        if not self.store_path:
            return

        path = Path(self.store_path)
        path.mkdir(parents=True, exist_ok=True)

        # Guardar metadata
        meta_file = path / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "dimension": self.dimension,
                "count": len(self.vectors),
                "metadata": self.metadata,
                "ids": list(self.vectors.keys()),
            }, f, ensure_ascii=False)

        # Guardar vectores como numpy binary
        if self.vectors:
            ids = list(self.vectors.keys())
            matrix = np.array([self.vectors[i] for i in ids])
            np.save(str(path / "vectors.npy"), matrix)

    def _load(self):
        """Carga el store desde disco."""
        path = Path(self.store_path)
        meta_file = path / "metadata.json"
        vectors_file = path / "vectors.npy"

        if not meta_file.exists():
            return

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.dimension = data.get("dimension", 0)
            self.metadata = data.get("metadata", {})
            ids = data.get("ids", [])

            if vectors_file.exists() and ids:
                matrix = np.load(str(vectors_file))
                for i, doc_id in enumerate(ids):
                    if i < len(matrix):
                        self.vectors[doc_id] = matrix[i]
        except Exception:
            pass

    def save(self):
        """Guarda el store (alias publico)."""
        self._save()

    def clear(self):
        """Limpia todo el store."""
        self.vectors.clear()
        self.metadata.clear()
        self.dimension = 0


class TFIDFEmbedder:
    """
    Fallback embedder usando TF-IDF cuando sentence-transformers
    no esta disponible.

    Genera vectores sparse basados en frecuencia de terminos.
    No es semantico pero es mejor que nada.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_count = 0
        self.name = "tfidf-fallback"

    def _tokenize(self, text: str) -> list[str]:
        """Tokenizacion simple."""
        text = text.lower()
        # Reemplazar puntuacion
        for ch in ".,;:!?()[]{}\"'/-_":
            text = text.replace(ch, " ")
        return [w for w in text.split() if len(w) > 1]

    def _hash_token(self, token: str) -> int:
        """Hash un token a un indice en [0, dimension)."""
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        return h % self.dimension

    def encode(self, text: str) -> np.ndarray:
        """Genera un embedding TF-IDF para un texto."""
        tokens = self._tokenize(text)
        if not tokens:
            return np.zeros(self.dimension, dtype=np.float32)

        vec = np.zeros(self.dimension, dtype=np.float32)
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        for token, count in tf.items():
            idx = self._hash_token(token)
            weight = count / len(tokens)  # TF normalizado
            vec[idx] += weight

        # Normalizar
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    def encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Genera embeddings para multiples textos."""
        return [self.encode(t) for t in texts]


class EmbeddingsEngine:
    """
    Motor de embeddings de Genesis.

    Intenta usar sentence-transformers (GPU) para embeddings semanticos.
    Si no esta disponible, usa TF-IDF como fallback.
    """

    def __init__(self, base_dir: str = "", model_name: str = ""):
        if not base_dir:
            base_dir = str(Path(__file__).parent.parent)
        self.base_dir = Path(base_dir)

        # Directorio de datos
        self.data_dir = self.base_dir / "embeddings_data"
        self.data_dir.mkdir(exist_ok=True)

        # Modelo
        self.model_name = model_name or "all-MiniLM-L6-v2"
        self.model = None
        self.embedder = None
        self.using_gpu = False
        self.backend = "none"

        # Vector store
        self.store = VectorStore(
            store_path=str(self.data_dir / "vector_store")
        )

        # Stats
        self.total_encoded = 0
        self.total_searches = 0
        self.encode_time_ms = 0.0
        self.search_time_ms = 0.0

        # Intentar inicializar sentence-transformers
        self._init_model()

    def _init_model(self):
        """Intenta cargar sentence-transformers, fallback a TF-IDF."""
        try:
            from sentence_transformers import SentenceTransformer
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = SentenceTransformer(self.model_name, device=device)
            self.using_gpu = device == "cuda"
            self.backend = f"sentence-transformers ({device})"
            self.embedder = self.model
        except ImportError:
            # Fallback a TF-IDF
            self.embedder = TFIDFEmbedder(dimension=384)
            self.backend = "tfidf-fallback"
        except Exception:
            self.embedder = TFIDFEmbedder(dimension=384)
            self.backend = "tfidf-fallback"

    def encode(self, text: str) -> np.ndarray:
        """Genera embedding para un texto."""
        start = time.time()

        if self.model is not None:
            # sentence-transformers
            embedding = self.model.encode(text, convert_to_numpy=True)
        else:
            # TF-IDF fallback
            embedding = self.embedder.encode(text)

        elapsed = (time.time() - start) * 1000
        self.encode_time_ms += elapsed
        self.total_encoded += 1

        return embedding

    def encode_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Genera embeddings para multiples textos (batch es mas eficiente en GPU)."""
        start = time.time()

        if self.model is not None:
            embeddings = self.model.encode(texts, convert_to_numpy=True,
                                           batch_size=32, show_progress_bar=False)
            result = [embeddings[i] for i in range(len(texts))]
        else:
            result = self.embedder.encode_batch(texts)

        elapsed = (time.time() - start) * 1000
        self.encode_time_ms += elapsed
        self.total_encoded += len(texts)

        return result

    def add_text(self, doc_id: str, text: str, source: str = "",
                 extra_metadata: dict = None) -> bool:
        """
        Agrega un texto al vector store.

        Args:
            doc_id: ID unico del documento
            text: Texto a indexar
            source: Fuente del texto (archivo, URL, etc)
            extra_metadata: Metadata adicional

        Returns:
            True si se agrego exitosamente
        """
        try:
            embedding = self.encode(text)
            metadata = {
                "text": text[:500],  # Guardar preview del texto
                "source": source,
                "length": len(text),
                "timestamp": time.time(),
            }
            if extra_metadata:
                metadata.update(extra_metadata)

            self.store.add(doc_id, embedding, metadata)
            return True
        except Exception:
            return False

    def add_texts_batch(self, items: list[dict]) -> int:
        """
        Agrega multiples textos en batch.

        Args:
            items: Lista de {"id": str, "text": str, "source": str}

        Returns:
            Numero de textos agregados exitosamente
        """
        if not items:
            return 0

        texts = [item["text"] for item in items]
        embeddings = self.encode_batch(texts)

        added = 0
        for i, item in enumerate(items):
            try:
                metadata = {
                    "text": item["text"][:500],
                    "source": item.get("source", ""),
                    "length": len(item["text"]),
                    "timestamp": time.time(),
                }
                self.store.add(item["id"], embeddings[i], metadata)
                added += 1
            except Exception:
                pass

        return added

    def search(self, query: str, top_k: int = 5,
               min_score: float = 0.1) -> list[dict]:
        """
        Busqueda semantica.

        Args:
            query: Texto de consulta
            top_k: Numero maximo de resultados
            min_score: Score minimo (0-1)

        Returns:
            Lista de resultados con score y metadata
        """
        start = time.time()

        query_embedding = self.encode(query)
        results = self.store.search(query_embedding, top_k=top_k,
                                     min_score=min_score)

        elapsed = (time.time() - start) * 1000
        self.search_time_ms += elapsed
        self.total_searches += 1

        return results

    def remove(self, doc_id: str) -> bool:
        """Elimina un documento del store."""
        return self.store.remove(doc_id)

    def save(self):
        """Persiste el vector store a disco."""
        self.store.save()

    def clear(self):
        """Limpia todo el vector store."""
        self.store.clear()

    def get_similar(self, doc_id: str, top_k: int = 5) -> list[dict]:
        """Encuentra documentos similares a uno existente."""
        vec = self.store.get(doc_id)
        if vec is None:
            return []
        results = self.store.search(vec, top_k=top_k + 1)
        # Excluir el documento mismo
        return [r for r in results if r["id"] != doc_id][:top_k]

    def get_stats(self) -> dict:
        """Estadisticas del engine."""
        avg_encode = (
            self.encode_time_ms / self.total_encoded
            if self.total_encoded > 0 else 0
        )
        avg_search = (
            self.search_time_ms / self.total_searches
            if self.total_searches > 0 else 0
        )
        return {
            "backend": self.backend,
            "model": self.model_name,
            "using_gpu": self.using_gpu,
            "documents": self.store.count(),
            "dimension": self.store.dimension,
            "total_encoded": self.total_encoded,
            "total_searches": self.total_searches,
            "avg_encode_ms": round(avg_encode, 2),
            "avg_search_ms": round(avg_search, 2),
        }

    def status(self) -> str:
        """Resumen para /status."""
        stats = self.get_stats()
        return (
            f"  Backend: {stats['backend']} | Docs: {stats['documents']} | "
            f"Dim: {stats['dimension']}\n"
            f"  Encoded: {stats['total_encoded']} | Searches: {stats['total_searches']} | "
            f"Avg encode: {stats['avg_encode_ms']}ms"
        )

    def generate_report(self) -> str:
        """Reporte completo del motor de embeddings."""
        stats = self.get_stats()
        lines = [
            "=== EMBEDDINGS ENGINE ===",
            f"  Backend: {stats['backend']}",
            f"  Modelo: {stats['model']}",
            f"  GPU: {'SI' if stats['using_gpu'] else 'NO'}",
            f"  Documentos indexados: {stats['documents']}",
            f"  Dimension: {stats['dimension']}",
            f"",
            f"  STATS:",
            f"    Total encoded: {stats['total_encoded']}",
            f"    Total searches: {stats['total_searches']}",
            f"    Avg encode time: {stats['avg_encode_ms']}ms",
            f"    Avg search time: {stats['avg_search_ms']}ms",
        ]

        if self.store.count() > 0:
            lines.append(f"\n  MUESTRA (5 ultimos docs):")
            recent = sorted(
                self.store.metadata.items(),
                key=lambda x: x[1].get("timestamp", 0),
                reverse=True,
            )[:5]
            for doc_id, meta in recent:
                text_preview = meta.get("text", "")[:60]
                lines.append(f"    {doc_id}: {text_preview}...")

        return "\n".join(lines)
