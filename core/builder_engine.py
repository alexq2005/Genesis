"""
GENESIS Builder Engine — Desarrollo y construcción autónoma de proyectos.

A diferencia del [TOOL:python] (que ejecuta UN snippet inline), el BuilderEngine
construye PROYECTOS multi-archivo REALES y los deja FUNCIONANDO:

  spec → planificar archivos → generar con qwen-coder → escribir en workspace
       → EJECUTAR → leer errores reales → corregir → repetir hasta que corre limpio

Principios:
- Usa el modelo de CÓDIGO (qwen2.5-coder), no el conversacional (8B genera código roto).
- Verificación por EJECUCIÓN real, no por opinión del LLM (anti-teatro).
- Escribe en un workspace aislado (genera_media/projects), nunca en core/.
- Guard de seguridad: bloquea patrones destructivos antes de ejecutar.
- Idempotente y barato de fallar: cada paso envuelto, reporta con datos reales.
"""
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional


# Patrones destructivos: si el código generado los contiene, NO se ejecuta.
_DANGEROUS = [
    "shutil.rmtree", "os.remove", "os.unlink", "os.rmdir",
    "rmdir /s", "rd /s", "del /", "format ", "mkfs",
    ":(){ :|:& };:", "shutdown", "reboot",
    "os.system(", "subprocess.Popen", "subprocess.call", "subprocess.run",
    "socket.", "urllib.request", "requests.get", "requests.post",
]

# Formato de archivo que el modelo debe seguir (parseable y robusto)
_FILE_RE = re.compile(
    r"===\s*FILE:\s*(?P<path>[^\n=]+?)\s*===\s*\n(?P<body>.*?)(?=\n===\s*(?:FILE:|END)\b|\Z)",
    re.DOTALL,
)


class BuildResult:
    """Resultado de una construcción."""
    def __init__(self):
        self.success = False
        self.project_dir = ""
        self.files: list[str] = []
        self.entry = ""
        self.iterations = 0
        self.output = ""
        self.error = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success, "project_dir": self.project_dir,
            "files": self.files, "entry": self.entry,
            "iterations": self.iterations,
            "output": self.output[:1500], "error": self.error[:800],
        }


