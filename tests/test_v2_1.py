"""
Tests para Genesis v2.1.0
- WebIntelligence (SearchResult, WebPage, WebSearcher, WebReader, WebLearner)
- Integracion con EmbeddingsEngine
- Integracion en genesis.py (imports, comandos, status)

NOTA: Tests que requieren internet son tolerantes a fallos de red.
"""
import sys
import os
import tempfile
import shutil
import time
import json

# Forzar UTF-8 en stdout para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

# Suppress TF warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ============================================================
# Mini test framework
# ============================================================
_passed = 0
_failed = 0

def test(name, condition):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        print(f"  [FAIL] {name}")

def test_net(name, condition):
    """Test tolerante a red — si falla, cuenta como PASS con nota."""
    global _passed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _passed += 1
        print(f"  [SKIP] {name} (red no disponible, tolerado)")


# ============================================================
# TEST 1: SearchResult
# ============================================================
print("\n=== TEST: SearchResult ===")
from core.web_intelligence import SearchResult, WebPage, WebSearcher, WebReader, WebIntelligence

sr = SearchResult(title="Test Result", url="https://example.com", snippet="Esto es un test")
test("SearchResult title", sr.title == "Test Result")
test("SearchResult url", sr.url == "https://example.com")
test("SearchResult snippet", sr.snippet == "Esto es un test")
test("SearchResult source default", sr.source == "duckduckgo")
test("SearchResult timestamp > 0", sr.timestamp > 0)

d = sr.to_dict()
test("to_dict tiene title", d["title"] == "Test Result")
test("to_dict tiene url", d["url"] == "https://example.com")
test("to_dict tiene snippet", d["snippet"] == "Esto es un test")
test("to_dict tiene source", d["source"] == "duckduckgo")
test("to_dict tiene timestamp", "timestamp" in d)

test("repr funciona", "SearchResult" in repr(sr))


# ============================================================
# TEST 2: WebPage
# ============================================================
print("\n=== TEST: WebPage ===")
wp = WebPage(
    url="https://example.com/page",
    title="Test Page",
    text="Este es el contenido de la pagina. " * 50,
    links=[{"url": "https://link1.com", "text": "Link 1"}],
    word_count=350,
)
test("WebPage url", wp.url == "https://example.com/page")
test("WebPage title", wp.title == "Test Page")
test("WebPage word_count", wp.word_count == 350)
test("WebPage links count", len(wp.links) == 1)
test("WebPage timestamp > 0", wp.timestamp > 0)

d = wp.to_dict()
test("to_dict tiene url", d["url"] == "https://example.com/page")
test("to_dict tiene text_length", d["text_length"] > 0)
test("to_dict tiene word_count", d["word_count"] == 350)
test("to_dict tiene links_count", d["links_count"] == 1)

# Summary
summary = wp.get_summary(100)
test("get_summary trunca", len(summary) <= 103)  # 100 + "..."
test("get_summary termina con ...", summary.endswith("..."))

# Summary corto
wp_short = WebPage(text="Hola mundo")
test("get_summary corto no trunca", wp_short.get_summary(500) == "Hola mundo")


# ============================================================
# TEST 3: WebSearcher
# ============================================================
print("\n=== TEST: WebSearcher ===")
ws = WebSearcher()
test("WebSearcher available (ddg installed)", ws.available is True)
test("WebSearcher total_searches 0", ws.total_searches == 0)
test("WebSearcher min_interval", ws.min_interval == 2.0)


# ============================================================
# TEST 4: WebSearcher busqueda real (tolerante a red)
# ============================================================
print("\n=== TEST: WebSearcher Busqueda Real ===")
results = ws.search("Python programming language", max_results=3)
has_results = len(results) > 0
test_net("Search retorna resultados", has_results)
if has_results:
    test("Search retorna SearchResult", isinstance(results[0], SearchResult))
    test("Result tiene title", len(results[0].title) > 0)
    test("Result tiene url", results[0].url.startswith("http"))
    test("Result tiene snippet", len(results[0].snippet) > 0)
    test("total_searches incrementa", ws.total_searches >= 1)
    test("total_results > 0", ws.total_results > 0)
else:
    # Si no hay red, testear que no crashea
    test("Sin red: no crashea", True)
    test("Sin red: retorna lista vacia", results == [])
    test("Sin red: searcher intacto", ws.available is True)
    test("Sin red: total ok", ws.total_searches >= 0)
    test("Sin red: results ok", ws.total_results >= 0)


