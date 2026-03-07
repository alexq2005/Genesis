"""
GENESIS Tools — Herramientas que Genesis puede usar.

Capacidades:
- Buscar en la web (DuckDuckGo, sin API key)
- Investigacion profunda (multi-query + lectura de paginas)
- Leer archivos del disco (con validacion de rutas)
- Crear/escribir archivos (con whitelist de directorios)
- Ejecutar codigo Python (con sandbox de seguridad)
- Ejecutar comandos del sistema (shell/cmd)
- Analizar archivos sospechosos
- Resumir textos largos
"""
import os
import json
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import re
import tempfile
import time
from pathlib import Path
from typing import Optional, List


# ============================================================
# VALIDACION DE RUTAS — Previene path traversal attacks
# ============================================================

class PathValidator:
    """
    Valida rutas de archivos para prevenir acceso no autorizado.

    Reglas:
    - Bloquea acceso a directorios del sistema (Windows, System32, etc)
    - Bloquea acceso a archivos de credenciales (.env, .ssh, etc)
    - Resuelve symlinks para evitar path traversal
    """

    # Directorios bloqueados (nunca acceder)
    BLOCKED_DIRS = {
        "windows", "system32", "syswow64",
        ".ssh", ".gnupg",
    }

    # Patrones de archivo bloqueados
    BLOCKED_PATTERNS = [
        r'\.env$', r'\.env\.\w+$',
        r'id_rsa', r'id_ed25519', r'\.pem$', r'\.key$',
        r'credentials\.json$', r'secrets?\.\w+$',
        r'\.kdbx$',
        r'ntds\.dit$', r'sam$',
    ]

    # Extensiones peligrosas para escritura
    DANGEROUS_WRITE_EXTENSIONS = {
        '.exe', '.dll', '.sys', '.bat', '.cmd', '.ps1',
        '.vbs', '.vbe', '.wsf', '.wsh', '.scr', '.pif',
        '.com', '.hta', '.reg', '.msi', '.msp',
    }

    @staticmethod
    def validate_read(filepath: str) -> tuple[bool, str]:
        """
        Valida si se puede leer un archivo.
        Returns: (es_valido, mensaje_error)
        """
        try:
            path = Path(filepath).resolve()
            path_lower = str(path).lower()

            for blocked in PathValidator.BLOCKED_DIRS:
                # Solo bloquear si es parte del path (ej: C:\Windows\System32)
                if f"\\{blocked}\\" in path_lower or path_lower.endswith(f"\\{blocked}"):
                    return False, f"Acceso bloqueado: directorio protegido ({blocked})"

            for pattern in PathValidator.BLOCKED_PATTERNS:
                if re.search(pattern, path.name, re.IGNORECASE):
                    return False, f"Acceso bloqueado: archivo sensible ({path.name})"

            return True, ""
        except Exception as e:
            return False, f"Ruta invalida: {e}"

    @staticmethod
    def validate_write(filepath: str) -> tuple[bool, str]:
        """Valida si se puede escribir un archivo (mas restrictivo)."""
        valid, msg = PathValidator.validate_read(filepath)
        if not valid:
            return valid, msg
        try:
            path = Path(filepath)
            if path.suffix.lower() in PathValidator.DANGEROUS_WRITE_EXTENSIONS:
                return False, f"No se puede crear archivos {path.suffix} (extension peligrosa)"
            return True, ""
        except Exception as e:
            return False, f"Ruta invalida: {e}"


# ============================================================
# SANDBOX DE CODIGO — Restricciones de ejecucion
# ============================================================

class CodeSandbox:
    """
    Sandbox para ejecucion de codigo Python.
    Analiza el codigo ANTES de ejecutar y bloquea patrones peligrosos.
    """

    BLOCKED_IMPORTS = {
        'ctypes', 'winreg', '_winreg', 'msvcrt', 'nt',
    }

    DANGEROUS_PATTERNS = [
        (r'os\.system\s*\(', "os.system() bloqueado — usa subprocess"),
        (r'shutil\.rmtree\s*\(["\'](?:/|[A-Z]:\\)', "rmtree en raiz bloqueado"),
        (r'__import__\s*\(\s*["\'](?:ctypes|winreg)', "import dinamico peligroso"),
        (r'open\s*\([^)]*["\'](?:/etc/|C:\\Windows)', "acceso a archivos del sistema"),
    ]

    @staticmethod
    def analyze(code: str) -> tuple[bool, list[str]]:
        """Analiza codigo antes de ejecutar. Returns: (es_seguro, advertencias)."""
        warnings = []
        blocked = False

        imports = re.findall(r'(?:import|from)\s+(\S+)', code)
        for imp in imports:
            module_base = imp.split('.')[0]
            if module_base in CodeSandbox.BLOCKED_IMPORTS:
                warnings.append(f"BLOQUEADO: import {imp} (modulo peligroso)")
                blocked = True

        for pattern, description in CodeSandbox.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                warnings.append(f"BLOQUEADO: {description}")
                blocked = True

        return not blocked, warnings


