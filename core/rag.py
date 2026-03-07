"""
GENESIS — RAG (Retrieval Augmented Generation)
Sistema de indexacion y busqueda semantica de documentos locales.
Permite a Genesis consultar archivos como contexto para respuestas.

Soporta: .txt, .md, .py, .js, .ts, .json, .csv, .html, .css, .yaml, .toml, .cfg, .ini, .log
Chunking inteligente por parrafos con overlap.
Busqueda por TF-IDF (sin dependencias externas).

Uso:
    rag = RAGSystem(base_dir)
    rag.index_file("documento.txt")
    rag.index_directory("./docs")
    results = rag.search("como funciona X", top_k=5)
    context = rag.get_context("pregunta del usuario", max_tokens=500)
"""
import os
import re
import json
import math
import time
import hashlib
from pathlib import Path
from typing import Optional, List
from collections import Counter


# ============================================================
# Chunker — divide documentos en fragmentos indexables
# ============================================================
class DocumentChunker:
    """Divide documentos en chunks con overlap para mejor cobertura."""

    # Extensiones soportadas
    SUPPORTED = {
        ".txt", ".md", ".py", ".js", ".ts", ".json", ".csv",
        ".html", ".css", ".yaml", ".yml", ".toml", ".cfg",
        ".ini", ".log", ".sh", ".bat", ".sql", ".xml",
        ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb",
    }

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Args:
            chunk_size: caracteres maximos por chunk
            overlap: caracteres de solapamiento entre chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def can_process(self, path: str) -> bool:
        """Verifica si el archivo tiene extension soportada."""
        return Path(path).suffix.lower() in self.SUPPORTED

    def read_file(self, path: str) -> Optional[str]:
        """Lee un archivo de texto con manejo de encoding."""
        encodings = ["utf-8", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                return None
        return None

    def chunk_text(self, text: str, source: str = "") -> list:
        """
        Divide texto en chunks con metadata.
        Intenta cortar en limites naturales (parrafos, lineas vacias).

        Returns:
            Lista de dicts: {text, source, chunk_id, char_start, char_end}
        """
        if not text or not text.strip():
            return []

        chunks = []
        # Intentar dividir por parrafos primero
        paragraphs = re.split(r'\n\s*\n', text)

        current = ""
        chunk_id = 0
        char_pos = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Si el parrafo cabe en el chunk actual
            if len(current) + len(para) + 1 <= self.chunk_size:
                current = f"{current}\n{para}" if current else para
            else:
                # Guardar chunk actual si tiene contenido
                if current:
                    chunks.append({
                        "text": current.strip(),
                        "source": source,
                        "chunk_id": chunk_id,
                        "char_start": char_pos,
                        "char_end": char_pos + len(current),
                    })
                    chunk_id += 1
                    # Overlap: tomar los ultimos N caracteres
                    if self.overlap > 0 and len(current) > self.overlap:
                        overlap_text = current[-self.overlap:]
                        char_pos += len(current) - self.overlap
                        current = overlap_text + "\n" + para
                    else:
                        char_pos += len(current)
                        current = para
                else:
                    current = para

                # Si un solo parrafo es mas grande que chunk_size, dividir por lineas
                while len(current) > self.chunk_size:
                    cut_point = current[:self.chunk_size].rfind('\n')
                    if cut_point <= 0:
                        cut_point = self.chunk_size

                    chunks.append({
                        "text": current[:cut_point].strip(),
                        "source": source,
                        "chunk_id": chunk_id,
                        "char_start": char_pos,
                        "char_end": char_pos + cut_point,
                    })
                    chunk_id += 1
                    char_pos += cut_point - self.overlap
                    current = current[cut_point - self.overlap:] if self.overlap > 0 else current[cut_point:]

        # Ultimo chunk
        if current.strip():
            chunks.append({
                "text": current.strip(),
                "source": source,
                "chunk_id": chunk_id,
                "char_start": char_pos,
                "char_end": char_pos + len(current),
            })

        return chunks


# ============================================================
# TF-IDF Vectorizer — busqueda semantica sin dependencias
# ============================================================
class RAGVectorizer:
    """Vectorizador TF-IDF para busqueda semantica en chunks."""

    # Stopwords en espanol e ingles (las mas comunes)
    STOPWORDS = {
        "el", "la", "los", "las", "un", "una", "de", "del", "en", "y",
        "que", "es", "por", "con", "para", "al", "se", "no", "lo", "le",
        "su", "como", "mas", "pero", "sus", "ya", "fue", "este", "ha",
        "si", "entre", "cuando", "muy", "sin", "sobre", "ser", "tiene",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "is", "it", "this", "that", "are",
        "was", "be", "has", "had", "not", "from", "as", "do", "if",
    }

    def __init__(self):
        self.vocabulary = {}   # word -> index
        self.idf = {}          # word -> idf score
        self.doc_count = 0

    def _tokenize(self, text: str) -> list:
        """Tokeniza texto en palabras normalizadas."""
        words = re.findall(r'[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ_]\w{2,}', text.lower())
        return [w for w in words if w not in self.STOPWORDS]

    def fit(self, documents: list):
        """Construye vocabulario e IDF desde lista de textos."""
        self.doc_count = len(documents)
        if self.doc_count == 0:
            return

        # Contar en cuantos docs aparece cada palabra
        doc_freq = Counter()
        for doc in documents:
            unique_words = set(self._tokenize(doc))
            doc_freq.update(unique_words)

        # Calcular IDF
        self.vocabulary = {}
        self.idf = {}
        for idx, (word, freq) in enumerate(doc_freq.items()):
            self.vocabulary[word] = idx
            # IDF con suavizado logaritmico
            self.idf[word] = math.log((self.doc_count + 1) / (freq + 1)) + 1

    def vectorize(self, text: str) -> dict:
        """Convierte texto en vector TF-IDF sparse (dict word->score)."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        # Term frequency
        tf = Counter(tokens)
        total = len(tokens)

        # TF-IDF
        vector = {}
        for word, count in tf.items():
            if word in self.idf:
                tf_score = count / total
                vector[word] = tf_score * self.idf[word]

        return vector

    def similarity(self, vec_a: dict, vec_b: dict) -> float:
        """Cosine similarity entre dos vectores sparse."""
        if not vec_a or not vec_b:
            return 0.0

        # Dot product
        common_keys = set(vec_a.keys()) & set(vec_b.keys())
        if not common_keys:
            return 0.0

        dot = sum(vec_a[k] * vec_b[k] for k in common_keys)

        # Magnitudes
        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot / (mag_a * mag_b)


# ============================================================
# RAG System — sistema principal
# ============================================================
class RAGSystem:
    """
    Sistema RAG completo: indexa documentos, busca por similaridad,
    y genera contexto para inyectar en prompts del LLM.
    """

    def __init__(self, base_dir: str = ".", persist_file: str = "rag_index.json"):
        self.base_dir = Path(base_dir)
        self.persist_path = self.base_dir / "memory_data" / persist_file
        self.chunker = DocumentChunker(chunk_size=500, overlap=50)
        self.vectorizer = RAGVectorizer()

        # Almacenamiento
        self.chunks = []          # Lista de chunks con metadata
        self.vectors = []         # Vectores TF-IDF correspondientes
        self.indexed_files = {}   # path -> {hash, timestamp, chunk_count}

        # Stats
        self.total_queries = 0
        self.total_indexed = 0

        # Cargar indice persistido
        self._load_index()

    def _file_hash(self, path: str) -> str:
        """Hash MD5 del contenido para detectar cambios."""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def index_file(self, path: str, force: bool = False) -> dict:
        """
        Indexa un archivo individual.

        Args:
            path: ruta al archivo
            force: re-indexar aunque no haya cambiado

        Returns:
            dict con resultado: {success, chunks_added, message}
        """
        path = str(Path(path).resolve())

        if not os.path.isfile(path):
            return {"success": False, "chunks_added": 0, "message": f"Archivo no encontrado: {path}"}

        if not self.chunker.can_process(path):
            ext = Path(path).suffix
            return {"success": False, "chunks_added": 0, "message": f"Extension no soportada: {ext}"}

        # Verificar si ya esta indexado y no ha cambiado
        file_hash = self._file_hash(path)
        if not force and path in self.indexed_files:
            if self.indexed_files[path].get("hash") == file_hash:
                return {"success": True, "chunks_added": 0, "message": "Archivo sin cambios, ya indexado"}

        # Leer y chunkar
        content = self.chunker.read_file(path)
        if content is None:
            return {"success": False, "chunks_added": 0, "message": "Error al leer archivo"}

        new_chunks = self.chunker.chunk_text(content, source=path)
        if not new_chunks:
            return {"success": True, "chunks_added": 0, "message": "Archivo vacio o sin contenido util"}

        # Remover chunks anteriores de este archivo si existian
        self._remove_file_chunks(path)

        # Agregar nuevos chunks
        self.chunks.extend(new_chunks)

        # Registrar archivo indexado
        self.indexed_files[path] = {
            "hash": file_hash,
            "timestamp": time.time(),
            "chunk_count": len(new_chunks),
        }
        self.total_indexed += 1

        # Reconstruir indice TF-IDF
        self._rebuild_vectors()

        # Persistir
        self._save_index()

        return {"success": True, "chunks_added": len(new_chunks), "message": f"Indexado: {len(new_chunks)} chunks"}

    def index_directory(self, dir_path: str, recursive: bool = True, force: bool = False) -> dict:
        """
        Indexa todos los archivos soportados en un directorio.

        Returns:
            dict con resultado: {files_processed, chunks_total, errors}
        """
        dir_path = Path(dir_path).resolve()
        if not dir_path.is_dir():
            return {"files_processed": 0, "chunks_total": 0, "errors": ["Directorio no encontrado"]}

        files_processed = 0
        chunks_total = 0
        errors = []

        # Obtener archivos
        if recursive:
            files = list(dir_path.rglob("*"))
        else:
            files = list(dir_path.glob("*"))

        for f in files:
            if not f.is_file():
                continue
            if not self.chunker.can_process(str(f)):
                continue
            # Excluir directorios ocultos y __pycache__
            parts = f.parts
            if any(p.startswith('.') or p == '__pycache__' or p == 'node_modules' for p in parts):
                continue
            # Limite de tamano: 1MB
            if f.stat().st_size > 1_000_000:
                continue

            result = self.index_file(str(f), force=force)
            if result["success"]:
                files_processed += 1
                chunks_total += result["chunks_added"]
            else:
                errors.append(f"{f.name}: {result['message']}")

        return {
            "files_processed": files_processed,
            "chunks_total": chunks_total,
            "errors": errors,
        }

    def search(self, query: str, top_k: int = 5, min_score: float = 0.1) -> list:
        """
        Busca chunks relevantes para una consulta.

        Args:
            query: texto de busqueda
            top_k: maximo de resultados
            min_score: score minimo para incluir

        Returns:
            Lista de dicts: {text, source, score, chunk_id}
        """
        if not self.chunks or not self.vectors:
            return []

        self.total_queries += 1

        query_vec = self.vectorizer.vectorize(query)
        if not query_vec:
            return []

        # Calcular similaridad con todos los chunks
        scored = []
        for i, chunk_vec in enumerate(self.vectors):
            score = self.vectorizer.similarity(query_vec, chunk_vec)
            if score >= min_score:
                scored.append({
                    "text": self.chunks[i]["text"],
                    "source": self.chunks[i]["source"],
                    "score": round(score, 4),
                    "chunk_id": self.chunks[i]["chunk_id"],
                })

        # Ordenar por score descendente
        scored.sort(key=lambda x: x["score"], reverse=True)

        return scored[:top_k]

    def get_context(self, query: str, max_chars: int = 2000, top_k: int = 5) -> str:
        """
        Genera contexto formateado listo para inyectar en el prompt.

        Args:
            query: consulta del usuario
            max_chars: limite de caracteres del contexto
            top_k: maximo de chunks a considerar

        Returns:
            String formateado con los chunks relevantes
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for r in results:
            chunk_text = r["text"]
            source_name = Path(r["source"]).name
            entry = f"[Fuente: {source_name} | Relevancia: {r['score']:.0%}]\n{chunk_text}"

            if total_chars + len(entry) > max_chars:
                # Truncar ultimo chunk si es necesario
                remaining = max_chars - total_chars - 50
                if remaining > 100:
                    context_parts.append(entry[:remaining] + "...")
                break

            context_parts.append(entry)
            total_chars += len(entry)

        if not context_parts:
            return ""

        return "--- CONTEXTO RAG ---\n" + "\n\n".join(context_parts) + "\n--- FIN CONTEXTO ---"

    def remove_file(self, path: str) -> bool:
        """Elimina un archivo del indice."""
        path = str(Path(path).resolve())
        if path not in self.indexed_files:
            return False

        self._remove_file_chunks(path)
        del self.indexed_files[path]
        self._rebuild_vectors()
        self._save_index()
        return True

    def clear(self):
        """Limpia todo el indice RAG."""
        self.chunks = []
        self.vectors = []
        self.indexed_files = {}
        self._save_index()

    def status(self) -> str:
        """Retorna estado del sistema RAG."""
        lines = [
            "=== RAG System ===",
            f"  Archivos indexados: {len(self.indexed_files)}",
            f"  Chunks totales: {len(self.chunks)}",
            f"  Vocabulario: {len(self.vectorizer.vocabulary)} terminos",
            f"  Consultas realizadas: {self.total_queries}",
        ]
        if self.indexed_files:
            lines.append("  Archivos:")
            for path, info in list(self.indexed_files.items())[:10]:
                name = Path(path).name
                lines.append(f"    - {name} ({info['chunk_count']} chunks)")
            if len(self.indexed_files) > 10:
                lines.append(f"    ... y {len(self.indexed_files) - 10} mas")
        return "\n".join(lines)

    # --- Internos ---

    def _remove_file_chunks(self, path: str):
        """Elimina chunks de un archivo especifico."""
        self.chunks = [c for c in self.chunks if c["source"] != path]

    def _rebuild_vectors(self):
        """Reconstruye vectores TF-IDF para todos los chunks."""
        if not self.chunks:
            self.vectors = []
            return
        texts = [c["text"] for c in self.chunks]
        self.vectorizer.fit(texts)
        self.vectors = [self.vectorizer.vectorize(t) for t in texts]

    def _save_index(self):
        """Persiste el indice a disco."""
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "chunks": self.chunks,
                "indexed_files": self.indexed_files,
                "total_queries": self.total_queries,
                "total_indexed": self.total_indexed,
            }
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_index(self):
        """Carga indice desde disco."""
        try:
            if self.persist_path.exists():
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = data.get("chunks", [])
                self.indexed_files = data.get("indexed_files", {})
                self.total_queries = data.get("total_queries", 0)
                self.total_indexed = data.get("total_indexed", 0)
                # Reconstruir vectores desde chunks cargados
                if self.chunks:
                    self._rebuild_vectors()
        except Exception:
            pass
