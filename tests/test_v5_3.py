"""
GENESIS Test Suite v5.3 — Document Processor Tests
Tests para el sistema de procesamiento de documentos.

Cubre:
1. DocumentReader — lectura multi-formato
2. SmartChunker — chunking inteligente
3. EntityExtractor — extraccion regex
4. DocumentProcessor — coordinador
5. Tool integration
6. Web UI endpoints
"""
import sys
import os
import json
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  ✓ {name}")
        passed += 1
    else:
        print(f"  ✗ {name}")
        failed += 1


# ============================================================
# 1. Imports
# ============================================================
print("\n--- Imports ---")

from core.document_processor import (
    DocumentProcessor, DocumentReader, SmartChunker,
    EntityExtractor, ProcessedDocument
)
test("DocumentProcessor importable", True)
test("DocumentReader importable", True)
test("SmartChunker importable", True)
test("EntityExtractor importable", True)
test("ProcessedDocument importable", True)


# ============================================================
# 2. Required Packages
# ============================================================
print("\n--- Required Packages ---")

test("PyMuPDF (fitz) importable", (lambda: (__import__('fitz'), True)[-1])())
test("python-docx importable", (lambda: (__import__('docx'), True)[-1])())
test("openpyxl importable", (lambda: (__import__('openpyxl'), True)[-1])())
test("Pillow importable", (lambda: (__import__('PIL'), True)[-1])())


# ============================================================
# 3. DocumentReader
# ============================================================
print("\n--- DocumentReader ---")

reader = DocumentReader()

test("DocumentReader has SUPPORTED_FORMATS", len(reader.SUPPORTED_FORMATS) >= 15)
test("PDF in supported formats", ".pdf" in reader.SUPPORTED_FORMATS)
test("DOCX in supported formats", ".docx" in reader.SUPPORTED_FORMATS)
test("XLSX in supported formats", ".xlsx" in reader.SUPPORTED_FORMATS)
test("CSV in supported formats", ".csv" in reader.SUPPORTED_FORMATS)
test("TXT in supported formats", ".txt" in reader.SUPPORTED_FORMATS)
test("PNG in supported formats", ".png" in reader.SUPPORTED_FORMATS)

# Test reading nonexistent file
result = reader.read("/nonexistent/file.pdf")
test("Read nonexistent file returns error", "error" in result)

# Test unsupported format
result = reader.read("file.xyz")
test("Read unsupported format returns error", "error" in result)

# Test reading a TXT file
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write("Linea uno del documento.\nLinea dos con mas texto.\nLinea tres final.")
    tmp_txt = f.name

result = reader.read(tmp_txt)
test("Read TXT succeeds", "error" not in result)
test("Read TXT has text", len(result.get("text", "")) > 20)
test("Read TXT format is txt", result.get("format") == "txt")
test("Read TXT has metadata", "metadata" in result)
os.unlink(tmp_txt)

# Test reading a CSV file
with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
    f.write("nombre,edad,ciudad\nJuan,25,Buenos Aires\nMaria,30,Cordoba\nPedro,28,Rosario")
    tmp_csv = f.name

result = reader.read(tmp_csv)
test("Read CSV succeeds", "error" not in result)
test("Read CSV has tables", len(result.get("tables", [])) > 0)
test("Read CSV table has headers", result["tables"][0].get("headers") == ["nombre", "edad", "ciudad"])
test("Read CSV table has data rows", len(result["tables"][0].get("data", [])) == 3)
os.unlink(tmp_csv)

# Test reading a JSON file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json.dump({"nombre": "Genesis", "version": "5.3", "modulos": 112}, f)
    tmp_json = f.name

result = reader.read(tmp_json)
test("Read JSON succeeds", "error" not in result)
test("Read JSON has json_keys metadata", "json_keys" in result.get("metadata", {}))
os.unlink(tmp_json)


# ============================================================
# 4. SmartChunker
# ============================================================
print("\n--- SmartChunker ---")

chunker = SmartChunker(max_chunk_tokens=100, overlap_tokens=20)

# Short text (single chunk)
short = "Esta es una oracion corta."
chunks = chunker.chunk(short)
test("Short text = 1 chunk", len(chunks) == 1)
test("Chunk has text", chunks[0]["text"] == short)
test("Chunk has chunk_id", chunks[0]["chunk_id"] == 0)
test("Chunk has token_estimate", chunks[0]["token_estimate"] > 0)

# Long text (multiple chunks)
long_text = ". ".join([f"Oracion numero {i} del documento de prueba con contenido variado y texto largo suficiente" for i in range(50)])
chunks = chunker.chunk(long_text)
test("Long text = multiple chunks", len(chunks) > 1)
test("All chunks have text", all(c["text"] for c in chunks))
test("Chunks are sequential", all(chunks[i]["chunk_id"] == i for i in range(len(chunks))))

# Empty text
chunks = chunker.chunk("")
test("Empty text = 0 chunks", len(chunks) == 0)