class BuilderEngine:
    """Construye proyectos reales con un loop generar→ejecutar→corregir."""

    def __init__(self, brain, base_dir: Optional[Path] = None, logger=None):
        """
        Args:
            brain: ProviderRouter o Brain. Si tiene get_coding_brain(), se usa qwen.
            base_dir: raíz de Genesis (los proyectos van a base_dir/generated_media/projects)
            logger: GenesisLogger opcional
        """
        self.brain = brain
        self.base_dir = (base_dir or Path(__file__).parent.parent).resolve()
        self.projects_dir = self.base_dir / "generated_media" / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.log = logger
        self.builds: list[dict] = []
        # Cola de objetivos para construcción AUTÓNOMA (el heartbeat la procesa).
        self._queue_file = self.base_dir / "memory_data" / "build_queue.json"
        self.queue: list[str] = self._load_queue()

    def _load_queue(self) -> list:
        try:
            from core.safe_io import safe_read_json
            return safe_read_json(self._queue_file, default=[]) or []
        except Exception:
            return []

    def _save_queue(self):
        try:
            from core.safe_io import safe_write_json
            safe_write_json(self._queue_file, self.queue, create_backup=False)
        except Exception:
            pass

    def queue_goal(self, spec: str) -> int:
        """Agrega un objetivo de construcción a la cola autónoma. Retorna posición."""
        self.queue.append(spec.strip())
        self._save_queue()
        return len(self.queue)

    def process_next(self) -> Optional[dict]:
        """Construye el siguiente objetivo de la cola (lo usa el loop autónomo).
        Retorna el resultado, o None si la cola está vacía."""
        if not self.queue:
            return None
        spec = self.queue.pop(0)
        self._save_queue()
        res = self.build(spec, max_iters=4, run_timeout=45)
        return res.to_dict()

    # ----------------------------------------------------------------
    def _coding_brain(self):
        """Brain de código (qwen) si está disponible."""
        if hasattr(self.brain, "get_coding_brain"):
            try:
                return self.brain.get_coding_brain()
            except Exception:
                pass
        return self.brain

    def _think(self, system: str, user: str, temperature: float = 0.2) -> str:
        brain = self._coding_brain()
        # max_tokens alto: proyectos multi-archivo no deben truncarse a mitad.
        return brain.think(system, [{"role": "user", "content": user}],
                           temperature=temperature, max_tokens=8192)

    def _safe(self, code: str) -> Optional[str]:
        """Devuelve el patrón peligroso encontrado, o None si es seguro."""
        low = code
        for p in _DANGEROUS:
            if p in low:
                return p
        return None

    def _parse_files(self, text: str) -> list[tuple]:
        """Extrae [(path, content)] del formato === FILE: x === ... ."""
        out = []
        for m in _FILE_RE.finditer(text):
            path = m.group("path").strip().strip("`").replace("\\", "/")
            body = m.group("body")
            # Limpiar fences markdown si el modelo los metió
            body = re.sub(r"^```[a-zA-Z0-9]*\n", "", body)
            body = re.sub(r"\n```\s*$", "", body)
            if path and not path.startswith("/") and ".." not in path:
                out.append((path, body.rstrip() + "\n"))
        return out

    def _write_files(self, proj: Path, files: list[tuple]):
        for rel, content in files:
            dest = (proj / rel).resolve()
            # Containment: nunca escribir fuera del proyecto
            if not str(dest).startswith(str(proj.resolve())):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    def _run(self, proj: Path, entry: str, timeout: int = 60) -> tuple:
        """Ejecuta el entry point. Retorna (ok, salida_combinada)."""
        entry_path = (proj / entry).resolve()
        if not str(entry_path).startswith(str(proj.resolve())) or not entry_path.exists():
            return False, f"[entry no existe: {entry}]"
        try:
            r = subprocess.run(
                [sys.executable, str(entry_path)],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(proj), encoding="utf-8", errors="replace",
            )
            out = (r.stdout or "") + (("\n[STDERR]\n" + r.stderr) if r.stderr else "")
            ok = r.returncode == 0 and "Traceback" not in (r.stderr or "")
            return ok, out.strip()
        except subprocess.TimeoutExpired:
            return False, f"[TIMEOUT tras {timeout}s — posible input() o loop infinito]"
        except Exception as e:
            return False, f"[error ejecutando: {e}]"

    def _log(self, action: str, detail: str):
        if self.log:
            try:
                self.log.info(f"[Builder] {action}: {detail}")
            except Exception:
                pass

    # ----------------------------------------------------------------
    def build(self, spec: str, max_iters: int = 4, run_timeout: int = 60) -> BuildResult:
        """Construye un proyecto a partir de una especificación y lo deja corriendo."""
        res = BuildResult()
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^a-z0-9_]+", "_", spec.lower())[:30].strip("_") or "proyecto"
        proj = self.projects_dir / f"{safe_name}_{ts}"
        proj.mkdir(parents=True, exist_ok=True)
        res.project_dir = str(proj)
        self._log("INICIO", f"{spec[:60]} → {proj.name}")

        sys_prompt = (
            "Eres un ingeniero de software senior. Generas proyectos Python COMPLETOS "
            "y FUNCIONALES. Responde SOLO con archivos en este formato EXACTO, sin "
            "explicaciones fuera de los bloques:\n"
            "=== FILE: main.py ===\n<codigo completo>\n=== END ===\n"
            "=== FILE: otro.py ===\n<codigo>\n=== END ===\n"
            "Reglas: el proyecto debe correr con `python main.py` (entry = main.py). "
            "Código autocontenido, solo librería estándar de Python (sin pip externos, "
            "sin red, sin borrar archivos). Si necesita mostrar resultado, usa print(). "
            "Incluye toda la lógica; nada de TODO ni placeholders."
        )
        user = f"Construye este proyecto:\n\n{spec}\n\nEntry point: main.py"

        last_err = ""
        for it in range(1, max_iters + 1):
            res.iterations = it
            if it == 1:
                gen = self._think(sys_prompt, user)
            else:
                fix_user = (
                    f"El proyecto falló al ejecutarse. Error real:\n```\n{last_err[:1500]}\n```\n\n"
                    f"Especificación original: {spec}\n\n"
                    f"Devuelve los archivos CORREGIDOS (formato === FILE: ... ===). "
                    f"Arregla la causa del error. Entry = main.py."
                )
                gen = self._think(sys_prompt, fix_user)

            files = self._parse_files(gen)
            if not files:
                last_err = "el modelo no devolvió archivos en el formato esperado"
                self._log("REINTENTO", f"iter {it}: sin archivos parseables")
                continue

            # Guard de seguridad sobre TODO el código antes de escribir/ejecutar
            danger = self._safe("\n".join(c for _, c in files))
            if danger:
                res.error = f"Bloqueado por seguridad: patrón '{danger}' en el código generado"
                self._log("BLOQUEADO", danger)
                self.builds.append(res.to_dict())
                return res

            self._write_files(proj, files)
            res.files = [p for p, _ in files]
            res.entry = "main.py" if any(p == "main.py" for p, _ in files) else (res.files[0] if res.files else "")

            ok, out = self._run(proj, res.entry, timeout=run_timeout)
            res.output = out
            self._log("EJECUTADO", f"iter {it}: {'OK' if ok else 'FALLO'}")
            if ok:
                res.success = True
                self.builds.append(res.to_dict())
                return res
            last_err = out

        res.error = f"No quedó funcionando tras {max_iters} iteraciones. Último error: {last_err[:400]}"
        self.builds.append(res.to_dict())
        return res

    # ----------------------------------------------------------------
    def status(self) -> str:
        ok = sum(1 for b in self.builds if b.get("success"))
        return f"  Proyectos construidos: {len(self.builds)} ({ok} funcionando)\n  Carpeta: {self.projects_dir}"

    def get_stats(self) -> dict:
        return {
            "total_builds": len(self.builds),
            "successful": sum(1 for b in self.builds if b.get("success")),
            "projects_dir": str(self.projects_dir),
        }

    def save(self):
        pass  # estado efímero; los proyectos viven en disco
