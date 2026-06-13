"""
GENESIS — Document Processor.

Coordinador principal de procesamiento de documentos.
Usa DocumentReader, SmartChunker, y EntityExtractor internamente.
"""
import os
import re
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from core.document_reader import DocumentReader  # noqa: F401 — re-export
from core.document_chunker import SmartChunker  # noqa: F401 — re-export
from core.document_entities import EntityExtractor  # noqa: F401 — re-export

# Backward compatibility: these classes are re-exported so existing imports
# like `from core.document_processor import DocumentReader` still work.
__all__ = [
    "DocumentProcessor", "ProcessedDocument",
    "DocumentReader", "SmartChunker", "EntityExtractor",
]


@dataclass
class ProcessedDocument:
    """Resultado completo de un documento procesado."""
    doc_id: str = ""
    source_path: str = ""
    filename: str = ""
    format: str = ""
    raw_text: str = ""
    pages: int = 0
    word_count: int = 0
    char_count: int = 0
    tables: list = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    summary: str = ""
    chunks: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    processed_at: str = ""
    processing_time_s: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        # No guardar raw_text completo en persistencia (puede ser enorme)
        if len(d.get("raw_text", "")) > 5000:
            d["raw_text_preview"] = d["raw_text"][:5000] + "..."
            d["raw_text_full_length"] = len(d["raw_text"])
            d.pop("raw_text")
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessedDocument":
        # Restaurar raw_text si fue truncado
        if "raw_text_preview" in d:
            d["raw_text"] = d.pop("raw_text_preview", "")
            d.pop("raw_text_full_length", None)
        # Filtrar campos que no existen en el dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)