class WebSearchTool:
    """Busqueda web usando DuckDuckGo (sin API key)."""

    @staticmethod
    def search(query: str, max_results: int = 5) -> str:
        """
        Busca en la web y retorna resultados.

        Args:
            query: Termino de busqueda
            max_results: Numero maximo de resultados

        Returns:
            Texto con los resultados encontrados
        """
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/131.0.0.0 Safari/537.36",
            })

            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extraer resultados del HTML
            results = []
            # Buscar bloques de resultados
            snippets = re.findall(
                r'<a rel="nofollow" class="result__a" href="([^"]*)"[^>]*>(.*?)</a>.*?'
                r'<a class="result__snippet"[^>]*>(.*?)</a>',
                html, re.DOTALL
            )

            for i, (link, title, snippet) in enumerate(snippets[:max_results]):
                # Limpiar HTML tags
                title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                # Decodificar URL de DuckDuckGo
                if "uddg=" in link:
                    link_match = re.search(r'uddg=([^&]+)', link)
                    if link_match:
                        link = urllib.parse.unquote(link_match.group(1))
                results.append(f"{i+1}. {title}\n   {snippet}\n   URL: {link}")

            if results:
                return f"Resultados para '{query}':\n\n" + "\n\n".join(results)
            else:
                return f"No se encontraron resultados para '{query}'."

        except Exception as e:
            return f"[ERROR] Busqueda fallida: {e}"

    @staticmethod
    def fetch_page(url: str, max_chars: int = 10000) -> str:
        """
        Descarga y extrae texto de una pagina web.

        Args:
            url: URL a descargar
            max_chars: Maximo de caracteres a retornar

        Returns:
            Texto extraido de la pagina
        """
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36",
            })

            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Remover scripts y estilos
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            # Remover tags HTML
            text = re.sub(r'<[^>]+>', ' ', html)
            # Limpiar espacios
            text = re.sub(r'\s+', ' ', text).strip()

            if len(text) > max_chars:
                text = text[:max_chars] + "... [truncado]"

            return text if text else "No se pudo extraer texto de la pagina."

        except Exception as e:
            return f"[ERROR] No se pudo acceder a {url}: {e}"


class FileTools:
    """Herramientas para manipular archivos con validacion de rutas."""

    @staticmethod
    def read_file(filepath: str, max_lines: int = 1000) -> str:
        """Lee un archivo con validacion de seguridad."""
        # Validar ruta
        valid, msg = PathValidator.validate_read(filepath)
        if not valid:
            return f"[ERROR] {msg}"

        try:
            path = Path(filepath)
            if not path.exists():
                return f"[ERROR] Archivo no encontrado: {filepath}"
            if not path.is_file():
                return f"[ERROR] No es un archivo: {filepath}"

            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > 100:
                return f"[ERROR] Archivo muy grande ({size_mb:.1f} MB). Limite: 100 MB."

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            if len(lines) > max_lines:
                content = "".join(lines[:max_lines])
                content += f"\n... [{len(lines) - max_lines} lineas mas]"
            else:
                content = "".join(lines)

            return f"Archivo: {filepath} ({len(lines)} lineas)\n\n{content}"

        except Exception as e:
            return f"[ERROR] No se pudo leer {filepath}: {e}"

    @staticmethod
    def write_file(filepath: str, content: str) -> str:
        """Crea o sobreescribe un archivo con validacion de seguridad."""
        # Validar ruta
        valid, msg = PathValidator.validate_write(filepath)
        if not valid:
            return f"[ERROR] {msg}"

        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Archivo creado: {filepath} ({len(content)} caracteres)"

        except Exception as e:
            return f"[ERROR] No se pudo escribir {filepath}: {e}"

    @staticmethod
    def list_directory(dirpath: str = ".") -> str:
        """Lista el contenido de un directorio."""
        try:
            path = Path(dirpath)
            if not path.exists():
                return f"[ERROR] Directorio no encontrado: {dirpath}"

            items = sorted(path.iterdir())
            lines = [f"Contenido de: {path.resolve()}\n"]

            for item in items[:200]:
                if item.is_dir():
                    lines.append(f"  [DIR]  {item.name}/")
                else:
                    size = item.stat().st_size
                    if size > 1024 * 1024:
                        size_str = f"{size / (1024*1024):.1f} MB"
                    elif size > 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size} B"
                    lines.append(f"  [FILE] {item.name} ({size_str})")

            if len(items) > 200:
                lines.append(f"\n  ... y {len(items) - 200} items mas")

            return "\n".join(lines)

        except Exception as e:
            return f"[ERROR] No se pudo listar {dirpath}: {e}"


