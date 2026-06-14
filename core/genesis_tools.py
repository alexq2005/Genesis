"""
Genesis Tools Mixin.

Contiene la lógica de auto-detección y ejecución de herramientas:
- _auto_detect_tool: mega-detector de intenciones (apps, web, archivos, sistema)
- _auto_builder: fuerza ejecución de código mostrado pero no ejecutado
- Filtros anti-alucinación y calidad de respuesta
"""
import json
import os
_GX_HOME = os.path.expanduser("~").replace("\\", "/")  # N7: portabilidad multi-usuario
import re
import sys
import time
from pathlib import Path

_re = re  # Alias used throughout this module

# Carpetas conocidas del usuario (portable vía _GX_HOME). Constante de módulo
# compartida por los detectores de archivos/carpetas (Fase 2).
_PATH_KEYWORDS = {
    "escritorio": "" + _GX_HOME + "/Desktop",
    "desktop": "" + _GX_HOME + "/Desktop",
    "descargas": "" + _GX_HOME + "/Downloads",
    "downloads": "" + _GX_HOME + "/Downloads",
    "documentos": "" + _GX_HOME + "/Documents",
    "documents": "" + _GX_HOME + "/Documents",
    "imagenes": "" + _GX_HOME + "/Pictures",
    "pictures": "" + _GX_HOME + "/Pictures",
    "musica": "" + _GX_HOME + "/Music",
    "videos": "" + _GX_HOME + "/Videos",
}


def _text_payload(user_input: str):
    """Extrae el texto a transformar de un comando de utilidades de texto.
    Prioridad: texto entre comillas → texto tras la palabra clave → None
    (None = usar el portapapeles). Preserva mayúsculas/minúsculas originales."""
    import re as _re
    m = _re.search(r'["“‘\'](.+?)["”’\']', user_input)
    if m:
        return m.group(1).strip()
    m = _re.search(
        r'(?:may[úu]sculas?|min[úu]sculas?|t[íi]tulo|base\s*64|hash|md5|sha\d*|'
        r'palabras?|texto|caracteres)\s+(.+)$', user_input, _re.I)
    if m:
        t = _re.sub(r'^(de|del|el|la|los|las|en|a|:)\s+', '', m.group(1).strip(),
                    flags=_re.I).strip().strip('"\'')
        if len(t) >= 1 and t.lower() not in ("de texto", "del texto"):
            return t
    return None


def _search_folder_everywhere(qname: str, max_hits: int = 12) -> list:
    """Busca carpetas por nombre exacto (case-insensitive) en raíces conocidas,
    con profundidad acotada y saltando dirs pesados/de sistema. Devuelve lista
    de rutas únicas. Para nombres comunes ('logs') puede devolver varias →
    el caller pregunta cuál abrir en vez de adivinar."""
    q = (qname or "").lower().strip().replace(" ", "")
    if not q:
        return []
    _genesis_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roots = ["" + _GX_HOME + "/Desktop", "" + _GX_HOME + "/Documents",
             "" + _GX_HOME + "/Downloads", "F:/programas", "F:/", "D:/",
             _genesis_dir]
    skip = {"$recycle.bin", "system volume information", "msdownld.tmp",
            "config.msi", "recovery", "$winreagent", "node_modules", "venv",
            ".git", "__pycache__", ".pytest_cache", "site-packages",
            ".venv", "windows", "appdata", "$sysreset"}
    hits, seen = [], set()
    _t0 = __import__("time").time()
    for root in roots:
        if not os.path.isdir(root) or len(hits) >= max_hits:
            continue
        if __import__("time").time() - _t0 > 3.0:
            break  # presupuesto: no colgarse si no existe
        base_depth = root.rstrip("/\\").count(os.sep)
        for cur, dirs, _files in os.walk(root):
            if __import__("time").time() - _t0 > 3.0:
                break
            depth = cur.count(os.sep) - base_depth
            if depth >= 3:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d.lower() not in skip
                       and not d.startswith("$")]
            for d in dirs:
                if d.lower().replace(" ", "") == q:
                    fp = os.path.normpath(os.path.join(cur, d))
                    if fp.lower() not in seen:
                        seen.add(fp.lower())
                        hits.append(fp)
                        if len(hits) >= max_hits:
                            break
            if len(hits) >= max_hits:
                break
    return hits


def _resolve_file(qname: str, max_hits: int = 12) -> list:
    """Resuelve un ARCHIVO por nombre (sin ruta completa). Si ya es ruta
    absoluta y existe, la devuelve. Si no, busca por nombre exacto
    (case-insensitive) en raíces conocidas, depth acotado. Devuelve lista
    de rutas; si hay varias el caller pregunta cuál."""
    name = (qname or "").strip().strip('"\'')
    if not name:
        return []
    # ruta absoluta directa
    if _re.match(r'^[A-Za-z]:[/\\]', name) and os.path.isfile(name):
        return [os.path.normpath(name)]
    q = name.lower().replace("\\", "/").split("/")[-1]  # solo el nombre
    home = os.path.expanduser("~")
    roots = [os.path.join(home, "Desktop"), os.path.join(home, "Documents"),
             os.path.join(home, "Downloads"), home, "F:/programas",
             os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    skip = {"$recycle.bin", "system volume information", "node_modules",
            "venv", ".venv", ".git", "__pycache__", ".pytest_cache",
            "site-packages", "windows", "appdata", "$winreagent"}
    hits, seen = [], set()
    _t0 = __import__("time").time()
    _deadline = 3.0  # presupuesto: no colgarse buscando algo inexistente
    for root in roots:
        if not os.path.isdir(root) or len(hits) >= max_hits:
            continue
        if __import__("time").time() - _t0 > _deadline:
            break
        base_depth = root.rstrip("/\\").count(os.sep)
        for cur, dirs, files in os.walk(root):
            if __import__("time").time() - _t0 > _deadline:
                break
            if cur.count(os.sep) - base_depth >= 4:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d.lower() not in skip
                       and not d.startswith("$")]
            for f in files:
                if f.lower() == q:
                    fp = os.path.normpath(os.path.join(cur, f))
                    if fp.lower() not in seen:
                        seen.add(fp.lower())
                        hits.append(fp)
                        if len(hits) >= max_hits:
                            break
            if len(hits) >= max_hits:
                break
    return hits


def _abs_or_resolve(name, allow_folder=True):
    """Devuelve (path, error_msg). Resuelve por nombre si no es ruta."""
    name = (name or "").strip().strip('"\'')
    for prep in ("el ", "la ", "los ", "las ", "mi ", "archivo ", "carpeta ",
                 "la carpeta ", "el archivo "):
        if name.lower().startswith(prep):
            name = name[len(prep):]
    name = name.strip().rstrip(".?!,")
    if _re.match(r'^[A-Za-z]:[/\\]', name) and os.path.exists(name):
        return name, None
    hits = _resolve_file(name)
    # Solo buscar como CARPETA si el nombre no parece archivo (sin extensión)
    looks_like_file = bool(_re.search(r'\.\w{1,5}$', name))
    if not hits and allow_folder and not looks_like_file:
        hits = _search_folder_everywhere(name)
    if len(hits) == 1:
        return hits[0], None
    if len(hits) > 1:
        lst = "\n".join("  • " + h for h in hits[:8])
        return None, (f"Encontré varios «{name}». ¿Cuál? Pasame la ruta:\n{lst}")
    return None, f"No encontré «{name}»."


def _resolve_folder(name: str) -> str:
    """Resuelve un nombre de carpeta a su ruta real. Retorna path o None."""
    _genesis_dir = os.path.dirname(os.path.abspath(__file__))
    folder_map = {
        # Carpetas del usuario
        "documentos": "" + _GX_HOME + "/Documents",
        "documents": "" + _GX_HOME + "/Documents",
        "mis documentos": "" + _GX_HOME + "/Documents",
        "escritorio": "" + _GX_HOME + "/Desktop",
        "desktop": "" + _GX_HOME + "/Desktop",
        "mi escritorio": "" + _GX_HOME + "/Desktop",
        "descargas": "" + _GX_HOME + "/Downloads",
        "downloads": "" + _GX_HOME + "/Downloads",
        "mis descargas": "" + _GX_HOME + "/Downloads",
        "imagenes": "" + _GX_HOME + "/Pictures",
        "pictures": "" + _GX_HOME + "/Pictures",
        "fotos": "" + _GX_HOME + "/Pictures",
        "mis imagenes": "" + _GX_HOME + "/Pictures",
        "musica": "" + _GX_HOME + "/Music",
        "music": "" + _GX_HOME + "/Music",
        "mi musica": "" + _GX_HOME + "/Music",
        "videos": "" + _GX_HOME + "/Videos",
        "mis videos": "" + _GX_HOME + "/Videos",
        # Carpetas del sistema
        "disco c": "C:/", "disco d": "D:/", "disco f": "F:/",
        "unidad c": "C:/", "c:": "C:/", "d:": "D:/", "f:": "F:/",
        "home": "" + _GX_HOME + "",
        "mi carpeta": "" + _GX_HOME + "",
        "mi usuario": "" + _GX_HOME + "",
        "perfil": "" + _GX_HOME + "",
        "appdata": "" + _GX_HOME + "/AppData",
        "temp": "" + _GX_HOME + "/AppData/Local/Temp",
        "temporal": "" + _GX_HOME + "/AppData/Local/Temp",
        # Carpetas del proyecto
        "genesis": _genesis_dir,
        "mi proyecto": _genesis_dir,
        "proyecto genesis": _genesis_dir,
        # Programas
        "archivos de programa": "C:/Program Files",
        "program files": "C:/Program Files",
    }
    # Limpiar prefijos
    clean = name.lower().strip()
    for prefix in ["carpeta de ", "carpeta ", "folder de ", "folder ",
                   "directorio de ", "directorio "]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):]

    # 0. Carpeta en una UNIDAD específica: "descargas de la unidad F",
    #    "documentos en D", "F:/algo". Antes "descargas" SIEMPRE iba a C:.
    _drive = None
    _fname = clean
    _dm = _re.match(r'^([a-zA-Z]):[\\/]?(.*)$', name.strip())
    if _dm:
        _drive, _fname = _dm.group(1).upper(), _dm.group(2).strip().lower()
    else:
        _mu = _re.search(
            r'(?:de\s+la\s+|de\s+|en\s+la\s+|en\s+)?(?:unidad|disco|drive)\s+([a-zA-Z])\b',
            clean)
        if not _mu:
            _mu = _re.search(r'\ben\s+([a-zA-Z]):?(?:\s|$)', clean)
        if _mu:
            _drive = _mu.group(1).upper()
            _fname = (clean[:_mu.start()] + clean[_mu.end():]).strip()
    if _drive:
        _root = _drive + ":/"
        # Limpiar conectores residuales: "prueba que se encuentra" → "prueba",
        # "proyecto ubicado" → "proyecto", "la carpeta x" → "x".
        _fname = _re.sub(
            r'\b(que\s+se\s+encuentr[ao]|que\s+se\s+halla|que\s+est[áa]n?|'
            r'que\s+tengo|que\s+hay|ubicad[oa]s?|localizad[oa]s?|guardad[oa]s?|'
            r'situad[oa]s?|llamad[oa]|de\s+nombre)\b', '', _fname)
        _fname = _re.sub(r'^(la\s+|el\s+|los\s+|las\s+)?(carpeta|directorio|folder)\s+',
                         '', _fname)
        _fname = _re.sub(r'\s+', ' ', _fname).strip().strip('"\'')
        if not _fname:
            return _root if os.path.isdir(_root) else None
        _aliases = {
            "descargas": ["Descargas", "Downloads"],
            "downloads": ["Downloads", "Descargas"],
            "documentos": ["Documentos", "Documents"],
            "documents": ["Documents", "Documentos"],
            "imagenes": ["Imágenes", "Imagenes", "Pictures"],
            "fotos": ["Imágenes", "Imagenes", "Pictures"],
            "musica": ["Música", "Musica", "Music"],
            "videos": ["Vídeos", "Videos"],
            "escritorio": ["Escritorio", "Desktop"],
            "desktop": ["Desktop", "Escritorio"],
        }
        _cands = _aliases.get(_fname, []) + [_fname]
        for _c in _cands:
            _p = os.path.join(_root, _c)
            if os.path.isdir(_p):
                return _p
        try:
            _items = os.listdir(_root)
            for _it in _items:  # match exacto case-insensitive
                if _it.lower().replace(" ", "") == _fname.replace(" ", ""):
                    _fp = os.path.join(_root, _it)
                    if os.path.isdir(_fp):
                        return _fp
            for _it in _items:  # fuzzy: alias/nombre contenido
                for _c in _cands:
                    if _c.lower() in _it.lower() and os.path.isdir(os.path.join(_root, _it)):
                        return os.path.join(_root, _it)
        except OSError:
            pass
        # No está en la raíz → buscar en subcarpetas (depth 2), saltando
        # dirs de sistema. Ej: "prueba en F" → F:/programas/prueba.
        _skip = {"$recycle.bin", "system volume information", "msdownld.tmp",
                 "config.msi", "recovery", "$winreagent"}
        _fkey = _fname.replace(" ", "")
        _partial = None
        try:
            for _top in os.listdir(_root):
                if _top.lower() in _skip:
                    continue
                _tp = os.path.join(_root, _top)
                if not os.path.isdir(_tp):
                    continue
                try:
                    for _sub in os.listdir(_tp):
                        _sl = _sub.lower()
                        _sp = os.path.join(_tp, _sub)
                        if not os.path.isdir(_sp):
                            continue
                        if _sl.replace(" ", "") == _fkey:
                            return _sp  # match exacto gana
                        if _partial is None and _fkey in _sl.replace(" ", ""):
                            _partial = _sp
                except OSError:
                    continue
        except OSError:
            pass
        return _partial

    # 1. Buscar en mapa
    path = folder_map.get(clean) or folder_map.get(name.lower())
    if path and os.path.exists(path):
        return path
    # 2. Ruta directa (C:/...)
    if _re.match(r'^[A-Za-z]:[/\\]', name) and os.path.exists(name):
        return name
    # 3. Busqueda inteligente: buscar en Desktop, Documents, discos
    search_dirs = [
        "" + _GX_HOME + "/Desktop", "" + _GX_HOME + "/Documents",
        "" + _GX_HOME + "/Downloads", "" + _GX_HOME + "",
        "F:/programas", "F:/programas/playground",
        "D:/",
    ]
    for sd in search_dirs:
        try:
            if not os.path.isdir(sd):
                continue
            for item in os.listdir(sd):
                if item.lower() == clean or item.lower().replace(" ", "") == clean.replace(" ", ""):
                    full = os.path.join(sd, item)
                    if os.path.isdir(full):
                        return full
        except OSError:
            pass
    # 4. Busqueda fuzzy parcial
    for sd in search_dirs:
        try:
            if not os.path.isdir(sd):
                continue
            for item in os.listdir(sd):
                if clean in item.lower() and os.path.isdir(os.path.join(sd, item)):
                    return os.path.join(sd, item)
        except OSError:
            pass
    return None


def _list_folder_contents(path: str, max_items: int = 50) -> str:
    """Lista el contenido de una carpeta de forma legible."""
    try:
        items = sorted(os.listdir(path))
    except PermissionError:
        return f"[Sin permisos para listar {path}]"
    except Exception as e:
        return f"[Error listando {path}: {e}]"
    if not items:
        return f"Carpeta vacía: {path}"
    dirs = []
    files = []
    for item in items:
        full = os.path.join(path, item)
        if os.path.isdir(full):
            dirs.append(f"  📁 {item}/")
        else:
            try:
                size = os.path.getsize(full)
                if size >= 1024 * 1024:
                    sz = f"{size / (1024*1024):.1f} MB"
                elif size >= 1024:
                    sz = f"{size / 1024:.1f} KB"
                else:
                    sz = f"{size} B"
                files.append(f"  📄 {item} ({sz})")
            except OSError:
                files.append(f"  📄 {item}")
    total = len(dirs) + len(files)
    lines = [f"📂 {path}", f"   {len(dirs)} carpetas, {len(files)} archivos\n"]
    shown = (dirs + files)[:max_items]
    lines.extend(shown)
    if total > max_items:
        lines.append(f"\n  ... y {total - max_items} elementos más")
    return "\n".join(lines)