# ============================================================
# DocumentProcessor — Coordinador principal
# ============================================================
class DocumentProcessor:
    """
    Sistema completo de procesamiento de documentos.

    Coordina lectura, chunking, resumen y extraccion de entidades.
    Sigue el patron de modulos Genesis: save/load/clear/status/get_stats.
    """

    def __init__(self, base_dir: str = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path("data/document_processor")

        self.data_file = self.base_dir / "processor_state.json"
        self.uploads_dir = self.base_dir / "uploads"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(exist_ok=True)

        self.reader = DocumentReader()
        self.chunker = SmartChunker()
        self.extractor = EntityExtractor()

        # Estado persistente
        self.processed_docs: Dict[str, dict] = {}  # doc_id -> ProcessedDocument.to_dict()
        # Cache en memoria del texto completo (no se persiste a disco)
        self._full_text_cache: Dict[str, str] = {}  # doc_id -> raw_text completo
        self.total_processed = 0
        self.total_pages_read = 0
        self.total_entities_found = 0
        self.enabled = True

        self._load()

    def process(self, filepath: str, brain=None,
                summarize: bool = True, extract_entities: bool = True) -> dict:
        """
        Procesa un documento completo.

        Args:
            filepath: Ruta al documento
            brain: Instancia de Brain para resumen/extraccion LLM
            summarize: Generar resumen automatico
            extract_entities: Extraer entidades

        Returns:
            dict con toda la info del documento procesado
        """
        start_time = time.time()
        filepath = str(filepath).strip().strip('"').strip("'")

        # Leer documento
        read_result = self.reader.read(filepath)
        if "error" in read_result:
            return {"error": read_result["error"]}

        text = read_result.get("text", "")
        if not text.strip():
            return {"error": "El documento esta vacio o no se pudo extraer texto"}

        # Generar ID unico
        doc_id = hashlib.md5(f"{filepath}:{os.path.getmtime(filepath)}".encode()).hexdigest()[:12]
        filename = Path(filepath).name

        # Chunking
        chunks = self.chunker.chunk(text, source=filename)

        # Extraccion de entidades (regex — instantanea)
        entities = {}
        if extract_entities:
            entities = self.extractor.extract_regex(text)
            # Tablas del reader
            tables_from_reader = read_result.get("tables", [])
            # Tablas en texto plano
            tables_from_text = self.extractor.extract_tables_from_text(text)
            all_tables = tables_from_reader + tables_from_text
        else:
            all_tables = read_result.get("tables", [])

        # Extraccion LLM (si hay brain y el texto tiene contenido significativo)
        if extract_entities and brain and len(text) > 100:
            # Solo enviar los primeros chunks para no saturar
            for chunk in chunks[:3]:
                try:
                    llm_entities = self.extractor.extract_with_llm(chunk["text"], brain)
                    for key, values in llm_entities.items():
                        if isinstance(values, list):
                            existing = entities.get(key, [])
                            entities[key] = list(dict.fromkeys(existing + values))
                except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                    pass  # LLM entity extraction is best-effort

        # Resumen
        summary = ""
        if summarize and brain:
            summary = self._summarize_with_brain(text, chunks, brain)
        elif summarize:
            # Resumen extractivo inteligente sin LLM
            summary = self._extractive_summary(text, chunks)

        processing_time = time.time() - start_time

        # Crear documento procesado
        doc = ProcessedDocument(
            doc_id=doc_id,
            source_path=filepath,
            filename=filename,
            format=read_result.get("format", "unknown"),
            raw_text=text,
            pages=read_result.get("pages", 1),
            word_count=len(text.split()),
            char_count=len(text),
            tables=all_tables,
            entities=entities,
            summary=summary,
            chunks=[{"chunk_id": c["chunk_id"], "token_estimate": c["token_estimate"]} for c in chunks],
            metadata=read_result.get("metadata", {}),
            processed_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            processing_time_s=round(processing_time, 2),
        )

        # Guardar en estado
        self.processed_docs[doc_id] = doc.to_dict()
        # Cache del texto completo en memoria (to_dict() lo trunca a 5000 chars)
        self._full_text_cache[doc_id] = text
        # Limpiar cache viejo (max 10 documentos en memoria)
        if len(self._full_text_cache) > 10:
            oldest = list(self._full_text_cache.keys())[0]
            del self._full_text_cache[oldest]
        self.total_processed += 1
        self.total_pages_read += doc.pages
        self.total_entities_found += sum(len(v) for v in entities.values() if isinstance(v, list))
        self.save()

        # Construir respuesta formateada
        return self._format_result(doc, entities, all_tables)

    def get_full_text(self, doc_id: str) -> str:
        """Obtiene el texto completo de un documento procesado.
        Busca primero en cache de memoria, luego en estado persistido."""
        # Cache en memoria (texto completo)
        if doc_id in self._full_text_cache:
            return self._full_text_cache[doc_id]
        # Estado persistido (puede estar truncado a 5000 chars)
        stored = self.processed_docs.get(doc_id, {})
        return stored.get("raw_text", stored.get("raw_text_preview", ""))

    def summarize_document(self, filepath_or_text: str, brain=None,
                           level: str = "standard", is_text: bool = False) -> str:
        """
        Genera resumen de un documento o texto.

        Args:
            filepath_or_text: Ruta al archivo o texto directo
            brain: Instancia de Brain
            level: 'brief' (512 tok), 'standard' (2048), 'detailed' (4096),
                   'study' (8192) — material de estudio con tablas, dosis,
                   clasificaciones, valores clinicos, mecanismos de accion
            is_text: True si es texto directo, False si es ruta
        """
        if is_text:
            text = filepath_or_text
        else:
            read_result = self.reader.read(filepath_or_text)
            if "error" in read_result:
                return f"[ERROR] {read_result['error']}"
            text = read_result.get("text", "")

        if not text.strip():
            return "[ERROR] Documento vacio"

        chunks = self.chunker.chunk(text)

        if brain:
            return self._summarize_with_brain(text, chunks, brain, level=level)
        else:
            # Resumen sin LLM
            preview = text[:800].strip()
            cut = preview.rfind(".")
            if cut > 300:
                preview = preview[:cut + 1]
            word_count = len(text.split())
            return f"📄 Documento: {word_count} palabras\n\nVista previa:\n{preview}"

    def extract_from_document(self, filepath: str, brain=None,
                              entity_types: list = None) -> dict:
        """Extrae entidades de un documento."""
        read_result = self.reader.read(filepath)
        if "error" in read_result:
            return {"error": read_result["error"]}

        text = read_result.get("text", "")
        entities = self.extractor.extract_regex(text)

        if brain:
            chunks = self.chunker.chunk(text)
            for chunk in chunks[:5]:
                try:
                    llm_ents = self.extractor.extract_with_llm(
                        chunk["text"], brain, entity_types
                    )
                    for key, values in llm_ents.items():
                        if isinstance(values, list):
                            existing = entities.get(key, [])
                            entities[key] = list(dict.fromkeys(existing + values))
                except (json.JSONDecodeError, ValueError, TypeError, KeyError):
                    pass  # LLM entity extraction is best-effort

        # Agregar tablas
        tables = read_result.get("tables", [])
        tables += self.extractor.extract_tables_from_text(text)

        return {
            "filename": Path(filepath).name,
            "entities": entities,
            "tables": tables,
            "word_count": len(text.split()),
            "entity_count": sum(len(v) for v in entities.values() if isinstance(v, list)),
        }

    def _select_representative_chunks(self, chunks: list, max_samples: int = 40) -> list:
        """
        Selecciona chunks representativos para documentos muy largos.

        Estrategia: primeros N (intro/contexto) + muestreo uniforme del medio
        + ultimos M (conclusion). Asi se cubre todo el documento sin procesar
        los 312 chunks de un libro completo.

        Returns:
            Lista de tuplas (indice_original, chunk)
        """
        total = len(chunks)
        if total <= max_samples:
            return list(enumerate(chunks))

        # Primeros 8 chunks (introduccion, prefacio, indice)
        head_n = min(8, total // 4)
        # Ultimos 5 chunks (conclusion, bibliografia, anexos)
        tail_n = min(5, total // 6)
        # Del medio: muestreo uniforme
        middle_budget = max_samples - head_n - tail_n
        middle_start = head_n
        middle_end = total - tail_n

        selected = []

        # Head
        for i in range(head_n):
            selected.append((i, chunks[i]))

        # Middle — muestreo uniforme
        middle_range = middle_end - middle_start
        if middle_range > 0 and middle_budget > 0:
            step = max(1, middle_range // middle_budget)
            for i in range(middle_start, middle_end, step):
                if len(selected) >= head_n + middle_budget:
                    break
                selected.append((i, chunks[i]))

        # Tail
        for i in range(max(middle_end, head_n), total):
            selected.append((i, chunks[i]))

        return selected

    def _hierarchical_reduce(self, partial_summaries: list, brain,
                              instruction: str, max_tok: int,
                              batch_size: int = 12,
                              max_context_chars: int = 18000,
                              level: str = "standard") -> str:
        """
        Reduce jerarquico: si los resumenes parciales no caben en un solo
        prompt de reduce, los agrupa en batches y reduce en multiples niveles.

        Nivel 1: batches de 12 resumenes → meta-resumenes
        Nivel 2: todos los meta-resumenes → resumen final
        (se repite si aun excede el contexto)

        En modo 'study', preserva datos exactos, tablas, clasificaciones.
        """
        is_study = (level == "study")
        combined = "\n\n".join(partial_summaries)

        # System prompts según nivel
        if is_study:
            single_reduce_system = (
                "Eres un profesor universitario creando material de estudio exhaustivo. "
                "Combina las extracciones parciales en un documento de estudio COMPLETO. "
                "PRESERVA todos los datos exactos: tablas de farmacos, dosis, clasificaciones, "
                "valores clinicos, formulas, mecanismos. Organiza por capitulo/tema. "
                "Usa tablas markdown. NO omitas ni generalices datos. Responde en español."
            )
            batch_reduce_system = (
                "Integra estas extracciones de estudio preservando TODOS los datos exactos: "
                "definiciones, tablas, clasificaciones, dosis, valores clinicos, formulas. "
                "Usa tablas markdown. No generalices ni omitas datos. Responde en español."
            )
            final_reduce_system = (
                "Eres un profesor universitario creando el material de estudio DEFINITIVO. "
                "Combina todas las secciones en un resumen de estudio exhaustivo, organizado "
                "por capitulo/tema. PRESERVA: todas las tablas de farmacos con dosis exactas, "
                "todas las clasificaciones completas, todos los valores clinicos con rangos, "
                "todos los mecanismos de accion, todas las formulas. "
                "Formato: encabezados por tema, tablas markdown para datos tabulares, "
                "listas para clasificaciones. El resultado debe servir para estudiar "
                "sin necesidad del texto original. Responde en español."
            )
        else:
            single_reduce_system = "Combina estos resumenes parciales en un resumen final coherente y completo en español. No omitas temas importantes."
            batch_reduce_system = "Integra estos resumenes parciales en un resumen cohesivo en español. Captura todos los puntos clave sin omitir temas."
            final_reduce_system = "Combina estos resumenes seccionales en un resumen final coherente, detallado y completo en español. Asegurate de cubrir todos los capitulos y temas del documento."

        # Si cabe en un solo reduce, hacerlo directo
        if len(combined) <= max_context_chars:
            if is_study:
                reduce_prompt = f"""{instruction}

Estas son las extracciones de contenido de estudio de cada seccion del documento:

{combined}

Genera el MATERIAL DE ESTUDIO FINAL organizado por capitulo/tema. Preserva TODOS los datos exactos (tablas, dosis, clasificaciones, valores, formulas):"""
            else:
                reduce_prompt = f"""{instruction}

Estos son los resumenes parciales del documento completo:

{combined}

Genera el resumen final unificado. Asegurate de cubrir TODOS los temas mencionados:"""
            try:
                return brain.think(
                    system_prompt=single_reduce_system,
                    messages=[{"role": "user", "content": reduce_prompt}],
                    max_tokens=max_tok,
                )
            except (RuntimeError, ValueError, TimeoutError, OSError) as e:
                # LLM single-reduce failed; fall back to concatenated summaries
                return combined

        # Multi-nivel: agrupar en batches y reducir
        meta_summaries = []
        batch_max_tok = min(4096, max_tok) if is_study else min(2048, max_tok)

        for batch_start in range(0, len(partial_summaries), batch_size):
            batch = partial_summaries[batch_start:batch_start + batch_size]
            batch_text = "\n\n".join(batch)

            if is_study:
                batch_prompt = f"""Integra las siguientes extracciones de estudio (grupo {batch_start // batch_size + 1}) en un material de estudio cohesivo:

{batch_text[:max_context_chars]}

Material de estudio integrado — preserva TODOS los datos exactos (tablas, dosis, clasificaciones, valores):"""
            else:
                batch_prompt = f"""Resume de forma concisa los siguientes fragmentos de un documento largo (grupo {batch_start // batch_size + 1}):

{batch_text[:max_context_chars]}

Resumen integrado de este grupo:"""
            try:
                meta = brain.think(
                    system_prompt=batch_reduce_system,
                    messages=[{"role": "user", "content": batch_prompt}],
                    max_tokens=batch_max_tok,
                )
                if meta and meta.strip():
                    meta_summaries.append(meta.strip())
            except (RuntimeError, ValueError, TimeoutError, OSError) as e:
                # LLM batch-reduce failed; fall back to first summary in batch
                if batch:
                    meta_summaries.append(batch[0])

        if not meta_summaries:
            return combined[:3000]

        # Recursion si aun hay demasiados meta-resumenes
        meta_combined = "\n\n".join(meta_summaries)
        if len(meta_combined) > max_context_chars and len(meta_summaries) > batch_size:
            return self._hierarchical_reduce(
                meta_summaries, brain, instruction, max_tok,
                batch_size=batch_size, max_context_chars=max_context_chars,
                level=level,
            )

        # Reduce final
        if is_study:
            final_prompt = f"""{instruction}

El documento fue analizado en {len(meta_summaries)} secciones. Estas son las extracciones de estudio de cada seccion:

{meta_combined[:max_context_chars]}

Genera el MATERIAL DE ESTUDIO DEFINITIVO. Organiza por capitulo/tema.
OBLIGATORIO preservar: tablas de farmacos con dosis, clasificaciones completas,
valores clinicos con rangos, mecanismos de accion, formulas, procedimientos.
Usa tablas markdown. El resultado debe servir para estudiar sin el texto original:"""
        else:
            final_prompt = f"""{instruction}

El documento fue analizado en {len(meta_summaries)} secciones. Estos son los resumenes de cada seccion:

{meta_combined[:max_context_chars]}

Genera el resumen final COMPLETO y unificado. Cubre TODOS los temas del documento:"""
        try:
            return brain.think(
                system_prompt=final_reduce_system,
                messages=[{"role": "user", "content": final_prompt}],
                max_tokens=max_tok,
            )
        except (RuntimeError, ValueError, TimeoutError, OSError) as e:
            # LLM final-reduce failed; fall back to concatenated meta-summaries
            return meta_combined

    def _extractive_summary(self, text: str, chunks: list) -> str:
        """
        Resumen extractivo inteligente SIN LLM.
        Extrae estructura del documento (TOC, headings, secciones) y
        muestrea contenido representativo de distintas partes.
        Mucho mejor que text[:500] que solo muestra la portada.
        """
        lines = text.split("\n")
        total_lines = len(lines)
        word_count = len(text.split())

        # 1. Detectar donde empieza el contenido real (saltar portada/dedicatoria/TOC)
        content_start = 0
        for i, line in enumerate(lines[:min(300, total_lines)]):
            stripped = line.strip().lower()
            # Detectar inicio de contenido narrativo real
            if re.match(r'^(cap[ií]tulo\s+[1i]|tema\s+1|parte\s+[1i][\s\.]|'
                         r'[1i][\.\)]\s+[a-záéíóú]|introducci[oó]n\b|'
                         r'indice|índice)', stripped):
                content_start = i
                break

        # 2. Extraer headings de nivel CAPITULO/PARTE (no sub-secciones)
        chapters = []
        # Patron estricto: solo "Capitulo N", "Parte N", "Tema N", numerados
        chapter_patterns = [
            r'^(Cap[ií]tulo|CAPITULO|CAP[ÍI]TULO)\s+\d+',
            r'^(Tema|TEMA)\s+\d+',
            r'^(Parte|PARTE)\s+[IVXLivxl\d]+',
            r'^(Secci[oó]n|SECCI[OÓ]N|Unidad|UNIDAD)\s+\d+',
        ]
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or len(stripped) < 5:
                continue
            for pattern in chapter_patterns:
                m = re.match(pattern, stripped, re.IGNORECASE)
                if m:
                    # Tomar la linea completa como titulo del capitulo (max 120 chars)
                    chapter_title = stripped[:120]
                    if chapter_title not in [c[1] for c in chapters]:
                        chapters.append((i, chapter_title))
                    break

        # Si no hay capitulos explicitos, buscar patron numerico "1. Titulo"
        if len(chapters) < 3:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue
                # Solo "N. Titulo" al inicio de linea con titulo capitalizado
                m = re.match(r'^(\d{1,2})[\.\)]\s+([A-ZÁÉÍÓÚ][a-záéíóúña-z\s]{5,})', stripped)
                if m:
                    num = int(m.group(1))
                    if 1 <= num <= 50:
                        chapter_title = stripped[:120]
                        if chapter_title not in [c[1] for c in chapters]:
                            chapters.append((i, chapter_title))

        # 3. Construir resumen estructurado
        parts = []

        # Titulo del documento (primeras 3 lineas no vacias significativas)
        title_lines = []
        for line in lines[:30]:
            stripped = line.strip()
            if stripped and len(stripped) > 2:
                # Saltar lineas que parecen metadata (paginas, numeros)
                if not re.match(r'^\d+$', stripped) and len(stripped) > 4:
                    title_lines.append(stripped)
                    if len(title_lines) >= 3:
                        break
        if title_lines:
            parts.append("\n".join(title_lines))

        # Estructura del documento (capitulos detectados)
        if chapters:
            parts.append("")
            parts.append("📚 **Estructura del documento:**")
            shown = 0
            for _, ch_title in chapters[:30]:
                h_clean = ch_title.strip()
                if len(h_clean) > 90:
                    h_clean = h_clean[:87] + "..."
                parts.append(f"  • {h_clean}")
                shown += 1
            if len(chapters) > 30:
                parts.append(f"  ... y {len(chapters) - 30} capitulos mas")

        # 4. Muestra de contenido real (buscar primer parrafo narrativo)
        # Saltar TOC, indices, y buscar texto de mas de 80 chars (oraciones reales)
        first_paragraph = ""
        search_start = max(content_start, 10)  # Saltar al menos las primeras 10 lineas
        for i in range(search_start, min(search_start + 200, total_lines)):
            stripped = lines[i].strip()
            # Buscar linea con texto narrativo (>80 chars, no es heading, no es TOC)
            if (len(stripped) > 80 and
                not stripped.isupper() and
                not re.match(r'^\d+[\.\)]\s', stripped) and
                not re.match(r'^(cap[ií]tulo|tema|parte|secci)', stripped, re.IGNORECASE) and
                '.' in stripped):  # Contiene al menos un punto (oracion)
                # Acumular parrafo
                first_paragraph = stripped
                # Tomar las siguientes lineas del mismo parrafo
                for j in range(i + 1, min(i + 5, total_lines)):
                    next_line = lines[j].strip()
                    if next_line and len(next_line) > 20 and not next_line.isupper():
                        first_paragraph += " " + next_line
                    else:
                        break
                break

        if first_paragraph:
            # Cortar en punto si es muy largo
            if len(first_paragraph) > 400:
                cut = first_paragraph[:400].rfind(".")
                if cut > 150:
                    first_paragraph = first_paragraph[:cut + 1]
                else:
                    first_paragraph = first_paragraph[:400] + "..."
            parts.append("")
            parts.append("📖 **Inicio del contenido:**")
            parts.append(first_paragraph.strip())

        # 5. Muestra del medio del documento (buscar parrafo narrativo)
        if len(chunks) > 10:
            mid_idx = len(chunks) // 2
            mid_chunk = chunks[mid_idx]
            mid_text = mid_chunk["text"] if isinstance(mid_chunk, dict) else str(mid_chunk)
            # Buscar la primera oracion completa en el chunk medio
            mid_lines = mid_text.split("\n")
            mid_sample = ""
            for ml in mid_lines:
                ml = ml.strip()
                if len(ml) > 60 and '.' in ml and not ml.isupper():
                    mid_sample = ml
                    break
            if not mid_sample:
                mid_sample = mid_text[:300].strip()
            if len(mid_sample) > 350:
                cut = mid_sample[:350].rfind(".")
                if cut > 100:
                    mid_sample = mid_sample[:cut + 1]
                else:
                    mid_sample = mid_sample[:350] + "..."
            if mid_sample.strip():
                parts.append("")
                parts.append(f"📖 **Contenido medio (seccion {mid_idx + 1}/{len(chunks)}):**")
                parts.append(mid_sample)

        # Si no hay capitulos ni contenido, al menos mostrar algo util
        if not chapters and not first_paragraph:
            # Documento sin estructura clara — mostrar primeros parrafos no triviales
            meaningful_text = ""
            for line in lines:
                stripped = line.strip()
                if stripped and len(stripped) > 50:
                    meaningful_text += stripped + " "
                    if len(meaningful_text) > 500:
                        break
            if meaningful_text:
                cut = meaningful_text[:500].rfind(".")
                if cut > 200:
                    meaningful_text = meaningful_text[:cut + 1]
                else:
                    meaningful_text = meaningful_text[:500] + "..."
                parts.append("")
                parts.append(meaningful_text.strip())

        return "\n".join(parts)

    def _summarize_with_brain(self, text: str, chunks: list,
                               brain, level: str = "standard") -> str:
        """
        Resumen Map-Reduce jerarquico usando el LLM.

        1. Si cabe en 1 chunk → resumen directo
        2. Si multiples chunks (<=50) → Map-Reduce estandar
        3. Si muchos chunks (>50) → muestreo inteligente + reduce jerarquico

        Esto permite resumir libros de 300+ paginas sin procesar cada chunk
        individualmente (lo que tardaria 15+ minutos).
        """
        max_tokens_map = {"brief": 512, "standard": 2048, "detailed": 4096, "study": 8192}
        max_tok = max_tokens_map.get(level, 2048)

        level_instruction = {
            "brief": "Genera un resumen MUY breve (2-3 oraciones) del documento.",
            "standard": "Genera un resumen completo del documento. Incluye los puntos principales, conclusiones clave y datos importantes.",
            "detailed": "Genera un resumen detallado y extenso del documento. Incluye: estructura general, puntos principales de cada seccion o capitulo, datos especificos relevantes, conclusiones, y una lista de hallazgos clave. El resumen debe cubrir TODO el contenido del documento, no solo el inicio.",
            "study": (
                "Genera un RESUMEN DE ESTUDIO completo y exhaustivo del documento. "
                "Este resumen debe servir como material de estudio academico. "
                "OBLIGATORIO incluir:\n"
                "- Definiciones textuales de conceptos clave\n"
                "- Clasificaciones completas (con todos los tipos/grados/categorias)\n"
                "- Tablas de datos: farmacos con dosis, onset, duracion, via de administracion\n"
                "- Valores clinicos especificos (rangos normales, umbrales, parametros)\n"
                "- Mecanismos de accion (receptores, vias metabolicas, farmacocinetica)\n"
                "- Indicaciones y contraindicaciones\n"
                "- Procedimientos paso a paso\n"
                "- Complicaciones y su manejo\n"
                "- Formulas y calculos relevantes\n\n"
                "FORMATO: Organizar por capitulo/tema. Usar tablas markdown cuando haya "
                "datos tabulares (farmacos, clasificaciones, valores). NO generalizar — "
                "incluir los datos EXACTOS del texto (nombres, numeros, dosis, porcentajes). "
                "El resumen debe ser lo suficientemente detallado para estudiar sin el texto original."
            ),
        }

        instruction = level_instruction.get(level, level_instruction["standard"])
        is_study = (level == "study")

        # System prompt segun nivel
        if is_study:
            system_prompt_direct = (
                "Eres un profesor universitario experto creando material de estudio. "
                "Extrae TODOS los datos concretos: definiciones, clasificaciones, "
                "tablas de farmacos (nombre, dosis, onset, duracion), valores clinicos, "
                "mecanismos de accion, formulas. Usa tablas markdown. "
                "NO generalices — incluye datos EXACTOS del texto. Responde en español."
            )
        else:
            system_prompt_direct = "Eres un experto en analisis de documentos. Genera resumenes claros y precisos en español."

        # Caso simple: 1 chunk
        if len(chunks) <= 1:
            prompt = f"""{instruction}

Documento:
---
{text[:12000] if is_study else text[:7000]}
---

Resumen:"""
            try:
                return brain.think(
                    system_prompt=system_prompt_direct,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tok,
                )
            except (RuntimeError, ValueError, TimeoutError, OSError) as e:
                return f"[Error generando resumen: {e}]"

        # Seleccionar chunks representativos (muestreo inteligente para docs grandes)
        # En modo study se procesan más chunks para mayor cobertura
        max_samples = 60 if is_study else 40
        selected_chunks = self._select_representative_chunks(chunks, max_samples=max_samples)
        total_chunks = len(chunks)
        sampled = len(selected_chunks)

        # Tokens por chunk en MAP phase — study necesita más para capturar datos técnicos
        map_max_tokens = 1500 if is_study else 800
        chunk_text_limit = 6000 if is_study else 5000

        # Map phase: resumir cada chunk seleccionado
        partial_summaries = []

        # System prompt del Map phase
        if is_study:
            map_system_prompt = (
                "Eres un profesor extrayendo contenido de estudio de un texto academico. "
                "EXTRAE del fragmento: definiciones textuales, clasificaciones con TODOS sus "
                "tipos/grados, tablas de farmacos (nombre, dosis, onset, duracion, via), "
                "valores clinicos con rangos normales, mecanismos de accion, formulas, "
                "indicaciones/contraindicaciones, procedimientos. "
                "Usa formato markdown con tablas. Incluye datos EXACTOS (numeros, nombres, "
                "porcentajes). NO generalices ni omitas datos. Responde en español."
            )
        else:
            map_system_prompt = "Resume este fragmento de documento de forma concisa en español. Captura los puntos clave, conceptos y datos relevantes."

        for idx, (orig_idx, chunk) in enumerate(selected_chunks):
            chunk_text = chunk["text"] if isinstance(chunk, dict) else chunk
            # Indicar posicion real en el documento
            position_hint = ""
            if orig_idx < 3:
                position_hint = "(inicio del documento) "
            elif orig_idx >= total_chunks - 3:
                position_hint = "(final del documento) "

            if is_study:
                prompt = f"""Extrae TODO el contenido de estudio del siguiente fragmento {position_hint}(seccion {orig_idx + 1} de {total_chunks}) de un texto academico:

---
{chunk_text[:chunk_text_limit]}
---

Extrae: definiciones, clasificaciones completas, tablas de datos (farmacos/dosis/valores), mecanismos, formulas, procedimientos. Usa tablas markdown donde corresponda. Datos EXACTOS, NO generalices:"""
            else:
                prompt = f"""Resume el siguiente fragmento {position_hint}(seccion {orig_idx + 1} de {total_chunks}) de un documento:

---
{chunk_text[:chunk_text_limit]}
---

Resumen del fragmento (captura los puntos clave, temas y datos importantes):"""
            try:
                partial = brain.think(
                    system_prompt=map_system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=map_max_tokens,
                )
                if partial and partial.strip():
                    partial_summaries.append(f"Seccion {orig_idx + 1}/{total_chunks}: {partial.strip()}")
            except (RuntimeError, ValueError, TimeoutError) as e:
                pass  # LLM chunk summarization can fail; skip chunk

        if not partial_summaries:
            return text[:500] + "..."

        # Reduce: usar reduce jerarquico para manejar muchos resumenes parciales
        # En modo study, batches más grandes y más contexto para preservar datos
        reduce_batch = 8 if is_study else 12
        reduce_context = 24000 if is_study else 18000
        return self._hierarchical_reduce(
            partial_summaries, brain, instruction, max_tok,
            batch_size=reduce_batch, max_context_chars=reduce_context,
            level=level,
        )

    def _format_result(self, doc: ProcessedDocument, entities: dict, tables: list) -> dict:
        """Formatea el resultado para mostrar al usuario."""
        # Construir texto formateado
        lines = []
        lines.append(f"📄 **{doc.filename}** ({doc.format.upper()})")
        lines.append(f"📊 {doc.pages} paginas | {doc.word_count:,} palabras | {doc.char_count:,} caracteres")
        lines.append(f"⏱️ Procesado en {doc.processing_time_s}s")
        lines.append("")

        # Metadata relevante
        if doc.metadata:
            meta_items = []
            for k, v in doc.metadata.items():
                if v and k not in ("page_count",):
                    meta_items.append(f"  - {k}: {v}")
            if meta_items:
                lines.append("📋 **Metadata:**")
                lines.extend(meta_items[:8])
                lines.append("")

        # Resumen o vista previa
        if doc.summary:
            # Si el resumen es corto y parece una vista previa (no generado por LLM)
            is_preview = len(doc.summary) < 600 and doc.word_count > 1000
            if is_preview:
                lines.append("📝 **Vista previa del contenido:**")
                lines.append(doc.summary)
            else:
                lines.append("📝 **Resumen:**")
                lines.append(doc.summary)
            lines.append("")

        # Entidades
        if entities:
            lines.append("🔍 **Entidades encontradas:**")
            for etype, values in entities.items():
                if isinstance(values, list) and values:
                    display = values[:10]
                    extra = f" (+{len(values)-10} mas)" if len(values) > 10 else ""
                    lines.append(f"  - **{etype}** ({len(values)}): {', '.join(str(v) for v in display)}{extra}")
            lines.append("")

        # Tablas
        if tables:
            lines.append(f"📊 **Tablas detectadas:** {len(tables)}")
            for i, t in enumerate(tables[:5]):
                headers = t.get("headers", [])
                rows = t.get("rows", 0)
                cols = t.get("cols", 0)
                header_str = " | ".join(str(h) for h in headers[:6])
                if len(headers) > 6:
                    header_str += " | ..."
                lines.append(f"  Tabla {i+1}: {rows} filas x {cols} cols — [{header_str}]")
            lines.append("")

        formatted_text = "\n".join(lines)

        return {
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "format": doc.format,
            "pages": doc.pages,
            "word_count": doc.word_count,
            "char_count": doc.char_count,
            "summary": doc.summary,
            "entities": entities,
            "tables": tables,
            "metadata": doc.metadata,
            "processing_time_s": doc.processing_time_s,
            "formatted_output": formatted_text,
            "chunks_count": len(doc.chunks),
        }

    def get_document_info(self, doc_id: str) -> dict:
        """Info de un documento ya procesado."""
        return self.processed_docs.get(doc_id, {"error": f"Documento {doc_id} no encontrado"})

    def search_documents(self, query: str, top_k: int = 5) -> list:
        """Busca en documentos procesados por palabras clave."""
        query_words = set(query.lower().split())
        results = []

        for doc_id, doc_data in self.processed_docs.items():
            # Buscar en filename, summary
            searchable = f"{doc_data.get('filename', '')} {doc_data.get('summary', '')}".lower()
            score = sum(1 for w in query_words if w in searchable)
            if score > 0:
                results.append({
                    "doc_id": doc_id,
                    "filename": doc_data.get("filename", ""),
                    "score": score,
                    "summary_preview": doc_data.get("summary", "")[:200],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # ============================================================
    # Interfaz estandar de modulo Genesis
    # ============================================================
    def save(self):
        """Persiste estado a disco."""
        try:
            state = {
                "processed_docs": self.processed_docs,
                "total_processed": self.total_processed,
                "total_pages_read": self.total_pages_read,
                "total_entities_found": self.total_entities_found,
            }
            self.base_dir.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError):
            pass  # Non-critical: state persistence is best-effort

    def _load(self):
        """Carga estado desde disco."""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.processed_docs = state.get("processed_docs", {})
                self.total_processed = state.get("total_processed", 0)
                self.total_pages_read = state.get("total_pages_read", 0)
                self.total_entities_found = state.get("total_entities_found", 0)
        except (OSError, json.JSONDecodeError, ValueError, KeyError):
            pass  # Start fresh if state file is corrupted

    def clear(self):
        """Limpia todos los documentos procesados."""
        self.processed_docs = {}
        self.total_processed = 0
        self.total_pages_read = 0
        self.total_entities_found = 0
        self.save()

    def status(self) -> str:
        """Estado del procesador de documentos."""
        formats = set()
        for doc in self.processed_docs.values():
            formats.add(doc.get("format", "?"))

        return (
            f"=== Document Processor ===\n"
            f"  Documentos procesados: {self.total_processed}\n"
            f"  Paginas leidas: {self.total_pages_read}\n"
            f"  Entidades encontradas: {self.total_entities_found}\n"
            f"  Formatos usados: {', '.join(formats) if formats else 'ninguno'}\n"
            f"  Soportados: PDF, DOCX, XLSX, CSV, TXT, MD, JSON, imagenes (OCR)"
        )

    def generate_report(self) -> str:
        """Reporte detallado."""
        lines = [self.status(), ""]

        if self.processed_docs:
            lines.append("Ultimos documentos:")
            for doc_id, doc_data in list(self.processed_docs.items())[-5:]:
                lines.append(
                    f"  [{doc_id}] {doc_data.get('filename', '?')} "
                    f"({doc_data.get('format', '?')}, "
                    f"{doc_data.get('word_count', 0)} words, "
                    f"{doc_data.get('processed_at', '?')})"
                )

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Stats para dashboard."""
        return {
            "total_processed": self.total_processed,
            "total_pages": self.total_pages_read,
            "total_entities": self.total_entities_found,
            "docs_in_memory": len(self.processed_docs),
        }

