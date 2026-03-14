"""
GENESIS — Diagram Generator (v3.3)

Generacion de diagramas Mermaid desde descripciones en texto natural.
Detecta automaticamente el tipo de diagrama, construye nodos y edges,
y genera el bloque Mermaid markdown listo para renderizar.

Componentes:
- DiagramType: tipos de diagrama con template y descripcion
- DiagramSpec: especificacion completa de un diagrama
- DiagramDetector: deteccion de tipo desde input del usuario
- DiagramGenerator: coordinador con persistencia
"""
import re
import time
import json
from pathlib import Path
from collections import defaultdict, deque


class DiagramType:
    """Tipo de diagrama Mermaid con template base."""

    TYPES = {
        "flowchart": {
            "description": "Diagrama de flujo con decisiones y procesos",
            "header": "flowchart TD",
            "node_fmt": "    {name}[{label}]",
            "edge_fmt": "    {src} -->|{label}| {dst}",
            "edge_fmt_no_label": "    {src} --> {dst}",
        },
        "sequence": {
            "description": "Diagrama de secuencia entre actores/sistemas",
            "header": "sequenceDiagram",
            "node_fmt": "    participant {name} as {label}",
            "edge_fmt": "    {src}->>+{dst}: {label}",
            "edge_fmt_no_label": "    {src}->>{dst}: (interaccion)",
        },
        "class_diagram": {
            "description": "Diagrama de clases con atributos y relaciones",
            "header": "classDiagram",
            "node_fmt": "    class {name} {{\n        {label}\n    }}",
            "edge_fmt": "    {src} --> {dst} : {label}",
            "edge_fmt_no_label": "    {src} --> {dst}",
        },
        "er_diagram": {
            "description": "Diagrama entidad-relacion para bases de datos",
            "header": "erDiagram",
            "node_fmt": "    {name} {{\n        string {label}\n    }}",
            "edge_fmt": '    {src} ||--o{{ {dst} : "{label}"',
            "edge_fmt_no_label": '    {src} ||--o{{ {dst} : "relaciona"',
        },
        "state": {
            "description": "Diagrama de estados y transiciones",
            "header": "stateDiagram-v2",
            "node_fmt": "    {name} : {label}",
            "edge_fmt": "    {src} --> {dst} : {label}",
            "edge_fmt_no_label": "    {src} --> {dst}",
        },
        "gantt": {
            "description": "Diagrama de Gantt para planificacion temporal",
            "header": "gantt\n    dateFormat YYYY-MM-DD\n    title {title}",
            "node_fmt": "    {label} : {name}, after {name}, 5d",
            "edge_fmt": "",
            "edge_fmt_no_label": "",
        },
    }

    def __init__(self, type_name: str):
        config = self.TYPES.get(type_name, self.TYPES["flowchart"])
        self.name = type_name
        self.description = config["description"]
        self.header = config["header"]
        self.node_fmt = config["node_fmt"]
        self.edge_fmt = config["edge_fmt"]
        self.edge_fmt_no_label = config["edge_fmt_no_label"]

    @classmethod
    def list_types(cls) -> list:
        return list(cls.TYPES.keys())

    @classmethod
    def get_description(cls, type_name: str) -> str:
        return cls.TYPES.get(type_name, {}).get("description", "Desconocido")


class DiagramSpec:
    """Especificacion completa de un diagrama."""

    def __init__(self, title: str = "", diagram_type: str = "flowchart"):
        self.title = title
        self.diagram_type = diagram_type
        self.nodes = []   # [{"name": str, "label": str}]
        self.edges = []   # [{"src": str, "dst": str, "label": str}]
        self.raw_mermaid = ""
        self.created_at = time.time()

    def add_node(self, name: str, label: str = ""):
        """Agrega un nodo al diagrama."""
        label = label or name
        # Evitar duplicados
        if not any(n["name"] == name for n in self.nodes):
            self.nodes.append({"name": name, "label": label})

    def add_edge(self, src: str, dst: str, label: str = ""):
        """Agrega una arista entre dos nodos."""
        self.edges.append({"src": src, "dst": dst, "label": label})
        # Auto-agregar nodos si no existen
        self.add_node(src)
        self.add_node(dst)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "diagram_type": self.diagram_type,
            "nodes": self.nodes,
            "edges": self.edges,
            "raw_mermaid": self.raw_mermaid,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DiagramSpec":
        s = cls(d.get("title", ""), d.get("diagram_type", "flowchart"))
        s.nodes = d.get("nodes", [])
        s.edges = d.get("edges", [])
        s.raw_mermaid = d.get("raw_mermaid", "")
        s.created_at = d.get("created_at", time.time())
        return s


