"""
GENESIS Workspace — Proyecto activo del usuario.

Genesis necesita saber DONDE esta el codigo del usuario para poder:
- Leer archivos relevantes antes de programar
- Generar codigo que encaje con el proyecto existente
- Navegar la estructura sin que el usuario de rutas exactas

El workspace persiste entre sesiones (se guarda en disco).
"""
import json
import re
import time
from pathlib import Path
from typing import Optional


class Workspace:
    """
    Gestiona el proyecto activo del usuario.

    Almacena:
    - path: Ruta al directorio del proyecto
    - project_type: Tipo detectado (python, node, etc.)
    - structure: Cache de la estructura escaneada
    - file_index: Indice de archivos con sus funciones/clases
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.path: Optional[str] = None
        self.project_type: str = "unknown"
        self.structure: str = ""
        self.file_index: list[dict] = []
        self.last_scan: float = 0
        self._load()

    def _load(self):
        """Carga workspace desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.path = data.get("path")
                self.project_type = data.get("project_type", "unknown")
                self.structure = data.get("structure", "")
                self.file_index = data.get("file_index", [])
                self.last_scan = data.get("last_scan", 0)
            except (json.JSONDecodeError, Exception):
                pass

    def _save(self):
        """Guarda workspace a disco."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "path": self.path,
            "project_type": self.project_type,
            "structure": self.structure,
            "file_index": self.file_index,
            "last_scan": self.last_scan,
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def set(self, dirpath: str) -> str:
        """
        Establece el workspace activo y escanea el proyecto.

        Args:
            dirpath: Ruta al directorio del proyecto

        Returns:
            Resumen del escaneo
        """
        root = Path(dirpath).resolve()
        if not root.exists():
            return f"[ERROR] Directorio no encontrado: {dirpath}"
        if not root.is_dir():
            return f"[ERROR] No es un directorio: {dirpath}"

        self.path = str(root)
        result = self.scan()
        return result

    def scan(self) -> str:
        """Escanea el workspace activo y actualiza el indice."""
        if not self.path:
            return "[ERROR] No hay workspace activo. Usa /workspace <ruta>"

        root = Path(self.path)
        if not root.exists():
            return f"[ERROR] Directorio del workspace ya no existe: {self.path}"

        # Directorios y archivos a ignorar
        ignore_dirs = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'env', '.env', '.idea', '.vscode', 'dist', 'build',
            '.egg-info', '.tox', '.mypy_cache', '.pytest_cache',
            'models', '.cache', 'backups',
        }
        ignore_ext = {'.pyc', '.pyo', '.exe', '.dll', '.so', '.o',
                      '.gguf', '.bin', '.pt', '.pth', '.safetensors'}

        lines = []
        self.file_index = []
        file_count = 0
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java',
                           '.cpp', '.c', '.h', '.cs', '.go', '.rs',
                           '.rb', '.php', '.html', '.css', '.sql'}

        def scan_dir(path: Path, depth: int, prefix: str = ""):
            nonlocal file_count
            if depth > 4:
                return
            try:
                items = sorted(path.iterdir())
            except PermissionError:
                return

            dirs = [i for i in items if i.is_dir() and i.name not in ignore_dirs]
            files = [i for i in items if i.is_file() and i.suffix not in ignore_ext]

            for d in dirs:
                lines.append(f"{prefix}{d.name}/")
                scan_dir(d, depth + 1, prefix + "  ")

            for f in files:
                file_count += 1
                lines.append(f"{prefix}  {f.name}")

                # Indexar archivos de codigo
                if f.suffix in code_extensions:
                    file_info = self._index_file(f, root)
                    if file_info:
                        self.file_index.append(file_info)

        scan_dir(root, 0)

        # Detectar tipo de proyecto
        self.project_type = self._detect_project_type(root)
        self.last_scan = time.time()

        # Construir resumen
        summary_lines = [
            f"Workspace: {self.path}",
            f"Tipo: {self.project_type}",
            f"Archivos: {file_count}",
            f"Archivos de codigo indexados: {len(self.file_index)}",
        ]

        self.structure = "\n".join(lines)
        self._save()

        # Retornar resumen legible
        result = "\n".join(summary_lines)
        result += f"\n\nEstructura:\n{self.structure}"

        if self.file_index:
            result += "\n\nIndice de codigo:"
            for fi in self.file_index[:30]:
                parts = []
                if fi.get("classes"):
                    parts.append(f"clases: {', '.join(fi['classes'][:5])}")
                if fi.get("functions"):
                    parts.append(f"func: {', '.join(fi['functions'][:5])}")
                if parts:
                    result += f"\n  {fi['relative_path']}: {' | '.join(parts)}"

        return result

    def _index_file(self, filepath: Path, root: Path) -> Optional[dict]:
        """Indexa un archivo de codigo: extrae funciones, clases, imports."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(5000)  # Solo primeros 5KB
        except Exception:
            return None

        rel_path = str(filepath.relative_to(root))

        # Extraer info segun extension
        functions = re.findall(r'^(?:def|function|func|fn)\s+(\w+)', content, re.MULTILINE)
        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
        imports = re.findall(r'^(?:import|from|require|use)\s+(\S+)', content, re.MULTILINE)

        if not functions and not classes and not imports:
            return None

        return {
            "relative_path": rel_path,
            "absolute_path": str(filepath),
            "extension": filepath.suffix,
            "functions": functions[:15],
            "classes": classes[:10],
            "imports": imports[:10],
            "size": filepath.stat().st_size,
        }

    def _detect_project_type(self, root: Path) -> str:
        """Detecta el tipo de proyecto."""
        if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
            return "python"
        if (root / "package.json").exists():
            return "node"
        if (root / "Cargo.toml").exists():
            return "rust"
        if (root / "go.mod").exists():
            return "go"
        if (root / "pom.xml").exists():
            return "java"

        # Detectar por archivos mas comunes
        py_files = list(root.rglob("*.py"))
        js_files = list(root.rglob("*.js"))
        if len(py_files) > len(js_files):
            return "python"
        elif js_files:
            return "node"
        return "unknown"

    def find_relevant_files(self, query: str, max_files: int = 5) -> list[dict]:
        """
        Encuentra archivos relevantes en el workspace para una consulta.

        Busca por nombre de archivo, funciones, clases, e imports.
        """
        if not self.file_index:
            return []

        query_tokens = set(query.lower().split())
        scored = []

        for fi in self.file_index:
            score = 0

            # Match por nombre de archivo
            filename = fi["relative_path"].lower()
            for token in query_tokens:
                if token in filename:
                    score += 3

            # Match por funciones
            for func in fi.get("functions", []):
                for token in query_tokens:
                    if token in func.lower():
                        score += 2

            # Match por clases
            for cls in fi.get("classes", []):
                for token in query_tokens:
                    if token in cls.lower():
                        score += 2

            # Match por imports
            for imp in fi.get("imports", []):
                for token in query_tokens:
                    if token in imp.lower():
                        score += 1

            if score > 0:
                scored.append((score, fi))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:max_files]]

    def read_relevant_context(self, query: str, max_chars: int = 3000) -> str:
        """
        Lee y retorna el contenido de archivos relevantes al query.
        Esto se inyecta en el system prompt para que Genesis
        genere codigo que encaje con el proyecto.
        """
        if not self.path or not self.file_index:
            return ""

        relevant = self.find_relevant_files(query, max_files=3)
        if not relevant:
            return ""

        lines = ["[ARCHIVOS DE TU WORKSPACE RELEVANTES — Usa como referencia:]"]
        total_chars = 0

        for fi in relevant:
            try:
                with open(fi["absolute_path"], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(max_chars - total_chars)

                lines.append(f"\n--- {fi['relative_path']} ---")
                lines.append(content)
                total_chars += len(content)

                if total_chars >= max_chars:
                    break
            except Exception:
                continue

        return "\n".join(lines) if len(lines) > 1 else ""

    def get_prompt_context(self) -> str:
        """Genera contexto del workspace para inyectar en el system prompt."""
        if not self.path:
            return ""

        lines = [f"[WORKSPACE ACTIVO: {self.path}]"]
        lines.append(f"Tipo: {self.project_type}")
        lines.append(f"Archivos indexados: {len(self.file_index)}")

        # Resumen compacto del indice
        if self.file_index:
            lines.append("Archivos principales:")
            for fi in self.file_index[:10]:
                parts = []
                if fi.get("classes"):
                    parts.append(f"clases: {', '.join(fi['classes'][:3])}")
                if fi.get("functions"):
                    parts.append(f"func: {', '.join(fi['functions'][:3])}")
                if parts:
                    lines.append(f"  {fi['relative_path']}: {' | '.join(parts)}")

        return "\n".join(lines)

    def is_set(self) -> bool:
        """Verifica si hay un workspace activo."""
        return self.path is not None and Path(self.path).exists()

    def status(self) -> str:
        """Retorna estado del workspace."""
        if not self.is_set():
            return "  No hay workspace activo. Usa /workspace <ruta>"
        return (
            f"  Ruta: {self.path}\n"
            f"  Tipo: {self.project_type}\n"
            f"  Archivos indexados: {len(self.file_index)}\n"
            f"  Ultimo escaneo: {time.strftime('%H:%M:%S', time.localtime(self.last_scan))}"
        )

    def clear(self):
        """Limpia el workspace activo."""
        self.path = None
        self.project_type = "unknown"
        self.structure = ""
        self.file_index = []
        self.last_scan = 0
        self._save()