class GenesisToolsMixin:
    """Mixin con auto-detección de herramientas y filtros de calidad."""

    # Patrones que indican que el usuario quiere que Genesis APRENDA
    LEARN_TRIGGERS = [
        "aprende sobre", "aprende de", "aprende acerca",
        "especialízate en", "especializate en", "especializa en",
        "estudia sobre", "estudia de",
        "investiga y aprende", "investiga sobre", "investiga de",
        "quiero que aprendas", "quiero que sepas",
        "aprende todo sobre", "aprende mas sobre",
        "capacítate en", "capacitate en",
        "entrénate en", "entrenate en",
        "enfócate en", "enfocate en",
        "domina el tema", "domina sobre",
        "conviértete en experto", "conviertete en experto",
        "vuelvete experto", "se experto en",
        "learn about", "specialize in", "study about",
    ]

    # Cache de programas descubiertos (se refresca cada 5 min)
    _installed_apps_cache = None
    _installed_apps_cache_time = 0

    def _auto_builder(self, user_input: str, response: str, system_prompt: str) -> str:
        """
        AUTO-BUILDER: Intercepta respuestas del LLM y fuerza ejecución cuando corresponde.

        Maneja 2 casos:
        1. LLM mostró código en bloques markdown pero no usó [TOOL:] → ejecutar el código
        2. LLM se rehusó ("no puedo", "lo siento") cuando sí puede → re-intentar con prompt forzado

        Esto compensa que llama3.1 8B tiende a "explicar/rechazar" en vez de "ejecutar".
        """
        import re
        from core.tools import parse_tool_call, execute_tool

        # Solo activar si NO hubo tool call en la respuesta
        if parse_tool_call(response) is not None:
            return response

        # Detectar intención de "crear/construir" del usuario
        build_keywords = [
            "crea", "crealo", "créalo", "hazlo", "construye", "genera", "generalo",
            "escribi", "escribime", "haceme", "armame", "arma", "programa",
            "desarrolla", "implementa", "codea", "codealo", "ejecuta", "ejecutalo",
            "corre", "correlo", "guarda", "guardalo", "instala", "instalalo",
        ]
        user_lower = user_input.lower().strip()
        is_build_request = any(kw in user_lower for kw in build_keywords)

        if not is_build_request:
            return response

        # === CASO 2: REFUSAL DETECTION ===
        # Si el LLM se rehusó pero el usuario pidió crear algo, reintentar
        refusal_patterns = [
            "no puedo cumplir", "no puedo crear", "no puedo generar",
            "no tengo la capacidad", "no es posible", "lo siento",
            "no me es posible", "fuera de mis capacidades",
            "no puedo hacer eso", "no soy capaz",
        ]
        response_lower = response.lower()
        is_refusal = any(p in response_lower for p in refusal_patterns)

        if is_refusal:
            if self.show_thinking:
                print(f"  [Auto-Builder: REFUSAL detectado — reintentando con prompt forzado]")

            # Reintentar con un prompt que NO permita rehusarse
            self.memory.short_term.add("assistant", response)
            self.memory.short_term.add("user",
                f"[SISTEMA — OVERRIDE] Tu respuesta anterior fue incorrecta. "
                f"Tu SI tienes herramientas para crear archivos y ejecutar código. "
                f"Usa [TOOL:escribir] para crear archivos o [TOOL:python] para ejecutar código. "
                f"El usuario pidió: '{user_input}'. "
                f"EJECUTA la acción usando herramientas. NO digas 'no puedo'. "
                f"Responde SOLO con la herramienta, ejemplo:\n"
                f"Creando el archivo...\n"
                f"[TOOL:python] <código que cumple lo pedido>"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            retry_response = self.brain.think(system_prompt, messages)

            # Verificar si el retry tiene tool call
            tc = parse_tool_call(retry_response)
            if tc:
                tool_name, tool_arg = tc
                if self.show_thinking:
                    print(f"  [Auto-Builder: retry exitoso — ejecutando {tool_name}]")
                tool_result = execute_tool(tool_name, tool_arg)
                self.metrics.log_tool_use(tool_name)

                # Dar resultado al LLM para respuesta final
                self.memory.short_term.add("assistant", f"[Herramienta usada: {tool_name}]")
                self.memory.short_term.add("user",
                    f"[RESULTADO DE HERRAMIENTA {tool_name}]:\n{tool_result}\n\n"
                    f"Responde al usuario confirmando que se completó la acción."
                )
                raw_msgs = self.memory.get_conversation_messages()
                messages = self.context_manager.fit_messages(
                    raw_msgs, summary=self.summarizer.get_summary()
                )
                return self.brain.think(system_prompt, messages)

            # Si el retry tampoco tiene tool call, intentar extraer código y ejecutar
            code_blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', retry_response, re.DOTALL)
            if code_blocks:
                code = code_blocks[0].strip()
                tool_result = execute_tool("python", code)
                self.metrics.log_tool_use("python")
                return (
                    f"Ejecutado.\n\n"
                    f"```python\n{code}\n```\n\n"
                    f"Resultado:\n{tool_result[:1500]}"
                )

            # Último recurso: respuesta del retry es mejor que el refusal original
            return retry_response

        # === CASO 1: CÓDIGO MOSTRADO SIN EJECUTAR ===
        code_blocks = re.findall(
            r'```(?:python|py)?\s*\n(.*?)```',
            response,
            re.DOTALL
        )

        if not code_blocks:
            return response

        # Tenemos código Y pedido de build → AUTO-EJECUTAR
        code = code_blocks[0].strip()

        if self.show_thinking:
            print(f"  [Auto-Builder: LLM mostró código sin ejecutar → forzando ejecución]")
            print(f"  [Auto-Builder: código de {len(code)} chars]")

        if len(code) > 30:
            # Ejecutar el código con [TOOL:python]
            tool_result = execute_tool("python", code)
            self.metrics.log_tool_use("python")

            has_error = (
                "Error" in tool_result
                or "Traceback" in tool_result
                or "Codigo de salida: 1" in tool_result
            )

            if has_error:
                # Código falló — pedir al LLM que corrija
                if self.show_thinking:
                    print(f"  [Auto-Builder: código falló, pidiendo corrección]")

                self.memory.short_term.add("assistant", "[Ejecuté el código pero falló]")
                self.memory.short_term.add("user",
                    f"[AUTO-BUILDER: El código que generaste falló al ejecutarse]\n"
                    f"Error:\n{tool_result[:800]}\n\n"
                    f"Codigo:\n```python\n{code[:1500]}\n```\n\n"
                    f"Corrige el error y usa [TOOL:python] para ejecutar el código corregido."
                )
                raw_msgs = self.memory.get_conversation_messages()
                messages = self.context_manager.fit_messages(
                    raw_msgs, summary=self.summarizer.get_summary()
                )
                corrected = self.brain.think(system_prompt, messages)

                tc = parse_tool_call(corrected)
                if tc:
                    tool_name, tool_arg = tc
                    result2 = execute_tool(tool_name, tool_arg)
                    self.metrics.log_tool_use(tool_name)
                    return (
                        f"Ejecutado (con corrección).\n\n"
                        f"```python\n{tool_arg[:2000]}\n```\n\n"
                        f"Resultado:\n{result2[:1000]}"
                    )
                return corrected
            else:
                # Código exitoso
                if self.show_thinking:
                    print(f"  [Auto-Builder: código ejecutado exitosamente]")

                self.code_memory.store(
                    task=user_input,
                    code=code,
                    output=tool_result[:500],
                    language="python",
                )

                text_before = response.split('```')[0].strip()
                if not text_before or len(text_before) < 10:
                    text_before = "Hecho."

                return (
                    f"{text_before}\n\n"
                    f"```python\n{code}\n```\n\n"
                    f"**Ejecutado automáticamente.** Resultado:\n{tool_result[:1500]}"
                )

        return response

    def _anti_hallucination_filter(self, user_input: str, response: str) -> str:
        """
        Detecta si el LLM inventó acciones o datos del sistema que no realizó.
        Si detecta alucinación, reemplaza con datos reales o respuesta honesta.
        """
        resp_lower = response.lower()
        user_lower = user_input.lower()

        # === CAPA 1: Hardware fabricado ===
        # Si la respuesta contiene especificaciones de hardware que parecen inventadas,
        # reemplazar con datos reales del sistema
        hw_fabrication_indicators = [
            # CPUs inventados comunes (el LLM los fabrica con frecuencia)
            "i7-10700", "i7-11700", "i7-12700", "i7-13700", "i7-14700",
            "i9-10900", "i9-11900", "i9-12900", "i9-13900", "i9-14900",
            "ryzen 9", "ryzen 7 5800", "ryzen 7 3700",
            # RAM inventada
            "64 gb ddr", "128 gb ddr", "32 gb ddr4", "16 gb ddr5",
            # GPUs inventadas (no es la RTX 3060 Ti real)
            "rtx 3080", "rtx 3090", "rtx 4060", "rtx 4070", "rtx 4080", "rtx 4090",
            "rtx 3070 ti", "rtx 3080 ti",
            # Discos inventados
            "samsung 970", "samsung 980", "samsung 990",
            "wd black", "crucial p5",
            # Fechas absurdas
            "01/03/2023",
        ]
        # Contar cuántos indicadores de fabricación hay
        hw_fabrication_count = sum(1 for ind in hw_fabrication_indicators if ind in resp_lower)
        if hw_fabrication_count >= 2:
            # 2+ indicadores = claramente fabricado → reemplazar con datos reales
            self.log.info(f"Anti-hallucination: {hw_fabrication_count} indicadores de HW fabricado detectados")
            try:
                from core.tools import SystemInfoTool
                real_info = SystemInfoTool.get_system_info()
                return (f"⚠️ Detuve una respuesta incorrecta. Estos son tus datos reales:\n\n"
                        f"{real_info}")
            except (ImportError, AttributeError, OSError):
                return ("⚠️ Detecté que iba a darte datos incorrectos. "
                        "Pedime 'info del sistema' para obtener los datos reales de tu equipo.")

        # === CAPA 2: Refusal / negación de capacidades ===
        refusal_phrases = [
            "no puedo acceder directamente",
            "no tengo acceso directo",
            "no puedo acceder a tu sistema",
            "no puedo acceder a las aplicaciones",
            "no tengo la capacidad",
            "no puedo ejecutar aplicaciones",
            "no puedo abrir aplicaciones",
            "no tengo acceso físico",
            "no tengo acceso a tu sistema",
            "solo tengo una voz",
            "sólo tengo una voz",
            "una voz digitalizada",
            "una única voz",
            "no tengo múltiples voces",
        ]
        if any(rp in resp_lower for rp in refusal_phrases):
            self.log.info("Anti-hallucination: refusal de capacidades detectado")
            return ("Sí puedo hacer eso. Tengo acceso completo a tu sistema: "
                    "abrir apps, gestionar archivos, info de hardware, TTS con 22 voces, "
                    "y más. Pedímelo de forma directa, por ejemplo: "
                    "'abre excel', 'info del sistema', 'busca archivos de X'.")

        # === CAPA 3: Acciones fabricadas ===
        hallucination_patterns = [
            ("restaurando", "restaurar archivos"),
            ("he restaurado", "restaurar archivos"),
            ("ha sido restaurado", "restaurar archivos"),
            ("archivo restaurado", "restaurar archivos"),
            ("accediendo a", "acceder al sistema"),
            ("he accedido", "acceder al sistema"),
            ("eliminando el archivo", "eliminar archivos"),
            ("he eliminado", "eliminar archivos"),
            ("archivo eliminado", "eliminar archivos"),
            ("moviendo el archivo", "mover archivos"),
            ("he movido", "mover archivos"),
            ("copiando el archivo", "copiar archivos"),
            ("he copiado", "copiar archivos"),
            ("instalando", "instalar software"),
            ("he instalado", "instalar software"),
            ("descargando", "descargar archivos"),
            ("he descargado", "descargar archivos"),
            ("ejecutando el comando", "ejecutar comandos"),
            ("he ejecutado", "ejecutar comandos"),
        ]

        # Solo verificar si NO hubo tool call real en esta interacción
        from core.tools import parse_tool_call
        had_tool = parse_tool_call(response) is not None

        if not had_tool:
            for pattern, action in hallucination_patterns:
                if pattern in resp_lower:
                    fake_indicators = [
                        "informe de ventas", "fotos de vacaciones",
                        "confirmación de reserva", "proyecto de diseño",
                        "lista de compras", "documento.txt", "imagen.jpg",
                        "el archivo ha sido", "ahora muestra 0",
                        "se ha completado", "operación exitosa",
                    ]
                    if any(fi in resp_lower for fi in fake_indicators):
                        return (f"No pude {action} — esa acción requiere una "
                                f"herramienta que no se ejecutó. "
                                f"Intenta pedirlo de forma más específica.")

        # === CAPA 4: Incertidumbre detectada — auto-investigar ===
        # Si el LLM admite no saber o da una respuesta vaga/incierta,
        # buscar en internet y re-generar con datos reales
        uncertainty_phrases = [
            "no estoy seguro",
            "no tengo información",
            "no dispongo de",
            "no cuento con datos",
            "no tengo datos",
            "no tengo certeza",
            "podría estar equivocado",
            "no puedo confirmar",
            "no tengo acceso a esa información",
            "mi conocimiento llega hasta",
            "mis datos llegan hasta",
            "no tengo información actualizada",
            "no puedo verificar",
            "desconozco",
            "no sabría decirte",
            "no tengo forma de saber",
            "habría que verificar",
            "no me consta",
        ]
        if any(up in resp_lower for up in uncertainty_phrases):
            # El LLM admitió no saber — intentar buscar en la web
            try:
                if hasattr(self, 'web') and self.web and self.web.searcher.available:
                    # Extraer tema de la pregunta del usuario
                    topic = user_input.strip().rstrip("?.,!")
                    if self.show_thinking:
                        print(f"  [Anti-hallucination Capa 4: incertidumbre detectada — investigando '{topic}']")

                    results = self.web.searcher.search(topic, max_results=3)
                    if results:
                        search_ctx = f"[INVESTIGACIÓN AUTOMÁTICA — Genesis detectó que no tenía la respuesta y buscó en internet]:\n"
                        for i, r in enumerate(results[:3], 1):
                            title = r.get("title", "")
                            snippet = r.get("snippet", r.get("body", ""))
                            url = r.get("url", r.get("href", ""))
                            search_ctx += f"{i}. {title}\n   {snippet[:250]}\n   Fuente: {url}\n\n"

                        # Leer primera pagina para mas detalle
                        first_url = results[0].get("url", results[0].get("href", ""))
                        if first_url:
                            try:
                                page_text = self.web.reader.read_page(first_url)
                                if page_text and len(page_text) > 100:
                                    search_ctx += f"\n[CONTENIDO DETALLADO]:\n{page_text[:2000]}\n"
                            except (OSError, ValueError, AttributeError):
                                pass

                        search_ctx += (
                            "\nCon esta información REAL, responde la pregunta del usuario. "
                            "Cita las fuentes. NO inventes nada que no esté en los resultados."
                        )

                        # Re-generar respuesta con datos reales
                        self.memory.short_term.add("assistant", response)
                        self.memory.short_term.add("user", search_ctx)
                        raw_msgs = self.memory.get_conversation_messages()
                        messages = self.context_manager.fit_messages(
                            raw_msgs, summary=self.summarizer.get_summary()
                        )
                        # Usar system_prompt del build actual
                        sys_prompt = self.build_system_prompt()
                        new_response = self.brain.think(sys_prompt, messages, temperature=0.3)
                        if new_response and len(new_response) > len(response):
                            self.log.info("Anti-hallucination Capa 4: respuesta regenerada con datos web")
                            return new_response
            except Exception as e:
                if self.show_thinking:
                    print(f"  [Anti-hallucination Capa 4: error en investigación — {e}]")

        return response

    def _response_quality_guard(self, user_input: str, response: str,
                                 system_prompt: str) -> str:
        """
        Response Quality Guard — Detecta respuestas vacías, genéricas o inútiles
        y fuerza regeneración con prompt mejorado.

        Detecta:
        1. Respuestas demasiado cortas para la complejidad de la pregunta
        2. Respuestas genéricas que no aportan valor
        3. Contradicciones (dice "puedo" y luego "no puedo" en la misma respuesta)
        4. Respuestas en inglés cuando debería ser español
        """
        resp_lower = response.lower().strip()
        user_lower = user_input.lower().strip()

        # No aplicar si la respuesta ya contiene resultado de herramienta
        if "[RESULTADO" in response or "[TOOL:" in response:
            return response

        # 1. Respuesta demasiado corta para preguntas sustanciales
        is_complex_query = len(user_input) > 30 or any(
            w in user_lower for w in ["como", "cómo", "por que", "por qué",
                                       "explica", "investiga", "analiza"]
        )
        if is_complex_query and len(response.strip()) < 40:
            if self.show_thinking:
                print(f"  [QualityGuard: respuesta muy corta ({len(response)} chars) para query compleja — regenerando]")
            self.memory.short_term.add("assistant", response)
            self.memory.short_term.add("user",
                f"[SISTEMA: Tu respuesta anterior fue demasiado corta y genérica. "
                f"El usuario hizo una pregunta sustancial. "
                f"Responde con profundidad y detalle. "
                f"Mínimo 3-4 oraciones con información útil y específica.]"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            return self.brain.think(system_prompt, messages, temperature=0.8)

        # 2. Respuestas genéricas/relleno
        generic_patterns = [
            "como asistente de ia",
            "como modelo de lenguaje",
            "no tengo la capacidad de",
            "estoy aqui para ayudarte",
            "¿en que puedo ayudarte",
            "¿como puedo ayudarte",
            "no dudes en preguntar",
            "si tienes alguna otra pregunta",
            "estoy a tu disposicion",
            "estaré encantado de ayudarte",
            "claro, con gusto",
            "por supuesto, con mucho gusto",
        ]
        has_generic = sum(1 for p in generic_patterns if p in resp_lower)
        if has_generic >= 2:
            # Demasiadas frases genéricas — regenerar
            if self.show_thinking:
                print(f"  [QualityGuard: {has_generic} frases genéricas detectadas — regenerando]")
            self.memory.short_term.add("assistant", response)
            self.memory.short_term.add("user",
                f"[SISTEMA: Tu respuesta usa frases genéricas de chatbot. "
                f"Eres Genesis, no un asistente corporativo. "
                f"Responde de forma directa, específica y con personalidad. "
                f"NO uses frases como 'estoy aqui para ayudarte' ni '¿como puedo ayudarte?'. "
                f"Responde la pregunta original: '{user_input[:200]}']"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            return self.brain.think(system_prompt, messages, temperature=0.7)

        # 3. Contradición: dice "puedo" y "no puedo" sobre lo mismo
        can_do = any(w in resp_lower for w in ["puedo hacerlo", "si puedo", "soy capaz", "tengo la capacidad"])
        cant_do = any(w in resp_lower for w in ["no puedo", "no soy capaz", "fuera de mis capacidades", "no tengo la capacidad"])
        if can_do and cant_do:
            if self.show_thinking:
                print(f"  [QualityGuard: contradicción detectada (puedo + no puedo) — regenerando]")
            self.memory.short_term.add("assistant",
                "[Tu respuesta anterior se contradijo — dijiste que podías y no podías hacer lo mismo]")
            self.memory.short_term.add("user",
                f"[SISTEMA: COHERENCIA — NO te contradigas. "
                f"Si puedes hacer algo con herramientas, HAZLO. "
                f"Si genuinamente no puedes, di por qué y sugiere alternativa. "
                f"Pregunta original: '{user_input[:200]}']"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            return self.brain.think(system_prompt, messages, temperature=0.5)

        return response

    def _clean_internal_messages(self):
        """
        Limpia mensajes internos del short-term memory que no son
        parte de la conversación real.

        Después del tool loop, la memoria se llena de mensajes como:
        - "[Sistema: herramienta ejecutada exitosamente]"
        - "[TAREA COMPLETADA — RESULTADO]: ..."
        - "[RESULTADO DE HERRAMIENTA python — paso 1/10]: ..."
        - "[ERROR EN CODIGO — CORRIGE Y REINTENTA]"

        Estos mensajes son útiles DURANTE el procesamiento pero no
        deberían persistir en la memoria de corto plazo. Los reemplazamos
        por versiones compactas.
        """
        st = self.memory.short_term
        if not st.messages:
            return

        internal_prefixes = [
            "[Sistema:", "[TAREA COMPLETADA", "[RESULTADO DE HERRAMIENTA",
            "[ERROR EN CODIGO", "[MAXIMO DE REINTENTOS", "[AUTO-BUILDER:",
            "[SISTEMA — OVERRIDE]", "[SISTEMA:",
        ]

        cleaned = []
        tool_results_summary = []

        for msg in st.messages:
            content = msg.get("content", "")
            is_internal = any(content.startswith(p) for p in internal_prefixes)

            if is_internal:
                # Extraer resumen compacto del resultado de herramienta
                if "RESULTADO" in content and "\n" in content:
                    # Mantener solo la primera línea del resultado
                    first_line = content.split("\n")[0][:150]
                    tool_results_summary.append(first_line)
                # No agregar el mensaje completo — se pierde
                continue
            else:
                cleaned.append(msg)

        # Si hubo tool results, agregar un resumen compacto
        if tool_results_summary and cleaned:
            summary = "[Resumen herramientas: " + "; ".join(tool_results_summary[-3:]) + "]"
            # Insertar antes del último mensaje si es del assistant
            if cleaned[-1].get("role") == "assistant":
                cleaned.insert(-1, {"role": "user", "content": summary})

        st.messages = cleaned

    def _clean_trailing_filler(self, response: str) -> str:
        """
        Elimina preguntas/frases genéricas al final de la respuesta.

        El LLM tiende a agregar "¿Quieres que te ayude con algo más?" o
        "¿Necesitas algo más?" al final, lo cual es robotico y prohibido
        por las CORE_RULES. Este método las limpia.
        """
        import re

        # Patrones de trailing filler (al final de la respuesta)
        trailing_patterns = [
            r'\n*¿(?:Quieres|Necesitas|Deseas|Te gustaría|Hay algo más).*?\?$',
            r'\n*¿(?:En qué|Cómo|Como) (?:más )?(?:puedo|te puedo) (?:ayudarte|ayudar|asistirte).*?\?$',
            r'\n*(?:Si necesitas|Si quieres|No dudes en) (?:algo más|preguntar|consultarme).*$',
            r'\n*(?:Estoy (?:aquí|a tu disposición|disponible) (?:para|si)).*$',
            r'\n*¿(?:Algo más|Algo otro|Otra cosa).*?\?$',
        ]

        cleaned = response.rstrip()
        for pattern in trailing_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE).rstrip()

        # Solo limpiar si no eliminamos demasiado (>70% del contenido)
        if len(cleaned) > len(response) * 0.3 and len(cleaned) > 20:
            return cleaned
        return response

    @staticmethod
    def _learn_app(filepath: str, current_map: dict, name: str, target: str):
        """Aprende una app/URL para la proxima vez que el usuario la pida."""
        try:
            current_map[name] = target
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(current_map, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError):
            pass

    def _discover_installed_app(self, query: str) -> str:
        """
        Busca un programa instalado escaneando los shortcuts del Menú Inicio.
        Retorna la ruta al .lnk/.url si encuentra match, o None.
        Cache se refresca cada 5 minutos para detectar nuevas instalaciones.
        Escanea tanto .lnk (apps normales) como .url (juegos Steam, etc).
        """
        import glob as _glob
        import time as _time

        # Refrescar cache cada 5 minutos o si no existe
        now = _time.time()
        if GenesisToolsMixin._installed_apps_cache is None or (now - GenesisToolsMixin._installed_apps_cache_time) > 300:
            GenesisToolsMixin._installed_apps_cache = {}
            GenesisToolsMixin._installed_apps_cache_time = now
            skip_words = ['uninstall', 'readme', 'sample', 'reference', 'license',
                          'help', 'release notes', 'documentation', 'manual',
                          'module docs', 'desinstala', 'faq', 'homepage',
                          'website', 'documentation']
            start_menu_dirs = [
                os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs'),
                os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
            ]
            for sdir in start_menu_dirs:
                try:
                    # Escanear .lnk (apps normales) y .url (juegos Steam, etc.)
                    for ext in ('*.lnk', '*.url'):
                        for shortcut_path in _glob.glob(os.path.join(sdir, '**', ext), recursive=True):
                            name = os.path.splitext(os.path.basename(shortcut_path))[0]
                            name_lower = name.lower()
                            if any(s in name_lower for s in skip_words):
                                continue
                            # Guardar con nombre en lowercase como clave
                            if name_lower not in GenesisToolsMixin._installed_apps_cache:
                                GenesisToolsMixin._installed_apps_cache[name_lower] = shortcut_path
                except OSError:
                    pass

        cache = GenesisToolsMixin._installed_apps_cache
        query = query.strip().lower()

        # 1. Match exacto
        if query in cache:
            return cache[query]

        # 2. Match parcial: query contenido en nombre o viceversa
        # Priorizar matches más cortos (más específicos)
        candidates = []
        for name, path in cache.items():
            if query in name or name in query:
                candidates.append((name, path))
            elif query.replace(" ", "") in name.replace(" ", ""):
                candidates.append((name, path))

        if candidates:
            # Preferir match más cercano en longitud al query
            candidates.sort(key=lambda x: abs(len(x[0]) - len(query)))
            return candidates[0][1]

        return None

    def _ui_action(self, inp: str, raw: str):
        """Automatización de UI: controla menús, botones y teclado de CUALQUIER app.
        Devuelve un mensaje si ejecutó una acción, o None si el input no aplica.
        Va ANTES de open/content para que 'abrí el menú X' no caiga en el launcher."""
        import re as _re
        try:
            from core import ui_automation as _ui
        except Exception:
            return None
        if not _ui.available().get("uiautomation"):
            return None
        t = (inp or "").strip()

        def _split_app(s):
            """Separa 'guardar de notepad' → ('guardar', 'notepad'). Toma el PRIMER
            separador (de/del/en/al) para que apps con 'de' en el nombre ('bloc de
            notas') queden enteras: 'menús del bloc de notas' → app='bloc de notas'."""
            m = _re.search(r"\s+(?:del|de\s+la|de\s+los|de\s+las|de|en\s+el|"
                           r"en\s+la|en|al|a\s+la)\s+(?:la\s+|el\s+)?(.+)$", s)
            if m:
                return s[:m.start()].strip(), m.group(1).strip().rstrip(".?!,")
            return s.strip(), None

        # 1. Listar ventanas abiertas
        if _re.search(r"(qu[eé]\s+ventanas|ventanas\s+(abiertas|tengo|hay)|"
                      r"qu[eé]\s+(tengo|hay)\s+abierto)", t):
            ws = _ui.list_windows()
            return ("Ventanas abiertas:\n" + "\n".join("  • " + w for w in ws)
                    if ws else "No detecté ventanas abiertas.")

        # 1b. MACRO copiar→pegar entre ventanas (multi-paso):
        #     "copiá el contenido de A y pegalo en B" / "seleccioná todo de A,
        #     copialo y pegalo en B". Resuelve "este/el otro" si hay 2 ventanas.
        if _re.search(r"\bcopi[áa]", t) and _re.search(r"\bpeg[áa]", t):
            sm = _re.search(
                r"(?:de|desde|del)\s+(?:la\s+|el\s+)?(?:ventana\s+|app\s+|"
                r"documento\s+|archivo\s+|pesta[ñn]a\s+)?(.+?)"
                r"(?:\s*,|\s+y\s+|\s+luego|\s+despu[eé]s|\s+peg)", t)
            tm = _re.search(
                r"peg[áa]\w*\s+(?:lo|la|los|las\s+)?(?:en|a|al)\s+(?:la\s+|el\s+|"
                r"este\s+|esta\s+)?(?:ventana\s+|app\s+|documento\s+|archivo\s+|"
                r"pesta[ñn]a\s+|otro\s+|otra\s+)?(.+)$", t)
            src = sm.group(1).strip() if sm else None
            tgt = tm.group(1).strip().rstrip(".?!,") if tm else None
            return self._do_copy_paste(src, tgt)

        # 1c. Enfocar / traer una ventana al frente
        m = _re.search(r"(?:enfoc[áa]r?|activ[áa]r?|tra[ée]r?|cambi[áa]r?\s+a|"
                       r"pas[áa]r?\s+a|mostr[áa]r?)\s+(?:la\s+|el\s+)?"
                       r"(?:ventana\s+|app\s+|aplicaci[oó]n\s+)(.+)$", t)
        if m:
            tgtw = m.group(1).strip().rstrip(".?!,")
            return (f"Traje «{tgtw}» al frente."
                    if _ui.focus_app(tgtw) else f"No encontré la ventana «{tgtw}».")

        # 2. Inspeccionar menús/botones de una app
        m = _re.search(r"(?:inspeccion[áa]r?|mostr[aá]me?\s+(?:los\s+|las\s+)?"
                       r"(?:men[uú]s?|opciones|botones)|qu[eé]\s+(?:men[uú]s?|"
                       r"opciones|botones))\b(.*)$", t)
        if m:
            _, app = _split_app(m.group(1))
            items = _ui.inspect_ui(app)
            if not items:
                tgt = f"«{app}»" if app else "la ventana activa"
                return f"No pude inspeccionar {tgt} (¿está abierta y al frente?)."
            head = (f"Elementos de «{app}»:" if app
                    else "Elementos de la ventana activa:")
            return head + "\n" + "\n".join(
                f"  • [{e['type']}] {e['name']}" for e in items[:40])

        # 3. Menú: "abrí el menú archivo > guardar de notepad" / "andá a archivo guardar"
        m = _re.search(r"(?:abr[ií]r?|abre|and[áa]|ir|navega[r]?|despleg[áa]r?)\s+"
                       r"(?:a\s+|al\s+)?(?:el\s+)?men[uú]\s+(.+)$", t)
        if not m and "men" in t:
            m = _re.search(r"\bmen[uú]\s+(.+)$", t)
        if m:
            rest, app = _split_app(m.group(1))
            steps = [s for s in (x.strip() for x in _re.split(
                r"\s*(?:>|→|->|,|\s+y\s+|\s+luego\s+|\s+despu[eé]s\s+)\s*", rest)) if s]
            return _ui.open_menu(steps or rest, app)

        # 4. Atajo de teclado: "apretá/presioná/tecleá ctrl+s"
        m = _re.search(r"(?:apret[áa]|presion[áa]|mand[áa]|tecle[áa]|atajo|"
                       r"combinaci[oó]n|teclas?)\s+(.+)$", t)
        if m:
            combo, _ = _split_app(m.group(1))
            combo = combo or m.group(1)
            if "+" in combo or _re.search(
                    r"\b(ctrl|control|alt|shift|win|enter|intro|esc|escape|tab|"
                    r"supr|suprimir|espacio|f[0-9]{1,2})\b", combo):
                return _ui.press_hotkey(combo)

        # 5. Escribir texto. Para NO secuestrar pedidos de código ("escribí una
        #    función en python"), con "escribí" solo activa si: hay comillas, el
        #    verbo es tipeá/redactá (inequívocos), o la "app" es una VENTANA real.
        m = _re.search(r"(?:escrib[íi]|tipe[áa]|redact[áa])\s+(.+)$", t)
        if m:
            verb = t[m.start():].split()[0]
            rawm = _re.search(r"(?:escrib[íi]|tipe[áa]|redact[áa])\s+(.+)$",
                              (raw or "").strip(), _re.IGNORECASE)
            raw_g = (rawm.group(1) if rawm else m.group(1)).strip()
            qm = _re.search(r"['\"“](.+?)['\"”]", raw_g)
            _, app = _split_app(m.group(1))
            app_win = bool(app) and (_ui._find_window(app) is not None)
            if qm or app_win or verb.startswith(("tipe", "redact")):
                if app_win:
                    _ui.focus_app(app)
                if qm:
                    txt = qm.group(1)
                else:
                    txt = raw_g
                    if app_win:  # quitar "... en <app>" del final
                        txt = _re.sub(r"\s+(?:del|de|en|al)\s+.+$", "", txt).strip()
                txt = txt.strip().strip("'\"“”")
                if txt:
                    return _ui.type_text(txt)

        # 6. Click en un elemento por nombre
        m = _re.search(r"(?:cli?cke[áa]r?|hac[ée]\s+cli?ck\s+en|toc[áa]|puls[áa]|"
                       r"selccion[áa]|seleccion[áa])\s+(?:el\s+|la\s+)?"
                       r"(?:bot[oó]n\s+|men[uú]\s+|pesta[ñn]a\s+|opci[oó]n\s+|item\s+)?"
                       r"(.+)$", t)
        if m:
            rest, app = _split_app(m.group(1))
            return _ui.click_element(rest, app)

        return None

    def _do_copy_paste(self, src, tgt):
        """Macro: enfoca origen → Ctrl+A → Ctrl+C → enfoca destino → Ctrl+V.
        Resuelve deícticos: origen vacío/'este' = ventana activa; destino
        'el otro/este otro' = la otra ventana si solo hay dos candidatas."""
        import re as _re
        import time as _t
        from core import ui_automation as _ui
        DEIXIS = {"este", "esta", "esto", "este documento", "este otro", "el otro",
                  "la otra", "el otro documento", "la otra ventana", "ese", "aquel",
                  "aca", "acá", "aqui", "aquí", "alla", "allá", "esto", "documento",
                  "otro", "otra", "el de al lado"}
        wins = _ui.list_windows()
        if not wins:
            return "No detecté ventanas abiertas."

        def resolve(name, exclude=None):
            if not name or name.lower().strip() in DEIXIS:
                return None  # deixis / vacío
            nl = name.lower().strip()
            for w in wins:
                if nl in w.lower() and w != exclude:
                    return w
            words = [x for x in nl.split() if len(x) > 2]
            for w in wins:
                if w != exclude and words and all(x in w.lower() for x in words):
                    return w
            return False  # nombrada pero no hallada

        act = _ui._active_window()
        act_name = act.Name if act else None
        s = resolve(src)
        if s is None:
            s = act_name
        if not s:
            return ("No supe de qué ventana copiar. Nombrala. Abiertas: "
                    + ", ".join(wins))
        if s is False:
            return (f"No encontré la ventana de origen «{src}». Abiertas: "
                    + ", ".join(wins))
        tg = resolve(tgt, exclude=s)
        if tg is None:  # destino deíctico ("el otro") → inferir
            cabin = "genesis ai"
            # 1) preferir otra ventana del MISMO tipo de app que el origen
            #    (ej: origen "Doc1 - Word" → buscar otra "... Word")
            s_app = s.split(" - ")[-1].split(":")[-1].strip().lower()
            same = [w for w in wins if w != s and w.lower() != cabin
                    and s_app and len(s_app) > 3 and s_app in w.lower()]
            others = [w for w in wins if w != s and w.lower() != cabin]
            if len(same) == 1:
                tg = same[0]
            elif len(others) == 1:
                tg = others[0]
            else:
                cands = same or others
                return ("¿En cuál pego? Decime el nombre. Candidatas: "
                        + ", ".join(cands[:8]))
        if tg is False:
            return (f"No encontré la ventana destino «{tgt}». Abiertas: "
                    + ", ".join(wins))
        # Secuencia
        if not _ui.focus_app(s):
            return f"No pude enfocar la ventana de origen «{s}»."
        _t.sleep(0.35)
        _ui.press_hotkey("ctrl+a")
        _t.sleep(0.2)
        _ui.press_hotkey("ctrl+c")
        _t.sleep(0.35)
        if not _ui.focus_app(tg):
            return f"Copié de «{s}» pero no pude enfocar el destino «{tg}»."
        _t.sleep(0.35)
        _ui.press_hotkey("ctrl+v")
        return f"Listo: copié el contenido de «{s}» y lo pegué en «{tg}»."

    def _wake_callback(self, reminder):
        """Acción de despertador: cuando un recordatorio 🌅 se dispara, te HABLA
        (anuncio por voz) y DESPUÉS reproduce música. Un despertador de verdad."""
        try:
            msg = getattr(reminder, "message", "") or ""
            if not (msg.startswith("🌅") and "▶" in msg):
                return
            song = msg.split("▶", 1)[1].strip()
            # 1) ANUNCIO HABLADO (TTS local, suena por los parlantes directo).
            try:
                import datetime as _dt
                hora = _dt.datetime.now().strftime("%H:%M")
                texto = (f"Buen día. Son las {hora}. Arriba, hora de levantarse. "
                         f"Te pongo música.")
                # COM init: el callback corre en el thread del timer (no el main)
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except Exception:
                    pass
                import pyttsx3
                eng = pyttsx3.init()
                eng.setProperty("rate", 165)
                eng.say(texto)
                eng.runAndWait()
                try:
                    eng.stop()
                except Exception:
                    pass
            except Exception:
                pass
            # 2) MÚSICA
            from core import music_player as _mp
            _mp.play_in_app(song)
        except Exception:
            pass

    def _ensure_reminders(self):
        """Crea el ReminderSystem y garantiza el callback de despertador."""
        from core.reminder_system import ReminderSystem
        if not hasattr(self, "_reminders"):
            self._reminders = ReminderSystem()
        self._reminders.set_callback(self._wake_callback)
        return self._reminders

    @staticmethod
    def _parse_clock_time(text):
        """Hora absoluta ('a las 7', '7:30', '7 am', '7 de la tarde') → segundos
        hasta esa hora (hoy si es futura, mañana si ya pasó). None si no hay hora."""
        import re as _r
        import datetime as _dt
        t = (text or "").lower()
        m = _r.search(
            r"(?:a\s+la[s]?\s+)?\b(\d{1,2})(?::(\d{2}))?\s*"
            r"(a\.?m\.?|p\.?m\.?|de\s+la\s+ma[ñn]ana|de\s+la\s+tarde|"
            r"de\s+la\s+noche|hs|hrs|h)?\b", t)
        if not m:
            return None
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        suf = (m.group(3) or "").replace(".", "").strip()
        if suf in ("pm", "de la tarde", "de la noche") and hh < 12:
            hh += 12
        if suf in ("am", "de la mañana") and hh == 12:
            hh = 0
        if hh > 23 or mm > 59:
            return None
        now = _dt.datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target += _dt.timedelta(days=1)
        return int((target - now).total_seconds())

    def _detect_device_control(self, inp, user_input):
        """Control de dispositivos/sistema: volumen, energía, brillo, WiFi/BT/USB,
        Chromecast/cast y multi-monitor. Devuelve str (resultado) o None si no aplica.
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # === CONTROL DEL SISTEMA (volumen / energía / brillo / bloqueo) ===
        from core import system_control as _sc
        # Confirmación pendiente de acción destructiva (apagar/reiniciar)
        _pp = getattr(self, "_pending_power", None)
        if _pp and _re.search(r"^\s*(s[íi]|confirm[áo]?|dale|hacelo|ok|de una)\s*$", inp):
            self._pending_power = None
            return getattr(_sc, _pp)()
        if _pp and _re.search(r"^\s*(no|cancel[áa]r?|dejalo|olvidalo)\s*$", inp):
            self._pending_power = None
            return "Listo, cancelé eso."
        # VOLUMEN
        _mvol = _re.search(r"\bvolumen\s+(?:al?\s+)?(\d{1,3})", inp)
        if _mvol:
            return _sc.set_volume(int(_mvol.group(1)))
        if _re.search(r"\b(sub[íie]\w*|aument\w*|m[áa]s)\b.*\bvolumen\b", inp) or \
           _re.search(r"\bvolumen\b.*\b(arriba|m[áa]s alto|fuerte)\b", inp):
            return _sc.volume_up()
        if _re.search(r"\b(baj[áae]\w*|disminu\w*|menos)\b.*\bvolumen\b", inp) or \
           _re.search(r"\bvolumen\b.*\b(abajo|m[áa]s bajo)\b", inp):
            return _sc.volume_down()
        if _re.search(r"\b(silenci[áa]r?|mute[áa]r?|mute[ao]|sin sonido)\b", inp) and \
           not any(w in inp for w in ("musica", "música", "cancion", "canción",
                                      "reproduc", "tema")):  # no chocar con pausa de música
            return _sc.volume_mute()
        # BRILLO
        _mbri = _re.search(r"\bbrillo\s+(?:al?\s+)?(\d{1,3})", inp)
        if _mbri:
            return _sc.set_brightness(int(_mbri.group(1)))
        # ENERGÍA
        if _re.search(r"\b(bloque[áa]r?|lock|trab[áa])\b.*\b(pc|compu|computadora|pantalla|sistema|sesi[óo]n)\b", inp) \
           or inp.strip() in ("bloquea", "bloqueá", "bloquear pc", "lock"):
            return _sc.lock()
        if _re.search(r"\b(suspend[ée]r?|dorm[íi]|hibern[áa]r?|modo\s+suspensi[óo]n)\b", inp) \
           and ("pc" in inp or "compu" in inp or "sistema" in inp or "computadora" in inp):
            return _sc.sleep()
        if _re.search(r"\bcancel[áa]r?\b.*\b(apagado|reinicio|apagar|reiniciar)\b", inp):
            return _sc.cancel_shutdown()
        if _re.search(r"\b(cerr[áa]r?\s+(la\s+)?sesi[óo]n|log\s*off|logoff)\b", inp):
            return _sc.logoff()
        if _re.search(r"\b(apag[áa]r?|apaga)\b.*\b(pc|compu|computadora|sistema|equipo|m[áa]quina)\b", inp):
            self._pending_power = "shutdown"
            return "🔌 ¿Seguro que apago la PC? Decime «sí» para confirmar o «no» para cancelar."
        if _re.search(r"\b(reinici[áa]r?|reinicia|reset)\b.*\b(pc|compu|computadora|sistema|equipo|m[áa]quina)\b", inp):
            self._pending_power = "restart"
            return "🔄 ¿Seguro que reinicio la PC? Decime «sí» para confirmar o «no» para cancelar."
        # IMPRESORAS (listar) — el "imprimí X" se maneja en la sección de archivos
        if _re.search(r"\b(qu[ée]\s+impresoras?|impresoras?\s+(hay|tengo|disponibles|"
                      r"instaladas)|list[áa]r?\s+impresoras|mis\s+impresoras)\b", inp):
            return _sc.list_printers()

        # === CONEXIONES: WiFi / Bluetooth / USB ===
        from core import connections as _cx
        # WiFi: encender/apagar
        if _re.search(r"\b(apag[áa]r?|desactiv[áa]r?|prend[ée]r?|encend[ée]r?|activ[áa]r?)\b.*\bwifi\b", inp) \
                or _re.search(r"\bwifi\b.*\b(on|off)\b", inp):
            _on = bool(_re.search(r"\b(prend[ée]|encend[ée]|activ[áa])", inp) or _re.search(r"\bon\b", inp))
            return _cx.wifi_toggle(_on)
        # WiFi: conectar a una red
        _wc = _re.search(r"\bconect[áa]r?(?:te|me)?\s+a(?:l)?\s+(?:la\s+)?(?:red\s+|wifi\s+)?(.+)$", inp)
        if _wc and ("wifi" in inp or "red" in inp):
            ssid = _wc.group(1).strip().rstrip(".?!").strip('"\'')
            return _cx.wifi_connect(ssid)
        # WiFi: listar redes
        if _re.search(r"\b(redes?\s+wifi|wifi\s+(disponibles?|cercan|que hay)|"
                      r"escane[áa]r?\s+wifi|list[áa]r?\s+(redes|wifi)|qu[ée]\s+redes)\b", inp):
            return _cx.wifi_list()
        # Bluetooth: encender/apagar
        if _re.search(r"\b(apag[áa]r?|desactiv[áa]r?|prend[ée]r?|encend[ée]r?|activ[áa]r?)\b.*\b(bluetooth|bt)\b", inp):
            _on = bool(_re.search(r"\b(prend[ée]|encend[ée]|activ[áa])", inp))
            return _cx.bluetooth_toggle(_on)
        # Bluetooth: listar
        if _re.search(r"\b(dispositivos?\s+bluetooth|bluetooth\s+(conectados?|emparejados?|que hay)|"
                      r"qu[ée]\s+bluetooth|list[áa]r?\s+bluetooth|mis?\s+bluetooth)\b", inp):
            return _cx.bluetooth_list()
        # USB: expulsar
        _ue = _re.search(r"\b(expuls[áa]r?|sac[áa]r?|desconect[áa]r?|extrae?r?)\b.*\b(usb|pendrive|"
                         r"unidad)\b\s*([a-zA-Z])?", inp)
        if _ue and _re.search(r"\b(usb|pendrive)\b", inp) and \
           _re.search(r"\b(expuls|sac|desconect|extrae)", inp):
            _dl = _re.search(r"\b([d-zD-Z]):?\b(?:\s|$)", inp)
            if _dl:
                return _cx.usb_eject(_dl.group(1))
            return "🔌 ¿Qué unidad USB expulso? Decime la letra (ej: E)."
        # USB: listar
        if _re.search(r"\b(dispositivos?\s+usb|usb\s+(conectados?|que hay)|qu[ée]\s+usb|"
                      r"unidades?\s+usb|pendrives?)\b", inp):
            return _cx.usb_list()

        # === SALIDA DE AUDIO (dispositivo de reproducción por defecto) ===
        if (_re.search(r"\b(salida\s+de\s+(audio|sonido)|dispositivos?\s+de\s+salida|"
                       r"salidas?\s+de\s+audio)\b", inp)
                or _re.search(r"\bsalida\s+[a-záéíóúñ0-9]+", inp)
                or _re.search(r"\b(audio|sonido)\s+(en|a|al|por)\b", inp)
                or _re.search(r"\b(jbl|logitech)\b", inp)):
            from core import audio_output as _ao
            _devkey = _re.search(r"\b(jbl|logitech|philips|flip|tune|realtek|nvidia|"
                                 r"parlante|altavoz|altavoces|auricular\w*|monitor|"
                                 r"g27|digital|koshi)\b", inp)
            _islist = _re.search(r"\b(qu[ée]|cu[áa]les|list\w*|mostr\w*|cu[áa]nt\w*)\b",
                                 inp)
            if _islist and not _devkey:
                return _ao.list_text()
            return _ao.set_output(inp)

        # === SEGURIDAD DEL SISTEMA (Defender/Firewall/UAC/updates) ===
        if _re.search(r"\bseguridad\b", inp) and _re.search(
                r"\b(sistema|pc|computadora|compu|equipo|defender|firewall|"
                r"antivirus|revis\w*|chequ\w*|verific\w*|estado|escane\w*|"
                r"analiz\w*|audit\w*)\b", inp):
            from core import security_check as _sec
            return _sec.check()

        # === CHROMECAST / CAST a la TV ===
        _is_cast = bool(_re.search(r"\b(chromecast|chrome\s*cast|caste\w*|transmit\w*|cast|"
                                   r"tv|tele|televisi[óo]n|pantalla\s+grande|dormitorio)\b", inp))
        if _is_cast and "netflix" in inp:
            # Netflix → Chromecast vía NAVEGADOR (Chrome cast), no pychromecast.
            from core import netflix as _nf
            from core import casting as _ct
            import time as _tm
            # resolver dispositivo destino (nombre real del Chromecast)
            _known = _ct._CACHE.get("devices") or _ct.discover()
            _dev = None
            for _d in _known:
                for _w in _d["name"].lower().split():
                    if len(_w) > 3 and _w in inp:
                        _dev = _d["name"]
                        break
                if _dev:
                    break
            if not _dev and _known:
                _dev = _known[0]["name"]
            # ¿pidió reproducir un título antes de castear?
            _pm2 = _re.search(r"perfil\s+(?:de\s+)?([a-záéíóúñ0-9]+)", inp)
            _prof2 = _pm2.group(1).strip() if _pm2 else None
            _pl2 = _re.search(r"(?:repro\w*|pon[ée]r?|mir[áa]r?|ve[ar]?|pas[áa]r?)\s+"
                              r"(?:a\s+|la\s+|el\s+)?(?:pel[íi]cula\s+|serie\s+)?"
                              r"(.+?)\s+en\s+netflix", inp)
            _q2 = _pl2.group(1).strip() if _pl2 else ""
            _q2 = "" if _q2 in ("algo", "una", "una pelicula", "una película",
                                "una serie") else _q2
            # Preferir la APP (logueada como Alex) → castea sin pedir login extra.
            if _nf.app_installed():
                _res = _nf.cast_app(_dev)
                if _q2:
                    _res += (f"\nℹ️ En la app no puedo buscar «{_q2}» por código — ponelo "
                             f"vos en la app y casteo lo que estés viendo.")
                return _res
            # app no instalada → vía Chrome (puede pedir login 1 vez)
            if _q2:
                _r = _nf.play(_q2, _prof2)
                if _r.startswith("[ERROR]") or "iniciar sesión" in _r or "no encontré" in _r.lower():
                    return _r
                _tm.sleep(5)
                return _nf.cast(_dev)
            return _nf.cast(_dev)
        if _is_cast:
            from core import casting as _ct
            # Identificar / listar
            if _re.search(r"\b(identific[áa]r?|busc[áa]r?|detect[áa]r?|encontr[áa]r?|"
                          r"list[áa]r?|qu[ée]|hay|tengo|dispositivos?\s+(de\s+)?cast)\b", inp) \
               and not _re.search(r"\b(reproduc|caste|mand[áa]|tir[áa]|pon[ée]|deten|par[áa]|volumen)\b", inp):
                return _ct.list_devices()
            # Detener
            if _re.search(r"\b(deten[ée]r?|par[áa]r?|fren[áa]r?|cort[áa]r?|stop)\b", inp):
                return _ct.cast_stop()
            # Volumen del cast
            _cv = _re.search(r"\bvolumen\b.*?(\d{1,3})", inp)
            if _cv and _re.search(r"\b(chromecast|tv|tele)\b", inp):
                return _ct.cast_volume(int(_cv.group(1)))
            # Castear contenido (YouTube)
            _cm = _re.search(r"(?:caste\w*|repro\w*|pon[ée]|mand[áa]r?|tir[áa]r?|"
                             r"mostr[áa]r?|mir[áa]r?)\s+(.+?)\s+(?:en|a|al|por)\s+"
                             r"(?:el\s+|la\s+)?(?:chromecast|tv|tele|televisi[óo]n)", inp)
            if _cm:
                _cq = _cm.group(1).strip().rstrip(".?!")
                if _cq and _cq not in ("algo", "musica", "música", "un video", "una pelicula"):
                    return _ct.cast_youtube(_cq)
                return "📺 ¿Qué te casteo a la TV? Decime el tema o video."

        # NETFLIX: SIEMPRE la app de la Store (decisión del usuario, 2026-06-12).
        #   Una sola Netflix → nunca abre dos. La app no busca por código (WebView
        #   no automatizable) → si pide un título, abre la app y avisa.
        if "netflix" in inp:
            from core import netflix as _nf
            # pausar/reanudar/detener → sobre la app
            if _re.search(r"\b(pausa|pausá|pausar|reanud[áa]r?|deten[ée]r?|par[áa]r?|"
                          r"fren[áa]r?|cort[áa]r?)\b", inp):
                return _nf.app_playpause()
            # ¿mencionó un título?
            _pl = _re.search(r"(?:repro\w*|pon[ée]r?|mir[áa]r?|ve[ar]?|pas[áa]r?|busc[áa]r?|"
                             r"dale?\s+play)\s+(?:a\s+|la\s+|el\s+)?"
                             r"(?:pel[íi]cula\s+|serie\s+)?(.+?)\s+en\s+netflix", inp)
            _qp = _pl.group(1).strip() if _pl else ""
            _qp = "" if _qp in ("algo", "una", "una pelicula", "una película",
                                "una serie", "peliculas", "películas") else _qp
            _r = _nf.launch_app()
            if _qp:
                _r += (f"\nℹ️ Buscá **{_qp}** en la app y dale play (dentro de la app no "
                       f"puedo buscar por código). ¿Querés que la castee a la TV?")
            return _r

        # ABRIR EN OTRA PANTALLA (multi-monitor): "poné netflix en la segunda pantalla"
        if _re.search(r"\b(segunda|2da|otra|secundaria|primera|1ra|tercera|3ra)\s+pantalla\b", inp) \
                or _re.search(r"\b(pantalla|monitor)\s*([123])\b", inp):
            scr = 2
            _mn = _re.search(r"\b(?:pantalla|monitor)\s*([123])\b", inp)
            if _mn:
                scr = int(_mn.group(1))
            elif _re.search(r"\b(primera|1ra)\s+pantalla\b", inp):
                scr = 1
            elif _re.search(r"\b(tercera|3ra)\s+pantalla\b", inp):
                scr = 3
            _STREAM = {
                "youtube music": "https://music.youtube.com",
                "netflix": "https://www.netflix.com",
                "youtube": "https://www.youtube.com",
                "disney": "https://www.disneyplus.com",
                "prime video": "https://www.primevideo.com",
                "prime": "https://www.primevideo.com",
                "hbo max": "https://www.max.com", "hbo": "https://www.max.com",
                "max": "https://www.max.com", "twitch": "https://www.twitch.tv",
                "crunchyroll": "https://www.crunchyroll.com",
            }
            _url = None
            for k in sorted(_STREAM, key=len, reverse=True):
                if k in inp:
                    _url = _STREAM[k]
                    # Netflix + nombre de peli → búsqueda
                    if k == "netflix":
                        _mfx = (_re.search(r"(?:repro\w*|pon[ée]|mir[áa]|ve[ar]?|pas[áa]|busc[áa])\s+(?:la\s+|el\s+)?(?:pel[íi]cula\s+|serie\s+)?(.+?)\s+en\s+netflix", inp)
                                or _re.search(r"netflix\s+(.+?)\s+(?:en|a)\s+(?:la\s+)?(?:segunda|2|otra|primera|tercera|pantalla|monitor)", inp))
                        _q = _mfx.group(1).strip() if _mfx else ""
                        if _q and _q not in ("una", "una pelicula", "una película",
                                             "algo", "peliculas", "películas", "una serie"):
                            import urllib.parse as _up
                            _url = "https://www.netflix.com/search?q=" + _up.quote(_q)
                    break
            if not _url:
                _du = _re.search(r"https?://\S+", user_input)
                _url = _du.group(0) if _du else None
            if _url:
                return _sc.open_on_screen(_url, scr)
            return ("¿Qué abro en esa pantalla? Decime el servicio (Netflix, YouTube…) "
                    "o una URL.")

        return None

    def _detect_email(self, inp, user_input):
        """Email: enviar (SMTP) y leer bandeja (IMAP). Devuelve str o None.
        Extraído de _auto_detect_tool (Fase 2)."""
        import re as _re
        # --- EMAIL: enviar correo (capacidad de red concedida por humano) ---
        # Confirmación en 2 pasos: 1) "enviá email a X que diga Y" → muestra y pide
        # confirmar; 2) "sí/confirmá/dale" → envía. Acción hacia afuera.
        _pend = getattr(self, "_pending_email", None)
        if _pend and _re.search(r'^\s*(s[íi]|confirm[áo]?|dale|envialo|envíalo|'
                                r'manda(lo)?|s[íi]\s+envia|ok|de una)\s*$', inp):
            from core import email_sender as _es
            r = _es.send_email(_pend["to"], _pend.get("subject", "Mensaje de Genesis"),
                               _pend["body"])
            self._pending_email = None
            return ("📧 " + r["message"]) if r.get("ok") else ("⚠️ " + r["message"])
        if _pend and _re.search(r'^\s*(no|cancel[áa]r?|dejalo|olvidalo)\s*$', inp):
            self._pending_email = None
            return "Listo, cancelé el envío del email."
        if _re.search(r'\b(envi[áa]r?|mand[áa]r?|escrib[íi]r?)\b.*\b(e?-?mail|correo)\b', inp) \
                or _re.search(r'\b(e?-?mail|correo)\b.*\ba\s+\S+@\S+', inp):
            _addr = _re.search(r'[\w.\-+]+@[\w.\-]+\.\w+', user_input)
            if not _addr:
                return "¿A qué dirección de email te lo envío? Decime el correo."
            to = _addr.group(0)
            # cuerpo: comillas, o tras "que diga/diciendo/con el mensaje/con el texto"
            _bm = _re.search(r'["“]([^"”]+)["”]', user_input)
            if _bm:
                body = _bm.group(1)
            else:
                _bm2 = _re.search(r'(?:que\s+diga|diciendo|con\s+el\s+mensaje|'
                                  r'con\s+el\s+texto|mensaje:?)\s+(.+)$',
                                  user_input, _re.IGNORECASE)
                body = _bm2.group(1).strip() if _bm2 else ""
            _sm = _re.search(r'(?:con\s+asunto|asunto:?)\s+["“]?([^"”\n]+)', user_input, _re.IGNORECASE)
            subject = _sm.group(1).strip() if _sm else "Mensaje de Genesis"
            if not body:
                return f"¿Qué mensaje le mando a {to}? Decime el texto (ej: que diga «hola»)."
            from core import email_sender as _es
            if not _es.is_configured():
                return ("📧 Tengo todo listo para enviarlo, pero falta configurar el email: "
                        "generá un App Password de Gmail y poné GMAIL_USER y "
                        "GMAIL_APP_PASSWORD en el .env. Después repetí el pedido.")
            self._pending_email = {"to": to, "subject": subject, "body": body}
            return (f"📧 ¿Confirmás el envío?\n  Para: {to}\n  Asunto: {subject}\n  "
                    f"Mensaje: «{body}»\nDecime «sí» para enviar o «no» para cancelar.")

        # --- EMAIL: leer bandeja de entrada (IMAP) ---
        if (_re.search(r'\b(le[ée]r?|leeme|revis[áa]r?|chec(?:k|que[áa]r?)|mostr[áa]r?|'
                       r'fij[áa]te|tengo)\b.*\b(correos?|emails?|e-?mails?|mails?|'
                       r'bandeja|casilla)\b', inp)
                or _re.search(r'\b(correos?|emails?|mails?)\s+(nuevos?|sin\s+leer|recientes?)', inp)
                or inp.strip() in ("mis correos", "mis emails", "mis mails", "leer correos")):
            from core import email_reader as _er
            if not _er.is_configured():
                return ("📬 Para leer correos necesito credenciales IMAP. Si querés leer "
                        "TU casilla, generá un App Password de alexq2005@gmail.com y poné "
                        "GMAIL_READ_USER + GMAIL_READ_APP_PASSWORD en el .env.")
            _unread = bool(_re.search(r'\b(nuevos?|sin\s+leer|no\s+le[íi]dos?)\b', inp))
            _r = _er.read_inbox(limit=5, unread_only=_unread)
            if not _r.get("ok"):
                return "⚠️ " + _r["message"]
            ems = _r.get("emails", [])
            if not ems:
                return f"📭 No tenés correos {'nuevos' if _unread else 'recientes'} en {_r.get('account','')}."
            out = [f"📬 Últimos {len(ems)} correos de {_r.get('account','')}:\n"]
            for i, e in enumerate(ems, 1):
                snip = (e.get("snippet", "") or "").replace("\n", " ")[:120]
                out.append(f"{i}. De: {e.get('from','')[:45]}\n   📌 {e.get('subject','')[:70]}"
                           + (f"\n   « {snip} »" if snip else ""))
            return "\n".join(out)

        return None

    def _detect_media_playback(self, inp, user_input):
        """Reproducción de música/video: pausar, reanudar, detener y reproducir.
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # --- Control de reproducción: pausar / reanudar / cerrar (ANTES del play) ---
        _re2 = __import__("re")
        _obj = (r"(m[úu]sica|cancion|canci[óo]n|tema|reproducci[óo]n|reproductor|player|"
                r"video|sonido|audio|lo que estabas|la que estabas)")
        def _media(fn):
            # Control de la app de YouTube Music vía tecla multimedia / cierre.
            try:
                from core import music_player as _mpc
                getattr(_mpc, fn)()
            except Exception:
                pass
        # SIGUIENTE / ANTERIOR canción
        if _re2.search(r"\b(siguiente|próxim[ao]|proxim[ao]|pasa(?:la)?|"
                       r"otra)\b.*(cancion|canci[óo]n|tema|m[úu]sica)", inp) \
                or inp.strip() in ("siguiente", "próxima", "proxima", "pasala", "next"):
            _media("media_next")
            return "⏭️ Siguiente tema."
        if _re2.search(r"\b(anterior|previa|volv[ée]|atr[áa]s)\b.*(cancion|canci[óo]n|tema|m[úu]sica)", inp) \
                or inp.strip() in ("anterior", "previa", "atrás", "atras", "prev"):
            _media("media_prev")
            return "⏮️ Tema anterior."
        # REANUDAR / continuar (tecla play/pause + marcador de cabina)
        if (_re2.search(r"\b(continu[áa]|segu[íi]|reanud[áa]|resum[íi]|retom[áa])\b", inp)
                and _re2.search(_obj, inp)) or inp.strip() in (
                "continua", "continuá", "segui", "seguí", "dale", "reanuda",
                "reanudá", "resume", "segui dale", "dale play"):
            _media("media_playpause")
            return "▶️ Sigo donde quedó.\n[[RESUME]]"
        # CERRAR el reproductor (cierra la ventana de YouTube Music + marcador)
        if _re2.search(r"\b(cerr[áa]|sac[áa]|quit[áa]|saca|cerrar)\b.*" + _obj, inp) \
                or _re2.search(r"\bcerr[áa]\s+(el\s+)?reproductor\b", inp):
            _media("stop_app")
            return "⏹️ Cierro el reproductor.\n[[STOP]]"
        # PAUSAR (resumible) — "detené/pará/pausá la música"
        _pause_re = _re2.search(
            r"\b(deten[ée]r?|par[áa]|fren[áa]|stop|basta|pausa|paus[áa]|"
            r"silenci[oa]|c[áa]llate)\b.*" + _obj, inp)
        if _pause_re or inp.strip() in (
                "stop", "basta", "pará", "para", "silencio", "callate",
                "cállate", "pausa", "pausá", "pausalo"):
            _media("media_playpause")
            return "⏸️ Pausado. Decime 'continuá' para seguir.\n[[PAUSE]]"

        # --- Reproducir música/video (ANTES del open genérico, que lo rompía) ---
        _music_verbs = ["reproduce ", "reproducí ", "reproduci ", "reproducir ",
                        "reproducime ", "reproduzca ", "reproduzca ", "pone ", "poné ",
                        "pon ", "poner ", "ponme ", "poneme ", "ponémela ", "pasame ",
                        "escuchar ", "escucha ", "escuchá ", "quiero escuchar ",
                        "quiero oir ", "play "]
        if any(inp.startswith(v) or f" {v}" in inp for v in _music_verbs) and \
           not any(w in inp for w in ("pomodoro", "temporizador", "cronometro",
                                      "cronómetro", "recordatorio", "despertador",
                                      "alarma")):
            import re as _mre, urllib.parse as _up, webbrowser as _wb
            q = inp
            for v in _music_verbs:
                if q.startswith(v): q = q[len(v):]; break
                if f" {v}" in q: q = q.split(v, 1)[-1]; break
            # Detectar plataforma y limpiarla del query
            plat, base = "youtube_music", "https://music.youtube.com/search?q={}"
            if _mre.search(r"\bspotify\b", q):
                plat, base = "spotify", "https://open.spotify.com/search/{}"
            elif _mre.search(r"\byoutube music|youtube\s*music|yt\s*music\b", q):
                plat, base = "youtube_music", "https://music.youtube.com/search?q={}"
            elif _mre.search(r"\byoutube|yt\b", q):
                plat, base = "youtube", "https://www.youtube.com/results?search_query={}"
            # Quitar "en <plataforma>" y palabras de relleno
            q = _mre.sub(r"\s+(en|por|desde)\s+(youtube\s*music|youtube|yt\s*music|yt|spotify).*$", "", q, flags=_mre.I)
            q = _mre.sub(r"\b(la\s+canci[oó]n|el\s+tema|musica|música|cancion|canci[oó]n)\b", "", q, flags=_mre.I)
            q = q.strip().strip("\"'").rstrip(".,;!?").strip()
            if q:
                # Spotify: sin API/login no se puede autoreproducir → abrir búsqueda (honesto).
                if plat == "spotify":
                    try:
                        _wb.open(base.format(_up.quote(q)))
                        return (f"🎵 Te abrí la búsqueda de «{q}» en Spotify. Para "
                                f"reproducir un tema puntual automático necesito tu login "
                                f"de Spotify (su API). Dale play vos, o pedímelo en YouTube "
                                f"Music que ahí sí lo pongo a sonar solo.")
                    except Exception as e:
                        return f"[ERROR] No pude abrir Spotify: {e}"
                # PRIORIDAD: app de YouTube Music (PWA logueada del usuario).
                # Reproduce sin yt-dlp/cookies/anti-bot — es la YT Music real. La
                # cabina (stream propio) queda como fallback si no está Chrome/YTM.
                try:
                    from core import music_player as _mp
                    if _mp.ytmusic_available():
                        _r = _mp.play_in_app(q)
                        if _r.get("ok"):
                            _art = f" de {_r['uploader']}" if _r.get("uploader") else ""
                            _dur = _fmt = ""
                            try:
                                _s = int(_r.get("duration") or 0)
                                if _s:
                                    _dur = f" ({_s // 60}:{_s % 60:02d})"
                            except Exception:
                                pass
                            return (f"🎵 Reproduciendo **{_r['title']}**{_art}{_dur} "
                                    f"en YouTube Music.")
                        # si la app falló, seguimos al fallback de cabina
                except Exception:
                    pass

                # FALLBACK: búsqueda REAL + reproducción DENTRO de la cabina (stream).
                try:
                    from core.music_player import play as _play
                    res = _play(q, platform=("youtube" if plat == "youtube" else "youtube_music"),
                                open_browser=False)
                except Exception as e:
                    return f"[ERROR] No pude reproducir: {e}"

                if res.get("reason") == "not_found":
                    return (f"🔎 Busqué «{q}» en YouTube y no encontré nada que coincida. "
                            f"¿Lo escribí bien? Probá con el artista + nombre del tema.")
                if not res.get("ok"):
                    return (f"🔎 Encontré el tema pero no pude abrir el reproductor "
                            f"({res.get('detail', res.get('reason'))}).")

                tr = res["track"]
                artista = f" de {tr['uploader']}" if tr.get("uploader") else ""
                # Razonamiento: ¿el resultado coincide con lo pedido?
                if res["match"] >= 0.6:
                    razona = "Coincide con lo que pediste."
                elif res["match"] >= 0.3:
                    razona = "No estoy 100% seguro que sea exactamente ese, pero es el mejor match."
                else:
                    razona = "Ojo: el resultado no se parece mucho a lo que pediste, fijate si es."
                # El marcador [[PLAY:id]] lo lee el HUD para embeber el reproductor
                # DENTRO de la cabina. Si se usa fuera del HUD, queda como texto inocuo.
                return (f"🎵 Reproduciendo **{tr['title']}**{artista} ({res['duration_fmt']}). "
                        f"{razona}\n[[PLAY:{res['video_id']}]]")

        return None

    def _detect_capabilities(self, inp, user_input):
        """Capacidades de Genesis: voces disponibles, qué puede hacer, etc.
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # --- Capacidades de Genesis (voces, que puedes hacer, etc.) ---
        # NOTA: Estas secciones no requieren imports pesados, van primero para respuesta instantánea
        cap_keywords = ["cuantas voces", "cuántas voces", "que voces", "qué voces",
                        "cambiar la voz", "cambiar voz", "seleccionar voz",
                        "voces tienes", "voces tenes", "voces disponibles",
                        "una unica voz", "única voz", "una sola voz",
                        "solo una voz", "solo tienes una", "solo tenes una",
                        "no tienes voz", "no tenes voz", "cuantas voces",
                        "las voces", "tus voces", "elegir voz"]
        if any(k in inp for k in cap_keywords):
            return ("🎙️ VOCES DISPONIBLES\n\n"
                    "Tengo 3 motores de voz, todos elegibles desde el panel:\n"
                    "  • Clon XTTS — voz clonada local (ej. JARVIS latino)\n"
                    "  • 8 voces neurales edge-tts (acentos AR/ES/MX/US/CO)\n"
                    "  • Piper — voces neurales 100% offline\n\n"
                    "Para cambiar la voz:\n"
                    "  1. Tocá el ⚙️ engranaje (abajo a la derecha de la cabina)\n"
                    "  2. Elegí el tipo de voz y la velocidad\n"
                    "  3. ▶ PROBAR para escucharla · 💾 GUARDAR para aplicarla\n"
                    "  (se usa igual en la cabina y en el manos libres)\n\n"
                    "Importar más voces Piper (offline):\n"
                    "  python -m piper.download_voices <voz> --data-dir models/piper")

        cap_general = ["que puedes hacer", "qué puedes hacer", "que podes hacer", "qué podés hacer",
                       "cuales son tus capacidades", "que capacidades", "que sabes hacer",
                       "para que sirves", "que funciones tienes", "tus habilidades"]
        if (any(k in inp for k in cap_general)
                or _re.fullmatch(r"\s*(ayuda|help|men[uú]|comandos|/help)\.?\s*", inp)):
            from config import GENESIS_VERSION as _gv
            return (f"🧠 CAPACIDADES DE GENESIS v{_gv}\n\n"
                    "▸ 🎙️ VOZ MANOS LIBRES: decime «genesis ...» sin tocar nada (vosk + Whisper)\n"
                    "▸ 🗣️ VOZ: respondo hablando (clon XTTS / edge-tts / Piper) — configurable en ⚙️\n"
                    "▸ 👤 RECONOZCO TU VOZ: «entrená mi voz» → modo «solo mi voz» (voiceprint)\n"
                    "▸ 🌐 INTERNET: Buscar en la web, leer páginas, investigar temas\n"
                    "▸ 📄 DOCUMENTOS: Procesar PDF, DOCX, XLSX, CSV, TXT — resúmenes y extracción\n"
                    "▸ 📂 ARCHIVOS: Buscar, listar, organizar, mover, eliminar archivos\n"
                    "▸ 💻 SISTEMA: Info real de hardware (CPU, RAM, GPU, disco)\n"
                    "▸ 🚀 APPS: Abrir cualquier programa instalado (143 detectados automáticamente)\n"
                    "▸ 🌍 WEBS: Abrir sitios web (50+ mapeados + descubrimiento automático)\n"
                    "▸ 🐍 CÓDIGO: Crear y ejecutar scripts Python, proyectos completos\n"
                    "▸ 📋 PORTAPAPELES: Historial, búsqueda, monitoreo automático\n"
                    "▸ 📸 CAPTURAS: Tomar screenshots del escritorio\n"
                    "▸ 🔧 PROCESOS: Listar y administrar procesos del sistema\n"
                    "▸ 🗑️ PAPELERA: Ver y restaurar archivos eliminados\n"
                    "▸ 📝 NOTAS: Sistema de notas rápidas persistentes (nota: tu texto)\n"
                    "▸ ⏰ RECORDATORIOS: Temporizadores con notificación desktop\n"
                    "▸ 📶 RED: Estado de conexión, WiFi, ping, velocidad\n"
                    "▸ 🧹 MANTENIMIENTO: Limpiar temporales, DNS, ver uptime\n"
                    "▸ 🔤 TEXTO: Mayúsculas, base64, hash, contar palabras, extraer emails/URLs\n"
                    "▸ 🔄 UNIDADES: Convertir distancia, peso, temperatura, datos, tiempo\n"
                    "▸ 🍅 POMODORO: Timer de productividad con ciclos trabajo/descanso\n"
                    "▸ 🪟 VENTANAS: Mover, snap, tile, maximizar, minimizar ventanas por voz\n"
                    "▸ 🔍 LAUNCHER: Búsqueda unificada en apps, archivos, notas, clipboard\n"
                    "▸ ☀️ BRIEFING: Resumen diario del sistema, notas, motivación\n"
                    "▸ ⚡ MACROS: Grabar y ejecutar secuencias de comandos\n"
                    "▸ 📰 NOTICIAS: Titulares actuales («noticias» / «noticias de <tema>»)\n"
                    "▸ 🌤️ CLIMA: Tiempo actual y pronóstico\n"
                    "▸ 🛡️ SEGURIDAD: Chequeo de Defender, Firewall, UAC y updates\n"
                    "▸ 🔈 SALIDA DE AUDIO: Cambiar parlante/auricular por voz («salida jbl»)\n"
                    "▸ 🎬 MULTIMEDIA: Música (YouTube Music), Netflix, Chromecast\n"
                    "▸ 🎨 IMÁGENES: Generar imágenes localmente (Stable Diffusion en GPU)\n"
                    "▸ 🎮 JUEGOS: Lanzar juegos de Steam/Epic por voz («jugá <X>»)\n"
                    "▸ 📧 EMAIL: Enviar y leer correos (Gmail)\n"
                    "▸ 🧭 AGENTES: 6 especialistas coordinados que se auto-delegan\n"
                    "▸ 🧬 AUTO-EVOLUCIÓN: Aprender, mutar, evolucionar autónomamente")

        return None

    def _detect_datetime_sysinfo(self, inp, user_input):
        """Fecha, hora y datos básicos del sistema.
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # --- Fecha, Hora, Datos basicos del sistema (respuesta instantanea) ---
        import datetime as _dt
        _now = _dt.datetime.now()

        time_keywords = ["que hora es", "qué hora es", "hora actual", "dime la hora",
                         "que hora tenemos", "hora es"]
        if any(k in inp for k in time_keywords):
            return f"🕐 Son las **{_now.strftime('%H:%M:%S')}** del {_now.strftime('%d/%m/%Y')}"

        date_keywords = ["que dia es", "qué día es", "que fecha", "qué fecha",
                         "fecha actual", "fecha de hoy", "dia de hoy", "día de hoy",
                         "dame la fecha", "dime la fecha", "en que fecha",
                         "que dia estamos", "qué día estamos", "a cuanto estamos"]
        if any(k in inp for k in date_keywords):
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            d = _now
            return (f"📅 **{dias[d.weekday()]} {d.day} de {meses[d.month]} de {d.year}**\n"
                    f"Hora: {d.strftime('%H:%M:%S')}")

        # GUARDAR el nombre cuando el usuario lo dice ("mi nombre es Alex", "me llamo Alex", "soy Alex")
        import re as _ure
        _name_set = _ure.search(
            r"\b(?:mi nombre es|me llamo|llamame|llam[áa]me|dec[íi]me|soy)\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]{2,20})\b",
            inp)
        if _name_set and any(w in inp for w in ["nombre", "llamo", "llam", "soy", "decime", "dec"]):
            nombre = _name_set.group(1).strip().capitalize()
            # No confundir "soy X" con frases tipo "soy programador" — filtrar comunes
            _no_nombres = {"programador", "tu", "vos", "yo", "el", "la", "un", "una",
                           "feliz", "argentino", "nuevo", "humano", "genesis"}
            if nombre.lower() not in _no_nombres:
                try:
                    self.memory.long_term.remember(f"El nombre del usuario es {nombre}",
                                                   category="perfil_usuario", source="usuario")
                except Exception:
                    pass
                return f"👍 Listo, anotado. Te voy a llamar **{nombre}** de ahora en más."

        user_keywords = ["mi nombre de usuario", "mi usuario", "nombre de usuario",
                         "mi user", "mi username", "quien soy", "quién soy",
                         "como me llamo", "cómo me llamo", "mi nombre", "mi nombre real"]
        if any(k in inp for k in user_keywords):
            import os as _os
            username = _os.getenv("USERNAME", _os.getenv("USER", "desconocido"))
            hostname = _os.getenv("COMPUTERNAME", "desconocido")
            # Recordar el nombre que el usuario dijo (si lo guardó antes)
            nombre_real = ""
            try:
                for m in self.memory.long_term.memories:
                    if m.get("category") == "perfil_usuario" and "nombre del usuario es" in m.get("fact", ""):
                        nombre_real = m["fact"].split("es")[-1].strip()
            except Exception:
                pass
            if nombre_real:
                return (f"Sos **{nombre_real}** 😎 (cuenta de Windows: {username}, equipo {hostname}).")
            return (f"👤 **Usuario**: {username}\n"
                    f"💻 **Equipo**: {hostname}\n"
                    f"📁 **Home**: C:/Users/{username}\n"
                    f"_(Si querés que te llame por tu nombre, decime: «mi nombre es ...»)_")

        ip_keywords = ["mi ip", "cual es mi ip", "cuál es mi ip", "mi direccion ip",
                       "mi dirección ip", "ip local", "ip publica", "ip pública"]
        if any(k in inp for k in ip_keywords):
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except OSError:
                local_ip = "No disponible"
            hostname = socket.gethostname()
            result = f"🌐 **IP Local**: {local_ip}\n💻 **Hostname**: {hostname}"
            # Intentar obtener IP publica
            if "publica" in inp or "pública" in inp or "public" in inp:
                try:
                    import urllib.request
                    pub_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
                    result += f"\n🌍 **IP Pública**: {pub_ip}"
                except (OSError, ValueError):
                    result += "\n🌍 **IP Pública**: No se pudo obtener"
            return result

        return None

    def _detect_calculator(self, inp, user_input):
        """Calculadora: operaciones aritméticas.
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # --- Conversor de unidades (distancia, peso, temperatura) ---
        _cv = _re.search(r"([\d]+[.,]?\d*)\s*([a-záéíóú°]+)\s+(?:a|en|son|equivale[ns]?)"
                         r"\s+([a-záéíóú°]+)", inp)
        if _cv and ("convert" in inp or "cuant" in inp or " a " in inp):
            _U = {'km': 1000.0, 'kilometro': 1000.0, 'kilometros': 1000.0,
                  'kilómetro': 1000.0, 'kilómetros': 1000.0, 'm': 1.0, 'metro': 1.0,
                  'metros': 1.0, 'cm': 0.01, 'centimetro': 0.01, 'centimetros': 0.01,
                  'centímetro': 0.01, 'centímetros': 0.01, 'mm': 0.001,
                  'milla': 1609.34, 'millas': 1609.34, 'mi': 1609.34, 'pie': 0.3048,
                  'pies': 0.3048, 'ft': 0.3048, 'pulgada': 0.0254, 'pulgadas': 0.0254,
                  'in': 0.0254, 'yarda': 0.9144, 'yardas': 0.9144}
            _W = {'kg': 1000.0, 'kilo': 1000.0, 'kilos': 1000.0, 'kilogramo': 1000.0,
                  'kilogramos': 1000.0, 'g': 1.0, 'gramo': 1.0, 'gramos': 1.0,
                  'mg': 0.001, 'libra': 453.592, 'libras': 453.592, 'lb': 453.592,
                  'onza': 28.3495, 'onzas': 28.3495, 'oz': 28.3495,
                  'tonelada': 1e6, 'toneladas': 1e6}
            _T = {'c', 'celsius', 'f', 'fahrenheit', 'k', 'kelvin'}

            def _fmt(x):
                x = round(x, 4)
                return str(int(x)) if x == int(x) else str(x)
            try:
                _v = float(_cv.group(1).replace(",", "."))
                _fu = _cv.group(2).strip("°"); _tu = _cv.group(3).strip("°")
                if _fu in _T and _tu in _T:
                    _c = (_v if _fu[0] == 'c' else (_v - 32) * 5 / 9 if _fu[0] == 'f'
                          else _v - 273.15)
                    _o = (_c if _tu[0] == 'c' else _c * 9 / 5 + 32 if _tu[0] == 'f'
                          else _c + 273.15)
                    return (f"🔄 {_fmt(_v)}°{_fu[0].upper()} = "
                            f"**{_fmt(round(_o, 2))}°{_tu[0].upper()}**")
                for _tab in (_U, _W):
                    if _fu in _tab and _tu in _tab:
                        return (f"🔄 {_fmt(_v)} {_cv.group(2)} = "
                                f"**{_fmt(_v * _tab[_fu] / _tab[_tu])} {_cv.group(3)}**")
            except Exception:
                pass

        # --- Calculadora ---
        # Detectar expresiones matematicas simples
        math_keywords = ["cuanto es", "cuánto es", "calcula", "calculame", "calculá",
                         "resultado de", "cuanto da", "cuánto da"]
        if any(k in inp for k in math_keywords):
            # Extraer la expresion
            expr = inp
            for mk in math_keywords:
                if mk in expr:
                    expr = expr.split(mk, 1)[-1].strip()
                    break
            # Limpiar texto a expresion matematica
            expr = (expr.replace("x", "*").replace("×", "*").replace("÷", "/")
                    .replace("al cuadrado", "**2").replace("al cubo", "**3")
                    .replace("elevado a", "**").replace("^", "**")
                    .replace("raiz cuadrada de", "math.sqrt(").replace("raíz cuadrada de", "math.sqrt(")
                    .replace("por ciento de", "/100*").replace("% de", "/100*")
                    .replace(",", ".").strip().rstrip("?!."))
            # Solo permitir caracteres seguros
            import re as _re2
            if _re2.match(r'^[\d\s\+\-\*/\.\(\)math\.sqrtpiee]+$', expr.replace("math.sqrt(", "").replace(")", "")):
                try:
                    import math
                    # Cerrar parentesis abiertos
                    open_parens = expr.count("(") - expr.count(")")
                    if open_parens > 0:
                        expr += ")" * open_parens
                    result = eval(expr)
                    if isinstance(result, float):
                        # Formatear bonito
                        if result == int(result):
                            result = int(result)
                        else:
                            result = round(result, 6)
                    return f"🔢 **{expr}** = **{result}**"
                except (SyntaxError, NameError, TypeError, ValueError, ArithmeticError):
                    pass  # No es una expresion valida, continuar al LLM

        return None

    def _detect_identity(self, inp, user_input):
        """Identidad de Genesis (quién sos, tu nombre, etc.).
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # --- Identidad de Genesis ---
        identity_keywords = ["que modelo eres", "qué modelo eres", "como te llamas",
                             "cómo te llamas", "que eres", "qué eres", "tu nombre",
                             "que ia eres", "qué ia eres", "eres chatgpt", "eres gpt",
                             "eres gemini", "eres siri", "eres alexa", "eres cortana"]
        if any(k in inp for k in identity_keywords):
            from config import LLM_PROVIDER, LLM_MODELS, GENESIS_VERSION
            model = LLM_MODELS.get(LLM_PROVIDER, "desconocido")
            provider_names = {
                "ollama": "Ollama (modelo local)",
                "gemini": "Google Gemini API",
                "openai": "OpenAI API",
                "anthropic": "Anthropic API",
            }
            provider_display = provider_names.get(LLM_PROVIDER, LLM_PROVIDER)
            return (f"🧬 Soy **Genesis v{GENESIS_VERSION}** — IA autónoma de escritorio.\n\n"
                    f"▸ Motor actual: **{model}** via {provider_display}\n"
                    f"▸ Corro 100% en tu máquina (Windows 11 Pro)\n"
                    f"▸ Tengo acceso real a tu sistema: archivos, apps, hardware, internet\n"
                    f"▸ 22 voces TTS, STT por micrófono, memoria persistente\n"
                    f"▸ Creado para ser un asistente funcional sin fabulación")

        return None

    def _detect_builder_dev(self, inp, user_input, path_keywords):
        """Builder/desarrollo: instalar paquetes, procesar documentos, crear archivos/scripts/proyectos.
        Extraído de _auto_detect_tool (Fase 2 — descomposición del god-method)."""
        import re as _re
        # --- Instalar paquetes ---
        install_keywords = ["instala ", "instalame ", "instalar ", "instalá ",
                            "pip install", "npm install", "agrega el paquete ",
                            "necesito instalar", "quiero instalar"]
        if any(k in inp for k in install_keywords):
            # Extraer nombre del paquete
            package = ""
            for kw in install_keywords:
                if kw in inp:
                    package = inp.split(kw)[-1].strip().rstrip(".,;!?")
                    break

            if package:
                import subprocess as _sp
                # Detectar si es npm o pip
                if "npm" in inp or any(package.startswith(p) for p in ["react", "express", "next", "vue", "angular"]):
                    cmd = ["npm", "install", package]
                    pkg_type = "npm"
                else:
                    cmd = [sys.executable, "-m", "pip", "install", package]
                    pkg_type = "pip"

                if self.show_thinking:
                    print(f"  [Auto-Install: {pkg_type} install {package}]")

                try:
                    result = _sp.run(
                        cmd, capture_output=True, text=True, timeout=120,
                    )
                    output = result.stdout + result.stderr
                    success = result.returncode == 0

                    # Registrar en ActionTracker
                    try:
                        self.action_tracker.log_pip_install(package, success=success)
                    except (AttributeError, OSError):
                        pass

                    if success:
                        return (
                            f"Paquete '{package}' instalado exitosamente via {pkg_type}.\n\n"
                            f"{output[-500:]}"
                        )
                    else:
                        return (
                            f"Error instalando '{package}':\n{output[-800:]}"
                        )
                except _sp.TimeoutExpired:
                    return f"[TIMEOUT] La instalación de '{package}' tardó más de 2 minutos."
                except Exception as e:
                    return f"[ERROR] No se pudo instalar '{package}': {e}"

        # --- Procesar documento ---
        # Keywords que activan resumen nivel "study" (material de estudio)
        study_keywords = [
            "resumen para estudiar", "resumen de estudio", "resumen academico",
            "resumen para examen", "material de estudio", "resumen tipo estudio",
            "resumen con tablas", "resumen con datos", "resumen exhaustivo",
            "resumen completo para estudiar", "resumen detallado para estudiar",
            "quiero estudiar", "necesito estudiar", "para estudiar",
            "resumen con clasificaciones", "resumen con dosis",
            "resumen con definiciones", "resumelo para estudiar",
            "resumen tecnico", "resumen clinico", "resumen farmacologico",
            "resumen con formulas", "resumen con valores",
        ]
        is_study_request = any(k in inp for k in study_keywords)

        doc_keywords = ["analiza este documento", "analiza el documento", "procesa este documento",
                        "procesa el documento", "lee este pdf", "lee este archivo",
                        "resume este documento", "resumen de este", "resumir documento",
                        "resumir archivo", "que dice este", "que contiene este",
                        "extraer datos de", "extrae datos", "extrae entidades",
                        "extraer informacion de", "analiza este pdf", "lee este excel",
                        "procesa este pdf", "analiza el pdf", "lee el documento",
                        "resume el archivo", "resume este pdf", "resume este excel",
                        "realiza resumen", "realiza un resumen", "hazme un resumen",
                        "haz un resumen", "dame un resumen", "dame el resumen",
                        "resumelo", "resumen del documento", "resumen del pdf",
                        "resumen completo", "resumen mas completo", "resumen detallado",
                        "no procesa un resumen", "resumen incompleto",
                        "resume el pdf", "resume el documento", "resumir el pdf",
                        "resumir el documento", "genera un resumen", "genera resumen",
                        "necesito un resumen", "quiero un resumen", "quiero resumen"]
        if is_study_request or any(k in inp for k in doc_keywords):
            # Extraer ruta del archivo
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ \-]+\.\w{2,5}', user_input)
            if path_match:
                filepath = path_match.group(0)
                try:
                    if is_study_request and self.brain:
                        # Modo estudio: usar summarize_document con level="study"
                        summary = self.doc_processor.summarize_document(
                            filepath, brain=self.brain, level="study", is_text=False,
                        )
                        if summary and "[ERROR]" not in summary:
                            fname = os.path.basename(filepath)
                            return f"📄 **{fname}**\n\n📝 **Material de Estudio:**\n\n{summary}"
                        return summary
                    result = self.doc_processor.process(filepath, brain=self.brain)
                    if "error" not in result:
                        return result.get("formatted_output", str(result))
                    return f"[ERROR] {result['error']}"
                except Exception as e:
                    return f"[ERROR] Error procesando documento: {e}"
            elif hasattr(self, '_last_uploaded_doc') and self._last_uploaded_doc:
                # Sin ruta pero hay un documento recien subido — resumir con IA
                doc = self._last_uploaded_doc
                filename = doc.get("filename", "documento")
                pages = doc.get("pages", 0)
                words = doc.get("word_count", 0)

                # Obtener texto completo del cache del procesador
                doc_id = doc.get("doc_id", "")
                full_text = self.doc_processor.get_full_text(doc_id) if doc_id else ""

                if not full_text:
                    full_text = doc.get("summary", "")

                if not full_text.strip():
                    return f"📄 Documento **{filename}** procesado pero sin contenido de texto extraible."

                # Usar el sistema de resumen Map-Reduce del document_processor
                # Soporta documentos largos: chunking + resumen parcial + combinacion
                summary_level = "study" if is_study_request else "detailed"
                level_label = "Material de Estudio" if is_study_request else "Resumen"
                header = f"📄 **{filename}** ({pages} pag, {words} palabras)\n\n"

                if self.brain:
                    try:
                        summary = self.doc_processor.summarize_document(
                            full_text, brain=self.brain,
                            level=summary_level, is_text=True,
                        )
                        if summary and "[ERROR]" not in summary:
                            return header + f"📝 **{level_label}:**\n\n" + summary
                    except (AttributeError, OSError, ValueError):
                        pass

                # Fallback sin IA — vista previa del texto
                return header + f"📝 **Vista previa:**\n{full_text[:2000]}"

        # --- Crear archivo (Auto-Builder directo) ---
        create_file_keywords = ["crea un archivo", "crear un archivo", "crea archivo",
                                "creame un archivo", "haceme un archivo", "genera un archivo"]
        if any(k in inp for k in create_file_keywords):
            # Determinar ubicación
            target_dir = "" + _GX_HOME + "/Desktop"
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    target_dir = path
                    break

            # Extraer nombre de archivo si se menciona
            name_match = _re.search(r'(?:llamado|nombre|que se llame)\s+["\']?(\S+)["\']?', inp)
            file_ext = ".txt"
            if name_match:
                fname = name_match.group(1)
                if '.' not in fname:
                    fname += file_ext
            else:
                fname = "archivo_genesis.txt"

            # Extraer contenido — buscar después de "que diga", "con", "contenido"
            content = ""
            content_match = _re.search(
                r'(?:que diga|que contenga|con el texto|con contenido|con)\s+["\']?(.+?)["\']?\s*$',
                inp
            )
            if content_match:
                content = content_match.group(1).strip()
            if not content:
                content = "Archivo creado por Genesis"

            full_path = f"{target_dir}/{fname}"
            from core.tools import FileTools
            result = FileTools.write_file(full_path, content)
            self.metrics.log_tool_use("escribir")
            return f"Archivo creado: `{full_path}`\nContenido: {content}\n\n{result}"

        # --- ESTADO del build en background ---
        if _re.search(r'(termin[óo]\s+(el\s+)?build|c[óo]mo\s+va\s+(el\s+)?(build|desarrollo|'
                      r'proyecto)|estado\s+(del\s+)?(build|desarrollo)|listo\s+(el\s+)?(build|'
                      r'proyecto)|qu[ée]\s+pas[óo]\s+con\s+(el\s+)?(build|proyecto|desarrollo))', inp):
            st = getattr(self, "_build_status", None)
            if not st:
                return "No tengo ningún desarrollo en curso. Pedime «desarrollá una app que…»."
            if st.get("running"):
                return f"🔧 Todavía construyendo «{st['spec']}»… genero, ejecuto y corrijo. Dame un toque."
            r = st.get("result") or {}
            if r.get("success"):
                return (f"✅ Listo «{st['spec']}» — quedó FUNCIONANDO.\n"
                        f"📁 {r.get('project_dir','')}\n"
                        f"Archivos: {', '.join(r.get('files', []))}\n"
                        f"Salida real:\n{(r.get('output','') or '')[:400]}")
            return (f"⚠️ Construí «{st['spec']}» pero no quedó andando tras los intentos.\n"
                    f"📁 {r.get('project_dir','')}\n{(r.get('error','') or '')[:300]}")

        # --- DESARROLLO de código real (BuilderEngine en segundo plano) ---
        # genera → EJECUTA → lee el error real → corrige (qwen-coder, hasta 3 iters)
        if (_re.search(r'\b(desarroll[áa]r?|constru[íi]r?|program[áa]r?|cod(?:e|ific)[áa]r?)\b', inp)
                and _re.search(r'\b(app|aplicaci[óo]n|programa|script|juego|herramienta|'
                               r'bot|cli|calculadora|api|simulador|conversor|generador|'
                               r'analizador|scraper)\b', inp)):
            be = getattr(self, "builder_engine", None)
            if be is not None:
                spec = user_input.strip()
                import threading as _th
                self._build_status = {"running": True, "spec": spec[:70], "result": None}

                def _run_build(_spec=spec):
                    try:
                        _r = be.build(_spec, max_iters=3, run_timeout=30)
                        self._build_status = {"running": False, "spec": _spec[:70],
                                              "result": _r.to_dict()}
                    except Exception as _e:
                        self._build_status = {"running": False, "spec": _spec[:70],
                                              "result": {"error": str(_e)}}
                _t = _th.Thread(target=_run_build, daemon=True)
                _t.start()
                return (f"🔧 Arranqué a construir «{spec[:70]}». Lo hago en segundo plano: "
                        f"genero el código, lo EJECUTO y corrijo los errores reales (hasta "
                        f"3 intentos con qwen-coder). Preguntame «¿terminó el build?» en un "
                        f"rato y te paso el proyecto.")

        # --- Crear script/programa (Auto-Builder con LLM) ---
        create_code_keywords = ["crea un script", "crea un programa", "creame un script",
                                "genera un script", "crea un bot", "crea una app",
                                "programa que", "script que", "haceme un programa"]
        if any(k in inp for k in create_code_keywords):
            # Dejar que el LLM genere el código, pero marcar para auto-ejecución
            # El _auto_builder post-LLM se encargará de ejecutarlo
            pass  # Fall through al LLM con flag implícito

        # --- Crear carpeta con proyecto multi-archivo (Auto-Builder Multi-Step) ---
        create_project_keywords = ["crea en mi", "crea una carpeta", "crear carpeta", "nueva carpeta"]
        has_multiple_files = any(w in inp for w in ["archivos", "archivo", ".py", ".js", ".html", ".md", ".txt", ".css"])
        if any(k in inp for k in create_project_keywords):
            # Determinar carpeta base (portable: escritorio del usuario actual)
            base_dir = os.path.join(os.path.expanduser("~"), "Desktop").replace("\\", "/")
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    base_dir = path
                    break

            # Extraer nombre de carpeta (entre comillas, o después de "carpeta")
            folder_name = None
            quoted = _re.search(r'["\u201c]([^"\u201d]+)["\u201d]', user_input)
            if quoted:
                folder_name = quoted.group(1).strip()
            if not folder_name:
                name_match = _re.search(r'(?:carpeta|llamada|nombre)\s+(\S+)', inp)
                if name_match:
                    folder_name = name_match.group(1).strip('"\'')
            if not folder_name:
                folder_name = "proyecto_genesis"

            project_dir = f"{base_dir}/{folder_name}"
            import os as _os
            _os.makedirs(project_dir, exist_ok=True)
            results = [f"Carpeta creada: `{project_dir}`"]

            # Si hay archivos mencionados, usar LLM para generar contenido
            if has_multiple_files:
                # Pedir al LLM que genere los archivos como JSON estructurado
                file_prompt = (
                    f"El usuario quiere crear un proyecto en {project_dir}.\n"
                    f"Solicitud original: {user_input}\n\n"
                    f"Genera SOLO un JSON con los archivos a crear. Formato exacto:\n"
                    f'{{"files": [{{"name": "main.py", "content": "print(\'hola mundo\')"}}, '
                    f'{{"name": "utils.py", "content": "def suma(a, b):\\n    return a + b"}}]}}\n\n'
                    f"SOLO el JSON, nada más."
                )
                try:
                    import json as _json
                    llm_response = self.brain.think(
                        "Eres un generador de archivos. Responde SOLO con JSON valido.",
                        [{"role": "user", "content": file_prompt}],
                        temperature=0.3, max_tokens=2048,
                    )
                    # Extraer JSON de la respuesta
                    json_match = _re.search(r'\{[\s\S]*\}', llm_response)
                    if json_match:
                        file_data = _json.loads(json_match.group(0))
                        files_list = file_data.get("files", [])
                        from core.tools import FileTools
                        for f_info in files_list:
                            f_name = f_info.get("name", "")
                            f_content = f_info.get("content", "")
                            if f_name:
                                f_path = f"{project_dir}/{f_name}"
                                # Crear subdirectorio si es necesario
                                f_dir = _os.path.dirname(f_path)
                                if f_dir and not _os.path.exists(f_dir):
                                    _os.makedirs(f_dir, exist_ok=True)
                                FileTools.write_file(f_path, f_content)
                                results.append(f"  Archivo creado: `{f_name}`")
                                self.metrics.log_tool_use("escribir")
                        results.append(f"\nProyecto creado: {len(files_list)} archivos en `{project_dir}`")
                        # Auto-set workspace al proyecto creado
                        try:
                            self.workspace.set_path(project_dir)
                            results.append(f"Workspace configurado: `{project_dir}`")
                        except (AttributeError, OSError, ValueError):
                            pass
                        # Registrar en ActionTracker
                        try:
                            self.action_tracker.log_project_created(
                                project_dir,
                                [f.get("name", "") for f in files_list],
                            )
                        except (AttributeError, OSError):
                            pass
                    else:
                        results.append("[WARN] No pude parsear archivos del LLM — carpeta creada vacía")
                except Exception as e:
                    results.append(f"[ERROR] Generación de archivos: {e}")
            else:
                # Solo crear carpeta sin archivos
                results.append("Carpeta vacía lista para usar")

            return "\n".join(results)

        return None

    def _detect_file_ops(self, inp, user_input):
        """Manejo de archivos conversacional: imprimir, mover, copiar, renombrar,
        editar, eliminar (papelera), disco, leer, crear, info. Devuelve str o None.
        Extraído de _auto_detect_tool (Fase 2)."""
        import re as _re
        from core.device_tools import disk_analyzer, file_manager
        # === MANEJO DE ARCHIVOS conversacional (mover/copiar/renombrar/editar/borrar) ===

        # --- Imprimir documento ---
        if _re.search(r'\b(imprim[íi]r?|imprime|mand[áa]\s+a\s+imprimir|sac[áa]\s+(una\s+)?'
                      r'impresi[óo]n\s+de)\b', inp):
            from core import system_control as _scp
            _pm = _re.search(r'(?:imprim[íi]r?|imprime|imprimir|impresi[óo]n\s+de)\s+'
                             r'(?:el\s+|la\s+|un\s+|una\s+|archivo\s+|documento\s+|'
                             r'el\s+archivo\s+|el\s+documento\s+)?(.+)$', inp)
            if not _pm:
                return "¿Qué documento imprimo? Decime el nombre o la ruta."
            _pname = _pm.group(1).strip()
            # quitar "en la impresora X" del final si aparece
            _pr = None
            _prm = _re.search(r'\s+en\s+(?:la\s+impresora\s+)?(.+)$', _pname)
            src, err = _abs_or_resolve(_pname, allow_folder=False)
            if err:
                return err
            return _scp.print_document(src)

        # --- Mover archivo/carpeta ---
        _mv = _re.search(r'(?:mov[ée]r?|muev[ae]|mov[ée])\s+(?:el\s+|la\s+|los\s+|las\s+|'
                         r'mi\s+|archivo\s+|carpeta\s+)?(.+?)\s+(?:a|hacia|para|al|a la)\s+(.+)$', inp)
        if _mv and _re.search(r'\bmov', inp):
            src, err = _abs_or_resolve(_mv.group(1))
            if err:
                return err
            dst = _resolve_folder(_mv.group(2).strip()) or _mv.group(2).strip()
            return "📦 " + file_manager.move(src, dst)

        # --- Copiar archivo/carpeta ---
        _cp = _re.search(r'(?:copi[áa]r?|duplic[áa]r?)\s+(?:el\s+|la\s+|los\s+|las\s+|'
                         r'mi\s+|archivo\s+|carpeta\s+)?(.+?)\s+(?:a|hacia|para|al|en)\s+(.+)$', inp)
        if _cp and _re.search(r'\b(copi|duplic)', inp):
            src, err = _abs_or_resolve(_cp.group(1))
            if err:
                return err
            dst = _resolve_folder(_cp.group(2).strip()) or _cp.group(2).strip()
            return "📋 " + file_manager.copy(src, dst)

        # --- Renombrar archivo/carpeta ---
        _rn = _re.search(r'(?:renombr[áa]r?|camb[ií][áa]?\s+el\s+nombre\s+de)\s+'
                         r'(?:el\s+|la\s+|archivo\s+|carpeta\s+)?(.+?)\s+(?:a|por|como)\s+(.+)$', inp)
        if _rn and ("renombr" in inp or "nombre" in inp):
            src, err = _abs_or_resolve(_rn.group(1))
            if err:
                return err
            new_name = _rn.group(2).strip().strip('"\'').rstrip(".?!")
            return "✏️ " + file_manager.rename(src, new_name)

        # --- Editar archivo (buscar/reemplazar) ---
        if "reemplaz" in inp and (" por " in inp or " con " in inp):
            qs = _re.findall(r'["“]([^"”]+)["”]', user_input)
            _fm = (_re.search(r'\ben\s+(?:el\s+|la\s+)?(?:archivo\s+)?([^\s"]+\.\w+)', inp)
                   or _re.search(r'(?:edit[áa]r?|archivo)\s+([^\s"]+\.\w+)', inp))
            if len(qs) >= 2 and _fm:
                from core.tools import FileTools as _FT
                src, err = _abs_or_resolve(_fm.group(1), allow_folder=False)
                if err:
                    return err
                return "✏️ " + _FT.edit_file(src, qs[0], qs[1])
            if len(qs) < 2:
                return ('Para editar decime: reemplazá "texto viejo" por "texto nuevo" '
                        'en <archivo>. (Usá comillas en ambos textos.)')

        # --- Eliminar (SIEMPRE a la papelera — recuperable) ---
        # Acepta voseo con acento: borrá/eliminá/borralo, etc.
        _del_m = _re.search(r'\b(?:elimin[áa]r?|borr[áa]r?|elimin[áa]l[oa]|'
                            r'borr[áa]l[oa]|mand[áa]\s+a\s+la\s+papelera)\b\s*(.*)$', inp)
        if _del_m:
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\.\- ]+', user_input)
            if path_match:
                tp = path_match.group(0).strip()
            else:
                rest = _del_m.group(1).strip()
                if not rest:
                    return "¿Qué borro? Pasame el nombre o la ruta."
                tp, err = _abs_or_resolve(rest)
                if err:
                    return err
            if not tp:
                return "No entendí qué borrar. Pasame el nombre o la ruta."
            res = file_manager.delete(tp)
            if res.startswith("[ERROR]"):
                return res
            return ("🗑️ " + res +
                    "\n(Está en la papelera — lo podés recuperar si fue un error.)")

        # --- Disco / espacio ---
        disk_keywords = ["espacio en disco", "uso de disco", "cuanto espacio",
                         "archivos grandes", "que ocupa mas"]
        if any(k in inp for k in disk_keywords):
            return disk_analyzer.analyze()

        # --- Leer archivo ---
        read_keywords = ["lee ", "leer ", "muestra el contenido", "contenido del archivo",
                         "que dice el archivo", "abre el archivo"]
        if any(k in inp for k in read_keywords):
            from core.tools import FileTools
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                return FileTools.read_file(path_match.group(0))

        # --- Crear archivo ---
        create_file_keywords = ["crea un archivo", "crear archivo", "nuevo archivo",
                                "crea un documento", "crear documento"]
        if any(k in inp for k in create_file_keywords):
            # El LLM puede manejar esto con [TOOL:escribir] — no interceptar
            return ""

        # --- Info de archivo específico ---
        info_keywords = ["cuanto pesa", "tamaño de", "info de", "información de",
                         "detalles de"]
        if any(k in inp for k in info_keywords):
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                return file_manager.file_info(path_match.group(0))

        # =====================================================================
        # PHASE 19: Smart Productivity — Notas, Recordatorios, Red, Acciones
        # =====================================================================

        return None

    def _detect_fs_system_ops(self, inp, user_input):
        """Operaciones de archivos/sistema: listar, buscar, organizar, procesos, portapapeles, captura, papelera, duplicados, info del sistema.
        Extraído de _auto_detect_tool (Fase 2)."""
        import re as _re
        from core.device_tools import file_searcher, file_organizer, disk_analyzer, duplicate_finder, process_manager, clipboard_manager, screen_capture
        from core.tools import FileTools, SystemInfoTool
        # --- Listar archivos ---
        list_keywords = ["lista", "muestra", "que hay en", "archivos en", "que tiene",
                         "contenido de", "ver carpeta", "mostrar archivos", "que archivos"]
        path_keywords = _PATH_KEYWORDS

        if any(k in inp for k in list_keywords):
            target_path = None
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    target_path = path
                    break
            # Detectar ruta explicita
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                target_path = path_match.group(0)
            if target_path:
                return FileTools.list_directory(target_path)

        # --- Programas de inicio (antes de sistema para evitar false match) ---
        startup_keywords = ["programas de inicio", "inicio de windows", "startup",
                           "que se ejecuta al inicio", "arranque", "ejecutan al inicio"]
        if any(k in inp for k in startup_keywords):
            from core.device_tools import startup_manager as sm
            return sm.list_startup()

        # --- Info del sistema ---
        sys_keywords = ["mi sistema", "mi cpu", " ram ", "mi memoria", "mi gpu",
                        "mi disco", "mi hardware",
                        "que computadora", "que pc", "especificaciones", "specs",
                        "info del sistema", "informacion del sistema",
                        "caracteristicas del sistema", "características del sistema",
                        "del sistema operativo", "datos del sistema",
                        "que procesador", "que tarjeta", "que grafica",
                        "componentes del", "mi equipo", "mi computadora", "mi pc",
                        "mi procesador", "mi tarjeta", "info de hardware",
                        "dime de mi sistema", "dime del sistema", "cuanta ram",
                        "cuanto disco", "cuantos nucleos",
                        "system info", "hardware info",
                        # Variantes de "dame datos del sistema / actualiza datos"
                        "datos sobre mi sistema", "datos de mi sistema",
                        "datos actuales", "datos actualizados", "datos reales",
                        "actualiza los datos", "actualiza datos", "actualiza mi sistema",
                        "datos del equipo", "datos del pc", "datos de mi pc",
                        "resumen del sistema", "resumen de mi sistema",
                        "analiza mi sistema", "analizar mi sistema", "escanea mi sistema",
                        "obten datos", "obtener datos", "obtengas datos",
                        "sobre mi sistema", "de mi sistema"]
        if any(k in inp for k in sys_keywords):
            if "gpu" in inp or "grafica" in inp or "tarjeta" in inp:
                return SystemInfoTool.get_gpu_status()
            if "disco" in inp or "almacenamiento" in inp or "espacio" in inp:
                return disk_analyzer.analyze()
            return SystemInfoTool.get_system_info()

        # --- Buscar archivos ---
        search_keywords = ["busca archivo", "encuentra archivo", "buscar archivo",
                           "donde esta el archivo", "donde estan los archivos",
                           "encontrar archivo", "encontra archivo",
                           "busca archivos de ", "busca documentos de ",
                           "busca archivos sobre ", "busca documentos sobre ",
                           "busca en mis archivos ", "busca en mi pc ",
                           "busca en mi computadora ", "tenes algo de ",
                           "tenes archivos de ", "hay archivos de ",
                           "hay algo de ", "hay algo sobre "]
        # "busca X" genérico (solo si NO es busca web: "busca en internet/google/web")
        web_search_pattern = _re.search(r'\bbusca\b\s+(en\s+)?(internet|google|la\s+web|online|web)', inp)
        is_generic_search = (inp.startswith("busca ") or inp.startswith("buscá ") or
                             inp.startswith("buscame ") or inp.startswith("buscá ")) and not web_search_pattern

        if any(k in inp for k in search_keywords) or is_generic_search:
            # Extraer lo que buscan
            query = ""
            for kw in sorted(search_keywords, key=len, reverse=True):
                if kw in inp:
                    query = inp.split(kw)[-1].strip()
                    break
            if not query and is_generic_search:
                for prefix in ["buscame ", "buscá ", "busca "]:
                    if inp.startswith(prefix):
                        query = inp[len(prefix):].strip()
                        break
            # Limpiar preposiciones
            for prep in ["el ", "la ", "los ", "las ", "un ", "una ",
                         "mis ", "mi ", "de ", "sobre ", "llamado ", "llamada "]:
                if query.startswith(prep):
                    query = query[len(prep):]
            query = query.strip().rstrip(".,;!?")
            if query and len(query) >= 2:
                return file_searcher.search(query)

        # --- Organizar ---
        organize_keywords = ["organiza", "ordena", "clasifica", "organizar"]
        if any(k in inp for k in organize_keywords):
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    # Primero simular
                    return file_organizer.organize(path, dry_run=True)
            return ""

        # --- Procesos ---
        process_keywords = ["procesos", "que esta corriendo", "que esta ejecutando",
                           "programas abiertos", "apps abiertas", "tareas",
                           "que programas hay", "que apps hay", "que aplicaciones"]
        if any(k in inp for k in process_keywords):
            return process_manager.list_processes()

        # --- Cerrar proceso/app ---
        close_keywords = ["cierra ", "cerrar ", "cerrá ", "cerrame ", "ciérralo",
                          "mata ", "matá ", "termina ", "terminá ",
                          "cierra el ", "cierra la ", "cierra lo "]
        if any(inp.startswith(k) for k in close_keywords):
            # Extraer nombre del proceso
            proc_target = inp
            for kw in sorted(close_keywords, key=len, reverse=True):
                if proc_target.startswith(kw):
                    proc_target = proc_target[len(kw):].strip()
                    break
            # Limpiar prefijos comunes
            for prep in ["el ", "la ", "lo ", "programa ", "aplicación ", "aplicacion ",
                          "app ", "juego ", "proceso "]:
                if proc_target.startswith(prep):
                    proc_target = proc_target[len(prep):]
            proc_target = proc_target.strip().rstrip(".,;!?")
            if proc_target and len(proc_target) >= 2:
                # Mapear nombres comunes a nombres de proceso
                proc_map = {
                    "chrome": "chrome.exe", "google chrome": "chrome.exe",
                    "firefox": "firefox.exe", "edge": "msedge.exe",
                    "brave": "brave.exe", "opera": "opera.exe",
                    "discord": "Discord.exe", "telegram": "Telegram.exe",
                    "spotify": "Spotify.exe", "steam": "steam.exe",
                    "excel": "EXCEL.EXE", "word": "WINWORD.EXE",
                    "powerpoint": "POWERPNT.EXE", "outlook": "OUTLOOK.EXE",
                    "notepad": "notepad.exe", "notepad++": "notepad++.exe",
                    "obs": "obs64.exe", "obs studio": "obs64.exe",
                    "vlc": "vlc.exe", "vscode": "Code.exe",
                    "visual studio code": "Code.exe",
                    "dota 2": "dota2.exe", "dota": "dota2.exe",
                    "valorant": "VALORANT.exe", "league of legends": "LeagueClient.exe",
                    "fortnite": "FortniteClient-Win64-Shipping.exe",
                    "minecraft": "javaw.exe",
                }
                # Soportar multi-target: "cierra excel y word" → ["excel", "word"]
                targets = [t.strip() for t in _re.split(r'\s+y\s+|\s*,\s*', proc_target) if t.strip()]
                closed = []
                failed = []
                for t in targets:
                    exe_name = proc_map.get(t.lower(), t)
                    # Solo agregar .exe si no lo tiene ya
                    if not exe_name.lower().endswith(".exe"):
                        exe_name = exe_name + ".exe"
                    result = process_manager.kill_process(exe_name)
                    # Contar si cerró o no
                    display_name = t.capitalize()
                    if "correcto" in result.lower() or "terminó" in result.lower() or "termin" in result.lower():
                        closed.append(display_name)
                    elif "error" in result.lower() or "no se encontr" in result.lower():
                        failed.append(display_name)
                    else:
                        closed.append(display_name)
                # Respuesta limpia
                parts = []
                if closed:
                    parts.append(f"✅ {'Cerrado' if len(closed) == 1 else 'Cerrados'}: {', '.join(closed)}")
                if failed:
                    parts.append(f"❌ No encontrado: {', '.join(failed)}")
                return "\n".join(parts) if parts else "No se pudo cerrar ningún programa."

        # --- Verificar si app está abierta ---
        check_running_patterns = [
            r"(?:esta|está)\s+(?:abierto|abierta|corriendo|ejecutando|ejecutándose|activo|activa)\s+(.+)",
            r"(?:se\s+)?(?:esta|está)\s+(?:ejecutando|corriendo)\s+(.+)",
            r"(?:tengo|hay)\s+(?:abierto|abierta)\s+(.+)",
            r"(.+?)\s+(?:esta|está)\s+(?:abierto|abierta|corriendo|ejecutando)",
        ]
        for pattern in check_running_patterns:
            match = _re.search(pattern, inp)
            if match:
                check_name = match.group(1).strip().rstrip(".,;!? ")
                # Limpiar
                for prep in ["el ", "la ", "lo "]:
                    if check_name.startswith(prep):
                        check_name = check_name[len(prep):]
                if check_name and len(check_name) >= 2:
                    # Buscar en procesos reales
                    import subprocess
                    try:
                        result = subprocess.run(
                            ["tasklist", "/fo", "csv", "/nh"],
                            capture_output=True, text=True, timeout=10
                        )
                        procs = result.stdout.lower()
                        check_lower = check_name.lower().replace(" ", "")
                        # Buscar coincidencias
                        found = []
                        for line in procs.split("\n"):
                            parts = line.strip().strip('"').split('","')
                            if parts and len(parts) >= 2:
                                pname = parts[0].strip('"').lower()
                                if check_lower in pname or pname.replace(".exe", "").startswith(check_lower[:4]):
                                    found.append(parts[0].strip('"'))
                        if found:
                            unique = list(set(found))
                            return f"✅ Sí, '{check_name}' está corriendo.\nProcesos encontrados: {', '.join(unique[:5])}"
                        else:
                            return f"❌ No, '{check_name}' NO está corriendo actualmente."
                    except Exception as e:
                        return f"Error al verificar procesos: {e}"

        # --- Portapapeles ---
        clip_keywords = ["portapapeles", "clipboard", "que copie", "que tengo copiado"]
        if any(k in inp for k in clip_keywords):
            return clipboard_manager.read()

        # --- Captura ---
        capture_keywords = ["captura", "screenshot", "pantallazo", "foto de pantalla"]
        if any(k in inp for k in capture_keywords):
            return screen_capture.capture()

        # --- Papelera de reciclaje ---
        from core.device_tools import recycle_bin
        recycle_keywords = ["papelera", "reciclaje", "recycle", "eliminados recientemente"]
        if any(k in inp for k in recycle_keywords):
            if any(w in inp for w in ["vaciar", "limpiar", "vacia", "limpia"]):
                return recycle_bin.empty()
            return recycle_bin.list_items()

        # --- Restaurar de papelera ---
        restore_keywords = ["restaura", "recupera", "restaurar", "recuperar"]
        if any(k in inp for k in restore_keywords):
            from core.device_tools import recycle_bin as rb
            # Extraer nombre del archivo a restaurar
            # Buscar nombre entre comillas o después del keyword
            quoted = _re.search(r'["\'](.+?)["\']', user_input)
            if quoted:
                return rb.restore(quoted.group(1))
            # Extraer la última palabra significativa
            for kw in restore_keywords:
                if kw in inp:
                    rest = inp.split(kw)[-1].strip()
                    # Limpiar preposiciones
                    for prep in ["el ", "la ", "lo ", "los ", "las ", "al ", "del "]:
                        if rest.startswith(prep):
                            rest = rest[len(prep):]
                    if rest and len(rest) > 1:
                        return rb.restore(rest.strip())
            return "[ERROR] Especifica que archivo restaurar. Ejemplo: 'restaura GCC'"

        # --- Duplicados ---
        dup_keywords = ["duplicados", "archivos repetidos", "archivos duplicados"]
        if any(k in inp for k in dup_keywords):
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    return duplicate_finder.find(path)
            return duplicate_finder.find("" + _GX_HOME + "")

        # --- Helper: resolver nombre de carpeta a ruta ---




        # --- Refresco manual de índices (carpetas/programas) ---
        if (("reindex" in inp or "reescane" in inp or "actualiz" in inp or "refresc" in inp)
                and ("carpeta" in inp or "indice" in inp or "índice" in inp
                     or "programa" in inp)):
            try:
                msg = []
                if "programa" in inp or "indice" in inp or "índice" in inp:
                    from core import program_index as _pix
                    msg.append(f"{len(_pix.get_index(force=True))} programas")
                if "carpeta" in inp or "indice" in inp or "índice" in inp:
                    from core import folder_index as _fix
                    msg.append(f"{_fix.refresh()} carpetas")
                return "Índices actualizados: " + ", ".join(msg) + "."
            except Exception as e:
                return f"No pude actualizar los índices: {e}"

        # Email enviar/leer (extraído a _detect_email)
        _mail_r = self._detect_email(inp, user_input)
        if _mail_r is not None:
            return _mail_r

        return None

    def _detect_open_apps_folders(self, inp, user_input):
        """Abrir apps/sitios/carpetas y mostrar contenido de carpeta.
        Extraído de _auto_detect_tool (Fase 2)."""
        import re as _re
        from core.device_tools import app_launcher
        # --- Mostrar contenido de carpeta ---
        content_keywords = ["muestra contenido", "muestrame contenido", "muestra el contenido",
                           "muestra lo que hay", "que hay en ", "que tiene ",
                           "lista contenido", "listar contenido", "muestra la carpeta",
                           "muestrame la carpeta", "muestra los archivos",
                           "que archivos hay", "que archivos tiene", "listame ",
                           "contenido de ", "archivos de ", "archivos en "]
        if any(k in inp for k in content_keywords):
            # Extraer nombre de carpeta
            rest = inp
            for kw in sorted(content_keywords, key=len, reverse=True):
                if kw in rest:
                    rest = rest.split(kw)[-1].strip()
                    break
            # Limpiar preposiciones
            for prep in ["el ", "la ", "lo ", "los ", "las ", "mi ", "mis ", "de ", "en "]:
                if rest.startswith(prep):
                    rest = rest[len(prep):]
            rest = rest.strip().rstrip(".,;!?")
            if rest:
                folder_path = _resolve_folder(rest)
                if folder_path:
                    return _list_folder_contents(folder_path)
                return f"No encontré una carpeta llamada '{rest}'. Intenta con el nombre exacto o la ruta completa."

        # Reproducción de música/video: pausar, reanudar, detener y reproducir (extraído a _detect_media_playback)
        _media__r = self._detect_media_playback(inp, user_input)
        if _media__r is not None:
            return _media__r

        # --- Abrir ---
        open_keywords = ["abre ", "abrir ", "ejecuta ", "lanza ", "abri ",
                         "abrí ", "abrilo", "abrila", "abrelo", "abrela",
                         "abrime ", "abrame ",
                         # Reproducción / media → abren la app/web correspondiente
                         "reproduce ", "reproducir ", "reproducí ",
                         "pon musica ", "pon música ", "pone musica ", "pone música ",
                         "escuchar ", "escucha ", "poneme ",
                         "quiero ver ", "quiero escuchar ",
                         "play ", "inicia "]
        # Guard anti-colisión: "ejecuta"/"inicia" también aparecen en pedidos de
        # ESCRIBIR/EJECUTAR CÓDIGO ("ejecuta un script python..."). Si el input
        # tiene señales claras de código, NO lo trata como "abrir app" — deja
        # que caiga al loop de agente (LLM genera [TOOL:python]).
        _code_signals = ["script", "codigo", "código", " code", "funcion ", "función ",
                         "programa que", "programa en python", "python que",
                         "calcule", "imprima", "algoritmo", "def ", "clase ",
                         "fibonacci", "primos", "factorial"]
        _is_code_request = any(s in inp for s in _code_signals)
        if not _is_code_request and any(inp.startswith(k) or f" {k}" in inp for k in open_keywords):
            # Extraer que abrir
            for kw in open_keywords:
                if kw in inp:
                    target = inp.split(kw)[-1].strip()
                    # Limpiar preposiciones al inicio
                    for prep in ["el ", "la ", "lo ", "los ", "las ", "un ", "una ", "mi "]:
                        if target.startswith(prep):
                            target = target[len(prep):]
                    # Limpiar sustantivos genéricos: "aplicación X", "juego X", "programa X"
                    for generic in ["aplicación ", "aplicacion ", "juego ", "programa ",
                                    "app ", "game ", "carpeta ", "folder ",
                                    # Descriptores: "navegador de chrome" → "chrome"
                                    "navegador de ", "navegador ", "browser ",
                                    "pagina de ", "página de ", "pagina web de ",
                                    "sitio de ", "sitio web de ", "sitio web ",
                                    # Media: "música en youtube" → "youtube"
                                    "musica en ", "música en ", "musica de ", "música de ",
                                    "video de ", "videos de ", "video en ", "videos en ",
                                    "algo en ", "algo de "]:
                        if target.lower().startswith(generic):
                            target = target[len(generic):]
                    # Limpiar preposición "de" residual: "de dota 2" → "dota 2"
                    if target.lower().startswith("de "):
                        target = target[3:]
                    if target.lower().startswith("en "):
                        target = target[3:]
                    target = target.strip().rstrip(".,;!?")
                    if not target or len(target) > 80:
                        break

                    # --- Carpetas y rutas locales ---
                    # Limpiar sufijos comunes que contaminan el target
                    show_content = False
                    for suffix in [" y muestra su contenido", " y muestra contenido",
                                   " y muestrame su contenido", " y listame",
                                   " y muestrame que tiene", " y dime que tiene",
                                   " en explorador de archivos", " en el explorador de archivos",
                                   " en explorador", " en el explorador", " en explorer",
                                   " en file explorer", " en archivos",
                                   " por favor", " porfa", " porfavor"]:
                        if target.lower().endswith(suffix):
                            target = target[:len(target)-len(suffix)].strip()
                            if "contenido" in suffix or "listame" in suffix or "que tiene" in suffix:
                                show_content = True
                            break

                    folder_path = _resolve_folder(target)
                    if folder_path:
                        # Abrir en Explorer
                        app_launcher.open(folder_path)
                        # Mostrar contenido en el chat
                        content = _list_folder_contents(folder_path)
                        return f"Abriendo carpeta en Explorer.\n\n{content}"

                    # Intención EXPLÍCITA de carpeta ("abrí la CARPETA logs"): el usuario
                    # quiere el filesystem, NO una web. Nunca caer a web_map/URL-guessing
                    # (antes "carpeta logs" no encontrada terminaba abriendo logs.com).
                    _folder_intent = any(w in inp for w in
                                         ("carpeta", "directorio", "folder"))
                    if _folder_intent:
                        # Índice de carpetas (lookup ~1ms) primero; walk en vivo de fallback.
                        _hits = []
                        try:
                            from core import folder_index as _fidx
                            _hits = _fidx.find(target)
                            if not _hits:  # quizás recién creada → reescaneo único
                                _fidx.refresh()
                                _hits = _fidx.find(target)
                        except Exception:
                            _hits = []
                        if not _hits:
                            _hits = _search_folder_everywhere(target)
                        if len(_hits) == 1:
                            app_launcher.open(_hits[0])
                            return ("Abriendo carpeta en Explorer.\n\n"
                                    + _list_folder_contents(_hits[0]))
                        if len(_hits) > 1:
                            _lst = "\n".join("  • " + h for h in _hits[:10])
                            return (f"Encontré {len(_hits)} carpetas llamadas «{target}». "
                                    f"¿Cuál abro? Decime la ruta o la unidad:\n{_lst}")
                        return (f"No encontré ninguna carpeta llamada «{target}». "
                                f"Probá con la ruta completa (ej: F:\\programas\\{target}) "
                                f"o decime en qué unidad está.")

                    # Si tiene ruta valida (C:/ o similar), abrir directo
                    if _re.match(r'^[A-Za-z]:[/\\]', target):
                        return app_launcher.open(target)

                    # Detectar patron "en chrome X" / "en el navegador X"
                    browser_prefix = _re.match(r'^en\s+(?:el\s+)?(?:chrome|navegador|firefox|edge|brave)\s+(.+)', target, _re.IGNORECASE)
                    if browser_prefix:
                        target = browser_prefix.group(1).strip()

                    # Mapa de sitios web comunes → URLs
                    web_map = {
                        "netflix": "https://www.netflix.com",
                        "youtube": "https://www.youtube.com",
                        "youtube music": "https://music.youtube.com",
                        "youtube studio": "https://studio.youtube.com",
                        "youtube kids": "https://www.youtubekids.com",
                        "gmail": "https://mail.google.com",
                        "google": "https://www.google.com",
                        "google docs": "https://docs.google.com",
                        "google sheets": "https://sheets.google.com",
                        "google slides": "https://slides.google.com",
                        "google calendar": "https://calendar.google.com",
                        "google photos": "https://photos.google.com",
                        "google translate": "https://translate.google.com",
                        "traductor": "https://translate.google.com",
                        "twitter": "https://twitter.com", "x": "https://twitter.com",
                        "facebook": "https://www.facebook.com",
                        "instagram": "https://www.instagram.com",
                        "whatsapp web": "https://web.whatsapp.com",
                        "telegram web": "https://web.telegram.org",
                        "github": "https://github.com",
                        "reddit": "https://www.reddit.com",
                        "twitch": "https://www.twitch.tv",
                        "amazon": "https://www.amazon.com",
                        "mercadolibre": "https://www.mercadolibre.com.ar",
                        "mercado libre": "https://www.mercadolibre.com.ar",
                        "chatgpt": "https://chat.openai.com",
                        "claude": "https://claude.ai",
                        "maps": "https://maps.google.com", "google maps": "https://maps.google.com",
                        "drive": "https://drive.google.com", "google drive": "https://drive.google.com",
                        "linkedin": "https://www.linkedin.com",
                        "tiktok": "https://www.tiktok.com",
                        "disney": "https://www.disneyplus.com", "disney+": "https://www.disneyplus.com",
                        "disney plus": "https://www.disneyplus.com",
                        "hbo": "https://www.max.com", "hbo max": "https://www.max.com", "max": "https://www.max.com",
                        "prime video": "https://www.primevideo.com",
                        "amazon prime": "https://www.primevideo.com",
                        "spotify web": "https://open.spotify.com",
                        "crunchyroll": "https://www.crunchyroll.com",
                        "pinterest": "https://www.pinterest.com",
                        "notion": "https://www.notion.so",
                        "canva": "https://www.canva.com",
                        "figma": "https://www.figma.com",
                        "stackoverflow": "https://stackoverflow.com",
                        "stack overflow": "https://stackoverflow.com",
                    }

                    target_lower = target.lower()

                    # 1. Cargar mapa aprendido (persistent)
                    from config import BASE_DIR as _BASE_DIR
                    learned_map_path = os.path.join(str(_BASE_DIR), "data", "learned_apps.json")
                    learned_map = {}
                    try:
                        if os.path.exists(learned_map_path):
                            with open(learned_map_path, "r", encoding="utf-8") as _f:
                                learned_map = json.loads(_f.read())
                    except (OSError, json.JSONDecodeError, ValueError):
                        pass

                    # 1.5 PRIORIDAD: app instalada con match FUERTE gana sobre web_map
                    # y learned_map. Ej: si instalaste "YouTube Music", "abrí youtube
                    # music" debe abrir la APP, no music.youtube.com. Solo match fuerte
                    # (exacto o todas las palabras de un nombre multi-palabra) para no
                    # secuestrar intenciones web claras ("youtube" → sigue al sitio).
                    try:
                        from core import program_index as _pidx0
                        _hit0 = _pidx0.find(target_lower)
                        if not _hit0:  # quizás recién instalada → reescaneo único
                            _pidx0.get_index(force=True)
                            _hit0 = _pidx0.find(target_lower)
                        if _hit0:
                            _pn0 = _hit0[0].lower()
                            _tw0 = [w for w in target_lower.split() if w]
                            _strong0 = (_pn0 == target_lower
                                        or (len(_tw0) >= 2 and all(w in _pn0 for w in _tw0)))
                            if _strong0 and os.path.exists(_hit0[1]):
                                os.startfile(_hit0[1])
                                self._learn_app(learned_map_path, learned_map,
                                                target_lower, _hit0[1])
                                return f"Abriendo {_hit0[0]}"
                    except Exception:
                        pass

                    # 2. Buscar en mapa aprendido primero
                    if target_lower in learned_map:
                        learned_entry = learned_map[target_lower]
                        if learned_entry.startswith("http"):
                            import webbrowser
                            webbrowser.open(learned_entry)
                            return f"Abriendo {target}: {learned_entry} (aprendido)"
                        else:
                            return app_launcher.open(learned_entry)

                    # 3. Buscar en web_map estático
                    web_url = web_map.get(target_lower, None)

                    # Match parcial: "youtube music app" → matchea "youtube music"
                    if not web_url:
                        sorted_keys = sorted(web_map.keys(), key=len, reverse=True)
                        for wk in sorted_keys:
                            if target_lower.startswith(wk) or target_lower == wk:
                                web_url = web_map[wk]
                                break

                    if web_url:
                        import webbrowser
                        webbrowser.open(web_url)
                        # Aprender para la proxima
                        self._learn_app(learned_map_path, learned_map, target_lower, web_url)
                        return f"Abriendo {target} en el navegador: {web_url}"

                    # 4. Si es una URL directa
                    if _re.match(r'^https?://', target, _re.IGNORECASE) or _re.match(r'^www\.', target, _re.IGNORECASE):
                        url = target if target.startswith("http") else f"https://{target}"
                        import webbrowser
                        webbrowser.open(url)
                        self._learn_app(learned_map_path, learned_map, target_lower, url)
                        return f"Abriendo: {url}"

                    # 5. Mapear nombres comunes a ejecutables de escritorio
                    # IMPORTANTE: estos mapeos son SUGERENCIAS para fallback.
                    # El flujo prioriza _discover_installed_app (Start Menu), que funciona
                    # aunque el exe no esté en PATH. app_map solo se usa si discovery falla.
                    app_map = {
                        # Navegadores
                        "chrome": "chrome", "google chrome": "chrome",
                        "navegador": "chrome", "navegador web": "chrome",
                        "firefox": "firefox", "mozilla": "firefox", "mozilla firefox": "firefox",
                        "edge": "msedge", "microsoft edge": "msedge",
                        "brave": "brave", "brave browser": "brave",
                        "opera": "opera", "opera gx": "opera gx",
                        # Explorador / archivos
                        "explorador": "explorer", "explorador de archivos": "explorer",
                        "archivos": "explorer", "file explorer": "explorer",
                        "mis archivos": "explorer", "mi pc": "explorer",
                        # Editores de texto básicos
                        "bloc de notas": "notepad", "notepad": "notepad", "notepad++": "notepad++",
                        "wordpad": "wordpad", "write": "wordpad",
                        # Calculadora
                        "calculadora": "calc", "calc": "calc", "calculator": "calc",
                        # Terminales
                        "cmd": "cmd", "terminal": "cmd", "consola": "cmd",
                        "simbolo del sistema": "cmd", "símbolo del sistema": "cmd",
                        "powershell": "powershell", "ps": "powershell",
                        "windows terminal": "wt", "wt": "wt",
                        # Paint
                        "paint": "mspaint", "mspaint": "mspaint", "dibujo": "mspaint",
                        # Configuración / control
                        "panel de control": "control", "control": "control",
                        "configuracion": "ms-settings:", "configuración": "ms-settings:",
                        "settings": "ms-settings:", "ajustes": "ms-settings:",
                        "configuracion de windows": "ms-settings:",
                        "configuración de windows": "ms-settings:",
                        # Sistema
                        "administrador de tareas": "taskmgr", "task manager": "taskmgr",
                        "monitor de recursos": "resmon",
                        "editor de registro": "regedit", "regedit": "regedit",
                        "msconfig": "msconfig", "configuracion del sistema": "msconfig",
                        # IDEs / desarrollo
                        "vscode": "code", "visual studio code": "code", "code": "code",
                        "vs code": "code",
                        "visual studio": "devenv", "git bash": "git-bash",
                        "pycharm": "pycharm", "intellij": "idea", "idea": "idea",
                        "android studio": "studio",
                        # Office
                        "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
                        "outlook": "outlook", "onenote": "onenote", "access": "msaccess",
                        "teams": "teams", "microsoft teams": "teams",
                        # Media / comunicación
                        "spotify": "spotify", "vlc": "vlc", "media player": "wmplayer",
                        "discord": "discord", "slack": "slack", "zoom": "zoom",
                        "steam": "steam", "epic games": "epicgameslauncher",
                        "telegram": "telegram", "telegram desktop": "telegram",
                        "whatsapp": "whatsapp", "whatsap": "whatsapp",
                        "signal": "signal",
                        # Streaming / creación
                        "obs": "obs64", "obs studio": "obs64", "obes": "obs64",
                        "streamlabs": "streamlabs obs",
                        # Utilidades
                        "7zip": "7zfm", "7-zip": "7zfm", "winrar": "winrar",
                        "git": "git", "docker": "docker desktop",
                    }
                    # Normalizar números en español del speech-to-text
                    _num_words = {"uno": "1", "dos": "2", "tres": "3", "cuatro": "4",
                                  "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
                                  "nueve": "9", "diez": "10"}
                    _normalized = target_lower
                    for word, digit in _num_words.items():
                        _normalized = _normalized.replace(word, digit)
                    # Intentar con nombre original y normalizado
                    mapped = app_map.get(target_lower, None) or app_map.get(_normalized, None)

                    # 6a. ÍNDICE RÁPIDO: programas instalados pre-escaneados (lookup en memoria, ~1ms)
                    # Antes el discovery recorría el Start Menu en CADA pedido (lento, ~30-56s).
                    # program_index cachea el escaneo en data/installed_programs.json y se refresca
                    # solo desde el heartbeat. Esto es el camino feliz para "abrí steam/brave/etc".
                    try:
                        from core import program_index as _pidx
                        _hit = _pidx.find(target_lower)
                        if not _hit and _normalized != target_lower:
                            _hit = _pidx.find(_normalized)
                        if not _hit and mapped:
                            _hit = _pidx.find(mapped)
                        if _hit:
                            _pname, _ppath = _hit
                            if _ppath.lower().endswith('.lnk'):
                                _rexe = app_launcher.resolve_lnk_target(_ppath)
                                if _rexe is not None and not os.path.exists(_rexe):
                                    _hit = None  # shortcut roto → caer a discovery
                            if _hit and os.path.exists(_ppath):
                                os.startfile(_ppath)
                                self._learn_app(learned_map_path, learned_map, target_lower, _ppath)
                                return f"Abriendo {_pname}"
                    except Exception:
                        pass  # cualquier fallo → seguir con el discovery clásico

                    # 6b. DESCUBRIMIENTO AUTOMATICO: escanear Start Menu (prioridad sobre cmd /c start)
                    # Los .lnk/.url del Start Menu funcionan siempre, cmd /c start solo si está en PATH
                    discovered = self._discover_installed_app(target_lower)
                    if not discovered and _normalized != target_lower:
                        discovered = self._discover_installed_app(_normalized)
                    if not discovered and mapped:
                        discovered = self._discover_installed_app(mapped)
                    if discovered:
                        try:
                            # Si es .lnk, verificar que apunta a un .exe existente antes de lanzar
                            # (evita "falso éxito" cuando el shortcut está roto)
                            if discovered.lower().endswith('.lnk'):
                                resolved_exe = app_launcher.resolve_lnk_target(discovered)
                                if resolved_exe is None:
                                    # No pudimos resolver — intentar igual con os.startfile (Windows
                                    # suele manejar .lnk rotos con diálogo, no silencioso)
                                    pass
                                elif not os.path.exists(resolved_exe):
                                    # Shortcut roto — no intentar, caer al siguiente método
                                    discovered = None
                            if discovered:
                                os.startfile(discovered)
                                self._learn_app(learned_map_path, learned_map, target_lower, discovered)
                                app_name = os.path.splitext(os.path.basename(discovered))[0]
                                return f"Abriendo {app_name}"
                        except (OSError, FileNotFoundError):
                            pass  # Continuar con fallback

                    # 7. Fallback: cmd /c start (solo funciona para apps en PATH: notepad, calc, etc.)
                    if mapped:
                        self._learn_app(learned_map_path, learned_map, target_lower, mapped)
                        return app_launcher.open(mapped)

                    # 7. APRENDIZAJE: Si no lo conozco, intentar construir URL
                    # "twitch" → https://www.twitch.com, "notion" → https://www.notion.com
                    if len(target.split()) <= 3 and len(target) <= 30:
                        # Construir URL candidata: quitar espacios, usar .com
                        clean_name = target_lower.replace(" ", "")
                        candidate_url = f"https://www.{clean_name}.com"
                        # Verificar si la URL existe (HEAD request rapido)
                        try:
                            import urllib.request
                            req = urllib.request.Request(candidate_url, method='HEAD')
                            req.add_header('User-Agent', 'Mozilla/5.0')
                            resp = urllib.request.urlopen(req, timeout=3)
                            if resp.status < 400:
                                import webbrowser
                                webbrowser.open(candidate_url)
                                # Aprender para la proxima!
                                self._learn_app(learned_map_path, learned_map, target_lower, candidate_url)
                                return f"Abriendo {target}: {candidate_url} (descubierto y aprendido)"
                        except (OSError, ValueError):
                            pass

                        # Intentar sin www
                        candidate_url2 = f"https://{clean_name}.com"
                        try:
                            req = urllib.request.Request(candidate_url2, method='HEAD')
                            req.add_header('User-Agent', 'Mozilla/5.0')
                            resp = urllib.request.urlopen(req, timeout=3)
                            if resp.status < 400:
                                import webbrowser
                                webbrowser.open(candidate_url2)
                                self._learn_app(learned_map_path, learned_map, target_lower, candidate_url2)
                                return f"Abriendo {target}: {candidate_url2} (descubierto y aprendido)"
                        except (OSError, ValueError):
                            pass

                    # 8. No se pudo resolver — sugerir alternativas del cache de Start Menu
                    suggestions = []
                    try:
                        cache = GenesisToolsMixin._installed_apps_cache or {}
                        if cache:
                            import difflib as _difflib
                            # Buscar matches fuzzy (cutoff 0.5 = al menos 50% similar)
                            close = _difflib.get_close_matches(
                                target_lower, list(cache.keys()), n=5, cutoff=0.5
                            )
                            # También buscar substring matches (ej: "outlook" en "Microsoft Outlook")
                            for name in cache.keys():
                                if len(suggestions) >= 5:
                                    break
                                if target_lower in name and name not in close:
                                    close.append(name)
                            # Capitalizar para mostrar (usar nombre del archivo original)
                            for match in close[:5]:
                                path = cache.get(match, "")
                                if path:
                                    pretty = os.path.splitext(os.path.basename(path))[0]
                                    suggestions.append(pretty)
                    except Exception:
                        pass

                    if suggestions:
                        hints = ", ".join(f"'{s}'" for s in suggestions)
                        return (f"No encontré '{target}' exactamente. ¿Quisiste decir alguno de estos? "
                                f"{hints}. Decime el nombre correcto y lo abro.")
                    return (f"No encontré '{target}' como programa instalado, carpeta, ni sitio web. "
                            f"Intentá con el nombre exacto o decime más sobre qué querés abrir.")

        # Builder/desarrollo: instalar paquetes, procesar documentos, crear archivos/scripts/proyectos (extraído a _detect_builder_dev)
        _builde_r = self._detect_builder_dev(inp, user_input, _PATH_KEYWORDS)
        if _builde_r is not None:
            return _builde_r

        # --- Mover archivos ---
        move_keywords = ["mueve", "mover", "mueva"]
        if any(k in inp for k in move_keywords) and ("a " in inp or "al " in inp or "hacia " in inp):
            return ""  # Dejar al LLM con herramientas

        # Manejo de archivos conversacional (extraído a _detect_file_ops)
        _fops_r = self._detect_file_ops(inp, user_input)
        if _fops_r is not None:
            return _fops_r

        return None

    def _detect_games(self, inp, user_input):
        """Lanzador de juegos por voz/nombre (Steam/Epic). Devuelve str o None."""
        import re as _re
        from core import game_launcher as _gl
        # listar juegos instalados
        if _re.search(r"\b(qu[ée]\s+juegos|mis\s+juegos|juegos\s+(tengo|instalad|que\s+tengo)|"
                      r"list[áa]r?\s+(los\s+)?juegos|qu[ée]\s+puedo\s+jugar)\b", inp):
            return _gl.list_text()
        # "jugá/jugar/juguemos <juego>" → intención explícita de jugar
        _gm = _re.search(r"\b(?:jug[aáué]\w*|quiero\s+jugar(?:\s+a)?)\s+"
                         r"(?:al?\s+|el\s+juego\s+|la\s+)?(.+)", inp)
        if _gm:
            q = _gm.group(1).strip().rstrip(".?!")
            if q and q not in ("algo", "un juego", "un rato"):
                return _gl.launch_game(q)
            return "🎮 ¿A qué querés jugar? Decime el nombre (o «qué juegos tengo»)."
        if _re.search(r"\b(quiero\s+jugar|juguemos|vamos\s+a\s+jugar|a\s+jugar)\b", inp):
            return "🎮 ¿A qué? Decime el juego (o «qué juegos tengo»)."
        # "abrí/lanzá/poné <X>" SOLO si X es un juego instalado (si no, cae al open genérico)
        _am = _re.search(r"\b(?:abr[íi]r?|lanz[áa]r?|ejecut[áa]r?|inici[áa]r?|pon[ée]r?|arranc[áa]r?)\s+"
                         r"(?:el\s+juego\s+|al?\s+)?(.+)", inp)
        if _am:
            q = _am.group(1).strip().rstrip(".?!")
            try:
                if q and _gl._match(q, _gl.list_games()):
                    return _gl.launch_game(q)
            except Exception:
                pass
        return None

    def _auto_detect_tool(self, user_input: str) -> str:
        """
        Auto-detecta si el usuario pide algo del sistema y ejecuta
        la herramienta correspondiente sin depender del LLM.
        Retorna el resultado o cadena vacia si no aplica.
        """
        inp = user_input.lower().strip()
        import re as _re

        # --- ESCUCHA MANOS LIBRES (always-on con wake-word) — alta prioridad ---
        if _re.search(r"\b(manos\s+libres|escuch[áa]\s+siempre|modo\s+escucha|"
                      r"activ[áa]r?\s+(la\s+)?escucha|escucha\s+continua)\b", inp):
            from core import handsfree as _hf
            return _hf.get(self).start()
        if _re.search(r"\b(dej[áa]\s+de\s+escuchar|apag[áa]r?\s+(la\s+)?(escucha|manos\s+libres)|"
                      r"desactiv[áa]r?\s+(la\s+)?escucha)\b", inp):
            from core import handsfree as _hf
            return _hf.get(self).stop()
        if _re.search(r"\b(est[áa]s?\s+escuchando|estado\s+de\s+la\s+escucha)\b", inp):
            from core import handsfree as _hf
            return _hf.get(self).status()

        # --- HUELLA DE VOZ (reconocimiento del hablante) ---
        if _re.search(r"\b(entren[áa]r?|registr[áa]r?|aprend[ée]r?|guard[áa]r?)\s+"
                      r"(mi\s+|la\s+|tu\s+)?voz\b", inp) or \
           _re.search(r"\breconoc[ée]r?\s+mi\s+voz\b", inp):
            from core import voiceprint as _vp
            return _vp.start_enroll(self)
        if _re.search(r"\b(verific[áa]r?\s+(mi\s+)?voz|reconoc[ée]r?\s+qui[ée]n\s+soy|"
                      r"sabes\s+qui[ée]n\s+soy|esta?\s+es\s+mi\s+voz)\b", inp):
            from core import voiceprint as _vp
            return _vp.start_verify(self)

        # --- RUTINAS JARVIS (todas las versiones de Iron Man) — alta prioridad ---
        try:
            from core import jarvis_routines as _jr
            if inp in ("rutinas", "rutinas jarvis", "protocolos", "que rutinas tenes",
                       "qué rutinas tenés", "lista de rutinas"):
                return _jr.listar()
            _rk = _jr.detectar(inp)
            if _rk:
                return _jr.ejecutar(self, _rk)
        except Exception as _e:
            self.log.debug(f"Rutinas JARVIS skip: {_e}")

        # Capacidades de Genesis: voces disponibles, qué puede hacer, etc (extraído a _detect_capabilities)
        _capabi_r = self._detect_capabilities(inp, user_input)
        if _capabi_r is not None:
            return _capabi_r

        # Fecha, hora y datos básicos del sistema (extraído a _detect_datetime_sysinfo)
        _dateti_r = self._detect_datetime_sysinfo(inp, user_input)
        if _dateti_r is not None:
            return _dateti_r

        # Calculadora: operaciones aritméticas (extraído a _detect_calculator)
        _calcul_r = self._detect_calculator(inp, user_input)
        if _calcul_r is not None:
            return _calcul_r

        # Identidad de Genesis (quién sos, tu nombre, etc (extraído a _detect_identity)
        _identi_r = self._detect_identity(inp, user_input)
        if _identi_r is not None:
            return _identi_r

        # --- Contar archivos / tamano de carpeta ---
        count_keywords = ["cuantos archivos", "cuántos archivos", "cuantas carpetas",
                          "cuántas carpetas", "cantidad de archivos", "numero de archivos",
                          "cuantos elementos", "cuántos elementos"]
        size_keywords = ["cuanto pesa", "cuánto pesa", "cuanto ocupa", "cuánto ocupa",
                         "peso de la carpeta", "tamano de la carpeta", "tamaño de la carpeta",
                         "peso de ", "size de "]
        if any(k in inp for k in count_keywords + size_keywords):
            is_size = any(k in inp for k in size_keywords)
            # Extraer la carpeta mencionada
            _folder_map = {
                "escritorio": "" + _GX_HOME + "/Desktop",
                "desktop": "" + _GX_HOME + "/Desktop",
                "descargas": "" + _GX_HOME + "/Downloads",
                "downloads": "" + _GX_HOME + "/Downloads",
                "documentos": "" + _GX_HOME + "/Documents",
                "documents": "" + _GX_HOME + "/Documents",
                "genesis": os.path.dirname(os.path.abspath(__file__)),
            }
            # Detectar carpeta por nombre en la query
            target_dir = None
            for fname, fpath in _folder_map.items():
                if fname in inp:
                    target_dir = fpath
                    break
            if not target_dir:
                # Intentar con ruta
                _path_m = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
                if _path_m:
                    target_dir = _path_m.group(0)
            if target_dir and os.path.isdir(target_dir):
                try:
                    if is_size:
                        total = 0
                        file_count = 0
                        dir_count = 0
                        for dirpath, dirnames, filenames in os.walk(target_dir):
                            dir_count += len(dirnames)
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                try:
                                    total += os.path.getsize(fp)
                                    file_count += 1
                                except OSError:
                                    pass
                        # Formatear tamano
                        if total >= 1024**3:
                            size_str = f"{total/1024**3:.2f} GB"
                        elif total >= 1024**2:
                            size_str = f"{total/1024**2:.1f} MB"
                        elif total >= 1024:
                            size_str = f"{total/1024:.0f} KB"
                        else:
                            size_str = f"{total} bytes"
                        return (f"📂 **{os.path.basename(target_dir)}**\n"
                                f"  Peso total: **{size_str}**\n"
                                f"  Archivos: {file_count}\n"
                                f"  Subcarpetas: {dir_count}")
                    else:
                        items = os.listdir(target_dir)
                        files = [i for i in items if os.path.isfile(os.path.join(target_dir, i))]
                        dirs = [i for i in items if os.path.isdir(os.path.join(target_dir, i))]
                        return (f"📂 **{os.path.basename(target_dir)}**\n"
                                f"  Archivos: **{len(files)}**\n"
                                f"  Carpetas: **{len(dirs)}**\n"
                                f"  Total: **{len(items)}** elementos")
                except PermissionError:
                    return f"❌ Sin permisos para acceder a: {target_dir}"

        # --- Imports de herramientas (lazy, se cargan solo cuando se necesitan) ---
        from core.device_tools import (
            file_manager, file_searcher, file_organizer,
            disk_analyzer, duplicate_finder, process_manager,
            clipboard_manager, screen_capture, app_launcher,
        )
        from core.tools import FileTools, SystemInfoTool

        # Control de dispositivos/sistema (extraído a _detect_device_control)
        _dev_r = self._detect_device_control(inp, user_input)
        if _dev_r is not None:
            return _dev_r

        # Operaciones de archivos/sistema: listar, buscar, organizar, procesos, portapapeles, captura, papelera, duplicados, info del sistema (extraído a _detect_fs_system_ops)
        _fs_sys_r = self._detect_fs_system_ops(inp, user_input)
        if _fs_sys_r is not None:
            return _fs_sys_r

        # --- Automatización de UI (menús/clicks/teclado de cualquier app) ---
        # ANTES de open/content: "abrí el menú X" no debe caer en el launcher.
        _ui_res = self._ui_action(inp, user_input)
        if _ui_res is not None:
            return _ui_res

        # === JUEGOS: lanzar por voz/nombre (Steam/Epic) — ANTES del open genérico ===
        _games_r = self._detect_games(inp, user_input)
        if _games_r is not None:
            return _games_r

        # Abrir apps/sitios/carpetas y mostrar contenido de carpeta (extraído a _detect_open_apps_folders)
        _open_a_r = self._detect_open_apps_folders(inp, user_input)
        if _open_a_r is not None:
            return _open_a_r

        # --- Notas rápidas ---
        # "nota: comprar leche" → guarda nota
        # "mis notas" → lista notas
        # "busca en notas X" → busca
        # "elimina nota 3" → elimina
        note_save_kw = ["nota:", "anota:", "recuerda que ", "recordar que ",
                        "apunta:", "guarda nota:", "nota rapida:"]
        if any(inp.startswith(k) for k in note_save_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            content = inp
            for kw in note_save_kw:
                if inp.startswith(kw):
                    content = user_input[len(kw):].strip()
                    break
            # Detectar tag con #tag
            tag = ""
            tag_match = _re.search(r'#(\w+)', content)
            if tag_match:
                tag = tag_match.group(1)
                content = content.replace(f"#{tag}", "").strip()
            return self._quick_notes.add(content, tag)

        note_list_kw = ["mis notas", "ver notas", "lista notas", "mostrar notas",
                        "notas guardadas", "todas las notas", "muestra mis notas"]
        if any(k in inp for k in note_list_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            # Filtrar por tag si se menciona
            tag = ""
            tag_match = _re.search(r'#(\w+)', inp)
            if tag_match:
                tag = tag_match.group(1)
            return self._quick_notes.list_notes(tag=tag)

        note_search_kw = ["busca en notas", "buscar en notas", "busca nota",
                          "buscar nota"]
        if any(k in inp for k in note_search_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            query = inp
            for kw in note_search_kw:
                if kw in inp:
                    query = inp.split(kw)[-1].strip()
                    break
            return self._quick_notes.search(query)

        note_delete_kw = ["elimina nota", "borrar nota", "borra nota", "eliminar nota"]
        if any(k in inp for k in note_delete_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            id_match = _re.search(r'(\d+)', inp)
            if id_match:
                return self._quick_notes.delete(int(id_match.group(1)))
            return "Indicá el número de nota a eliminar (ej: 'elimina nota 3')"

        # --- Recordatorios / Temporizadores ---
        # "recuerdame en 5 minutos que..." → timer + notificación
        # "pon timer de 30 segundos" → timer
        # "mis recordatorios" → lista activos
        # "cancela recordatorio 2" → cancela
        # --- DESPERTADOR (hora absoluta + te despierta con MÚSICA) ---
        despertar_kw = ["despertame", "despertáme", "despiértame", "despiertame",
                        "despertarme", "despierta a las", "despiértame a las",
                        "despertador a las", "despertador para las",
                        "alarma a las", "alarma para las", "ponme una alarma a las"]
        if any(k in inp for k in despertar_kw):
            rems = self._ensure_reminders()
            secs = self._parse_clock_time(inp)
            if not secs:
                return ("¿A qué hora te despierto? Decime la hora, ej: "
                        "«despertame a las 7» o «despertame a las 7:30 de la mañana».")
            # canción opcional: "... con <canción>"
            song = "música enérgica para despertar"
            _mc = _re.search(r"\bcon\s+(.+)$", inp)
            if _mc:
                song = _mc.group(1).strip().rstrip(".?!")
            msg = f"🌅 ¡Hora de levantarse! ▶ {song}"
            rems.add(msg, secs)
            import datetime as _dt2
            tgt = (_dt2.datetime.now() + _dt2.timedelta(seconds=secs)).strftime("%H:%M")
            return (f"⏰ Listo, te despierto a las **{tgt}** con música 🎵 ({song}). "
                    f"Faltan {rems._format_time(secs)}. Voy a poner el tema a sonar "
                    f"en YouTube Music a esa hora.")

        reminder_kw = ["recuerdame en ", "recuérdame en ", "recordame en ",
                       "avísame en ", "avisame en ", "pon timer ",
                       "pon un timer ", "timer de ", "alarma en ",
                       "pon alarma ", "temporizador "]
        if any(k in inp for k in reminder_kw):
            from core.reminder_system import ReminderSystem
            if not hasattr(self, '_reminders'):
                self._reminders = ReminderSystem()
            # Extraer tiempo y mensaje
            text_after = inp
            for kw in reminder_kw:
                if kw in inp:
                    text_after = inp.split(kw, 1)[-1].strip()
                    break
            seconds = ReminderSystem.parse_time_expression(text_after)
            if seconds:
                # Extraer mensaje (lo que viene después de "que", "para", "de")
                message = text_after
                for sep in [" que ", " para ", " de que ", " - "]:
                    if sep in text_after:
                        message = text_after.split(sep, 1)[-1].strip()
                        break
                if message == text_after:
                    # Si no hay separador, el mensaje es genérico
                    message = "Recordatorio de Genesis"
                return self._reminders.add(message, seconds)
            return "No entendí el tiempo. Ejemplos: '5 minutos', '1 hora', '30 segundos'"

        reminder_list_kw = ["mis recordatorios", "recordatorios activos",
                            "que recordatorios", "timers activos", "mis timers",
                            "mis alarmas"]
        if any(k in inp for k in reminder_list_kw):
            from core.reminder_system import ReminderSystem
            if not hasattr(self, '_reminders'):
                self._reminders = ReminderSystem()
            return self._reminders.list_active()

        reminder_cancel_kw = ["cancela recordatorio", "cancelar recordatorio",
                              "cancela timer", "cancelar timer",
                              "cancela alarma", "cancelar alarma"]
        if any(k in inp for k in reminder_cancel_kw):
            from core.reminder_system import ReminderSystem
            if not hasattr(self, '_reminders'):
                self._reminders = ReminderSystem()
            id_match = _re.search(r'(\d+)', inp)
            if id_match:
                return self._reminders.cancel(int(id_match.group(1)))
            return "Indicá el número de recordatorio a cancelar."

        # --- Estado de red / Conectividad ---
        net_check_kw = ["estoy conectado", "hay internet", "tengo internet",
                        "conexion a internet", "conexión a internet",
                        "estado de red", "estado de la red", "hay conexion",
                        "funciona internet", "funciona la red"]
        if any(k in inp for k in net_check_kw):
            from core.network_tools import network_tools
            return network_tools.check_connectivity()

        wifi_kw = ["info wifi", "información wifi", "mi wifi", "estado wifi",
                   "red wifi", "a que wifi", "a qué wifi", "nombre del wifi",
                   "señal wifi", "wifi conectado"]
        if any(k in inp for k in wifi_kw):
            from core.network_tools import network_tools
            return network_tools.get_wifi_info()

        ping_kw = ["haz ping", "hacé ping", "ping a ", "hacer ping"]
        if any(k in inp for k in ping_kw):
            from core.network_tools import network_tools
            # Extraer host
            host = "8.8.8.8"
            host_match = _re.search(r'ping (?:a\s+)?(\S+)', inp)
            if host_match:
                host = host_match.group(1).rstrip(".,;!?")
            return network_tools.ping(host)

        speed_kw = ["velocidad de internet", "velocidad de red", "test de velocidad",
                    "speed test", "speedtest", "que tan rapido", "qué tan rápido"]
        if any(k in inp for k in speed_kw):
            from core.network_tools import network_tools
            return network_tools.speed_test_quick()

        # --- Acciones rápidas del sistema ---
        if any(k in inp for k in ["limpiar temp", "limpia temp", "limpiar temporales",
                                   "limpia temporales", "borrar temporales",
                                   "vaciar temp", "limpiar archivos temporales"]):
            from core.system_actions import system_actions
            return system_actions.clean_temp()

        if any(k in inp for k in ["limpiar dns", "limpia dns", "flush dns",
                                   "vaciar cache dns", "limpiar cache dns"]):
            from core.system_actions import system_actions
            return system_actions.flush_dns()

        if any(k in inp for k in ["uptime", "hace cuanto esta encendido",
                                   "hace cuánto está encendido",
                                   "tiempo encendido", "desde cuando esta prendido"]):
            from core.system_actions import system_actions
            return system_actions.system_uptime()

        if any(k in inp for k in ["bateria", "batería", "nivel de bateria",
                                   "estado bateria", "cuanta bateria"]):
            from core.system_actions import system_actions
            return system_actions.battery_status()

        if any(k in inp for k in ["bloquea pantalla", "bloquear pantalla",
                                   "bloquea la pantalla", "bloquea el equipo",
                                   "bloquear equipo", "lock screen"]):
            from core.system_actions import system_actions
            return system_actions.lock_screen()

        if any(k in inp for k in ["abre configuracion", "abre configuración",
                                   "abrir configuracion", "abre ajustes",
                                   "configuracion de windows", "configuración de windows"]):
            from core.system_actions import system_actions
            # Detectar sección específica
            section = ""
            for s in ["wifi", "bluetooth", "pantalla", "sonido", "audio",
                      "notificaciones", "almacenamiento", "actualizaciones",
                      "apps", "privacidad", "hora", "idioma", "personalización",
                      "fondo", "energía"]:
                if s in inp:
                    section = s
                    break
            return system_actions.open_settings(section)

        if any(k in inp for k in ["cuantas apps instaladas", "cuántas apps instaladas",
                                   "aplicaciones instaladas", "programas instalados",
                                   "cuantos programas tengo"]):
            from core.system_actions import system_actions
            return system_actions.get_installed_apps_count()

        # =====================================================================
        # PHASE 20 — Smart Utilities
        # =====================================================================

        # --- Clipboard Manager ---
        clipboard_current_kw = ["que hay en el portapapeles", "qué hay en el portapapeles",
                                "contenido portapapeles", "portapapeles actual",
                                "que copié", "qué copié", "clipboard actual",
                                "mostrar portapapeles", "ver portapapeles"]
        if any(k in inp for k in clipboard_current_kw):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.get_current()

        clipboard_hist_kw = ["historial portapapeles", "historial clipboard",
                             "historial de copiado", "lo que copié",
                             "que he copiado", "qué he copiado",
                             "mis copias", "portapapeles historial"]
        if any(k in inp for k in clipboard_hist_kw):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.list_history()

        clipboard_search_kw = ["busca en portapapeles", "buscar en portapapeles",
                                "busca en clipboard", "buscar en clipboard"]
        if any(k in inp for k in clipboard_search_kw):
            from core.clipboard_manager import clipboard_manager
            query = inp
            for k in clipboard_search_kw:
                query = query.replace(k, "").strip()
            return clipboard_manager.search(query)

        clipboard_monitor_kw = ["monitorear portapapeles", "monitorea portapapeles",
                                 "activa clipboard", "monitor clipboard"]
        if any(k in inp for k in clipboard_monitor_kw):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.start_monitoring()

        if any(k in inp for k in ["detener monitor portapapeles", "para monitor clipboard",
                                   "desactiva clipboard"]):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.stop_monitoring()

        if any(k in inp for k in ["limpiar portapapeles", "limpia portapapeles",
                                   "vaciar portapapeles", "borrar historial portapapeles"]):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.clear()

        # --- Text Transformer ---
        if any(k in inp for k in ["a mayusculas", "a mayúsculas", "convierte a mayusculas",
                                   "en mayusculas", "en mayúsculas", "pasa a mayusculas"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.to_upper(text)

        if any(k in inp for k in ["a minusculas", "a minúsculas", "convierte a minusculas",
                                   "en minusculas", "en minúsculas", "pasa a minusculas"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.to_lower(text)

        if any(k in inp for k in ["a titulo", "a título", "convierte a titulo",
                                   "formato titulo", "formato título"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.to_title(text)

        if any(k in inp for k in ["cuenta palabras", "contar palabras", "cuantas palabras",
                                   "cuántas palabras", "conta palabras", "contá palabras",
                                   "conta las palabras", "contá las palabras",
                                   "palabras tiene", "palabras hay", "estadisticas de texto",
                                   "estadísticas de texto", "analiza texto"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.count_text(text)

        if any(k in inp for k in ["codifica base64", "codificar base64", "encode base64",
                                   "a base64", "en base64", "base64 de", "base64:"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.encode_base64(text)

        if any(k in inp for k in ["decodifica base64", "decodificar base64", "decode base64",
                                   "desde base64", "de base64"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.decode_base64(text)

        if any(k in inp for k in ["hash del texto", "hash texto", "hashear", "hash md5",
                                   "hash sha", "genera hash", "generar hash"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.hash_text(text)

        if any(k in inp for k in ["extrae emails", "extraer emails", "busca emails",
                                   "encuentra emails", "sacar emails"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.extract_emails(text)

        if any(k in inp for k in ["extrae urls", "extraer urls", "busca urls",
                                   "encuentra urls", "sacar urls", "sacar links"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.extract_urls(text)

        if any(k in inp for k in ["extrae numeros", "extraer números", "busca numeros",
                                   "encuentra numeros", "sacar numeros"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.extract_numbers(text)

        if any(k in inp for k in ["formatea json", "formatear json", "prettify json",
                                   "json bonito", "json legible"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.to_json_pretty(text)

        if any(k in inp for k in ["ordena lineas", "ordena líneas", "ordenar lineas",
                                   "ordenar líneas", "sort lines"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.sort_lines(text)

        if any(k in inp for k in ["elimina duplicados", "quitar duplicados",
                                   "lineas unicas", "líneas únicas",
                                   "quita duplicados", "sin duplicados"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.remove_duplicates(text)

        if any(k in inp for k in ["invierte texto", "invertir texto", "texto invertido",
                                   "texto al reves", "texto al revés"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = _text_payload(user_input) or clipboard_manager._get_clipboard()
            if not text:
                return "📋 Decime el texto o copiá algo. Ej: «pasá a mayúsculas hola»"
            return text_transformer.reverse_text(text)

        # --- Unit Converter ---
        unit_kw = ["convierte ", "convertir ", "cuantos ", "cuántos ",
                   "cuantas ", "cuántas ", "equivale ", "equivalen "]
        unit_suffix = [" a ", " en ", " son ", " es "]
        if (any(k in inp for k in unit_kw) and any(s in inp for s in unit_suffix)):
            # Verificar que no sea una conversión de texto (mayúsculas, base64, etc.)
            text_actions = ["mayuscula", "minuscula", "titulo", "base64", "camel", "snake", "kebab"]
            if not any(ta in inp for ta in text_actions):
                from core.unit_converter import unit_converter
                return unit_converter.convert(inp)

        if any(k in inp for k in ["unidades disponibles", "que unidades", "qué unidades",
                                   "lista unidades", "unidades soportadas"]):
            from core.unit_converter import unit_converter
            return unit_converter.list_categories()

        # --- Pomodoro Timer ---
        # Inicio: cualquier mención de "pomodoro" con intención de arrancar
        # (poné/iniciá/arrancá/empezá… voseo incluido), EXCEPTO pausar/reanudar/parar.
        if "pomodoro" in inp and not any(k in inp for k in (
                "pausa", "pausá", "pause", "para el", "pará el", "reanud", "contin",
                "resume", "deten", "frena", "stop", "cancel", "termin", "cerra")):
            from core.pomodoro import pomodoro
            # Detectar tiempo personalizado
            import re as _re2
            m = _re2.search(r'(\d+)\s*(?:min|minuto)', inp)
            work_min = int(m.group(1)) if m else None
            return pomodoro.start(work_min)

        if any(k in inp for k in ["pausa pomodoro", "pausar pomodoro", "pomodoro pause",
                                   "para el pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.pause()

        if any(k in inp for k in ["reanuda pomodoro", "reanudar pomodoro", "continua pomodoro",
                                   "continúa pomodoro", "resume pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.resume()

        if any(k in inp for k in ["detener pomodoro", "para pomodoro", "detén pomodoro",
                                   "stop pomodoro", "cancela pomodoro",
                                   "termina pomodoro", "terminar pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.stop()

        if any(k in inp for k in ["salta pomodoro", "saltar pomodoro",
                                   "skip pomodoro", "siguiente pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.skip()

        if any(k in inp for k in ["estado pomodoro", "pomodoro status", "como va el pomodoro",
                                   "cómo va el pomodoro", "mi pomodoro", "pomodoro actual"]):
            from core.pomodoro import pomodoro
            return pomodoro.status()

        if any(k in inp for k in ["historial pomodoro", "pomodoro historial",
                                   "sesiones pomodoro", "mis pomodoros"]):
            from core.pomodoro import pomodoro
            return pomodoro.history()

        if any(k in inp for k in ["configura pomodoro", "configurar pomodoro",
                                   "ajustar pomodoro", "pomodoro config"]):
            from core.pomodoro import pomodoro
            import re as _re2
            work = _re2.search(r'trabajo\s*(\d+)', inp)
            short = _re2.search(r'descanso\s*(\d+)', inp)
            long = _re2.search(r'largo\s*(\d+)', inp)
            return pomodoro.configure(
                work=int(work.group(1)) if work else None,
                short_break=int(short.group(1)) if short else None,
                long_break=int(long.group(1)) if long else None
            )

        # =====================================================================
        # PHASE 21 — JARVIS Intelligence
        # =====================================================================

        # --- Window Manager ---
        window_action_kw = ["pon ", "snap ", "mueve la ventana"]
        window_targets = ["izquierda", "derecha", "left", "right", "arriba", "abajo"]
        if (any(k in inp for k in window_action_kw) and
            any(t in inp for t in window_targets)):
            from core.window_manager import window_manager
            return window_manager.parse_and_execute(inp)

        maximize_kw = ["maximiza ", "maximizar ", "maximizá ", "maximizá ", "maximices "]
        if any(k in inp for k in maximize_kw) or _re.search(r'\bmaxi\w*za\w*\b', inp):
            from core.window_manager import window_manager
            target = inp
            for prefix in maximize_kw + ["maximice ", "maximizame ", "maximizame "]:
                target = target.replace(prefix, "")
            for noise in ["el ", "la ", "al ", "a ", "por favor", "porfa",
                          "quiero que ", "podés ", "podes ", "me "]:
                target = target.replace(noise, "")
            target = _re.sub(r'\bmaxi\w+za\w*\s*', '', target).strip()
            if not target:
                return "🪟 ¿Qué ventana querés maximizar? Decime el nombre de la app."
            return window_manager.maximize(target)

        minimize_kw = ["minimiza ", "minimizar ", "minimizá ", "minimizá ", "minimices "]
        if any(k in inp for k in minimize_kw) or _re.search(r'\bminimi\w*\b', inp):
            from core.window_manager import window_manager
            target = inp
            # Limpiar todas las variantes del verbo y artículos
            for prefix in minimize_kw + ["minimice ", "minimizame ", "minimizame "]:
                target = target.replace(prefix, "")
            for noise in ["el ", "la ", "al ", "a ", "por favor", "porfa", "porfavor",
                          "quiero que ", "podés ", "podes ", "podrías ", "podrias ",
                          "puedes ", "me ", "che "]:
                target = target.replace(noise, "")
            target = _re.sub(r'\bminimi\w+\s*', '', target).strip()
            if not target or target in ("todo", "todas", "todas las ventanas", "all"):
                return window_manager.minimize_all()
            return window_manager.minimize(target)

        if any(k in inp for k in ["restaura ventana", "restaurar ventana"]):
            from core.window_manager import window_manager
            target = inp
            for prefix in ["restaura ventana ", "restaurar ventana ", "restaura ", "restaurar "]:
                target = target.replace(prefix, "")
            return window_manager.restore(target.strip())

        if any(k in inp for k in ["cambia a ", "cambiar a ", "enfoca ", "enfocar ",
                                   "ve a la ventana", "ir a "]):
            # Evitar colisión con "cambia a mayúsculas" etc.
            text_actions = ["mayuscula", "minuscula", "titulo", "base64", "camel", "snake", "kebab"]
            if not any(ta in inp for ta in text_actions):
                from core.window_manager import window_manager
                target = inp
                for prefix in ["cambia a ", "cambiar a ", "enfoca ", "enfocar ",
                               "ve a la ventana ", "ir a "]:
                    target = target.replace(prefix, "")
                return window_manager.focus(target.strip())

        if any(k in inp for k in ["ventanas abiertas", "listar ventanas", "lista ventanas",
                                   "mis ventanas", "que ventanas", "qué ventanas"]):
            from core.window_manager import window_manager
            return window_manager.list_windows()

        if any(k in inp for k in ["mostrar escritorio", "ver escritorio",
                                   "minimiza todo", "minimizar todo"]):
            from core.window_manager import window_manager
            return window_manager.minimize_all()

        if any(k in inp for k in ["info pantalla", "info monitor", "info monitores",
                                   "resolución pantalla", "resolucion pantalla"]):
            from core.window_manager import window_manager
            return window_manager.screen_info()

        # --- Smart Launcher ---
        if any(k in inp for k in ["busca todo ", "buscar todo ", "busca global ",
                                   "smart search ", "busqueda global",
                                   "búsqueda global"]):
            from core.smart_launcher import smart_launcher
            query = inp
            for prefix in ["busca todo ", "buscar todo ", "busca global ",
                          "smart search ", "busqueda global ", "búsqueda global "]:
                query = query.replace(prefix, "")
            return smart_launcher.search(query.strip())

        if any(k in inp for k in ["lanza ", "lanzar ", "launch "]):
            from core.smart_launcher import smart_launcher
            query = inp
            for prefix in ["lanza ", "lanzar ", "launch "]:
                query = query.replace(prefix, "")
            return smart_launcher.launch(query.strip())

        # --- Daily Briefing ---
        briefing_kw = ["buenos dias", "buenos días", "buen dia", "buen día",
                       "buenas tardes", "buenas noches",
                       "briefing", "resumen del dia", "resumen del día",
                       "como esta el sistema", "cómo está el sistema",
                       "estado general", "briefing diario",
                       "resumen matutino", "dame un resumen"]
        if any(k in inp for k in briefing_kw):
            from core.daily_briefing import daily_briefing
            return daily_briefing.generate()

        # --- Macro System ---
        # Crear macro: "macro trabajo: abre chrome, abre vscode, inicia pomodoro"
        if any(inp.startswith(k) for k in ["macro ", "crear macro ", "nueva macro "]):
            from core.macro_system import macro_system, MacroSystem
            parsed = MacroSystem.parse_macro_definition(inp)
            if parsed:
                name, commands = parsed
                return macro_system.create(name, commands)
            # Si no parseó como definición, ver si es un comando de gestión
            rest = inp
            for prefix in ["macro ", "crear macro ", "nueva macro "]:
                if rest.startswith(prefix):
                    rest = rest[len(prefix):]
                    break

        if any(k in inp for k in ["ejecuta macro ", "ejecutar macro ", "run macro ",
                                   "corre macro ", "correr macro "]):
            from core.macro_system import macro_system
            name = inp
            for prefix in ["ejecuta macro ", "ejecutar macro ", "run macro ",
                          "corre macro ", "correr macro "]:
                name = name.replace(prefix, "")
            return macro_system.execute(name.strip())

        if any(k in inp for k in ["mis macros", "listar macros", "lista macros",
                                   "macros disponibles", "ver macros", "mostrar macros"]):
            from core.macro_system import macro_system
            return macro_system.list_macros()

        if any(k in inp for k in ["elimina macro ", "eliminar macro ", "borra macro ",
                                   "borrar macro "]):
            from core.macro_system import macro_system
            name = inp
            for prefix in ["elimina macro ", "eliminar macro ", "borra macro ", "borrar macro "]:
                name = name.replace(prefix, "")
            return macro_system.delete(name.strip())

        if any(k in inp for k in ["detalle macro ", "detalles macro ", "ver macro ",
                                   "info macro "]):
            from core.macro_system import macro_system
            name = inp
            for prefix in ["detalle macro ", "detalles macro ", "ver macro ", "info macro "]:
                name = name.replace(prefix, "")
            return macro_system.show(name.strip())

        if any(k in inp for k in ["historial macros", "historial de macros",
                                   "ejecuciones macros"]):
            from core.macro_system import macro_system
            return macro_system.history()

        # =====================================================================
        # FIN PHASE 21
        # =====================================================================

        # =====================================================================
        # PHASE 22 — Autonomous Orchestration
        # =====================================================================

        # --- File Watcher: agregar regla ---
        if any(k in inp for k in ["vigila ", "vigilar ", "monitorea ", "monitorear ", "watch "]):
            if any(k in inp for k in ["carpeta", "directorio", "folder", "descargas", "downloads"]):
                from core.file_watcher import file_watcher
                return file_watcher.list_rules() + "\n\n💡 Para agregar una regla usá: 'vigila [carpeta] patrón [*.pdf] acción [move/copy/notify]'"

        # --- File Watcher: listar reglas ---
        if any(k in inp for k in ["reglas de vigilancia", "reglas del watcher", "reglas de archivo",
                                    "listar reglas", "mis reglas"]):
            from core.file_watcher import file_watcher
            return file_watcher.list_rules()

        # --- File Watcher: iniciar monitoreo ---
        if any(k in inp for k in ["iniciar monitoreo", "empezar a vigilar", "start watcher",
                                    "activar vigilancia", "activa el monitoreo"]):
            from core.file_watcher import file_watcher
            return file_watcher.start()

        # --- File Watcher: detener monitoreo ---
        if any(k in inp for k in ["detener monitoreo", "parar vigilancia", "stop watcher",
                                    "desactivar vigilancia", "detener vigilancia",
                                    "para el monitoreo", "deja de vigilar"]):
            from core.file_watcher import file_watcher
            return file_watcher.stop()

        # --- File Watcher: eventos recientes ---
        if any(k in inp for k in ["eventos del watcher", "eventos recientes del monitoreo",
                                    "qué pasó en las carpetas", "log de archivos"]):
            from core.file_watcher import file_watcher
            return file_watcher.events()

        # --- Smart Scheduler: programar tarea ---
        if any(k in inp for k in ["programa tarea", "programar tarea", "agenda tarea",
                                    "schedule ", "programa que cada"]):
            from core.smart_scheduler import smart_scheduler
            return smart_scheduler.list_tasks() + "\n\n💡 Ejemplo: 'programa tarea backup cada 2 horas: respaldar notas'"

        # --- Smart Scheduler: listar tareas ---
        if any(k in inp for k in ["tareas programadas", "mis tareas", "lista de tareas programadas",
                                    "scheduled tasks", "qué tengo programado"]):
            from core.smart_scheduler import smart_scheduler
            return smart_scheduler.list_tasks()

        # --- Smart Scheduler: historial ---
        if any(k in inp for k in ["historial de tareas", "historial del scheduler",
                                    "historial programado", "ejecuciones programadas"]):
            from core.smart_scheduler import smart_scheduler
            return smart_scheduler.history()

        # --- Habit Tracker: crear hábito ---
        if any(k in inp for k in ["nuevo hábito", "nuevo habito", "crear hábito", "crear habito",
                                    "agregar hábito", "agregar habito", "new habit"]):
            from core.habit_tracker import habit_tracker
            import re as _re
            m = _re.search(r'(?:nuevo|crear|agregar|new)\s+h[aá]bit[o]?\s+(.+)', inp)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                return habit_tracker.add(name)
            return "🎯 ¿Qué hábito querés crear? Ejemplo: 'nuevo hábito ejercicio'"

        # --- Habit Tracker: completar hábito ---
        if any(k in inp for k in ["completé ", "complete ", "hice ", "hice el hábito",
                                    "terminé ", "hábito hecho", "habito hecho",
                                    "marcar hábito", "marcar habito"]):
            from core.habit_tracker import habit_tracker
            import re as _re
            m = _re.search(r'(?:complet[eé]|hice|termin[eé]|marcar)\s+(?:el\s+)?(?:h[aá]bito\s+)?(.+)', inp)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                return habit_tracker.complete(name)
            return "🎯 ¿Qué hábito completaste? Ejemplo: 'completé ejercicio'"

        # --- Habit Tracker: hábitos de hoy ---
        if any(k in inp for k in ["hábitos de hoy", "habitos de hoy", "mis hábitos hoy",
                                    "hábitos pendientes", "habitos pendientes",
                                    "qué hábitos", "que habitos"]):
            from core.habit_tracker import habit_tracker
            return habit_tracker.today()

        # --- Habit Tracker: listar hábitos ---
        if any(k in inp for k in ["mis hábitos", "mis habitos", "lista de hábitos",
                                    "lista de habitos", "todos los hábitos",
                                    "todos los habitos", "listar hábitos"]):
            from core.habit_tracker import habit_tracker
            return habit_tracker.list_habits()

        # --- Habit Tracker: estadísticas ---
        if any(k in inp for k in ["estadísticas de hábitos", "estadisticas de habitos",
                                    "stats hábitos", "stats habitos",
                                    "rachas", "streaks", "mis rachas"]):
            from core.habit_tracker import habit_tracker
            return habit_tracker.stats()

        # --- Habit Tracker: eliminar hábito ---
        if any(k in inp for k in ["eliminar hábito", "eliminar habito", "borrar hábito",
                                    "borrar habito", "quitar hábito", "quitar habito"]):
            from core.habit_tracker import habit_tracker
            import re as _re
            m = _re.search(r'(?:eliminar|borrar|quitar)\s+(?:el\s+)?h[aá]bit[o]?\s+(.+)', inp)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                return habit_tracker.remove(name)
            return "🎯 ¿Qué hábito querés eliminar?"

        # --- Context Engine: comandos más usados ---
        if any(k in inp for k in ["comandos más usados", "comandos mas usados",
                                    "qué uso más", "que uso mas", "top comandos",
                                    "mis comandos frecuentes"]):
            from core.context_engine import context_engine
            return context_engine.top_commands()

        # --- Context Engine: patrones de uso ---
        if any(k in inp for k in ["patrones de uso", "análisis de uso", "analisis de uso",
                                    "cómo uso genesis", "como uso genesis",
                                    "mi actividad", "reporte de uso"]):
            from core.context_engine import context_engine
            return context_engine.full_report()

        # --- Context Engine: sugerencias ---
        if any(k in inp for k in ["qué sugerís", "que sugeris", "sugerencias",
                                    "qué me recomendás", "que me recomendas"]):
            from core.context_engine import context_engine
            suggestion = context_engine.suggest()
            if suggestion:
                return suggestion
            return "🧠 Aún no tengo suficientes datos para sugerencias. Seguí usando Genesis y aprenderé tus patrones."

        # --- Context Engine: borrar datos ---
        if any(k in inp for k in ["borrar datos de uso", "limpiar contexto",
                                    "borrar interacciones", "resetear patrones"]):
            from core.context_engine import context_engine
            return context_engine.clear()

        # =====================================================================
        # FIN PHASE 22
        # =====================================================================

        # =====================================================================
        # PHASE 23 — System Mastery
        # =====================================================================

        # --- Project Scaffolder: crear proyecto ---
        if any(k in inp for k in ["crea proyecto", "crear proyecto", "nuevo proyecto",
                                    "genera proyecto", "scaffold", "generar proyecto"]):
            from core.project_scaffolder import project_scaffolder
            import re as _re
            # Detectar template
            template = "python"
            for t in ["flask", "fastapi", "node", "react", "html"]:
                if t in inp:
                    template = t
                    break
            # Extraer nombre
            m = _re.search(r'(?:crea|crear|nuevo|genera|generar)\s+proyecto\s+(\S+)', inp)
            if m:
                name = m.group(1).strip('"').strip("'")
                return project_scaffolder.create(name, template=template)
            return "🏗️ ¿Qué proyecto querés crear? Ejemplo: 'crea proyecto mi-app con flask'"

        # --- Project Scaffolder: listar templates ---
        if any(k in inp for k in ["templates de proyecto", "plantillas de proyecto",
                                    "tipos de proyecto", "templates disponibles"]):
            from core.project_scaffolder import project_scaffolder
            return project_scaffolder.list_templates()

        # --- Project Scaffolder: historial ---
        if any(k in inp for k in ["proyectos generados", "historial de proyectos",
                                    "proyectos creados"]):
            from core.project_scaffolder import project_scaffolder
            return project_scaffolder.history()

        # --- Code Snippets: guardar ---
        if any(k in inp for k in ["guardar snippet", "guardar código", "guardar codigo",
                                    "nuevo snippet", "save snippet"]):
            from core.code_snippets import code_snippets
            import re as _re
            m = _re.search(r'(?:guardar|nuevo|save)\s+(?:snippet|código|codigo)\s+(\S+)(?:\s*:\s*|\s+)(.+)', inp, _re.DOTALL)
            if m:
                name = m.group(1).strip()
                code = m.group(2).strip()
                return code_snippets.add(name, code)
            return "📎 Ejemplo: 'guardar snippet hello: print(\"hola mundo\")'"

        # --- Code Snippets: obtener ---
        if any(k in inp for k in ["snippet ", "mostrar snippet", "ver snippet",
                                    "dame el snippet"]):
            if any(k in inp for k in ["guardar", "nuevo", "save", "eliminar", "borrar", "buscar"]):
                pass  # Dejamos que lo manejen los otros bloques
            else:
                from core.code_snippets import code_snippets
                import re as _re
                m = _re.search(r'(?:snippet|mostrar snippet|ver snippet|dame el snippet)\s+(\S+)', inp)
                if m:
                    return code_snippets.get(m.group(1).strip())
                return code_snippets.list_snippets()

        # --- Code Snippets: buscar ---
        if any(k in inp for k in ["buscar snippet", "buscar código", "buscar codigo",
                                    "snippets de ", "snippets con tag"]):
            from core.code_snippets import code_snippets
            import re as _re
            m = _re.search(r'(?:buscar|snippets de|snippets con tag)\s+(?:snippet\s+)?(\S+)', inp)
            if m:
                return code_snippets.search(m.group(1).strip())
            return code_snippets.list_snippets()

        # --- Code Snippets: listar ---
        if any(k in inp for k in ["mis snippets", "listar snippets", "lista de snippets",
                                    "todos los snippets"]):
            from core.code_snippets import code_snippets
            return code_snippets.list_snippets()

        # --- Code Snippets: eliminar ---
        if any(k in inp for k in ["eliminar snippet", "borrar snippet", "quitar snippet"]):
            from core.code_snippets import code_snippets
            import re as _re
            m = _re.search(r'(?:eliminar|borrar|quitar)\s+snippet\s+(\S+)', inp)
            if m:
                return code_snippets.remove(m.group(1).strip())
            return "📎 ¿Qué snippet querés eliminar?"

        # --- Template Engine: listar ---
        if any(k in inp for k in ["mis templates", "listar templates", "templates de texto",
                                    "plantillas de texto", "lista de plantillas"]):
            from core.template_engine import template_engine
            return template_engine.list_templates()

        # --- Template Engine: preview ---
        if any(k in inp for k in ["preview template", "ver template", "mostrar template",
                                    "ver plantilla", "mostrar plantilla"]):
            from core.template_engine import template_engine
            import re as _re
            m = _re.search(r'(?:preview|ver|mostrar)\s+(?:template|plantilla)\s+(\S+)', inp)
            if m:
                return template_engine.preview(m.group(1).strip())
            return template_engine.list_templates()

        # --- Template Engine: aplicar ---
        if any(k in inp for k in ["aplicar template", "usar template", "aplicar plantilla",
                                    "usar plantilla", "genera con template"]):
            from core.template_engine import template_engine
            import re as _re
            m = _re.search(r'(?:aplicar|usar|genera con)\s+(?:template|plantilla)\s+(\S+)', inp)
            if m:
                return template_engine.apply(m.group(1).strip())
            return template_engine.list_templates()

        # --- System Profiler: software instalado ---
        if any(k in inp for k in ["software instalado", "programas instalados",
                                    "qué tengo instalado", "que tengo instalado",
                                    "lista de programas", "apps instaladas"]):
            from core.system_profiler import system_profiler
            return system_profiler.installed_software()

        # --- System Profiler: programas de inicio ---
        if any(k in inp for k in ["programas de inicio", "startup programs",
                                    "qué se inicia con windows", "que se inicia con windows",
                                    "autostart", "arranque de windows"]):
            from core.system_profiler import system_profiler
            return system_profiler.startup_programs()

        # --- System Profiler: variables de entorno ---
        if any(k in inp for k in ["variables de entorno", "environment variables",
                                    "env vars", "mostrar path"]):
            from core.system_profiler import system_profiler
            return system_profiler.environment_vars()

        # --- System Profiler: uso de disco ---
        if any(k in inp for k in ["uso de disco por carpeta", "espacio por carpeta",
                                    "disk usage by folder", "carpetas más pesadas",
                                    "carpetas mas pesadas"]):
            from core.system_profiler import system_profiler
            return system_profiler.disk_usage()

        # --- System Profiler: conexiones de red ---
        if any(k in inp for k in ["conexiones de red", "conexiones activas",
                                    "network connections", "puertos abiertos"]):
            from core.system_profiler import system_profiler
            return system_profiler.network_connections()

        # --- System Profiler: servicios ---
        if any(k in inp for k in ["servicios del sistema", "servicios activos",
                                    "services running", "listar servicios"]):
            from core.system_profiler import system_profiler
            return system_profiler.services()

        # --- System Profiler: reporte completo ---
        if any(k in inp for k in ["reporte del sistema", "perfil del sistema",
                                    "system report", "auditoría del sistema",
                                    "auditoria del sistema"]):
            from core.system_profiler import system_profiler
            return system_profiler.full_report()

        # =====================================================================
        # FIN PHASE 23
        # =====================================================================

        # =====================================================================
        # NOTICIAS / TITULARES (Google News RSS)
        if _re.search(r"\b(noticias?|titulares?|novedades|qu[ée]\s+noticias)\b", inp):
            from core import news as _news
            _m = _re.search(r"(?:noticias?|titulares?|novedades)\s+"
                            r"(?:de|sobre|del?|acerca\s+de)\s+(.+)", inp)
            _topic = _m.group(1).strip().rstrip("?.!") if _m else None
            return _news.headlines(_topic)

        # WEATHER MODULE — Datos en tiempo real
        # =====================================================================

        # --- Clima actual ---
        if any(k in inp for k in ["clima", "tiempo en", "temperatura en",
                                    "weather", "clima en", "datos del clima",
                                    "cómo está el clima", "como esta el clima",
                                    "estado del tiempo", "el tiempo", "qué tiempo",
                                    "que tiempo", "cómo está el tiempo",
                                    "como esta el tiempo", "qué temperatura",
                                    "que temperatura", "cuántos grados", "cuantos grados",
                                    "hace frio", "hace frío", "hace calor", "va a llover",
                                    "está lloviendo", "esta lloviendo"]):
            from core.weather import weather_service
            import re as _re
            # Extraer ubicación si la hay
            m = _re.search(r'(?:clima|tiempo|temperatura|weather)\s+(?:en|de|in|for)\s+(.+)', inp)
            if m:
                location = m.group(1).strip().rstrip("?").rstrip(".")
                return weather_service.current(location)
            # Sin ubicación explícita → usar default
            return weather_service.current()

        # --- Pronóstico ---
        if any(k in inp for k in ["pronóstico", "pronostico", "forecast",
                                    "clima mañana", "clima manana",
                                    "próximos días", "proximos dias",
                                    "va a llover mañana"]):
            from core.weather import weather_service
            import re as _re
            m = _re.search(r'(?:pronóstico|pronostico|forecast)\s+(?:en|de|in|for|para)\s+(.+?)(?:\s+(\d+)\s*d[ií]as?)?$', inp)
            if m:
                location = m.group(1).strip()
                days = int(m.group(2)) if m.group(2) else 3
                return weather_service.forecast(location, days)
            m2 = _re.search(r'(\d+)\s*d[ií]as?', inp)
            days = int(m2.group(1)) if m2 else 3
            return weather_service.forecast("", days)

        # --- Configurar ubicación por defecto ---
        if any(k in inp for k in ["ubicación por defecto", "ubicacion por defecto",
                                    "mi ciudad es", "vivo en", "estoy en"]):
            from core.weather import weather_service
            import re as _re
            m = _re.search(r'(?:ciudad es|vivo en|estoy en|defecto)\s+(.+)', inp)
            if m:
                return weather_service.set_default_location(m.group(1).strip())
            return "🌤️ Ejemplo: 'mi ciudad es Córdoba'"

        # =====================================================================
        # FIN WEATHER MODULE
        # =====================================================================

        # =====================================================================
        # MEDIA GENERATION — Crear imagenes, audio, video
        # =====================================================================
        import re as _re

        # --- Generar imagen ---
        img_patterns = [
            r'(?:genera|crea|dibuja|haz|hazme|creame|créame|genera(?:me)?)\s+(?:una?\s+)?(?:imagen|foto|dibujo|ilustraci[oó]n|wallpaper|fondo)\s+(?:de\s+|sobre\s+|con\s+)?(.+)',
            r'(?:imagen|foto|dibujo)\s+(?:de|sobre|con)\s+(.+)',
            # Verbos de dibujo SIN el sustantivo "imagen" (ej: "dibuja un robot",
            # "ilustrame un paisaje", "pintame un gato"). Antes caian al LLM que
            # alucinaba haber creado la imagen.
            r'(?:dib[uú]ja(?:me)?|ilustra(?:me)?|p[ií]nta(?:me)?)\s+(?:una?\s+|el\s+|la\s+|unos?\s+)?(.+)',
        ]
        for pat in img_patterns:
            m = _re.search(pat, inp, _re.IGNORECASE)
            if m:
                prompt = m.group(1).strip().rstrip(".")
                # Detectar estilo
                style = ""
                style_map = {
                    "realista": "realistic", "anime": "anime", "pixel art": "pixel-art",
                    "acuarela": "watercolor", "oleo": "oil-painting", "3d": "3d-render",
                    "cartoon": "cartoon", "minimalista": "minimalist",
                    "cinematografico": "cinematic", "cinematográfico": "cinematic",
                    "digital": "digital-art", "retro": "retro",
                }
                for es, en in style_map.items():
                    if es in inp.lower():
                        style = en
                        prompt = prompt.replace(es, "").strip()
                        break

                try:
                    from core.media_generator import MediaGenerator
                    gen = self.media_generator if hasattr(self, '_modules') and 'media_generator' in self._modules else MediaGenerator()
                    result = gen.generate_image(prompt, style=style)
                    if result.get("success") and result.get("is_real"):
                        path = result["path"]
                        return (
                            f"🖼️ **Imagen generada**\n\n"
                            f"**Prompt:** {prompt}\n"
                            f"{'**Estilo:** ' + style + chr(10) if style else ''}"
                            f"**Dimensiones:** {result.get('dimensions', '1024x1024')}\n"
                            f"**Metodo:** {result.get('method', 'unknown')}\n"
                            f"**Tiempo:** {result.get('time_s', 0)}s\n\n"
                            f"📁 Guardada en: `{path}`"
                        )
                    elif result.get("success") and not result.get("is_real"):
                        # HONESTIDAD: no engañar — fue solo un placeholder de texto.
                        return (
                            f"⚠️ **No pude generar una imagen real.**\n\n"
                            f"El servicio gratuito de generación de imágenes dejó de estar "
                            f"disponible (ahora requiere pago). Solo generé un placeholder "
                            f"de texto en `{result.get('path','')}`, que NO es una imagen de IA.\n\n"
                            f"Para generar imágenes de verdad necesito que configures un "
                            f"backend (Stable Diffusion local con tu GPU, o una API key). "
                            f"Avisá y lo dejo funcionando."
                        )
                    else:
                        return f"❌ Error generando imagen: {result.get('error', 'desconocido')}"
                except Exception as e:
                    return f"❌ Error: {e}"

        # --- Generar audio ---
        audio_patterns = [
            r'(?:genera|crea|graba|hazme|creame|créame)\s+(?:un\s+)?audio\s+(?:que diga|diciendo|con|de)\s+["\']?(.+?)["\']?\s*$',
            r'(?:convierte|pasa)\s+(?:a|en)\s+audio[\s:]+["\']?(.+?)["\']?\s*$',
            r'(?:lee|di|dime)\s+en\s+(?:voz\s+)?(?:alta|audio)[\s:]+["\']?(.+?)["\']?\s*$',
        ]
        for pat in audio_patterns:
            m = _re.search(pat, inp, _re.IGNORECASE)
            if m:
                text = m.group(1).strip().strip("\"'")
                try:
                    from core.media_generator import MediaGenerator
                    gen = self.media_generator if hasattr(self, '_modules') and 'media_generator' in self._modules else MediaGenerator()
                    result = gen.generate_audio(text)
                    if result.get("success"):
                        return (
                            f"🎵 **Audio generado**\n\n"
                            f"**Texto:** {text[:100]}{'...' if len(text) > 100 else ''}\n"
                            f"**Metodo:** {result.get('method', 'unknown')}\n"
                            f"**Tamaño:** {result.get('size_kb', 0)} KB\n"
                            f"**Tiempo:** {result.get('time_s', 0)}s\n\n"
                            f"📁 Guardado en: `{result['path']}`"
                        )
                    else:
                        return f"❌ Error generando audio: {result.get('error', 'desconocido')}"
                except Exception as e:
                    return f"❌ Error: {e}"

        # --- Generar video ---
        video_patterns = [
            r'(?:genera|crea|hazme|creame|créame)\s+(?:un\s+)?video\s+(?:de|sobre|con)\s+(.+)',
        ]
        for pat in video_patterns:
            m = _re.search(pat, inp, _re.IGNORECASE)
            if m:
                prompt = m.group(1).strip().rstrip(".")
                try:
                    from core.media_generator import MediaGenerator
                    gen = self.media_generator if hasattr(self, '_modules') and 'media_generator' in self._modules else MediaGenerator()
                    # Generar imagen + audio → video
                    result = gen.generate_video(text=prompt)
                    if result.get("success"):
                        return (
                            f"🎬 **Video generado**\n\n"
                            f"**Tema:** {prompt}\n"
                            f"**Duracion:** {result.get('duration_s', 0)}s\n"
                            f"**Resolucion:** {result.get('resolution', '1280x720')}\n"
                            f"**Tamaño:** {result.get('size_mb', 0)} MB\n"
                            f"**Tiene audio:** {'Si' if result.get('has_audio') else 'No'}\n"
                            f"**Tiempo:** {result.get('time_s', 0)}s\n\n"
                            f"📁 Guardado en: `{result['path']}`"
                        )
                    else:
                        return f"❌ Error generando video: {result.get('error', 'desconocido')}"
                except Exception as e:
                    return f"❌ Error: {e}"

        # =====================================================================
        # FIN MEDIA GENERATION
        # =====================================================================

        # --- Research Auto-Trigger ---
        # Detectar preguntas factuales donde el LLM podría inventar
        # y auto-buscar en la web para dar respuestas reales
        research_patterns = [
            (r'^(?:que|qué) (?:es|son|significa) ', "definición"),
            (r'^(?:como|cómo) funciona ', "explicación"),
            (r'^(?:como|cómo) se (?:hace|usa|instala|configura) ', "tutorial"),
            (r'^(?:cual|cuál) es (?:la|el|las|los) (?:mejor|mejores|diferencia) ', "comparación"),
            (r'(?:ultimo|última|ultimas|últimas|recientes?|noticias?) (?:versión|version|actualización|update)', "actualidad"),
            (r'^(?:quien|quién) (?:es|fue|creo|creó|invento|inventó) ', "investigación"),
            (r'^(?:cuando|cuándo) (?:se|fue|salio|salió) ', "fecha"),
            (r'^investiga ', "investigación"),
            (r'^busca (?:info|información|sobre|acerca) ', "investigación"),
            (r'^(?:dime|explicame|explícame) (?:sobre|acerca|que es|qué es) ', "explicación"),
        ]
        for pattern, query_type in research_patterns:
            if _re.search(pattern, inp):
                # Extraer el tema de búsqueda
                topic = inp
                for prefix in ["que es ", "qué es ", "que son ", "qué son ",
                                "como funciona ", "cómo funciona ",
                                "como se hace ", "cómo se hace ",
                                "como se usa ", "cómo se usa ",
                                "como se instala ", "cómo se instala ",
                                "como se configura ", "cómo se configura ",
                                "quien es ", "quién es ", "quien fue ", "quién fue ",
                                "cuando se ", "cuándo se ", "cuando fue ", "cuándo fue ",
                                "investiga ", "busca info sobre ", "busca información sobre ",
                                "dime sobre ", "explicame ", "explícame ",
                                "cual es la mejor ", "cuál es la mejor ",
                                "cual es el mejor ", "cuál es el mejor "]:
                    if inp.startswith(prefix):
                        topic = inp[len(prefix):].strip().rstrip("?.,!")
                        break

                if topic and len(topic) > 2:
                    try:
                        if self.web.searcher.available:
                            if self.show_thinking:
                                print(f"  [Research: buscando '{topic}' ({query_type})]")
                            results = self.web.searcher.search(topic, max_results=3)
                            if results:
                                # Formatear resultados como contexto
                                search_ctx = f"[RESULTADOS DE BÚSQUEDA WEB para '{topic}']:\n"
                                for i, r in enumerate(results[:3], 1):
                                    title = r.get("title", "")
                                    snippet = r.get("snippet", r.get("body", ""))
                                    url = r.get("url", r.get("href", ""))
                                    search_ctx += f"{i}. {title}\n   {snippet[:200]}\n   Fuente: {url}\n\n"

                                # Intentar leer la primera página para más detalle
                                first_url = results[0].get("url", results[0].get("href", ""))
                                if first_url:
                                    try:
                                        page_text = self.web.reader.read_page(first_url)
                                        if page_text and len(page_text) > 100:
                                            search_ctx += f"\n[CONTENIDO PRINCIPAL]:\n{page_text[:1500]}\n"
                                    except (OSError, ValueError, AttributeError):
                                        pass  # No pasa nada si no puede leer

                                search_ctx += (
                                    "\nUsa esta información REAL para responder. "
                                    "NO inventes datos. Cita las fuentes si es relevante."
                                )
                                return search_ctx
                    except Exception as web_err:
                        if self.show_thinking:
                            print(f"  [Research: error — {web_err}]")

        return ""

    def _detect_and_learn(self, user_input: str) -> str:
        """
        Detecta si el usuario pide aprender y ejecuta busquedas web reales.

        Retorna contexto aprendido para inyectar en el system prompt,
        o string vacio si no es un pedido de aprendizaje.
        """
        text = user_input.lower().strip()

        # Detectar si es un pedido de aprendizaje
        topic = ""
        for trigger in self.LEARN_TRIGGERS:
            if trigger in text:
                # Extraer el tema despues del trigger
                idx = text.index(trigger) + len(trigger)
                topic = user_input[idx:].strip().strip(".,;:!?")
                break

        if not topic:
            return ""

        # Verificar que el modulo web esta disponible
        if not self.web.searcher.available:
            self.log.info(f"Aprendizaje solicitado pero web no disponible: {topic}")
            return ""

        self.log.info(f"Aprendizaje automatico activado: {topic}")

        # Buscar y aprender de la web
        try:
            report = self.web.search_and_learn(topic, max_results=5, max_pages=3)

            # Agregar como curiosidad resuelta
            self.curiosity.add_question(
                f"Aprender sobre: {topic}", priority=1.0
            )
            for q in self.curiosity.questions:
                if topic.lower() in q["question"].lower():
                    q["explored"] = True
                    q["exploration_result"] = f"Web: {report.get('pages_read', 0)} paginas leidas"
                    break

            # Recuperar conocimiento aprendido relevante
            recall = self.web.recall(topic, top_k=5)

            if recall:
                context_parts = [
                    f"[CONOCIMIENTO APRENDIDO sobre '{topic}' — {len(recall)} fragmentos de la web]"
                ]
                for i, item in enumerate(recall[:5], 1):
                    text_snippet = item.get("text", "")[:500]
                    source = item.get("source", "web")
                    context_parts.append(f"\nFuente {i} ({source}):\n{text_snippet}")

                context_parts.append(
                    f"\n[Usa este conocimiento real para responder. "
                    f"Total aprendido: {self.web.total_learned} paginas.]"
                )
                learn_ctx = "\n".join(context_parts)
                self.log.info(f"Conocimiento inyectado: {len(learn_ctx)} chars sobre '{topic}'")
                return learn_ctx

        except Exception as e:
            self.log.error(f"Error en aprendizaje automatico: {e}")

        return ""