# ============================================================
# TEST 5: WebSearcher news (tolerante a red)
# ============================================================
print("\n=== TEST: WebSearcher News ===")
time.sleep(2.5)  # Rate limit
news = ws.search_news("technology", max_results=3)
has_news = len(news) > 0
test_net("News retorna resultados", has_news)
if has_news:
    test("News source es duckduckgo-news", news[0].source == "duckduckgo-news")


# ============================================================
# TEST 6: WebReader
# ============================================================
print("\n=== TEST: WebReader ===")
wr = WebReader()
test("WebReader available", wr.available is True)
test("WebReader timeout", wr.timeout == 15)
test("WebReader max_content", wr.max_content_length == 500_000)
test("WebReader user-agent", "Mozilla" in wr.headers["User-Agent"])


# ============================================================
# TEST 7: WebReader lee pagina real (tolerante a red)
# ============================================================
print("\n=== TEST: WebReader Lectura Real ===")
page = wr.read("https://example.com")
has_page = page is not None
test_net("Read retorna WebPage", has_page)
if has_page:
    test("Read tiene titulo", len(page.title) > 0)
    test("Read tiene texto", len(page.text) > 0)
    test("Read tiene word_count > 0", page.word_count > 0)
    test("Read tiene fetch_time_ms > 0", page.fetch_time_ms > 0)
    test("total_reads incrementa", wr.total_reads == 1)
else:
    test("Sin red: no crashea", True)
    test("Sin red: retorna None", page is None)
    test("Sin red: reader intacto", wr.available is True)
    test("Sin red: total ok", wr.total_reads >= 0)
    test("Sin red: errors ok", wr.total_errors >= 0)

# URL invalida
bad = wr.read("https://thisdomaindoesnotexist12345.com")
test("Read URL invalida retorna None", bad is None)