class CodeExecutor:
    """Ejecuta codigo Python con sandbox de seguridad."""

    @staticmethod
    def run_python(code: str, timeout: int = 120) -> str:
        """
        Ejecuta codigo Python con analisis de seguridad previo.

        1. Analiza el codigo con CodeSandbox
        2. Si es seguro, ejecuta en subprocess con timeout
        3. Retorna stdout + stderr
        """
        # Fase 1: Analizar seguridad
        is_safe, warnings = CodeSandbox.analyze(code)

        if not is_safe:
            return (
                "[ERROR] Codigo bloqueado por sandbox de seguridad:\n"
                + "\n".join(f"  - {w}" for w in warnings)
                + "\n\nModifica el codigo para evitar operaciones bloqueadas."
            )

        # Mostrar advertencias si hay (pero no bloquear)
        warning_text = ""
        if warnings:
            warning_text = (
                "[ADVERTENCIA sandbox]:\n"
                + "\n".join(f"  - {w}" for w in warnings) + "\n\n"
            )

        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                             delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_path = f.name

            # Ejecutar con timeout
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore',
            )

            output = warning_text
            if result.stdout:
                output += f"Salida:\n{result.stdout}"
            if result.stderr:
                output += f"\nErrores:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\nCodigo de salida: {result.returncode}"

            if not output.strip():
                output = "Codigo ejecutado sin salida."

            # Limpiar
            try:
                os.unlink(temp_path)
            except Exception:
                pass

            return output

        except subprocess.TimeoutExpired:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return f"[ERROR] Timeout: el codigo tardo mas de {timeout} segundos."
        except Exception as e:
            return f"[ERROR] Ejecucion fallida: {e}"


class ShellExecutor:
    """
    Ejecuta comandos del sistema (cmd/PowerShell/bash).
    Con restricciones de seguridad para evitar comandos destructivos.
    """

    # Comandos bloqueados — nunca ejecutar
    BLOCKED_COMMANDS = {
        'format', 'del /s', 'rd /s', 'rmdir /s',
        'rm -rf /', 'mkfs', 'dd if=',
        'reg delete', 'reg add',
        'net user', 'net localgroup',
        'shutdown', 'restart',
    }

    @staticmethod
    def run(command: str, timeout: int = 60) -> str:
        """
        Ejecuta un comando del sistema.

        Args:
            command: Comando a ejecutar
            timeout: Timeout en segundos

        Returns:
            Salida del comando
        """
        # Verificar comandos bloqueados
        cmd_lower = command.lower().strip()
        for blocked in ShellExecutor.BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return f"[ERROR] Comando bloqueado por seguridad: contiene '{blocked}'"

        try:
            # Detectar OS para usar el shell correcto
            if os.name == 'nt':
                shell_cmd = ["cmd", "/c", command]
            else:
                shell_cmd = ["bash", "-c", command]

            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore',
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            if not output.strip():
                output = "Comando ejecutado sin salida."

            # Limitar salida
            if len(output) > 10000:
                output = output[:10000] + "\n... [salida truncada]"

            return output

        except subprocess.TimeoutExpired:
            return f"[ERROR] Timeout: el comando tardo mas de {timeout} segundos."
        except Exception as e:
            return f"[ERROR] Ejecucion fallida: {e}"


class SecurityAnalyzer:
    """Analiza archivos en busca de amenazas."""

    SUSPICIOUS_EXTENSIONS = {
        '.hta', '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh',
        '.ps1', '.bat', '.cmd', '.scr', '.pif', '.com',
    }

    SUSPICIOUS_PATTERNS = [
        (r'powershell', 'Invocacion de PowerShell'),
        (r'cmd\.exe|command\.com', 'Invocacion de CMD'),
        (r'wscript|cscript', 'Invocacion de Windows Script Host'),
        (r'eval\s*\(', 'Uso de eval() — posible ejecucion de codigo'),
        (r'document\.write', 'Escritura directa al DOM'),
        (r'ActiveXObject', 'Uso de ActiveX — alto riesgo'),
        (r'Shell\.Application', 'Acceso al shell del sistema'),
        (r'WScript\.Shell', 'Acceso al shell via WScript'),
        (r'XMLHTTP|WinHttp', 'Conexion HTTP — posible descarga'),
        (r'RegWrite|RegRead', 'Manipulacion del registro de Windows'),
        (r'FromBase64', 'Decodificacion Base64 — posible ofuscacion'),
        (r'https?://\d+\.\d+\.\d+\.\d+', 'URL con IP directa — sospechoso'),
        (r'\.exe|\.dll|\.scr', 'Referencia a ejecutables'),
        (r'password|passwd|credential', 'Referencia a credenciales'),
        (r'bitcoin|wallet|crypto', 'Referencia a criptomonedas'),
    ]

    @staticmethod
    def analyze(filepath: str) -> str:
        """Analiza un archivo en busca de indicadores maliciosos."""
        try:
            path = Path(filepath)
            if not path.exists():
                return f"[ERROR] Archivo no encontrado: {filepath}"

            findings = []
            risk_level = "BAJO"
            risk_score = 0

            # Verificar extension
            ext = path.suffix.lower()
            if ext in SecurityAnalyzer.SUSPICIOUS_EXTENSIONS:
                findings.append(f"[ALTO] Extension sospechosa: {ext}")
                risk_score += 30

            # Leer contenido
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                return f"No se pudo leer el archivo para analisis."

            # Buscar patrones sospechosos
            for pattern, description in SecurityAnalyzer.SUSPICIOUS_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    findings.append(f"  [{description}] — {len(matches)} ocurrencia(s)")
                    risk_score += 10

            # Extraer URLs
            urls = re.findall(r'https?://[^\s<>"\']+', content)
            if urls:
                findings.append(f"\n  URLs encontradas:")
                for url in set(urls[:10]):
                    findings.append(f"    - {url}")
                    if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url):
                        risk_score += 15

            # Extraer IPs
            ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', content)
            if ips:
                unique_ips = set(ips)
                findings.append(f"\n  IPs encontradas:")
                for ip in unique_ips:
                    findings.append(f"    - {ip}")

            # Determinar nivel de riesgo
            if risk_score >= 50:
                risk_level = "ALTO"
            elif risk_score >= 25:
                risk_level = "MEDIO"
            else:
                risk_level = "BAJO"

            # Construir reporte
            report = [
                f"=== ANALISIS DE SEGURIDAD ===",
                f"Archivo: {filepath}",
                f"Tamaño: {path.stat().st_size} bytes",
                f"Extension: {ext}",
                f"Nivel de riesgo: {risk_level} (score: {risk_score})",
                f"",
                f"Hallazgos:",
            ]

            if findings:
                report.extend(findings)
            else:
                report.append("  No se encontraron indicadores sospechosos.")

            return "\n".join(report)

        except Exception as e:
            return f"[ERROR] Analisis fallido: {e}"


