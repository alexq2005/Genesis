"""
GENESIS — Image Analyzer (v3.3)

Analisis de imagenes local basado en metadatos y path (sin modelo de vision).
Extrae informacion del nombre de archivo, extension y tamaño. Mantiene cache
de analisis con eviccion por antigüedad.

Componentes:
- ImageMetadata: metadatos extraidos del archivo
- AnalysisResult: resultado del analisis con tags y descripcion
- AnalysisCache: cache LRU por path con eviccion automatica
- ImageAnalyzer: coordinador con persistencia
"""
import os
import re
import time
import json
import math
from pathlib import Path
from collections import defaultdict, deque


class ImageMetadata:
    """Metadatos extraidos de un archivo de imagen."""

    IMAGE_EXTENSIONS = {
        ".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".gif": "GIF",
        ".bmp": "BMP", ".webp": "WebP", ".svg": "SVG", ".ico": "ICO",
        ".tiff": "TIFF", ".tif": "TIFF",
    }

    def __init__(self, path: str):
        self.path = str(path)
        p = Path(path)
        self.filename = p.name
        self.stem = p.stem
        self.extension = p.suffix.lower()
        self.format = self.IMAGE_EXTENSIONS.get(self.extension, "Unknown")
        self.size_bytes = 0
        self.dimensions = (0, 0)  # Placeholder — no image lib
        self.analyzed_at = time.time()
        self.exists = False

        # Intentar obtener tamaño real del archivo
        try:
            if p.exists() and p.is_file():
                self.size_bytes = p.stat().st_size
                self.exists = True
        except Exception:
            pass

    def size_human(self) -> str:
        """Retorna tamaño legible (KB, MB)."""
        if self.size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        idx = min(int(math.log(self.size_bytes, 1024)), len(units) - 1)
        val = self.size_bytes / (1024 ** idx)
        return f"{val:.1f} {units[idx]}"

    def is_image(self) -> bool:
        return self.format != "Unknown"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "filename": self.filename,
            "stem": self.stem,
            "extension": self.extension,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "dimensions": list(self.dimensions),
            "analyzed_at": self.analyzed_at,
            "exists": self.exists,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ImageMetadata":
        m = cls.__new__(cls)
        m.path = d["path"]
        m.filename = d.get("filename", "")
        m.stem = d.get("stem", "")
        m.extension = d.get("extension", "")
        m.format = d.get("format", "Unknown")
        m.size_bytes = d.get("size_bytes", 0)
        m.dimensions = tuple(d.get("dimensions", [0, 0]))
        m.analyzed_at = d.get("analyzed_at", 0)
        m.exists = d.get("exists", False)
        return m


class AnalysisResult:
    """Resultado del analisis de una imagen."""

    def __init__(self, metadata: ImageMetadata):
        self.metadata = metadata
        self.description = ""
        self.tags = []
        self.objects = []
        self.confidence = 0.0
        self.cached = False
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "description": self.description,
            "tags": self.tags,
            "objects": self.objects,
            "confidence": self.confidence,
            "cached": self.cached,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisResult":
        meta = ImageMetadata.from_dict(d["metadata"])
        r = cls(meta)
        r.description = d.get("description", "")
        r.tags = d.get("tags", [])
        r.objects = d.get("objects", [])
        r.confidence = d.get("confidence", 0.0)
        r.cached = d.get("cached", False)
        r.created_at = d.get("created_at", time.time())
        return r


class AnalysisCache:
    """Cache de analisis con eviccion por antigüedad."""

    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self.cache = {}  # path -> AnalysisResult dict
        self.access_times = {}  # path -> last access timestamp
        self.hits = 0
        self.misses = 0

    def get(self, path: str):
        """Retorna resultado cacheado o None."""
        if path in self.cache:
            self.hits += 1
            self.access_times[path] = time.time()
            return self.cache[path]
        self.misses += 1
        return None

    def put(self, path: str, result_dict: dict):
        """Almacena resultado en cache, evictando si necesario."""
        if len(self.cache) >= self.max_entries and path not in self.cache:
            self._evict()
        self.cache[path] = result_dict
        self.access_times[path] = time.time()

    def _evict(self):
        """Evicta la entrada mas vieja por ultimo acceso."""
        if not self.access_times:
            return
        oldest = min(self.access_times, key=self.access_times.get)
        self.cache.pop(oldest, None)
        self.access_times.pop(oldest, None)

    def to_dict(self) -> dict:
        return {
            "cache": self.cache,
            "access_times": self.access_times,
            "hits": self.hits,
            "misses": self.misses,
        }

    @classmethod
    def from_dict(cls, d: dict, max_entries: int = 100) -> "AnalysisCache":
        c = cls(max_entries)
        c.cache = d.get("cache", {})
        c.access_times = d.get("access_times", {})
        c.hits = d.get("hits", 0)
        c.misses = d.get("misses", 0)
        return c


