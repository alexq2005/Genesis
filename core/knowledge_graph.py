"""
GENESIS Knowledge Graph — Memorias conectadas entre si.

Problema:
La memoria de largo plazo es una lista plana de hechos independientes.
"El usuario programa en Python" y "Python es un lenguaje interpretado" no
se conectan — Genesis no puede hacer inferencias como "al usuario le
convienen herramientas interpretadas".

Solucion:
Un grafo de conocimiento simple donde:
- Los NODOS son conceptos (palabras clave extraidas de memorias)
- Las ARISTAS son relaciones (co-ocurrencia, causalidad, similitud)
- Se puede navegar el grafo para encontrar contexto relevante
- Se puede expandir un concepto para ver todo lo relacionado

No usa bibliotecas externas — es un grafo en dict puro.
"""
import re
import time
from pathlib import Path
from typing import Optional
from collections import defaultdict

try:
    from core.safe_io import safe_read_json, safe_write_json
except ImportError:
    import json
    def safe_read_json(path, default=None):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    def safe_write_json(path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True


# Stopwords en espanol e ingles para filtrar al extraer conceptos
STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "en", "con", "por", "para", "que", "es",
    "no", "si", "yo", "tu", "el", "se", "me", "te", "lo",
    "al", "le", "su", "mi", "mas", "ya", "como", "pero",
    "este", "esta", "estos", "estas", "ese", "esa", "esos",
    "hay", "muy", "ser", "son", "fue", "era", "han", "ha",
    "the", "a", "an", "is", "are", "was", "were", "be",
    "to", "of", "in", "for", "on", "with", "at", "by",
    "it", "he", "she", "we", "they", "my", "your", "his",
    "and", "or", "but", "not", "this", "that", "from",
    "i", "you", "do", "does", "did", "has", "have", "had",
}