class DiagramDetector:
    """Detecta tipo de diagrama desde input del usuario."""

    KEYWORD_MAP = {
        "flowchart": [
            "flujo", "flowchart", "proceso", "decision", "pasos",
            "flow", "steps", "algoritmo", "workflow",
        ],
        "sequence": [
            "secuencia", "sequence", "interaccion", "comunicacion",
            "mensajes", "llamadas", "request", "response", "api",
        ],
        "class_diagram": [
            "clases", "class", "herencia", "objetos", "atributos",
            "metodos", "inheritance", "oop", "uml",
        ],
        "er_diagram": [
            "entidad", "entity", "relacion", "relationship", "base de datos",
            "database", "tabla", "table", "er", "esquema db",
        ],
        "state": [
            "estado", "state", "transicion", "transition", "maquina de estados",
            "state machine", "lifecycle", "ciclo de vida",
        ],
        "gantt": [
            "gantt", "timeline", "cronograma", "planificacion", "schedule",
            "fases", "hitos", "milestones", "proyecto temporal",
        ],
    }

    def detect(self, text: str) -> str:
        """Detecta tipo de diagrama desde texto. Retorna nombre del tipo."""
        text_lower = text.lower()
        scores = defaultdict(float)

        for dtype, keywords in self.KEYWORD_MAP.items():
            for kw in keywords:
                if kw in text_lower:
                    # Keywords mas largos pesan mas
                    weight = len(kw) / 10.0 + 0.5
                    scores[dtype] += weight

        if not scores:
            return "flowchart"  # Default

        return max(scores, key=scores.get)

    def extract_elements(self, text: str) -> dict:
        """Extrae posibles nodos y relaciones del texto."""
        elements = {"nodes": [], "edges": []}

        # Buscar patrones "A -> B", "A conecta con B", "A envia a B"
        arrow_patterns = [
            r"(\w[\w\s]{0,20}?)\s*(?:->|-->|=>|→)\s*(\w[\w\s]{0,20})",
            r"(\w+)\s+(?:conecta|envia|llama|usa|depende de)\s+(\w+)",
        ]
        for pattern in arrow_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                src = match.group(1).strip()
                dst = match.group(2).strip()
                if src and dst:
                    elements["edges"].append({"src": src, "dst": dst, "label": ""})
                    if src not in elements["nodes"]:
                        elements["nodes"].append(src)
                    if dst not in elements["nodes"]:
                        elements["nodes"].append(dst)

        # Buscar items listados con viñetas o numeracion
        list_pattern = r"(?:^|\n)\s*(?:[-*•]|\d+[.)]\s)\s*(.+)"
        for match in re.finditer(list_pattern, text):
            item = match.group(1).strip()
            if item and item not in elements["nodes"]:
                elements["nodes"].append(item)

        return elements