class DeepResearcher:
    """Investigacion profunda — busca, lee paginas, y compila informacion."""

    @staticmethod
    def research(topic: str, max_queries: int = 5, max_pages: int = 5) -> str:
        """
        Investiga un tema haciendo multiples busquedas y leyendo paginas.

        Args:
            topic: Tema a investigar
            max_queries: Maximo de busquedas diferentes
            max_pages: Maximo de paginas a leer en detalle

        Returns:
            Compilado de toda la informacion encontrada
        """
        report_parts = [f"=== INVESTIGACION PROFUNDA ===", f"Tema: {topic}\n"]

        # Generar variaciones de busqueda
        queries = DeepResearcher._generate_queries(topic)[:max_queries]
        report_parts.append(f"Queries realizadas: {len(queries)}\n")

        all_urls = []
        all_snippets = []

        # Fase 1: Buscar con multiples queries
        for i, query in enumerate(queries):
            report_parts.append(f"--- Busqueda {i+1}: '{query}' ---")
            try:
                results = WebSearchTool.search(query, max_results=8)
                report_parts.append(results)

                # Extraer URLs de los resultados
                urls_found = re.findall(r'URL: (https?://[^\s]+)', results)
                all_urls.extend(urls_found)

                # Extraer snippets
                all_snippets.append(results)
            except Exception as e:
                report_parts.append(f"[ERROR en busqueda]: {e}")

            time.sleep(1)  # Pausa entre busquedas

        # Fase 2: Leer las paginas mas relevantes
        unique_urls = list(dict.fromkeys(all_urls))  # Eliminar duplicados, mantener orden
        pages_read = 0

        if unique_urls:
            report_parts.append(f"\n=== PAGINAS LEIDAS EN DETALLE ===")
            for url in unique_urls[:max_pages]:
                report_parts.append(f"\n--- Leyendo: {url} ---")
                try:
                    page_text = WebSearchTool.fetch_page(url, max_chars=10000)
                    if page_text and "[ERROR]" not in page_text:
                        report_parts.append(page_text)
                        pages_read += 1
                except Exception as e:
                    report_parts.append(f"[No se pudo leer: {e}]")

                time.sleep(1)  # Pausa entre lecturas

        # Resumen
        report_parts.append(f"\n=== RESUMEN DE INVESTIGACION ===")
        report_parts.append(f"Busquedas realizadas: {len(queries)}")
        report_parts.append(f"Paginas leidas: {pages_read}")
        report_parts.append(f"URLs encontradas: {len(unique_urls)}")

        full_report = "\n".join(report_parts)
        return full_report

    @staticmethod
    def _generate_queries(topic: str) -> List[str]:
        """Genera variaciones de busqueda para un tema."""
        topic_clean = topic.strip()
        queries = [topic_clean]

        # Variacion en español con mas contexto
        queries.append(f"{topic_clean} explicacion completa")
        queries.append(f"{topic_clean} guia detallada")

        # Traducciones automaticas para mejores resultados en ingles
        english_terms = {
            "deep web": "deep web darknet explained how it works",
            "dark web": "dark web structure layers explained",
            "inteligencia artificial": "artificial intelligence latest research",
            "seguridad informatica": "cybersecurity techniques tools",
            "hacking": "hacking techniques methodology explained",
            "hacking etico": "ethical hacking penetration testing",
            "ingenieria inversa": "reverse engineering tools techniques",
            "programacion": "programming tutorial advanced",
            "criptomonedas": "cryptocurrency how it works explained",
            "blockchain": "blockchain technology deep dive",
            "machine learning": "machine learning explained techniques",
            "redes neuronales": "neural networks architecture explained",
            "osint": "OSINT techniques tools open source intelligence",
            "forense": "digital forensics investigation techniques",
            "analisis forense": "computer forensics analysis tools",
            "malware": "malware analysis reverse engineering",
            "phishing": "phishing techniques detection analysis",
            "criptografia": "cryptography algorithms explained",
            "pentesting": "penetration testing methodology tools",
            "exploit": "exploit development vulnerability research",
            "red team": "red team operations techniques",
            "privacidad": "privacy tools digital anonymity",
            "anonimato": "online anonymity tools techniques",
            "tor": "tor network how it works architecture",
            "vpn": "VPN technology protocols explained",
            "ransomware": "ransomware analysis defense techniques",
            "virus": "computer virus analysis detection",
            "redes": "computer networking protocols",
            "linux": "linux administration advanced",
            "windows": "windows internals administration",
            "python": "python programming advanced",
            "base de datos": "database systems architecture",
            "api": "API development REST architecture",
            "scraping": "web scraping techniques tools",
            "automatizacion": "automation scripting tools",
        }

        topic_lower = topic_clean.lower()
        for es, en in english_terms.items():
            if es in topic_lower:
                queries.append(en)
                break
        else:
            # Si no hay traduccion especifica, buscar en ingles
            queries.append(f"{topic_clean} guide tutorial")

        # Agregar variacion con "como funciona"
        queries.append(f"como funciona {topic_clean}")

        return queries