class KnowledgeGraph:
    """
    Grafo de conocimiento basado en co-ocurrencia de conceptos.

    Estructura interna:
        nodes: {
            "python": {
                "mentions": 15,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "context_snippets": ["programa en python", "usa python 3.10"]
            }
        }
        edges: {
            "python|programacion": {
                "weight": 5,
                "relation": "co-occurrence"
            }
        }

    Las aristas son bidireccionales (A|B == B|A, siempre sorted).
    """

    MAX_NODES = 500
    MAX_EDGES = 2000
    MAX_SNIPPETS_PER_NODE = 5

    def __init__(self, graph_file: Optional[Path] = None):
        if graph_file is None:
            data_dir = Path(__file__).parent.parent / "memory_data"
            data_dir.mkdir(exist_ok=True)
            graph_file = data_dir / "knowledge_graph.json"
        self.graph_file = graph_file

        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self._load()

    def _load(self):
        """Carga el grafo desde disco."""
        data = safe_read_json(self.graph_file, default={
            "nodes": {}, "edges": {}
        })
        self.nodes = data.get("nodes", {})
        self.edges = data.get("edges", {})

    def _save(self):
        """Guarda el grafo a disco."""
        safe_write_json(self.graph_file, {
            "nodes": self.nodes,
            "edges": self.edges,
        })

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def clear(self):
        """Resetea el grafo de conocimiento y elimina el archivo."""
        self.nodes = {}
        self.edges = {}
        if self.graph_file.exists():
            self.graph_file.unlink()

    @staticmethod
    def _make_edge_key(a: str, b: str) -> str:
        """Crea clave de arista normalizada (siempre sorted)."""
        return "|".join(sorted([a.lower(), b.lower()]))

    @staticmethod
    def extract_concepts(text: str, min_length: int = 3) -> list[str]:
        """
        Extrae conceptos (palabras clave) de un texto.

        Reglas:
        - Palabras de 3+ caracteres
        - No stopwords
        - Alfanumericas (permite guiones/puntos para cosas como "node.js")
        """
        # Tokenizar: palabras y cosas como "node.js", "c++", "3060ti"
        tokens = re.findall(r'[a-zA-Z0-9_.+#]+', text.lower())

        concepts = []
        seen = set()
        for token in tokens:
            # Limpiar puntos al final
            token = token.strip(".")
            if (len(token) >= min_length
                    and token not in STOPWORDS
                    and token not in seen
                    and not token.isdigit()):
                concepts.append(token)
                seen.add(token)

        return concepts

    def learn(self, text: str, source: str = "conversation"):
        """
        Aprende de un texto — extrae conceptos y crea conexiones.

        Args:
            text: Texto del cual aprender
            source: Origen (conversation, fact, code, error, etc.)
        """
        concepts = self.extract_concepts(text)
        if len(concepts) < 1:
            return

        now = time.time()

        # Actualizar nodos
        for concept in concepts:
            if concept not in self.nodes:
                self.nodes[concept] = {
                    "mentions": 0,
                    "first_seen": now,
                    "last_seen": now,
                    "context_snippets": [],
                    "sources": [],
                }
            node = self.nodes[concept]
            node["mentions"] += 1
            node["last_seen"] = now

            # Guardar snippet de contexto (max 5)
            snippet = text[:100]
            if len(node["context_snippets"]) < self.MAX_SNIPPETS_PER_NODE:
                if snippet not in node["context_snippets"]:
                    node["context_snippets"].append(snippet)

            # Registrar source
            if source not in node.get("sources", []):
                node.setdefault("sources", []).append(source)

        # Crear aristas entre todos los conceptos que co-ocurren
        # (ventana completa — si aparecen en el mismo texto, estan relacionados)
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1:]:
                if c1 == c2:
                    continue
                edge_key = self._make_edge_key(c1, c2)
                if edge_key not in self.edges:
                    self.edges[edge_key] = {
                        "weight": 0,
                        "relation": "co-occurrence",
                        "first_seen": now,
                    }
                self.edges[edge_key]["weight"] += 1

        # Pruning si excede limites
        self._prune()
        self._save()

    def _prune(self):
        """Poda el grafo si excede los limites."""
        # Podar nodos menos mencionados
        if len(self.nodes) > self.MAX_NODES:
            sorted_nodes = sorted(
                self.nodes.items(),
                key=lambda x: x[1]["mentions"]
            )
            to_remove = len(self.nodes) - self.MAX_NODES
            for name, _ in sorted_nodes[:to_remove]:
                del self.nodes[name]
                # Remover aristas asociadas
                self.edges = {
                    k: v for k, v in self.edges.items()
                    if name not in k.split("|")
                }

        # Podar aristas mas debiles
        if len(self.edges) > self.MAX_EDGES:
            sorted_edges = sorted(
                self.edges.items(),
                key=lambda x: x[1]["weight"]
            )
            to_remove = len(self.edges) - self.MAX_EDGES
            for key, _ in sorted_edges[:to_remove]:
                del self.edges[key]

    def get_related(self, concept: str, depth: int = 1,
                    max_results: int = 10) -> list[dict]:
        """
        Encuentra conceptos relacionados (vecinos en el grafo).

        Args:
            concept: Concepto a expandir
            depth: Profundidad de busqueda (1 = vecinos directos, 2 = vecinos de vecinos)
            max_results: Maximo de resultados

        Returns:
            Lista de {"concept": str, "weight": int, "distance": int}
        """
        concept = concept.lower()
        if concept not in self.nodes:
            return []

        results = {}
        visited = {concept}
        frontier = [(concept, 0)]

        while frontier:
            current, dist = frontier.pop(0)
            if dist >= depth:
                continue

            # Buscar vecinos
            for edge_key, edge_data in self.edges.items():
                parts = edge_key.split("|")
                if current not in parts:
                    continue

                neighbor = parts[0] if parts[1] == current else parts[1]

                if neighbor in visited:
                    continue
                visited.add(neighbor)

                weight = edge_data["weight"]
                actual_dist = dist + 1

                if neighbor not in results or weight > results[neighbor]["weight"]:
                    results[neighbor] = {
                        "concept": neighbor,
                        "weight": weight,
                        "distance": actual_dist,
                    }

                if actual_dist < depth:
                    frontier.append((neighbor, actual_dist))

        # Ordenar por peso (mas fuerte primero)
        sorted_results = sorted(
            results.values(),
            key=lambda x: (-x["weight"], x["distance"])
        )

        return sorted_results[:max_results]

    def get_context_for_query(self, query: str, max_concepts: int = 5) -> str:
        """
        Dado un query del usuario, encuentra conceptos relacionados
        y genera contexto relevante para el LLM.

        Args:
            query: Texto del usuario
            max_concepts: Maximo de conceptos a expandir

        Returns:
            Texto con contexto del knowledge graph
        """
        concepts = self.extract_concepts(query)
        if not concepts:
            return ""

        all_related = {}
        matched_concepts = []

        for concept in concepts[:max_concepts]:
            if concept in self.nodes:
                matched_concepts.append(concept)
                related = self.get_related(concept, depth=1, max_results=5)
                for r in related:
                    if r["concept"] not in all_related:
                        all_related[r["concept"]] = r

        if not matched_concepts and not all_related:
            return ""

        lines = ["[CONOCIMIENTO PREVIO (Knowledge Graph)]"]

        # Conceptos directamente mencionados
        for concept in matched_concepts:
            node = self.nodes[concept]
            snippets = node.get("context_snippets", [])[:2]
            if snippets:
                lines.append(f"  {concept} ({node['mentions']} menciones):")
                for s in snippets:
                    lines.append(f"    - {s}")

        # Conceptos relacionados (top 5)
        if all_related:
            top_related = sorted(
                all_related.values(),
                key=lambda x: -x["weight"]
            )[:5]
            related_names = [r["concept"] for r in top_related]
            lines.append(f"  Conceptos relacionados: {', '.join(related_names)}")

        return "\n".join(lines)

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Busca nodos que coincidan con el query."""
        query_lower = query.lower()
        results = []

        for name, data in self.nodes.items():
            # Match exacto o parcial
            if query_lower in name or name in query_lower:
                results.append({
                    "concept": name,
                    "mentions": data["mentions"],
                    "snippets": data.get("context_snippets", [])[:3],
                    "sources": data.get("sources", []),
                })

        # Ordenar por menciones
        results.sort(key=lambda x: -x["mentions"])
        return results[:max_results]

    def format_graph(self, top_n: int = 20) -> str:
        """Formatea los top N conceptos con sus conexiones."""
        if not self.nodes:
            return "  Knowledge Graph vacio.\n  Se llena automaticamente con las conversaciones."

        # Top N nodos por menciones
        top_nodes = sorted(
            self.nodes.items(),
            key=lambda x: -x[1]["mentions"]
        )[:top_n]

        lines = []
        for name, data in top_nodes:
            related = self.get_related(name, depth=1, max_results=3)
            related_str = ", ".join(
                f"{r['concept']}({r['weight']})" for r in related
            )
            lines.append(
                f"  {name} [{data['mentions']} menciones] -> {related_str or 'sin conexiones'}"
            )

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen para /status."""
        n_nodes = len(self.nodes)
        n_edges = len(self.edges)
        if n_nodes == 0:
            return "  Nodos: 0, Aristas: 0 (vacio)"

        top_concept = max(self.nodes.items(), key=lambda x: x[1]["mentions"])
        return (
            f"  Nodos: {n_nodes}, Aristas: {n_edges}\n"
            f"  Concepto top: '{top_concept[0]}' ({top_concept[1]['mentions']} menciones)"
        )

    def get_stats(self) -> dict:
        """Estadisticas del grafo."""
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "avg_mentions": (
                sum(n["mentions"] for n in self.nodes.values()) / max(len(self.nodes), 1)
            ),
        }