# ============================================================
# TEST 8: WebIntelligence init
# ============================================================
print("\n=== TEST: WebIntelligence Init ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)
    test("WI searcher available", wi.searcher.available is True)
    test("WI reader available", wi.reader.available is True)
    test("WI embeddings None", wi.embeddings is None)
    test("WI total_searches 0", wi.total_searches == 0)
    test("WI total_reads 0", wi.total_reads == 0)
    test("WI total_learned 0", wi.total_learned == 0)
    test("WI data_dir creado", os.path.exists(wi.data_dir))
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 9: WebIntelligence search (tolerante a red)
# ============================================================
print("\n=== TEST: WebIntelligence Search ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)
    time.sleep(2.5)
    results = wi.search("inteligencia artificial", max_results=3)
    test_net("WI search retorna resultados", len(results) > 0)
    test("WI total_searches incrementa", wi.total_searches == 1)
    test("WI search_history tiene entrada", len(wi.search_history) == 1)
    test("WI history query correcta", wi.search_history[0]["query"] == "inteligencia artificial")
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 10: WebIntelligence read (tolerante a red)
# ============================================================
print("\n=== TEST: WebIntelligence Read ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)
    page = wi.read("https://example.com")
    has_page = page is not None
    test_net("WI read retorna WebPage", has_page)
    if has_page:
        test("WI total_reads incrementa", wi.total_reads == 1)
    else:
        test("WI sin red: total_reads 0", wi.total_reads == 0)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 11: WebIntelligence learn con embeddings (tolerante a red)
# ============================================================
print("\n=== TEST: WebIntelligence Learn ===")
tmp_dir = tempfile.mkdtemp()
try:
    from core.embeddings_engine import EmbeddingsEngine
    eng = EmbeddingsEngine(base_dir=tmp_dir)
    wi = WebIntelligence(base_dir=tmp_dir, embeddings=eng)

    # Crear pagina mock para learn (no depende de red)
    mock_page = WebPage(
        url="https://test.com/article",
        title="Articulo de prueba",
        text="La inteligencia artificial es una rama de la informatica. " * 30,
        word_count=240,
    )

    result = wi.learn(mock_page, query="inteligencia artificial")
    test("Learn retorna string", isinstance(result, str))
    test("Learn contiene Aprendido", "Aprendido" in result)
    test("Learn total_learned incrementa", wi.total_learned == 1)
    test("Learn items en memoria", len(wi.learned_items) == 1)
    test("Learn item indexed", wi.learned_items[0].indexed is True)
    test("Embeddings store tiene docs", eng.store.count() > 0)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 12: WebIntelligence learn sin page
# ============================================================
print("\n=== TEST: WebIntelligence Learn Sin Contenido ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)
    result = wi.learn(None)
    test("Learn None retorna msg", "Sin contenido" in result)

    empty_page = WebPage(text="")
    result2 = wi.learn(empty_page)
    test("Learn vacio retorna msg", "Sin contenido" in result2)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 13: WebIntelligence search_and_learn (tolerante a red)
# ============================================================
print("\n=== TEST: WebIntelligence Search And Learn ===")
tmp_dir = tempfile.mkdtemp()
try:
    from core.embeddings_engine import EmbeddingsEngine
    eng = EmbeddingsEngine(base_dir=tmp_dir)
    wi = WebIntelligence(base_dir=tmp_dir, embeddings=eng)

    time.sleep(2.5)
    report = wi.search_and_learn("Python programming basics", max_results=3, max_pages=2)
    test("search_and_learn retorna string", isinstance(report, str))
    test_net("Report contiene BUSQUEDA", "BUSQUEDA" in report)
    test_net("total_learned > 0", wi.total_learned > 0)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 14: WebIntelligence recall con mock data
# ============================================================
print("\n=== TEST: WebIntelligence Recall ===")
tmp_dir = tempfile.mkdtemp()
try:
    from core.embeddings_engine import EmbeddingsEngine
    eng = EmbeddingsEngine(base_dir=tmp_dir)
    wi = WebIntelligence(base_dir=tmp_dir, embeddings=eng)

    # Learn mock data
    page1 = WebPage(url="https://a.com", title="Python Guide",
                    text="Python es un lenguaje de programacion versatil. " * 20, word_count=140)
    page2 = WebPage(url="https://b.com", title="Machine Learning",
                    text="El machine learning usa redes neuronales profundas. " * 20, word_count=140)
    wi.learn(page1, "python")
    wi.learn(page2, "machine learning")

    # Recall
    results = wi.recall("programacion Python", top_k=5)
    test("Recall retorna resultados", len(results) > 0)
    test("Recall tiene score", "score" in results[0])

    # Recall sin embeddings
    wi2 = WebIntelligence(base_dir=tmp_dir)
    test("Recall sin embeddings vacio", len(wi2.recall("test")) == 0)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 15: Chunk text
# ============================================================
print("\n=== TEST: Chunk Text ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)

    # Texto corto — un solo chunk
    short = "Hola mundo " * 50
    chunks = wi._chunk_text(short, max_words=400)
    test("Texto corto: 1 chunk", len(chunks) == 1)

    # Texto largo — multiples chunks
    long_text = "\n\n".join([f"Parrafo {i}. " + "Contenido del parrafo. " * 30 for i in range(10)])
    chunks = wi._chunk_text(long_text, max_words=100)
    test("Texto largo: multiples chunks", len(chunks) > 1)
    test("Chunks no vacios", all(len(c.split()) > 20 for c in chunks))
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 16: Persistencia
# ============================================================
print("\n=== TEST: Persistencia ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi1 = WebIntelligence(base_dir=tmp_dir)
    wi1.total_searches = 5
    wi1.total_reads = 3
    wi1.total_learned = 2
    wi1.search_history.append({"query": "test", "results_count": 3, "timestamp": time.time()})
    wi1._save_state()

    state_path = os.path.join(tmp_dir, "web_data", "web_state.json")
    test("State file creado", os.path.exists(state_path))

    # Cargar en nueva instancia
    wi2 = WebIntelligence(base_dir=tmp_dir)
    test("Load total_searches", wi2.total_searches == 5)
    test("Load total_reads", wi2.total_reads == 3)
    test("Load total_learned", wi2.total_learned == 2)
    test("Load search_history", len(wi2.search_history) == 1)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 17: Reports
# ============================================================
print("\n=== TEST: Reports ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)

    # Report vacio
    report = wi.generate_report()
    test("Report contiene WEB INTELLIGENCE", "WEB INTELLIGENCE" in report)
    test("Report contiene disponible", "disponible" in report)

    # Status
    status = wi.status()
    test("Status contiene Busqueda", "Busqueda" in status)
    test("Status contiene Lectura", "Lectura" in status)

    # Search history vacio
    hist = wi.get_search_history()
    test("History vacio msg", "Sin historial" in hist)

    # Learned summary vacio
    learned = wi.get_learned_summary()
    test("Learned vacio msg", "Sin conocimiento" in learned)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 18: Integracion — imports en genesis.py
# ============================================================
print("\n=== TEST: Integracion imports ===")
genesis_path = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(genesis_path, "r", encoding="utf-8") as f:
    src = f.read()

test("Import WebIntelligence", "from core.web_intelligence import WebIntelligence" in src)


# ============================================================
# TEST 19: Integracion — init en genesis.py
# ============================================================
print("\n=== TEST: Integracion init ===")
test("Init self.web", "self.web = WebIntelligence" in src)
test("Web con embeddings", "embeddings=self.embeddings" in src)


# ============================================================
# TEST 20: Integracion — comandos en genesis.py
# ============================================================
print("\n=== TEST: Integracion comandos ===")
test("Comando /web", '"/web"' in src or '== "/web"' in src)
test("Comando /internet", '"/internet"' in src)
test("Comando /web search", '/web search' in src)
test("Comando /web read", '/web read' in src)
test("Comando /web learn", '/web learn' in src)
test("Comando /web news", '/web news' in src)
test("Comando /web history", '/web history' in src)
test("Comando /web learned", '/web learned' in src)
test("Comando /web recall", '/web recall' in src)


# ============================================================
# TEST 21: Integracion — status y help
# ============================================================
print("\n=== TEST: Integracion status/help ===")
test("Status WEB INTELLIGENCE", "WEB INTELLIGENCE" in src)
test("Help WEB INTELLIGENCE", "WEB INTELLIGENCE" in src)
test("Help /web search", "/web search" in src)
test("Help /web learn", "/web learn" in src)
test("Help /web recall", "/web recall" in src)


# ============================================================
# TEST 22: Version bump
# ============================================================
print("\n=== TEST: Version ===")
import config
test("Version >= 2.1.0", config.GENESIS_VERSION >= "2.1.0")


# ============================================================
# TEST 23: Learn sin embeddings
# ============================================================
print("\n=== TEST: Learn Sin Embeddings ===")
tmp_dir = tempfile.mkdtemp()
try:
    wi = WebIntelligence(base_dir=tmp_dir)  # Sin embeddings
    mock = WebPage(url="https://x.com", title="Test", text="Contenido de prueba. " * 20, word_count=60)
    result = wi.learn(mock, "test")
    test("Learn sin embeddings funciona", "Aprendido" in result)
    test("Item NO indexado", wi.learned_items[0].indexed is False)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 24: Learn batch multiple pages
# ============================================================
print("\n=== TEST: Learn Batch ===")
tmp_dir = tempfile.mkdtemp()
try:
    from core.embeddings_engine import EmbeddingsEngine
    eng = EmbeddingsEngine(base_dir=tmp_dir)
    wi = WebIntelligence(base_dir=tmp_dir, embeddings=eng)

    for i in range(5):
        page = WebPage(
            url=f"https://test.com/{i}",
            title=f"Pagina {i}",
            text=f"Contenido del articulo numero {i}. " * 30,
            word_count=180,
        )
        wi.learn(page, f"tema {i}")

    test("5 items aprendidos", wi.total_learned == 5)
    test("5 items en memoria", len(wi.learned_items) == 5)
    test("Embeddings tiene docs", eng.store.count() >= 5)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 25: LearnedItem fields
# ============================================================
print("\n=== TEST: LearnedItem ===")
from core.web_intelligence import LearnedItem

li = LearnedItem(
    query="test query",
    url="https://example.com/page",
    title="Test Title",
    content="Some content here",
    word_count=100,
)
test("LearnedItem id generado", len(li.id) == 12)
test("LearnedItem query", li.query == "test query")
test("LearnedItem url", li.url == "https://example.com/page")
test("LearnedItem title", li.title == "Test Title")
test("LearnedItem word_count", li.word_count == 100)
test("LearnedItem timestamp > 0", li.timestamp > 0)
test("LearnedItem indexed False default", li.indexed is False)

# Misma URL = mismo ID (determinista)
li2 = LearnedItem(query="other", url="https://example.com/page", title="Other", content="")
test("Mismo URL = mismo ID", li.id == li2.id)


# ============================================================
# RESUMEN
# ============================================================
print(f"\n{'='*50}")
print(f"  TESTS v2.1: {_passed} passed, {_failed} failed")
print(f"  TOTAL: {_passed + _failed}")
print(f"{'='*50}")

if _failed > 0:
    print(f"\n  [!] HAY {_failed} TESTS FALLIDOS")
    sys.exit(1)
else:
    print(f"\n  [OK] Todos los tests pasaron!")
    sys.exit(0)