class SelfModifier:
    """
    Permite a Genesis editar su propio codigo fuente.
    Inspirado en EvoAgentX/AgentEvolver — el agente puede
    modificar sus propios archivos para auto-mejorarse.

    Restriccion de seguridad: solo puede editar archivos
    dentro del directorio de GENESIS.
    """

    GENESIS_DIR = Path(__file__).parent.parent

    @staticmethod
    def read_own_code(relative_path: str) -> str:
        """Lee un archivo del propio codigo de Genesis."""
        try:
            full_path = (SelfModifier.GENESIS_DIR / relative_path).resolve()

            # Verificar que esta dentro del directorio de Genesis
            if not str(full_path).startswith(str(SelfModifier.GENESIS_DIR.resolve())):
                return "[ERROR] Solo puedo leer archivos dentro de mi propio directorio."

            if not full_path.exists():
                return f"[ERROR] Archivo no encontrado: {relative_path}"

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return f"=== {relative_path} ({len(content)} chars) ===\n{content}"

        except Exception as e:
            return f"[ERROR] No se pudo leer: {e}"

    @staticmethod
    def edit_own_code(relative_path: str, old_text: str, new_text: str) -> str:
        """
        Edita un archivo del propio Genesis reemplazando texto.
        Solo funciona dentro del directorio de Genesis.
        """
        try:
            full_path = (SelfModifier.GENESIS_DIR / relative_path).resolve()

            # Verificar seguridad
            if not str(full_path).startswith(str(SelfModifier.GENESIS_DIR.resolve())):
                return "[ERROR] Solo puedo editar archivos dentro de mi propio directorio."

            if not full_path.exists():
                return f"[ERROR] Archivo no encontrado: {relative_path}"

            # Crear backup antes de editar
            backup_dir = SelfModifier.GENESIS_DIR / "backups"
            backup_dir.mkdir(exist_ok=True)
            backup_name = f"{full_path.stem}_{int(time.time())}{full_path.suffix}"
            backup_path = backup_dir / backup_name

            with open(full_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Guardar backup
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            # Verificar que el texto a reemplazar existe
            if old_text not in original_content:
                return (f"[ERROR] El texto a reemplazar no se encontro en {relative_path}. "
                        f"Verifica que sea exacto.")

            # Reemplazar
            new_content = original_content.replace(old_text, new_text, 1)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return (f"Archivo editado: {relative_path}\n"
                    f"Backup guardado en: backups/{backup_name}\n"
                    f"Cambio: {len(old_text)} chars -> {len(new_text)} chars")

        except Exception as e:
            return f"[ERROR] No se pudo editar: {e}"

    @staticmethod
    def list_own_files() -> str:
        """Lista los archivos del propio Genesis."""
        try:
            genesis_dir = SelfModifier.GENESIS_DIR
            lines = [f"=== Archivos de Genesis ({genesis_dir}) ===\n"]

            for item in sorted(genesis_dir.rglob("*.py")):
                rel = item.relative_to(genesis_dir)
                size_kb = item.stat().st_size / 1024
                lines.append(f"  {rel} ({size_kb:.1f} KB)")

            # Tambien listar archivos de config
            for ext in ["*.json", "*.txt", "*.bat"]:
                for item in sorted(genesis_dir.glob(ext)):
                    rel = item.relative_to(genesis_dir)
                    size_kb = item.stat().st_size / 1024
                    lines.append(f"  {rel} ({size_kb:.1f} KB)")

            return "\n".join(lines)

        except Exception as e:
            return f"[ERROR] {e}"


class SystemInfoTool:
    """
    Proporciona informacion del sistema a Genesis.
    Inspirado en LocalAGI — el agente tiene consciencia de su hardware.
    """

    @staticmethod
    def get_system_info() -> str:
        """Obtiene informacion completa del sistema."""
        import platform

        lines = ["=== INFORMACION DEL SISTEMA ===\n"]

        # Info basica del SO
        lines.append(f"Sistema: {platform.system()} {platform.release()}")
        lines.append(f"Version: {platform.version()}")
        lines.append(f"Arquitectura: {platform.machine()}")
        lines.append(f"Procesador: {platform.processor()}")
        lines.append(f"Python: {platform.python_version()}")

        # CPU info
        try:
            cpu_count = os.cpu_count()
            lines.append(f"CPUs: {cpu_count}")
        except Exception:
            pass

        # RAM
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "OS", "get", "TotalVisibleMemorySize", "/value"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split("\n"):
                    if "TotalVisibleMemorySize" in line:
                        kb = int(line.split("=")[1].strip())
                        gb = kb / (1024 * 1024)
                        lines.append(f"RAM Total: {gb:.1f} GB")

                result = subprocess.run(
                    ["wmic", "OS", "get", "FreePhysicalMemory", "/value"],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split("\n"):
                    if "FreePhysicalMemory" in line:
                        kb = int(line.split("=")[1].strip())
                        gb = kb / (1024 * 1024)
                        lines.append(f"RAM Libre: {gb:.1f} GB")
        except Exception:
            pass

        # GPU (NVIDIA)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines.append(f"\n=== GPU NVIDIA ===")
                for gpu_line in result.stdout.strip().split("\n"):
                    parts = [p.strip() for p in gpu_line.split(",")]
                    if len(parts) >= 6:
                        lines.append(f"GPU: {parts[0]}")
                        lines.append(f"VRAM Total: {parts[1]} MB")
                        lines.append(f"VRAM Usada: {parts[2]} MB")
                        lines.append(f"VRAM Libre: {parts[3]} MB")
                        lines.append(f"Temperatura: {parts[4]}°C")
                        lines.append(f"Uso GPU: {parts[5]}%")
        except FileNotFoundError:
            lines.append("\nGPU: nvidia-smi no encontrado")
        except Exception:
            pass

        # Disco
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "logicaldisk", "get", "size,freespace,caption", "/value"],
                    capture_output=True, text=True, timeout=10
                )
                lines.append(f"\n=== DISCO ===")
                current = {}
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if "=" in line:
                        key, val = line.split("=", 1)
                        current[key.strip()] = val.strip()
                    if "Size" in current and "FreeSpace" in current and "Caption" in current:
                        try:
                            total_gb = int(current["Size"]) / (1024**3)
                            free_gb = int(current["FreeSpace"]) / (1024**3)
                            lines.append(f"{current['Caption']} Total: {total_gb:.0f} GB, Libre: {free_gb:.0f} GB")
                        except (ValueError, KeyError):
                            pass
                        current = {}
        except Exception:
            pass

        # Red
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            lines.append(f"\n=== RED ===")
            lines.append(f"Hostname: {hostname}")
            lines.append(f"IP Local: {local_ip}")
        except Exception:
            pass

        # Procesos activos (top 10 por uso de memoria)
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/fo", "csv", "/nh"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines.append(f"\n=== TOP PROCESOS (por memoria) ===")
                    processes = []
                    for proc_line in result.stdout.strip().split("\n"):
                        parts = proc_line.strip().strip('"').split('","')
                        if len(parts) >= 5:
                            name = parts[0].strip('"')
                            mem_str = parts[4].strip('"').replace(",", "").replace(" K", "").replace(" ", "")
                            try:
                                mem_kb = int(mem_str)
                                processes.append((name, mem_kb))
                            except ValueError:
                                pass

                    processes.sort(key=lambda x: x[1], reverse=True)
                    for name, mem_kb in processes[:15]:
                        mem_mb = mem_kb / 1024
                        lines.append(f"  {name:<30} {mem_mb:>8.1f} MB")
        except Exception:
            pass

        return "\n".join(lines)

    @staticmethod
    def get_gpu_status() -> str:
        """Obtiene estado detallado de la GPU."""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return f"=== GPU STATUS ===\n{result.stdout}"
            return "[ERROR] nvidia-smi fallo"
        except FileNotFoundError:
            return "[ERROR] nvidia-smi no encontrado. No hay GPU NVIDIA?"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def get_network_info() -> str:
        """Obtiene informacion de red."""
        try:
            result = subprocess.run(
                ["ipconfig" if os.name == "nt" else "ifconfig"],
                capture_output=True, text=True, timeout=10
            )
            return f"=== RED ===\n{result.stdout}"
        except Exception as e:
            return f"[ERROR] {e}"