# Token estimation
tokens = chunker._estimate_tokens("Hola mundo esto es una prueba")  # ~30 chars
test("Token estimate reasonable", 5 <= tokens <= 15)


# ============================================================
# 5. EntityExtractor
# ============================================================
print("\n--- EntityExtractor ---")

extractor = EntityExtractor()

text_with_entities = """
Contacto: juan.perez@gmail.com o maria@empresa.com.ar
Telefono: +54 11 4567-8901
Fecha: 15/03/2026
Monto: $1.500,00 pesos
CUIT: 20-12345678-9
DNI: 30.123.456
Web: https://genesis.local/api
Porcentaje: 15.5%
IP: 192.168.1.100
"""

entities = extractor.extract_regex(text_with_entities)
test("Extracts emails", len(entities.get("emails", [])) >= 2)
test("Extracts phones", len(entities.get("telefonos", [])) >= 1)
test("Extracts dates", len(entities.get("fechas", [])) >= 1)
test("Extracts money", len(entities.get("montos", [])) >= 1)
test("Extracts CUIT", len(entities.get("cuit_cuil", [])) >= 1)
test("Extracts URLs", len(entities.get("urls", [])) >= 1)
test("Extracts percentages", len(entities.get("porcentajes", [])) >= 1)
test("Extracts IPs", len(entities.get("ips", [])) >= 1)

# Empty text
entities_empty = extractor.extract_regex("")
test("Empty text = no entities", len(entities_empty) == 0)

# Table detection from text
table_text = """
Nombre | Edad | Ciudad
Juan | 25 | Buenos Aires
Maria | 30 | Cordoba
Pedro | 28 | Rosario
"""
tables = extractor.extract_tables_from_text(table_text)
test("Detects table from pipe-separated text", len(tables) >= 1)
test("Table has correct headers", tables[0]["headers"] == ["Nombre", "Edad", "Ciudad"] if tables else False)


# ============================================================
# 6. ProcessedDocument
# ============================================================
print("\n--- ProcessedDocument ---")

doc = ProcessedDocument(
    doc_id="test123",
    source_path="/tmp/test.txt",
    filename="test.txt",
    format="txt",
    raw_text="Texto corto de prueba",
    pages=1,
    word_count=4,
    char_count=21,
)
test("ProcessedDocument creates", doc.doc_id == "test123")
test("ProcessedDocument to_dict works", isinstance(doc.to_dict(), dict))

# Test with long raw_text (should truncate in to_dict)
doc_long = ProcessedDocument(
    doc_id="test456",
    filename="long.txt",
    format="txt",
    raw_text="x" * 10000,
)
d = doc_long.to_dict()
test("Long raw_text truncated in to_dict", "raw_text_preview" in d)
test("Long raw_text full_length preserved", d.get("raw_text_full_length") == 10000)

# from_dict
doc_restored = ProcessedDocument.from_dict(d)
test("from_dict restores doc", doc_restored.doc_id == "test456")


# ============================================================
# 7. DocumentProcessor Integration
# ============================================================
print("\n--- DocumentProcessor ---")

import tempfile
tmp_dir = tempfile.mkdtemp()
processor = DocumentProcessor(base_dir=tmp_dir)

test("DocumentProcessor creates", processor is not None)
test("DocumentProcessor has reader", processor.reader is not None)
test("DocumentProcessor has chunker", processor.chunker is not None)
test("DocumentProcessor has extractor", processor.extractor is not None)
test("DocumentProcessor total_processed starts at 0", processor.total_processed == 0)

# Process a TXT file
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write("Genesis es un sistema de IA auto-evolutivo.\n\n")
    f.write("Contacto: admin@genesis.local\n")
    f.write("Fecha: 15/03/2026\n")
    f.write("Monto: $5.000 pesos\n")
    tmp_file = f.name

result = processor.process(tmp_file, brain=None, summarize=True, extract_entities=True)
test("Process TXT succeeds", "error" not in result)
test("Process returns filename", result.get("filename", "").endswith(".txt"))
test("Process returns word_count", result.get("word_count", 0) > 0)
test("Process returns entities", isinstance(result.get("entities"), dict))
test("Process extracts email from TXT", len(result.get("entities", {}).get("emails", [])) >= 1)
test("Process returns formatted_output", len(result.get("formatted_output", "")) > 0)
test("Process increments total_processed", processor.total_processed == 1)
os.unlink(tmp_file)

# Status
status = processor.status()
test("Status includes 'Document Processor'", "Document Processor" in status)
test("Status includes processed count", "1" in status)

# Stats
stats = processor.get_stats()
test("Stats has total_processed", stats["total_processed"] == 1)

# Save and load
processor.save()
test("Save creates state file", os.path.exists(os.path.join(tmp_dir, "processor_state.json")))

processor2 = DocumentProcessor(base_dir=tmp_dir)
test("Load restores total_processed", processor2.total_processed == 1)
test("Load restores processed_docs", len(processor2.processed_docs) == 1)

