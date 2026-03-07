"""
GENESIS — Generador de Proyectos Multi-archivo
Parsea la respuesta del LLM para detectar multiples archivos y crearlos
automaticamente en la estructura correcta del workspace.

Formatos detectados:
1. ```filename.py  (bloque markdown con nombre de archivo)
2. # --- filename.py ---  (separador con nombre)
3. [FILE: path/to/file.py]  (tag explicito)
4. Estructura de carpetas descrita en la respuesta

Seguridad:
- Solo crea dentro del workspace (o directorio especificado)
- Valida nombres de archivo
- No sobreescribe sin confirmacion
- Bloquea rutas peligrosas
"""
import re
import os
from pathlib import Path
from typing import Optional
from core.logger import GenesisLogger


class ProjectGenerator:
    """
    Genera proyectos multi-archivo a partir de respuestas del LLM.

    Parsea la respuesta buscando multiples archivos definidos,
    crea la estructura de directorios y escribe los archivos.
    """

    # Extensiones permitidas
    ALLOWED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".html", ".css", ".scss", ".sass",
        ".json", ".yaml", ".yml", ".toml",
        ".md", ".txt", ".rst",
        ".sh", ".bat", ".ps1",
        ".sql", ".csv",
        ".gitignore", ".env.example",
        ".cfg", ".ini", ".conf",
        ".xml", ".svg",
        ".dockerfile", ".dockerignore",
    }

    # Patrones bloqueados en nombres de archivo
    BLOCKED_PATTERNS = [
        r'\.\.',       # Path traversal
        r'^/',         # Ruta absoluta unix
        r'^[A-Z]:',    # Ruta absoluta windows
        r'~',          # Home directory
        r'\$',         # Variables de entorno
        r'%',          # Variables Windows
    ]

    # Tamaño maximo por archivo (50KB)
    MAX_FILE_SIZE = 50_000

    def __init__(self):
        self.log = GenesisLogger().get_child("project_gen")
        self.last_generation: Optional[dict] = None

    def parse_files(self, response: str) -> list[dict]:
        """
        Parsea la respuesta del LLM y extrae archivos definidos.

        Returns:
            Lista de dicts: [{"path": "archivo.py", "content": "...", "language": "python"}, ...]
        """
        files = []

        # Metodo 1: [FILE: path/to/file.ext] seguido de bloque de codigo
        pattern1 = r'\[FILE:\s*([^\]]+)\]\s*\n```\w*\n(.*?)```'
        for match in re.finditer(pattern1, response, re.DOTALL):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            if self._validate_path(filepath):
                files.append({
                    "path": filepath,
                    "content": content,
                    "language": self._detect_language(filepath),
                })

        # Metodo 2: # --- filename.ext --- seguido de bloque de codigo
        pattern2 = r'#\s*-{2,}\s*([^\n-]+?)\s*-{2,}\s*\n```\w*\n(.*?)```'
        for match in re.finditer(pattern2, response, re.DOTALL):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            if self._validate_path(filepath) and not self._already_found(files, filepath):
                files.append({
                    "path": filepath,
                    "content": content,
                    "language": self._detect_language(filepath),
                })

        # Metodo 3: ```python filename.py (nombre en la primera linea del bloque)
        pattern3 = r'```(\w+)\s*\n#\s*(\S+\.\w+)\s*\n(.*?)```'
        for match in re.finditer(pattern3, response, re.DOTALL):
            lang = match.group(1)
            filepath = match.group(2).strip()
            content = f"# {filepath}\n{match.group(3).strip()}"
            if self._validate_path(filepath) and not self._already_found(files, filepath):
                files.append({
                    "path": filepath,
                    "content": content,
                    "language": lang,
                })

        # Metodo 4: Bloques con nombre de archivo como titulo (### filename.py)
        pattern4 = r'#{1,4}\s+`?([^\n`]+\.\w+)`?\s*\n+```\w*\n(.*?)```'
        for match in re.finditer(pattern4, response, re.DOTALL):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            if self._validate_path(filepath) and not self._already_found(files, filepath):
                files.append({
                    "path": filepath,
                    "content": content,
                    "language": self._detect_language(filepath),
                })

        return files

    def generate(self, response: str, base_dir: str,
                 overwrite: bool = False) -> dict:
        """
        Genera un proyecto multi-archivo a partir de la respuesta del LLM.

        Args:
            response: Respuesta del LLM con archivos definidos
            base_dir: Directorio base donde crear los archivos
            overwrite: Si True, sobreescribe archivos existentes

        Returns:
            dict con resultados: {"created": [...], "skipped": [...], "errors": [...]}
        """
        base_path = Path(base_dir)
        if not base_path.exists():
            try:
                base_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {"created": [], "skipped": [], "errors": [f"No se pudo crear {base_dir}: {e}"]}

        files = self.parse_files(response)
        if not files:
            return {"created": [], "skipped": [], "errors": ["No se encontraron archivos en la respuesta"]}

        result = {"created": [], "skipped": [], "errors": []}

        for file_info in files:
            filepath = base_path / file_info["path"]
            content = file_info["content"]

            # Validar tamaño
            if len(content) > self.MAX_FILE_SIZE:
                result["errors"].append(f"{file_info['path']}: excede {self.MAX_FILE_SIZE} bytes")
                continue

            # Verificar si existe
            if filepath.exists() and not overwrite:
                result["skipped"].append(file_info["path"])
                continue

            # Crear directorios intermedios
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                result["errors"].append(f"{file_info['path']}: error creando directorio: {e}")
                continue

            # Escribir archivo
            try:
                filepath.write_text(content, encoding="utf-8")
                result["created"].append(file_info["path"])
                self.log.info(f"Archivo creado: {filepath}")
            except Exception as e:
                result["errors"].append(f"{file_info['path']}: error escribiendo: {e}")

        # Guardar resultado
        self.last_generation = {
            "base_dir": str(base_dir),
            "files": files,
            "result": result,
        }

        return result

    def format_result(self, result: dict) -> str:
        """Formatea el resultado de la generacion para mostrar al usuario."""
        lines = ["=== PROYECTO GENERADO ==="]

        if result["created"]:
            lines.append(f"\n  Archivos creados ({len(result['created'])}):")
            for f in result["created"]:
                lines.append(f"    + {f}")

        if result["skipped"]:
            lines.append(f"\n  Archivos saltados ({len(result['skipped'])}):")
            for f in result["skipped"]:
                lines.append(f"    ~ {f} (ya existe)")

        if result["errors"]:
            lines.append(f"\n  Errores ({len(result['errors'])}):")
            for e in result["errors"]:
                lines.append(f"    ! {e}")

        if not result["created"] and not result["skipped"]:
            lines.append("\n  No se encontraron archivos para generar.")
            lines.append("  Tip: El LLM debe usar uno de estos formatos:")
            lines.append("    [FILE: path/archivo.py]")
            lines.append("    ```python")
            lines.append("    # codigo...")
            lines.append("    ```")

        return "\n".join(lines)

    def _validate_path(self, filepath: str) -> bool:
        """Valida que la ruta del archivo sea segura."""
        if not filepath or len(filepath) > 200:
            return False

        # Verificar patrones bloqueados
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, filepath):
                self.log.info(f"Ruta bloqueada: {filepath}")
                return False

        # Verificar extension
        ext = Path(filepath).suffix.lower()
        name = Path(filepath).name.lower()

        # Archivos sin extension permitidos si son conocidos
        if not ext and name not in {"makefile", "dockerfile", "procfile",
                                     ".gitignore", ".dockerignore"}:
            return False

        if ext and ext not in self.ALLOWED_EXTENSIONS:
            return False

        return True

    def _detect_language(self, filepath: str) -> str:
        """Detecta el lenguaje por extension."""
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "jsx", ".tsx": "tsx",
            ".html": "html", ".css": "css",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml",
            ".md": "markdown", ".sql": "sql",
            ".sh": "bash", ".bat": "batch",
        }
        ext = Path(filepath).suffix.lower()
        return ext_map.get(ext, "text")

    def _already_found(self, files: list, filepath: str) -> bool:
        """Verifica si el archivo ya fue encontrado."""
        return any(f["path"] == filepath for f in files)

    def has_multiple_files(self, response: str) -> bool:
        """Detecta rapidamente si la respuesta contiene multiples archivos."""
        files = self.parse_files(response)
        return len(files) >= 2

    def status(self) -> str:
        """Estado del generador."""
        if self.last_generation:
            result = self.last_generation["result"]
            total = len(result["created"]) + len(result["skipped"])
            return f"  Ultimo proyecto: {total} archivos en {self.last_generation['base_dir']}"
        return "  Sin proyectos generados aun."