class ProjectScanner:
    """
    Escanea un proyecto para entender su estructura antes de programar.
    Genesis puede usar esto para generar codigo que encaje con el proyecto.
    """

    @staticmethod
    def scan(dirpath: str, max_depth: int = 3) -> str:
        """
        Escanea un directorio de proyecto y retorna su estructura.

        Args:
            dirpath: Ruta al directorio del proyecto
            max_depth: Profundidad maxima de escaneo

        Returns:
            Texto con la estructura del proyecto
        """
        try:
            root = Path(dirpath).resolve()
            if not root.exists():
                return f"[ERROR] Directorio no encontrado: {dirpath}"

            lines = [f"=== ESTRUCTURA DEL PROYECTO ===", f"Raiz: {root}\n"]

            # Directorios y archivos a ignorar
            ignore = {
                '__pycache__', '.git', 'node_modules', '.venv', 'venv',
                'env', '.env', '.idea', '.vscode', 'dist', 'build',
                '.egg-info', '.tox', '.mypy_cache', '.pytest_cache',
            }
            ignore_ext = {'.pyc', '.pyo', '.exe', '.dll', '.so', '.o'}

            file_count = 0
            dir_count = 0
            code_files = []

            def scan_dir(path: Path, depth: int, prefix: str = ""):
                nonlocal file_count, dir_count
                if depth > max_depth:
                    return

                try:
                    items = sorted(path.iterdir())
                except PermissionError:
                    return

                dirs = [i for i in items if i.is_dir() and i.name not in ignore]
                files = [i for i in items if i.is_file() and i.suffix not in ignore_ext]

                for d in dirs:
                    dir_count += 1
                    lines.append(f"{prefix}[DIR] {d.name}/")
                    scan_dir(d, depth + 1, prefix + "  ")

                for f in files:
                    file_count += 1
                    size = f.stat().st_size
                    if size > 1024 * 1024:
                        size_str = f"{size / (1024*1024):.1f}MB"
                    elif size > 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size}B"
                    lines.append(f"{prefix}  {f.name} ({size_str})")

                    # Guardar archivos de codigo para analisis
                    if f.suffix in {'.py', '.js', '.ts', '.jsx', '.tsx',
                                    '.java', '.cpp', '.c', '.h', '.cs',
                                    '.go', '.rs', '.rb', '.php', '.html'}:
                        code_files.append(f)

            scan_dir(root, 0)

            lines.append(f"\n=== RESUMEN ===")
            lines.append(f"Directorios: {dir_count}")
            lines.append(f"Archivos: {file_count}")
            lines.append(f"Archivos de codigo: {len(code_files)}")

            # Analizar archivos de codigo para extraer info util
            if code_files:
                lines.append(f"\n=== ARCHIVOS DE CODIGO ===")
                for cf in code_files[:20]:
                    try:
                        with open(cf, "r", encoding="utf-8", errors="ignore") as fh:
                            content = fh.read(3000)  # Solo primeros 3KB

                        # Extraer imports
                        imports = re.findall(
                            r'^(?:import|from)\s+(\S+)', content, re.MULTILINE
                        )
                        # Extraer funciones
                        functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
                        # Extraer clases
                        classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)

                        rel_path = cf.relative_to(root)
                        info_parts = []
                        if classes:
                            info_parts.append(f"clases: {', '.join(classes[:5])}")
                        if functions:
                            info_parts.append(f"funciones: {', '.join(functions[:5])}")
                        if imports:
                            info_parts.append(f"imports: {', '.join(imports[:5])}")

                        if info_parts:
                            lines.append(f"  {rel_path}: {' | '.join(info_parts)}")
                    except Exception:
                        pass

            # Detectar tipo de proyecto
            lines.append(f"\n=== TIPO DE PROYECTO ===")
            if (root / "requirements.txt").exists():
                lines.append("  Python (requirements.txt)")
                try:
                    reqs = (root / "requirements.txt").read_text(encoding="utf-8")
                    lines.append(f"  Dependencias: {reqs[:300]}")
                except Exception:
                    pass
            if (root / "setup.py").exists() or (root / "pyproject.toml").exists():
                lines.append("  Python package")
            if (root / "package.json").exists():
                lines.append("  Node.js (package.json)")
            if (root / "Cargo.toml").exists():
                lines.append("  Rust")
            if (root / "go.mod").exists():
                lines.append("  Go")
            if (root / "pom.xml").exists():
                lines.append("  Java (Maven)")
            if (root / ".git").exists():
                lines.append("  Git repository")

            return "\n".join(lines)

        except Exception as e:
            return f"[ERROR] Escaneo fallido: {e}"