# Clear
processor.clear()
test("Clear resets state", processor.total_processed == 0 and len(processor.processed_docs) == 0)

# Clean up
import shutil
shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# 8. Tool Integration
# ============================================================
print("\n--- Tool Integration ---")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Check tools.py has document tools
tools_path = os.path.join(BASE, "core", "tools.py")
with open(tools_path, "r", encoding="utf-8") as f:
    tools_src = f.read()

test("tools.py has [TOOL:documento]", "[TOOL:documento]" in tools_src)
test("tools.py has [TOOL:resumir]", "[TOOL:resumir]" in tools_src)
test("tools.py has [TOOL:extraer]", "[TOOL:extraer]" in tools_src)
test("tools.py documento handler exists", 'tool_name == "documento"' in tools_src)
test("tools.py resumir handler exists", 'tool_name == "resumir"' in tools_src)
test("tools.py extraer handler exists", 'tool_name == "extraer"' in tools_src)


# ============================================================
# 9. Genesis Integration
# ============================================================
print("\n--- Genesis Integration ---")

genesis_path = os.path.join(BASE, "genesis.py")
with open(genesis_path, "r", encoding="utf-8") as f:
    genesis_src = f.read()

# Also read mixin files (genesis.py was split into mixins)
genesis_tools_path = os.path.join(BASE, "core", "genesis_tools.py")
genesis_full_src = genesis_src
if os.path.exists(genesis_tools_path):
    with open(genesis_tools_path, "r", encoding="utf-8") as f:
        genesis_full_src += f.read()

test("genesis.py has doc_processor lazy load", "'doc_processor'" in genesis_src and "DocumentProcessor" in genesis_src)
test("genesis.py has document auto-detect keywords", "analiza este documento" in genesis_full_src)
test("genesis.py CORE_RULES mentions documents", "[TOOL:documento]" in genesis_src)
test("genesis.py CORE_RULES mentions internet access", "TIENES internet" in genesis_src or "SI tienes acceso a internet" in genesis_src)
test("genesis.py CORE_RULES mentions voice", "VOZ" in genesis_src and "TTS" in genesis_src)


# ============================================================
# 10. Web UI Integration
# ============================================================
print("\n--- Web UI Integration ---")

webui_path = os.path.join(BASE, "web_ui.py")
with open(webui_path, "r", encoding="utf-8") as f:
    webui_src = f.read()

test("web_ui.py has /api/document/upload", '"/api/document/upload"' in webui_src)
test("web_ui.py has /api/document/list", '"/api/document/list"' in webui_src)
test("web_ui.py document upload accepts POST", 'methods=["POST"]' in webui_src and "api_document_upload" in webui_src)
test("web_ui.py validates document format", "SUPPORTED_FORMATS" in webui_src)
test("web_ui.py image analyzer fix (no prompt kwarg)", 'analyze(tmp.name)' in webui_src and 'prompt=message' not in webui_src)


# ============================================================
# 11. Frontend Integration
# ============================================================
print("\n--- Frontend Integration ---")

html_path = os.path.join(BASE, "templates", "index.html")
with open(html_path, "r", encoding="utf-8") as f:
    html_src = f.read()

test("Frontend accepts document formats", all(ext in html_src for ext in [".pdf", ".docx", ".doc", ".xlsx"]))
test("Frontend has uploadDocument function", "async function uploadDocument" in html_src)
test("Frontend has renderDocumentResult function", "function renderDocumentResult" in html_src)
test("Frontend has DOC_EXTENSIONS array", "DOC_EXTENSIONS" in html_src)
test("Frontend handleFileUpload routes docs correctly", "uploadDocument(file)" in html_src)
test("Frontend has doc-result CSS class", ".doc-result" in html_src)
test("Frontend has doc-section CSS", ".doc-section" in html_src)
test("Frontend has doc-mini-table CSS", ".doc-mini-table" in html_src)
test("Frontend drag & drop supports docs", "DOC_EXTENSIONS.includes(ext)" in html_src)
test("Frontend drop overlay says DROP FILE", "DROP FILE" in html_src)

# TTS chunking (no 500 char limit)
test("Frontend TTS has splitIntoChunks", "splitIntoChunks" in html_src)
test("Frontend TTS has speakNextChunk", "speakNextChunk" in html_src)
test("Frontend TTS has ttsQueue", "ttsQueue" in html_src)
test("Frontend TTS no 500 char limit", "substring(0, 497)" not in html_src)
test("Frontend TTS has stopTTS function", "function stopTTS" in html_src)

# Auto-activate TTS on voice
test("Frontend auto-activates TTS on voice", "lastMessageWasVoice" in html_src)


# ============================================================
print(f"\n{'='*60}")
print(f"RESULTADOS: {passed}/{passed+failed} passed, {failed} failed")
print(f"{'='*60}")

if failed > 0:
    sys.exit(1)