class ImageAnalyzer:
    """Coordinador de analisis de imagenes con persistencia."""

    # Patrones en nombre de archivo -> tags y objetos probables
    FILENAME_PATTERNS = {
        r"screenshot|captura|screen": (["screenshot", "ui"], ["ventana", "interfaz"]),
        r"logo|icon|icono": (["logo", "branding"], ["icono"]),
        r"photo|foto|img": (["fotografia", "captura"], []),
        r"chart|graph|grafico": (["grafico", "datos"], ["grafico", "ejes"]),
        r"diagram|diagrama": (["diagrama", "esquema"], ["nodos", "conexiones"]),
        r"banner|header": (["banner", "web"], ["texto", "imagen"]),
        r"avatar|profile|perfil": (["avatar", "perfil"], ["persona"]),
        r"map|mapa": (["mapa", "geoloc"], ["mapa"]),
        r"button|btn|boton": (["ui", "boton"], ["boton"]),
        r"error|bug": (["error", "debug"], ["mensaje_error"]),
    }

    # Carpeta padre -> contexto semántico
    FOLDER_CONTEXT = {
        "assets": "recurso del proyecto",
        "images": "imagen del proyecto",
        "screenshots": "captura de pantalla",
        "icons": "icono de la app",
        "uploads": "archivo subido por usuario",
        "media": "contenido multimedia",
        "temp": "archivo temporal",
        "output": "resultado generado",
        "docs": "imagen de documentacion",
    }

    def __init__(self, base_dir: str = "data/image_analyzer"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.cache = AnalysisCache(max_entries=100)
        self.total_analyzed = 0
        self.recent_analyses = deque(maxlen=20)

        self._load()

    def analyze(self, image_path: str) -> dict:
        """Analiza una imagen por metadatos y path. Retorna resultado."""
        path_str = str(image_path)

        # Revisar cache primero
        cached = self.cache.get(path_str)
        if cached:
            cached["cached"] = True
            return cached

        # Extraer metadatos
        metadata = ImageMetadata(path_str)

        # Construir resultado
        result = AnalysisResult(metadata)

        if not metadata.is_image():
            result.description = f"Archivo no reconocido como imagen: {metadata.filename}"
            result.confidence = 0.1
            result.tags = ["no_imagen"]
        else:
            result.description = self._generate_description(metadata)
            result.tags = self._extract_tags(metadata)
            result.objects = self._detect_objects(metadata)
            result.confidence = self._calculate_confidence(metadata)

        result_dict = result.to_dict()
        self.cache.put(path_str, result_dict)
        self.total_analyzed += 1
        self.recent_analyses.append({
            "path": path_str,
            "description": result.description,
            "timestamp": time.time(),
        })

        return result_dict

    def describe(self, image_path: str) -> str:
        """Obtiene o genera descripcion de la imagen."""
        result = self.analyze(image_path)
        return result.get("description", "Sin descripcion disponible")

    def get_cached(self, path: str):
        """Retorna analisis cacheado o None."""
        return self.cache.get(str(path))

    def _generate_description(self, meta: ImageMetadata) -> str:
        """Genera descripcion a partir de metadatos."""
        parts = []

        # Tipo de archivo
        parts.append(f"Imagen {meta.format}")

        # Nombre descriptivo (limpiar el stem)
        clean_name = re.sub(r"[-_]+", " ", meta.stem)
        clean_name = re.sub(r"\d{8,}", "", clean_name).strip()
        if clean_name and len(clean_name) > 2:
            parts.append(f'"{clean_name}"')

        # Tamaño
        if meta.size_bytes > 0:
            parts.append(f"({meta.size_human()})")

        # Contexto por carpeta
        parent_name = Path(meta.path).parent.name.lower()
        folder_ctx = self.FOLDER_CONTEXT.get(parent_name)
        if folder_ctx:
            parts.append(f"— {folder_ctx}")

        # Si no existe el archivo
        if not meta.exists:
            parts.append("[archivo no encontrado]")

        return " ".join(parts)

    def _extract_tags(self, meta: ImageMetadata) -> list:
        """Extrae tags del nombre de archivo y contexto."""
        tags = [meta.format.lower()]

        # Tags por tamaño
        if meta.size_bytes > 5_000_000:
            tags.append("alta_resolucion")
        elif meta.size_bytes < 10_000:
            tags.append("pequeno")

        # Tags por nombre
        name_lower = meta.stem.lower()
        for pattern, (pattern_tags, _) in self.FILENAME_PATTERNS.items():
            if re.search(pattern, name_lower):
                tags.extend(pattern_tags)
                break

        # Tags por carpeta
        parent = Path(meta.path).parent.name.lower()
        if parent in self.FOLDER_CONTEXT:
            tags.append(parent)

        return list(dict.fromkeys(tags))  # Deduplica preservando orden

    def _detect_objects(self, meta: ImageMetadata) -> list:
        """Detecta objetos probables por patrones de nombre."""
        name_lower = meta.stem.lower()

        for pattern, (_, objects) in self.FILENAME_PATTERNS.items():
            if re.search(pattern, name_lower):
                return objects

        # Objetos genéricos por formato
        if meta.format == "SVG":
            return ["vector", "formas"]
        if meta.format == "GIF":
            return ["animacion"]

        return []

    def _calculate_confidence(self, meta: ImageMetadata) -> float:
        """Calcula confianza del analisis (0-1)."""
        score = 0.3  # Base: solo tenemos metadatos

        if meta.exists:
            score += 0.2
        if meta.size_bytes > 0:
            score += 0.1

        # Nombre mas descriptivo → mas confianza
        clean = re.sub(r"[-_\d]+", "", meta.stem)
        if len(clean) > 5:
            score += 0.2

        # Patron reconocido → mas confianza
        name_lower = meta.stem.lower()
        for pattern in self.FILENAME_PATTERNS:
            if re.search(pattern, name_lower):
                score += 0.1
                break

        return min(1.0, score)

    def get_context_for_prompt(self, user_input: str = "", max_chars: int = 200) -> str:
        """Inyecta contexto de analisis si el usuario menciona imagenes."""
        image_keywords = [
            "imagen", "image", "foto", "photo", "captura", "screenshot",
            "grafico", "chart", "diagrama", "logo", "icono",
        ]
        input_lower = user_input.lower()

        if not any(kw in input_lower for kw in image_keywords):
            return ""

        if not self.recent_analyses:
            return "[IMAGEN] No hay imagenes analizadas recientemente."

        recent = list(self.recent_analyses)[-3:]
        descriptions = [a["description"] for a in recent]

        context = "[IMAGEN] Analisis recientes: " + " | ".join(descriptions)
        return context[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_analyzed": self.total_analyzed,
            "cache_entries": len(self.cache.cache),
            "cache_hits": self.cache.hits,
            "cache_misses": self.cache.misses,
            "cache_hit_rate": (
                self.cache.hits / max(1, self.cache.hits + self.cache.misses)
            ),
            "recent_count": len(self.recent_analyses),
        }

    def status(self) -> str:
        hits = self.cache.hits
        misses = self.cache.misses
        rate = hits / max(1, hits + misses) * 100
        return (f"  Analizadas: {self.total_analyzed} | "
                f"Cache: {len(self.cache.cache)} entradas, "
                f"{rate:.0f}% hit rate")

    def generate_report(self) -> str:
        lines = [
            "=== IMAGE ANALYZER ===",
            f"Total analizadas: {self.total_analyzed}",
            f"Cache: {len(self.cache.cache)}/{self.cache.max_entries} entradas",
            f"Cache hits: {self.cache.hits} | misses: {self.cache.misses}",
            "",
            "Analisis recientes:",
        ]
        for entry in list(self.recent_analyses)[-5:]:
            p = Path(entry["path"]).name
            lines.append(f"  {p}: {entry['description'][:80]}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_analyzed": self.total_analyzed,
            "recent_analyses": list(self.recent_analyses),
            "cache": self.cache.to_dict(),
        }
        path = self.base_dir / "image_analyzer.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "image_analyzer.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_analyzed = data.get("total_analyzed", 0)
            for entry in data.get("recent_analyses", []):
                self.recent_analyses.append(entry)
            if "cache" in data:
                self.cache = AnalysisCache.from_dict(data["cache"], max_entries=100)
        except Exception:
            pass

    def clear(self):
        self.cache = AnalysisCache(max_entries=100)
        self.total_analyzed = 0
        self.recent_analyses = deque(maxlen=20)
        self.save()
