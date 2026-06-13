"""
WebIntelligence — Acceso a internet para Genesis v2.1
Busqueda, lectura, y aprendizaje automatico desde la web.

Componentes:
- WebSearcher: busqueda via DuckDuckGo (sin API key)
- WebReader: extraccion de contenido de URLs (requests + BeautifulSoup)
- WebLearner: indexa hallazgos en EmbeddingsEngine + memoria

Principios:
- Sin API keys (DuckDuckGo es gratis)
- Graceful degradation si no hay internet
- Rate limiting integrado (no abusar de DDG)
- Contenido extraido se limpia y se indexa para busqueda semantica
"""

import time
import re
import json
import hashlib
import os
import socket
import ipaddress
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path


# ============================================================
# Anti-SSRF — validación de URLs antes de hacer fetch
# ============================================================
def is_safe_public_url(url: str) -> bool:
    """True si la URL es segura para hacer fetch desde el servidor.

    Bloquea SSRF: una página/documento malicioso (o el LLM influenciado por
    ellos) podría pedir leer http://127.0.0.1:5100, http://169.254.169.254
    (metadata cloud), file://, o IPs privadas de la LAN — y ese contenido
    volvería al prompt del LLM. Solo se permiten http/https hacia IPs
    públicas resueltas por DNS.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False
        # Resolver TODAS las IPs del host (evita DNS-rebind a una privada)
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        for info in infos:
            ip_str = info[4][0]
            ip = ipaddress.ip_address(ip_str)
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
        return True
    except (ValueError, socket.gaierror, OSError):
        return False


# ============================================================
# SearchResult
# ============================================================
class SearchResult:
    """Un resultado de busqueda web."""

    def __init__(self, title: str = "", url: str = "", snippet: str = "",
                 source: str = "duckduckgo"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return f"SearchResult('{self.title[:40]}...', '{self.url}')"


# ============================================================
# WebPage (contenido extraido)
# ============================================================
class WebPage:
    """Contenido extraido de una pagina web."""

    def __init__(self, url: str = "", title: str = "", text: str = "",
                 links: list = None, word_count: int = 0):
        self.url = url
        self.title = title
        self.text = text
        self.links = links or []
        self.word_count = word_count
        self.timestamp = time.time()
        self.fetch_time_ms = 0.0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text_length": len(self.text),
            "word_count": self.word_count,
            "links_count": len(self.links),
            "timestamp": self.timestamp,
            "fetch_time_ms": self.fetch_time_ms,
        }

    def get_summary(self, max_chars: int = 500) -> str:
        """Retorna un resumen del contenido."""
        if len(self.text) <= max_chars:
            return self.text
        return self.text[:max_chars].rsplit(" ", 1)[0] + "..."


# ============================================================
# WebSearcher — DuckDuckGo
# ============================================================
class WebSearcher:
    """Busqueda web via DuckDuckGo (sin API key)."""

    def __init__(self):
        self.available = False
        self.total_searches = 0
        self.total_results = 0
        self.last_search_time = 0.0
        self.min_interval = 2.0  # Segundos minimos entre busquedas
        self._ddgs = None

        # Paquete renombrado: 'ddgs' (nuevo) reemplaza a 'duckduckgo_search' (viejo).
        self._ddgs_class = None
        try:
            from ddgs import DDGS
            self._ddgs_class = DDGS
            self.available = True
        except ImportError:
            try:
                from duckduckgo_search import DDGS
                self._ddgs_class = DDGS
                self.available = True
            except ImportError:
                self._ddgs_class = None

    def search(self, query: str, max_results: int = 8,
               region: str = "wt-wt") -> list:
        """
        Busca en DuckDuckGo y retorna lista de SearchResult.

        Args:
            query: termino de busqueda
            max_results: maximo de resultados (default 8)
            region: region de busqueda (wt-wt = global)

        Returns:
            Lista de SearchResult
        """
        if not self.available:
            return []

        # Rate limiting
        elapsed = time.time() - self.last_search_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        results = []
        try:
            with self._ddgs_class() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results, region=region))

            for r in raw:
                sr = SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", r.get("link", "")),
                    snippet=r.get("body", r.get("snippet", "")),
                    source="duckduckgo",
                )
                results.append(sr)

            self.total_searches += 1
            self.total_results += len(results)
            self.last_search_time = time.time()

        except Exception as e:
            # Sin internet o error de DDG — degradar silenciosamente
            pass

        return results

    def search_news(self, query: str, max_results: int = 5) -> list:
        """Busca noticias recientes."""
        if not self.available:
            return []

        elapsed = time.time() - self.last_search_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        results = []
        try:
            with self._ddgs_class() as ddgs:
                raw = list(ddgs.news(query, max_results=max_results))

            for r in raw:
                sr = SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", r.get("link", "")),
                    snippet=r.get("body", ""),
                    source="duckduckgo-news",
                )
                results.append(sr)

            self.total_searches += 1
            self.total_results += len(results)
            self.last_search_time = time.time()

        except Exception:
            pass

        return results


# ============================================================
# WebReader — Extrae contenido de URLs
# ============================================================
class WebReader:
    """Extrae y limpia contenido de paginas web."""

    def __init__(self):
        self.available = False
        self.total_reads = 0
        self.total_errors = 0
        self.timeout = 15  # segundos
        self.max_content_length = 500_000  # 500KB max

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }

        try:
            import requests
            from bs4 import BeautifulSoup
            self._requests = requests
            self._bs4 = BeautifulSoup
            self.available = True
        except ImportError:
            self._requests = None
            self._bs4 = None

    def read(self, url: str) -> Optional[WebPage]:
        """
        Lee una URL y extrae el contenido limpio.

        Returns:
            WebPage con contenido extraido, o None si falla
        """
        if not self.available:
            return None

        # Anti-SSRF: validar la URL inicial antes de tocar la red.
        if not is_safe_public_url(url):
            self.total_errors += 1
            return None

        t0 = time.time()
        try:
            # Seguir redirects manualmente validando cada hop (anti-SSRF):
            # un 30x podría redirigir a 127.0.0.1 / IP privada / metadata cloud.
            current_url = url
            resp = None
            for _hop in range(5):
                resp = self._requests.get(
                    current_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=False,
                    stream=True,
                )
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    next_url = resp.headers.get("location", "")
                    resp.close()
                    if not next_url:
                        break
                    # Resolver relativa→absoluta y revalidar
                    next_url = self._requests.compat.urljoin(current_url, next_url)
                    if not is_safe_public_url(next_url):
                        self.total_errors += 1
                        return None
                    current_url = next_url
                    continue
                break
            if resp is None:
                self.total_errors += 1
                return None
            resp.raise_for_status()

            # Verificar content-type (solo HTML)
            ct = resp.headers.get("content-type", "")
            if "text/html" not in ct and "application/xhtml" not in ct:
                self.total_errors += 1
                return None

            # Leer contenido con limite
            content = resp.text[:self.max_content_length]

            # Parsear con BeautifulSoup
            soup = self._bs4(content, "html.parser")

            # Extraer titulo
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            # Remover scripts, styles, nav, footer, ads
            for tag in soup(["script", "style", "nav", "footer", "header",
                             "aside", "noscript", "iframe", "svg", "form"]):
                tag.decompose()

            # Extraer texto limpio
            text = self._extract_text(soup)

            # Extraer links relevantes
            links = self._extract_links(soup, url)

            word_count = len(text.split())

            page = WebPage(
                url=url,
                title=title,
                text=text,
                links=links[:20],  # Max 20 links
                word_count=word_count,
            )
            page.fetch_time_ms = (time.time() - t0) * 1000

            self.total_reads += 1
            return page

        except Exception as e:
            self.total_errors += 1
            return None

    def _extract_text(self, soup) -> str:
        """Extrae texto limpio del HTML."""
        # Intentar extraer de article o main primero
        main_content = soup.find("article") or soup.find("main") or soup.find("body")
        if not main_content:
            main_content = soup

        # Obtener texto de parrafos, headings, listas
        blocks = []
        for tag in main_content.find_all(["p", "h1", "h2", "h3", "h4", "li", "td", "th", "pre", "blockquote"]):
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 15:  # Ignorar fragmentos muy cortos
                # Agregar marcador para headings
                if tag.name.startswith("h"):
                    text = f"\n## {text}\n"
                blocks.append(text)

        full_text = "\n".join(blocks)

        # Limpiar whitespace excesivo
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = re.sub(r' {2,}', ' ', full_text)

        return full_text.strip()

    def _extract_links(self, soup, base_url: str) -> list:
        """Extrae links relevantes."""
        from urllib.parse import urljoin

        links = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)

            # Construir URL absoluta
            full_url = urljoin(base_url, href)

            # Filtrar
            if full_url in seen:
                continue
            if not full_url.startswith("http"):
                continue
            if any(ext in full_url for ext in [".jpg", ".png", ".gif", ".pdf", ".zip"]):
                continue

            seen.add(full_url)
            links.append({"url": full_url, "text": text[:100]})

        return links


# ============================================================
# LearnedItem
# ============================================================
class LearnedItem:
    """Un item aprendido de la web."""

    def __init__(self, query: str, url: str, title: str, content: str,
                 word_count: int = 0):
        self.id = hashlib.md5(url.encode()).hexdigest()[:12]
        self.query = query
        self.url = url
        self.title = title
        self.content = content
        self.word_count = word_count
        self.timestamp = time.time()
        self.indexed = False  # Si se indexo en embeddings


# ============================================================
# WebIntelligence — Modulo principal
# ============================================================
class WebIntelligence:
    """
    Modulo de inteligencia web para Genesis.

    Combina busqueda (DuckDuckGo), lectura (requests+BS4),
    y aprendizaje (indexado en embeddings + memoria).

    Uso:
        web = WebIntelligence(base_dir=".", embeddings=engine)
        results = web.search("quantum computing")
        page = web.read(results[0].url)
        web.learn(page, query="quantum computing")
    """

    def __init__(self, base_dir: str = ".", embeddings=None):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "web_data")
        os.makedirs(self.data_dir, exist_ok=True)

        # Sub-componentes
        self.searcher = WebSearcher()
        self.reader = WebReader()
        self.embeddings = embeddings  # Referencia al EmbeddingsEngine

        # Estado
        self.learned_items: list[LearnedItem] = []
        self.search_history: list[dict] = []
        self.total_searches = 0
        self.total_reads = 0
        self.total_learned = 0
        self.max_history = 100
        self.max_learned = 500

        # Cargar historial
        self._load_state()

    def search(self, query: str, max_results: int = 8) -> list:
        """
        Busca en la web y retorna resultados.

        Returns:
            Lista de SearchResult
        """
        results = self.searcher.search(query, max_results=max_results)
        self.total_searches += 1

        # Guardar en historial
        self.search_history.append({
            "query": query,
            "results_count": len(results),
            "timestamp": time.time(),
        })
        if len(self.search_history) > self.max_history:
            self.search_history = self.search_history[-self.max_history:]

        return results

    def search_news(self, query: str, max_results: int = 5) -> list:
        """Busca noticias recientes."""
        results = self.searcher.search_news(query, max_results=max_results)
        self.total_searches += 1
        return results

    def read(self, url: str) -> Optional[WebPage]:
        """
        Lee una pagina web y extrae contenido.

        Returns:
            WebPage o None si falla
        """
        page = self.reader.read(url)
        if page:
            self.total_reads += 1
        return page

    def learn(self, page: WebPage, query: str = "") -> str:
        """
        Aprende de una pagina web: indexa en embeddings + guarda en memoria.

        Args:
            page: WebPage con contenido extraido
            query: query original que llevo a esta pagina

        Returns:
            Mensaje de confirmacion
        """
        if not page or not page.text:
            return "  Sin contenido para aprender."

        # Crear LearnedItem
        item = LearnedItem(
            query=query,
            url=page.url,
            title=page.title,
            content=page.text[:10000],  # Max 10K chars
            word_count=page.word_count,
        )

        # Dividir en chunks para embeddings (max ~500 palabras cada uno)
        chunks = self._chunk_text(page.text, max_words=400)
        indexed_count = 0

        if self.embeddings:
            for i, chunk in enumerate(chunks):
                doc_id = f"web_{item.id}_{i}"
                ok = self.embeddings.add_text(
                    doc_id=doc_id,
                    text=chunk,
                    source=f"web:{page.url}",
                )
                if ok:
                    indexed_count += 1

            item.indexed = True

        # Guardar en memoria local
        self.learned_items.append(item)
        if len(self.learned_items) > self.max_learned:
            self.learned_items = self.learned_items[-self.max_learned:]
        self.total_learned += 1

        # Persistir
        self._save_state()

        return (
            f"  Aprendido: \"{page.title}\"\n"
            f"  URL: {page.url}\n"
            f"  Palabras: {page.word_count} | Chunks indexados: {indexed_count}\n"
            f"  Total aprendido: {self.total_learned} paginas"
        )

    def search_and_learn(self, query: str, max_results: int = 3,
                         max_pages: int = 3) -> str:
        """
        Busca, lee y aprende automaticamente.
        Flujo completo: DDG search -> read top pages -> index in embeddings.

        Args:
            query: que buscar
            max_results: cuantos resultados de DDG traer
            max_pages: cuantas paginas leer e indexar

        Returns:
            Reporte del aprendizaje
        """
        lines = [f"  BUSQUEDA: \"{query}\"", ""]

        # 1. Buscar
        results = self.search(query, max_results=max_results)
        if not results:
            return f"  Sin resultados para \"{query}\". Verificar conexion a internet."

        lines.append(f"  {len(results)} resultados encontrados:")
        for i, r in enumerate(results):
            lines.append(f"    {i+1}. {r.title[:60]}")
            lines.append(f"       {r.url}")
        lines.append("")

        # 2. Leer y aprender las top paginas
        learned_count = 0
        for r in results[:max_pages]:
            page = self.read(r.url)
            if page and page.word_count > 50:
                result = self.learn(page, query=query)
                lines.append(f"  [APRENDIDO] {page.title[:50]}")
                lines.append(f"    {page.word_count} palabras, {len(self._chunk_text(page.text, 400))} chunks")
                learned_count += 1
            else:
                lines.append(f"  [SKIP] {r.title[:50]} (contenido insuficiente)")

        lines.append("")
        lines.append(f"  Resultado: {learned_count}/{max_pages} paginas aprendidas")
        lines.append(f"  Los datos estan en el vector store para busqueda semantica.")

        return "\n".join(lines)

    def recall(self, query: str, top_k: int = 5) -> list:
        """
        Busca en el conocimiento aprendido via embeddings.

        Returns:
            Lista de resultados del vector store
        """
        if not self.embeddings:
            return []
        return self.embeddings.search(query, top_k=top_k, min_score=0.1)

    def _chunk_text(self, text: str, max_words: int = 400) -> list:
        """Divide texto en chunks de ~max_words palabras."""
        words = text.split()
        if len(words) <= max_words:
            return [text]

        chunks = []
        # Intentar dividir por parrafos primero
        paragraphs = text.split("\n\n")
        current_chunk = []
        current_words = 0

        for para in paragraphs:
            para_words = len(para.split())
            if current_words + para_words > max_words and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_words = para_words
            else:
                current_chunk.append(para)
                current_words += para_words

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return [c for c in chunks if len(c.split()) > 20]

    def get_search_history(self, n: int = 10) -> str:
        """Retorna las ultimas N busquedas."""
        if not self.search_history:
            return "  Sin historial de busquedas."

        lines = ["  HISTORIAL DE BUSQUEDAS:"]
        for h in self.search_history[-n:]:
            ts = datetime.fromtimestamp(h["timestamp"]).strftime("%H:%M:%S")
            lines.append(f"    [{ts}] \"{h['query']}\" -> {h['results_count']} resultados")
        return "\n".join(lines)

    def get_learned_summary(self, n: int = 10) -> str:
        """Resumen de lo aprendido."""
        if not self.learned_items:
            return "  Sin conocimiento web aprendido."

        lines = [f"  CONOCIMIENTO WEB ({self.total_learned} paginas):"]
        for item in self.learned_items[-n:]:
            ts = datetime.fromtimestamp(item.timestamp).strftime("%H:%M")
            indexed = "IDX" if item.indexed else "---"
            lines.append(f"    [{ts}] [{indexed}] {item.title[:50]}")
            lines.append(f"           {item.url}")
        return "\n".join(lines)

    def generate_report(self) -> str:
        """Reporte completo del modulo web."""
        lines = [
            "  ╔══ WEB INTELLIGENCE ══╗",
            "",
            f"  Busqueda: {'disponible' if self.searcher.available else 'NO DISPONIBLE'}",
            f"  Lectura:  {'disponible' if self.reader.available else 'NO DISPONIBLE'}",
            f"  Embeddings: {'conectado' if self.embeddings else 'desconectado'}",
            "",
            f"  Busquedas totales: {self.total_searches}",
            f"  Paginas leidas: {self.total_reads}",
            f"  Paginas aprendidas: {self.total_learned}",
            f"  Items en memoria: {len(self.learned_items)}",
            "",
        ]

        # Ultimas busquedas
        if self.search_history:
            lines.append("  ULTIMAS BUSQUEDAS:")
            for h in self.search_history[-5:]:
                ts = datetime.fromtimestamp(h["timestamp"]).strftime("%H:%M:%S")
                lines.append(f"    [{ts}] \"{h['query']}\" ({h['results_count']} res.)")
            lines.append("")

        # Ultimo contenido aprendido
        if self.learned_items:
            lines.append("  ULTIMO APRENDIDO:")
            for item in self.learned_items[-3:]:
                lines.append(f"    {item.title[:55]}")
                lines.append(f"    {item.word_count} palabras | {item.url[:60]}")
            lines.append("")

        return "\n".join(lines)

    def status(self) -> str:
        """Status compacto para /status."""
        search_status = "ON" if self.searcher.available else "OFF"
        read_status = "ON" if self.reader.available else "OFF"
        return (
            f"  Busqueda: {search_status} | Lectura: {read_status} | "
            f"Buscado: {self.total_searches} | Leido: {self.total_reads} | "
            f"Aprendido: {self.total_learned}"
        )

    def _save_state(self):
        """Guarda estado a disco."""
        state = {
            "total_searches": self.total_searches,
            "total_reads": self.total_reads,
            "total_learned": self.total_learned,
            "search_history": self.search_history[-self.max_history:],
            "learned_items": [
                {
                    "id": item.id,
                    "query": item.query,
                    "url": item.url,
                    "title": item.title,
                    "word_count": item.word_count,
                    "timestamp": item.timestamp,
                    "indexed": item.indexed,
                }
                for item in self.learned_items[-self.max_learned:]
            ],
        }
        try:
            path = os.path.join(self.data_dir, "web_state.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_state(self):
        """Carga estado desde disco."""
        path = os.path.join(self.data_dir, "web_state.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.total_searches = state.get("total_searches", 0)
            self.total_reads = state.get("total_reads", 0)
            self.total_learned = state.get("total_learned", 0)
            self.search_history = state.get("search_history", [])
            for item_data in state.get("learned_items", []):
                item = LearnedItem(
                    query=item_data.get("query", ""),
                    url=item_data.get("url", ""),
                    title=item_data.get("title", ""),
                    content="",  # No guardamos el contenido completo
                    word_count=item_data.get("word_count", 0),
                )
                item.id = item_data.get("id", "")
                item.timestamp = item_data.get("timestamp", 0)
                item.indexed = item_data.get("indexed", False)
                self.learned_items.append(item)
        except Exception:
            pass
