"""
GENESIS — Noticias / titulares (Google News RSS).

Trae titulares actuales en español (Argentina) sin API key ni dependencias
extra: feed RSS público + parser XML de la stdlib. Soporta tema libre
("noticias de tecnología") vía la búsqueda de Google News.
"""
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_BASE = "https://news.google.com/rss"
_PARAMS = "hl=es-419&gl=AR&ceid=AR:es-419"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _fetch(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read()


def headlines(topic=None, n=6):
    """Devuelve los últimos `n` titulares (generales o de un `topic`)."""
    try:
        if topic:
            url = f"{_BASE}/search?q={urllib.parse.quote(topic)}&{_PARAMS}"
        else:
            url = f"{_BASE}?{_PARAMS}"
        root = ET.fromstring(_fetch(url))
        items = root.findall(".//item")[:n]
        if not items:
            return f"📰 No encontré noticias{' de ' + topic if topic else ''} ahora."
        out = [f"📰 **Titulares{' · ' + topic if topic else ''}**", ""]
        for it in items:
            title = (it.findtext("title") or "").strip()
            parts = title.rsplit(" - ", 1)  # "Titular - Fuente"
            head = parts[0]
            src = parts[1] if len(parts) > 1 else ""
            out.append(f"• {head}" + (f"  _({src})_" if src else ""))
        return "\n".join(out)
    except Exception as e:
        return f"📰 No pude traer las noticias: {str(e)[:100]}"
