"""
GENESIS Code Memory — Memoria de soluciones de codigo.

Guarda snippets de codigo que funcionaron exitosamente.
Cuando Genesis necesita programar algo similar, busca en su
memoria de codigo para tener una referencia.

Usa TF-IDF simple para buscar por similitud de texto.
"""
import json
import time
import math
import re
from pathlib import Path
from typing import Optional
from collections import Counter


class CodeMemory:
    """
    Almacena soluciones de codigo exitosas para reutilizacion.

    Cada entrada tiene:
    - task: Descripcion de lo que se pidio
    - code: El codigo que funciono
    - language: Lenguaje (python, javascript, etc.)
    - output: La salida exitosa del codigo
    - tags: Palabras clave para busqueda
    - used_count: Cuantas veces se reutilizo
    - created_at: Timestamp de creacion
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.solutions: list[dict] = []
        self._load()

    def _load(self):
        """Carga soluciones desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.solutions = json.load(f)
            except (json.JSONDecodeError, Exception):
                self.solutions = []

    def _save(self):
        """Guarda soluciones a disco."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.solutions, f, ensure_ascii=False, indent=2)

    def store(self, task: str, code: str, output: str,
              language: str = "python") -> dict:
        """
        Guarda una solucion de codigo exitosa.

        Args:
            task: Descripcion de lo que se pidio
            code: El codigo que funciono
            output: La salida exitosa
            language: Lenguaje de programacion

        Returns:
            La solucion guardada
        """
        # Extraer tags automaticamente del task y codigo
        tags = self._extract_tags(task, code)

        solution = {
            "task": task[:500],
            "code": code[:5000],
            "output": output[:1000],
            "language": language,
            "tags": tags,
            "used_count": 0,
            "created_at": time.time(),
            "success": True,
        }

        # Evitar duplicados exactos
        for existing in self.solutions:
            if existing["code"].strip() == code.strip():
                return existing

        self.solutions.append(solution)

        # Limitar a 200 soluciones (eliminar las mas viejas y menos usadas)
        if len(self.solutions) > 200:
            self.solutions.sort(
                key=lambda s: (s["used_count"], s["created_at"])
            )
            self.solutions = self.solutions[-200:]

        self._save()
        return solution

    def search(self, query: str, max_results: int = 3) -> list[dict]:
        """
        Busca soluciones similares usando TF-IDF simple.

        Args:
            query: Descripcion de lo que se necesita
            max_results: Maximo de resultados

        Returns:
            Lista de soluciones relevantes ordenadas por similitud
        """
        if not self.solutions:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Calcular IDF
        doc_count = len(self.solutions)
        idf = {}
        for token in set(query_tokens):
            docs_with_token = sum(
                1 for s in self.solutions
                if token in self._tokenize(s["task"] + " " + " ".join(s["tags"]))
            )
            idf[token] = math.log(
                (doc_count + 1) / (docs_with_token + 1)
            ) + 1

        # Calcular similaridad para cada solucion
        scored = []
        for sol in self.solutions:
            doc_tokens = self._tokenize(
                sol["task"] + " " + " ".join(sol["tags"])
            )
            if not doc_tokens:
                continue

            doc_tf = Counter(doc_tokens)
            query_tf = Counter(query_tokens)

            # Cosine similarity con TF-IDF
            score = 0.0
            for token in set(query_tokens) & set(doc_tokens):
                tf_q = query_tf[token] / len(query_tokens)
                tf_d = doc_tf[token] / len(doc_tokens)
                w = idf.get(token, 1.0)
                score += (tf_q * w) * (tf_d * w)

            # Bonus por uso frecuente
            score += sol["used_count"] * 0.05

            if score > 0.1:
                scored.append((score, sol))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:max_results]]

    def get_context_for_prompt(self, query: str) -> str:
        """
        Genera contexto de codigo para inyectar en el system prompt.

        Args:
            query: Lo que el usuario pidio

        Returns:
            Texto formateado con soluciones relevantes
        """
        results = self.search(query, max_results=2)
        if not results:
            return ""

        lines = ["[CODIGO PREVIO EXITOSO — Usa como referencia, NO copies exacto:]"]
        for i, sol in enumerate(results):
            lines.append(f"\nReferencia {i+1}: {sol['task']}")
            lines.append(f"```{sol['language']}")
            # Solo mostrar primeras 30 lineas para no llenar el contexto
            code_lines = sol["code"].split("\n")[:30]
            lines.append("\n".join(code_lines))
            if len(sol["code"].split("\n")) > 30:
                lines.append("# ... (truncado)")
            lines.append("```")

            # Marcar como usado
            sol["used_count"] += 1

        self._save()
        return "\n".join(lines)

    def _extract_tags(self, task: str, code: str) -> list[str]:
        """Extrae tags automaticos del task y codigo."""
        tags = set()

        # Tags del task
        for token in self._tokenize(task):
            if len(token) > 3:
                tags.add(token)

        # Tags de imports en el codigo
        imports = re.findall(
            r'(?:import|from)\s+([\w.]+)', code
        )
        tags.update(imports)

        # Tags de funciones definidas
        functions = re.findall(r'def\s+(\w+)', code)
        tags.update(functions)

        # Tags de clases definidas
        classes = re.findall(r'class\s+(\w+)', code)
        tags.update(classes)

        return list(tags)[:20]

    def _tokenize(self, text: str) -> list[str]:
        """Tokeniza texto para busqueda."""
        text = text.lower()
        # Remover caracteres especiales
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        # Filtrar stopwords basicos
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en',
            'que', 'es', 'y', 'a', 'por', 'para', 'con', 'no', 'se',
            'lo', 'como', 'su', 'al', 'le', 'me', 'si', 'mi', 'ya',
            'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of',
            'and', 'or', 'is', 'it', 'be', 'as', 'do', 'by', 'this',
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    def get_stats(self) -> dict:
        """Retorna estadisticas de la memoria de codigo."""
        if not self.solutions:
            return {"total": 0, "languages": {}, "most_used": []}

        langs = Counter(s["language"] for s in self.solutions)
        most_used = sorted(
            self.solutions, key=lambda s: s["used_count"], reverse=True
        )[:5]

        return {
            "total": len(self.solutions),
            "languages": dict(langs),
            "most_used": [
                {"task": s["task"][:80], "used": s["used_count"]}
                for s in most_used if s["used_count"] > 0
            ],
        }

    def format_stats(self) -> str:
        """Formatea estadisticas para mostrar."""
        stats = self.get_stats()
        if stats["total"] == 0:
            return "  Sin soluciones guardadas."

        lines = [f"  Soluciones guardadas: {stats['total']}"]
        if stats["languages"]:
            langs = ", ".join(
                f"{lang}: {count}" for lang, count in stats["languages"].items()
            )
            lines.append(f"  Lenguajes: {langs}")
        if stats["most_used"]:
            lines.append(f"  Mas reutilizadas:")
            for s in stats["most_used"]:
                lines.append(f"    [{s['used']}x] {s['task']}")

        return "\n".join(lines)