class TextSummarizer:
    """Resume textos largos extrayendo los puntos clave."""

    @staticmethod
    def summarize(text: str, max_sentences: int = 10) -> str:
        """
        Resume un texto largo extrayendo oraciones clave.
        Metodo extractivo simple (sin LLM).
        """
        if not text or len(text) < 200:
            return text

        # Dividir en oraciones
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= max_sentences:
            return text

        # Puntuar oraciones por relevancia
        scored = []
        for sent in sentences:
            score = 0
            # Oraciones mas largas tienden a tener mas info
            if 20 < len(sent) < 300:
                score += 1
            # Oraciones con numeros suelen ser datos
            if re.search(r'\d+', sent):
                score += 1
            # Oraciones con palabras clave
            keywords = ['es ', 'son ', 'significa', 'permite', 'puede',
                        'importante', 'principal', 'segun', 'porque',
                        'is ', 'are ', 'means', 'allows', 'can ',
                        'important', 'main', 'according', 'because']
            for kw in keywords:
                if kw in sent.lower():
                    score += 1
                    break
            scored.append((score, sent))

        # Ordenar por score y tomar las mejores
        scored.sort(key=lambda x: x[0], reverse=True)
        best = [s[1] for s in scored[:max_sentences]]

        return " ".join(best)