class DiagramGenerator:
    """Coordinador de generacion de diagramas con persistencia."""

    def __init__(self, base_dir: str = "data/diagram_generator"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.detector = DiagramDetector()
        self.current_diagram = None  # DiagramSpec
        self.total_diagrams = 0
        self.history = deque(maxlen=20)
        self.type_counts = defaultdict(int)

        self._load()

    def generate(self, description: str, diagram_type: str = "auto") -> dict:
        """Genera un diagrama desde descripcion textual."""
        # Auto-detectar tipo
        if diagram_type == "auto":
            diagram_type = self.detector.detect(description)

        # Crear spec
        spec = DiagramSpec(title=description[:60], diagram_type=diagram_type)

        # Extraer elementos del texto
        elements = self.detector.extract_elements(description)

        for node_name in elements["nodes"]:
            clean = re.sub(r"[^\w\s]", "", node_name).strip()
            if clean:
                node_id = re.sub(r"\s+", "_", clean)
                spec.add_node(node_id, clean)

        for edge in elements["edges"]:
            src_id = re.sub(r"\s+", "_", re.sub(r"[^\w\s]", "", edge["src"]).strip())
            dst_id = re.sub(r"\s+", "_", re.sub(r"[^\w\s]", "", edge["dst"]).strip())
            if src_id and dst_id:
                spec.add_edge(src_id, dst_id, edge.get("label", ""))

        # Si no se extrajeron elementos, crear nodos desde palabras clave
        if not spec.nodes:
            words = re.findall(r"\b[A-Z]\w{2,}\b", description)
            for w in words[:6]:
                spec.add_node(w, w)
            # Conectar secuencialmente
            for i in range(len(spec.nodes) - 1):
                spec.add_edge(spec.nodes[i]["name"], spec.nodes[i + 1]["name"])

        # Generar Mermaid
        spec.raw_mermaid = self._render_mermaid(spec)

        # Actualizar estado
        self.current_diagram = spec
        self.total_diagrams += 1
        self.type_counts[diagram_type] += 1
        self.history.append(spec.to_dict())

        return {
            "type": diagram_type,
            "title": spec.title,
            "nodes": len(spec.nodes),
            "edges": len(spec.edges),
            "mermaid": spec.raw_mermaid,
        }

    def add_node(self, name: str, label: str = ""):
        """Agrega nodo al diagrama actual."""
        if self.current_diagram is None:
            self.current_diagram = DiagramSpec(title="Diagrama manual")
        self.current_diagram.add_node(name, label or name)
        self.current_diagram.raw_mermaid = self._render_mermaid(self.current_diagram)

    def add_edge(self, from_node: str, to_node: str, label: str = ""):
        """Agrega arista al diagrama actual."""
        if self.current_diagram is None:
            self.current_diagram = DiagramSpec(title="Diagrama manual")
        self.current_diagram.add_edge(from_node, to_node, label)
        self.current_diagram.raw_mermaid = self._render_mermaid(self.current_diagram)

    def get_mermaid(self) -> str:
        """Retorna el Mermaid markdown del diagrama actual."""
        if self.current_diagram is None:
            return ""
        return self.current_diagram.raw_mermaid

    def _render_mermaid(self, spec: DiagramSpec) -> str:
        """Renderiza un DiagramSpec a Mermaid markdown."""
        dtype = DiagramType(spec.diagram_type)
        lines = []

        # Header
        header = dtype.header
        if "{title}" in header:
            header = header.replace("{title}", spec.title or "Diagrama")
        lines.append(header)

        # Nodos (no aplica a todos los tipos igual)
        if spec.diagram_type == "gantt":
            # Gantt usa secciones y tareas
            lines.append(f"    section {spec.title or 'Tareas'}")
            for i, node in enumerate(spec.nodes):
                task_id = f"t{i}"
                if i == 0:
                    lines.append(f"    {node['label']} : {task_id}, 2024-01-01, 5d")
                else:
                    prev_id = f"t{i - 1}"
                    lines.append(f"    {node['label']} : {task_id}, after {prev_id}, 5d")
        else:
            # Nodos explícitos para sequence y class
            if spec.diagram_type in ("sequence", "class_diagram", "er_diagram"):
                for node in spec.nodes:
                    line = dtype.node_fmt.format(name=node["name"], label=node["label"])
                    lines.append(line)

            # Para flowchart y state, nodos se declaran con edges
            if spec.diagram_type in ("flowchart", "state"):
                # Nodos sueltos (sin edges)
                connected = set()
                for edge in spec.edges:
                    connected.add(edge["src"])
                    connected.add(edge["dst"])
                for node in spec.nodes:
                    if node["name"] not in connected:
                        line = dtype.node_fmt.format(
                            name=node["name"], label=node["label"]
                        )
                        lines.append(line)

            # Edges
            for edge in spec.edges:
                if edge.get("label"):
                    line = dtype.edge_fmt.format(
                        src=edge["src"], dst=edge["dst"], label=edge["label"]
                    )
                else:
                    line = dtype.edge_fmt_no_label.format(
                        src=edge["src"], dst=edge["dst"]
                    )
                lines.append(line)

        mermaid = "\n".join(lines)
        return f"```mermaid\n{mermaid}\n```"

    def get_context_for_prompt(self, user_input: str = "", max_chars: int = 200) -> str:
        """Inyecta guia de diagramas si se detecta solicitud."""
        diagram_keywords = [
            "diagrama", "diagram", "flujo", "flow", "secuencia", "sequence",
            "clases", "class", "entidad", "entity", "estado", "state",
            "gantt", "mermaid", "grafico", "esquema",
        ]
        input_lower = user_input.lower()

        if not any(kw in input_lower for kw in diagram_keywords):
            return ""

        detected = self.detector.detect(user_input)
        desc = DiagramType.get_description(detected)

        context = (
            f"[DIAGRAMA] Tipo detectado: {detected} — {desc}. "
            f"Diagramas generados: {self.total_diagrams}."
        )

        if self.current_diagram and self.current_diagram.nodes:
            context += (
                f" Diagrama actual: {len(self.current_diagram.nodes)} nodos, "
                f"{len(self.current_diagram.edges)} aristas."
            )

        return context[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_diagrams": self.total_diagrams,
            "current_type": (
                self.current_diagram.diagram_type if self.current_diagram else None
            ),
            "current_nodes": (
                len(self.current_diagram.nodes) if self.current_diagram else 0
            ),
            "current_edges": (
                len(self.current_diagram.edges) if self.current_diagram else 0
            ),
            "type_counts": dict(self.type_counts),
            "history_size": len(self.history),
        }

    def status(self) -> str:
        cur = self.current_diagram
        if cur:
            return (f"  Diagramas: {self.total_diagrams} | "
                    f"Actual: {cur.diagram_type} "
                    f"({len(cur.nodes)}N/{len(cur.edges)}E)")
        return f"  Diagramas: {self.total_diagrams} | Actual: ninguno"

    def generate_report(self) -> str:
        lines = [
            "=== DIAGRAM GENERATOR ===",
            f"Total diagramas generados: {self.total_diagrams}",
            "",
            "Por tipo:",
        ]
        for dtype, count in sorted(self.type_counts.items(),
                                     key=lambda x: x[1], reverse=True):
            desc = DiagramType.get_description(dtype)
            lines.append(f"  {dtype}: {count} ({desc})")

        if self.current_diagram:
            lines.append("")
            lines.append(f"Diagrama actual: {self.current_diagram.title}")
            lines.append(f"  Tipo: {self.current_diagram.diagram_type}")
            lines.append(f"  Nodos: {len(self.current_diagram.nodes)}")
            lines.append(f"  Aristas: {len(self.current_diagram.edges)}")

        lines.append("")
        lines.append("Historial reciente:")
        for entry in list(self.history)[-5:]:
            lines.append(f"  [{entry['diagram_type']}] {entry['title'][:50]}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_diagrams": self.total_diagrams,
            "type_counts": dict(self.type_counts),
            "history": list(self.history),
            "current_diagram": (
                self.current_diagram.to_dict() if self.current_diagram else None
            ),
        }
        path = self.base_dir / "diagram_generator.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "diagram_generator.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_diagrams = data.get("total_diagrams", 0)
            self.type_counts = defaultdict(int, data.get("type_counts", {}))
            for entry in data.get("history", []):
                self.history.append(entry)
            cd = data.get("current_diagram")
            if cd:
                self.current_diagram = DiagramSpec.from_dict(cd)
        except Exception:
            pass

    def clear(self):
        self.current_diagram = None
        self.total_diagrams = 0
        self.type_counts = defaultdict(int)
        self.history = deque(maxlen=20)
        self.save()
