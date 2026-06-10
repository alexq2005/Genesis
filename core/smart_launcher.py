"""
GENESIS Smart Launcher — Búsqueda unificada en todo el sistema.
Busca simultáneamente en: apps instaladas, archivos recientes, notas,
clipboard, bookmarks, procesos activos. Fuzzy matching integrado.
"""
import os
import subprocess
import time
from typing import Optional
from difflib import SequenceMatcher


class SmartLauncher:
    """Búsqueda unificada con fuzzy matching en múltiples fuentes."""

    def __init__(self):
        self._cache_apps: list[dict] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 300  # 5 min

    # ── Fuzzy Matching ────────────────────────────────
    @staticmethod
    def _fuzzy_score(query: str, text: str) -> float:
        """Score de similitud entre query y texto (0-1)."""
        q = query.lower()
        t = text.lower()

        # Match exacto
        if q in t:
            return 1.0

        # Match al inicio
        if t.startswith(q):
            return 0.95

        # Palabras contenidas
        q_words = q.split()
        if all(w in t for w in q_words):
            return 0.9

        # SequenceMatcher
        ratio = SequenceMatcher(None, q, t).ratio()

        # Boost si las iniciales coinciden
        t_initials = "".join(w[0] for w in t.split() if w)
        if q in t_initials:
            ratio = max(ratio, 0.85)

        return ratio

    # ── Fuentes de búsqueda ───────────────────────────
    def _search_apps(self, query: str) -> list[dict]:
        """Busca en aplicaciones instaladas (Start Menu)."""
        results = []
        start_paths = [
            os.path.join(os.environ.get("APPDATA", ""),
                         r"Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        ]

        for start_path in start_paths:
            if not os.path.isdir(start_path):
                continue
            try:
                for root, dirs, files in os.walk(start_path):
                    for f in files:
                        if f.endswith((".lnk", ".url")):
                            name = f.rsplit(".", 1)[0]
                            score = self._fuzzy_score(query, name)
                            if score >= 0.4:
                                results.append({
                                    "type": "🚀 App",
                                    "name": name,
                                    "path": os.path.join(root, f),
                                    "score": score
                                })
            except (PermissionError, OSError):
                continue

        return results

    def _search_recent_files(self, query: str) -> list[dict]:
        """Busca en archivos recientes."""
        results = []
        recent_path = os.path.join(os.environ.get("APPDATA", ""),
                                   r"Microsoft\Windows\Recent")
        if not os.path.isdir(recent_path):
            return results

        try:
            for f in os.listdir(recent_path):
                name = f.rsplit(".", 1)[0] if "." in f else f
                score = self._fuzzy_score(query, name)
                if score >= 0.4:
                    results.append({
                        "type": "📄 Reciente",
                        "name": name,
                        "path": os.path.join(recent_path, f),
                        "score": score
                    })
        except (PermissionError, OSError):
            pass

        return results

    def _search_desktop(self, query: str) -> list[dict]:
        """Busca en archivos del escritorio."""
        results = []
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.isdir(desktop):
            return results

        try:
            for f in os.listdir(desktop):
                name = f.rsplit(".", 1)[0] if "." in f else f
                score = self._fuzzy_score(query, name)
                if score >= 0.4:
                    results.append({
                        "type": "🖥️ Desktop",
                        "name": name,
                        "path": os.path.join(desktop, f),
                        "score": score
                    })
        except (PermissionError, OSError):
            pass

        return results

    def _search_notes(self, query: str) -> list[dict]:
        """Busca en notas de GENESIS."""
        results = []
        try:
            from core.quick_notes import QuickNotes
            qn = QuickNotes()
            for note in qn._notes:
                content = note.get("content", "")
                score = self._fuzzy_score(query, content)
                if score >= 0.35:
                    preview = content[:60] + ("..." if len(content) > 60 else "")
                    results.append({
                        "type": "📝 Nota",
                        "name": preview,
                        "path": f"nota #{note.get('id', '?')}",
                        "score": score
                    })
        except Exception:
            pass

        return results

    def _search_clipboard(self, query: str) -> list[dict]:
        """Busca en historial del portapapeles."""
        results = []
        try:
            from core.clipboard_manager import ClipboardManager
            cm = ClipboardManager()
            for item in cm._history:
                content = item.get("content", "")
                score = self._fuzzy_score(query, content)
                if score >= 0.35:
                    preview = content[:60] + ("..." if len(content) > 60 else "")
                    results.append({
                        "type": "📋 Clipboard",
                        "name": preview,
                        "path": f"clipboard #{item.get('id', '?')}",
                        "score": score
                    })
        except Exception:
            pass

        return results

    def _search_processes(self, query: str) -> list[dict]:
        """Busca en procesos activos."""
        results = []
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
                 "Select-Object ProcessName, MainWindowTitle | ConvertTo-Json"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace"
            )
            import json
            procs = json.loads(r.stdout) if r.stdout.strip() else []
            if isinstance(procs, dict):
                procs = [procs]
            for p in procs:
                name = p.get("ProcessName", "")
                title = p.get("MainWindowTitle", "")
                combined = f"{name} {title}"
                score = max(self._fuzzy_score(query, name),
                           self._fuzzy_score(query, title))
                if score >= 0.4:
                    results.append({
                        "type": "⚡ Activo",
                        "name": f"{name} — {title[:40]}",
                        "path": f"PID activo",
                        "score": score
                    })
        except Exception:
            pass

        return results

    # ── Búsqueda principal ────────────────────────────
    def search(self, query: str, max_results: int = 15) -> str:
        """Búsqueda unificada en todas las fuentes."""
        if not query.strip():
            return ("🔍 **Smart Launcher** — Buscá cualquier cosa:\n"
                    "  • Apps instaladas\n"
                    "  • Archivos recientes y del escritorio\n"
                    "  • Notas guardadas\n"
                    "  • Historial del portapapeles\n"
                    "  • Procesos activos\n\n"
                    "  Ejemplo: `busca chrome` o `lanzar spotify`")

        # Buscar en todas las fuentes en paralelo (secuencial por simplicidad)
        all_results = []
        t0 = time.time()

        all_results.extend(self._search_processes(query))
        all_results.extend(self._search_apps(query))
        all_results.extend(self._search_desktop(query))
        all_results.extend(self._search_recent_files(query))
        all_results.extend(self._search_notes(query))
        all_results.extend(self._search_clipboard(query))

        elapsed = time.time() - t0

        # Ordenar por score descendente, deduplicar por nombre
        all_results.sort(key=lambda r: r["score"], reverse=True)
        seen = set()
        unique = []
        for r in all_results:
            key = r["name"].lower()[:30]
            if key not in seen:
                seen.add(key)
                unique.append(r)
            if len(unique) >= max_results:
                break

        if not unique:
            return f"🔍 No encontré resultados para '{query}'."

        lines = [f"🔍 **RESULTADOS PARA '{query}'** — {len(unique)} encontrados ({elapsed:.2f}s)\n"]
        for i, r in enumerate(unique, 1):
            score_bar = "█" * int(r["score"] * 5) + "░" * (5 - int(r["score"] * 5))
            lines.append(f"  {i}. {r['type']} **{r['name']}**")
            lines.append(f"     {score_bar} {r['score']:.0%} — {r['path'][:50]}")

        return "\n".join(lines)

    def launch(self, query: str) -> str:
        """Busca y abre el mejor resultado."""
        all_results = []
        all_results.extend(self._search_processes(query))
        all_results.extend(self._search_apps(query))
        all_results.extend(self._search_desktop(query))

        if not all_results:
            return f"🔍 No encontré '{query}' para abrir."

        best = max(all_results, key=lambda r: r["score"])

        if best["type"] == "⚡ Activo":
            # Enfocar ventana
            try:
                from core.window_manager import window_manager
                return window_manager.focus(query)
            except Exception:
                return f"🔍 '{query}' ya está activo pero no pude enfocarlo."

        # Abrir archivo/app
        try:
            os.startfile(best["path"])
            return f"🚀 Abriendo **{best['name']}** ({best['score']:.0%} match)"
        except Exception as e:
            return f"🔍 Error abriendo '{best['name']}': {e}"


# Singleton
smart_launcher = SmartLauncher()