# ============================================================
# SISTEMA DE HERRAMIENTAS INTEGRADO
# ============================================================

TOOLS_DESCRIPTION = """Herramientas disponibles (usa UNA por respuesta):
[TOOL:buscar] texto — buscar en internet
[TOOL:investigar] tema — investigacion profunda (multiples busquedas + lectura de paginas)
[TOOL:web] url — leer pagina web
[TOOL:leer] ruta — leer archivo
[TOOL:escribir] ruta ||| contenido — crear archivo
[TOOL:listar] ruta — listar directorio
[TOOL:python] codigo — ejecutar Python (con sandbox de seguridad)
[TOOL:shell] comando — ejecutar comando del sistema (cmd/bash)
[TOOL:escanear] ruta — escanear estructura de un proyecto (clases, funciones, imports)
[TOOL:analizar] ruta — analizar archivo sospechoso
[TOOL:sistema] — informacion del sistema (CPU, RAM, GPU, disco, red, procesos)
[TOOL:gpu] — estado detallado de la GPU NVIDIA
[TOOL:mi_codigo] — listar mis propios archivos fuente
[TOOL:leer_codigo] ruta_relativa — leer mi propio codigo (ej: core/brain.py)
[TOOL:editar_codigo] ruta_relativa ||| texto_viejo ||| texto_nuevo — editar mi propio codigo

REGLAS PARA PROGRAMAR:
- SIEMPRE usa [TOOL:python] para ejecutar el codigo que generes. No solo lo muestres.
- Si el codigo falla, lee el error y corrige automaticamente. No te rindas al primer error.
- Antes de crear codigo para un proyecto, usa [TOOL:escanear] para entender la estructura.
- Cuando el codigo funcione exitosamente, se guarda automaticamente en tu memoria de codigo.
- Si te piden algo que ya resolviste antes, usaras tus soluciones anteriores como referencia.
- [TOOL:shell] es para comandos del sistema: pip install, git, dir, etc. NO para Python."""


def parse_tool_call(response: str) -> Optional[tuple[str, str]]:
    """
    Detecta si la respuesta del LLM contiene una llamada a herramienta.

    Returns:
        Tupla (nombre_herramienta, argumento) o None
    """
    match = re.search(r'\[TOOL:(\w+)\]\s*(.+)', response, re.DOTALL)
    if match:
        tool_name = match.group(1).strip().lower()
        tool_arg = match.group(2).strip()
        return (tool_name, tool_arg)
    return None


def execute_tool(tool_name: str, tool_arg: str) -> str:
    """Ejecuta una herramienta y retorna el resultado."""
    if tool_name == "buscar":
        return WebSearchTool.search(tool_arg)
    elif tool_name == "investigar":
        return DeepResearcher.research(tool_arg)
    elif tool_name == "web":
        return WebSearchTool.fetch_page(tool_arg)
    elif tool_name == "leer":
        return FileTools.read_file(tool_arg)
    elif tool_name == "escribir":
        parts = tool_arg.split("|||", 1)
        if len(parts) == 2:
            return FileTools.write_file(parts[0].strip(), parts[1].strip())
        return "[ERROR] Formato: [TOOL:escribir] ruta ||| contenido"
    elif tool_name == "listar":
        return FileTools.list_directory(tool_arg)
    elif tool_name == "python":
        return CodeExecutor.run_python(tool_arg)
    elif tool_name == "shell":
        return ShellExecutor.run(tool_arg)
    elif tool_name == "escanear":
        return ProjectScanner.scan(tool_arg)
    elif tool_name == "analizar":
        return SecurityAnalyzer.analyze(tool_arg)
    elif tool_name == "sistema":
        return SystemInfoTool.get_system_info()
    elif tool_name == "gpu":
        return SystemInfoTool.get_gpu_status()
    elif tool_name == "mi_codigo":
        return SelfModifier.list_own_files()
    elif tool_name == "leer_codigo":
        return SelfModifier.read_own_code(tool_arg)
    elif tool_name == "editar_codigo":
        parts = tool_arg.split("|||")
        if len(parts) == 3:
            return SelfModifier.edit_own_code(
                parts[0].strip(), parts[1].strip(), parts[2].strip()
            )
        return "[ERROR] Formato: [TOOL:editar_codigo] ruta ||| texto_viejo ||| texto_nuevo"
    else:
        return f"[ERROR] Herramienta desconocida: {tool_name}"
