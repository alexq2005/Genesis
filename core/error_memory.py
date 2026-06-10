"""
GENESIS Error Memory — Aprende de sus errores para no repetirlos.

Cuando Genesis ejecuta codigo y falla, guarda:
- El error exacto
- Que lo causo
- Como se resolvio (si se resolvio)

La proxima vez que encuentre un error similar, ya sabe como arreglarlo
ANTES de intentar. Esto acelera el Coding Agent Loop dramaticamente.

Inspirado en como un programador humano aprende:
"Ah, este error ya lo vi — era por X, se arregla con Y"
"""
import json
import time
import re
from pathlib import Path
from typing import Optional


class ErrorMemory:
    """Memoria de errores — aprende de fallos pasados."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.errors: list[dict] = self._load()

    def _load(self) -> list[dict]:
        """Carga errores desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save(self):
        """Persiste errores a disco."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.errors, f, ensure_ascii=False, indent=2)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def clear(self):
        """Resetea la memoria de errores y elimina el archivo."""
        self.errors = []
        if self.filepath.exists():
            self.filepath.unlink()

    def record_error(self, error_text: str, code: str,
                     fix: str = "", fix_code: str = "") -> dict:
        """
        Registra un error y opcionalmente su solucion.

        Args:
            error_text: El mensaje de error completo
            code: El codigo que causo el error
            fix: Descripcion de como se arreglo
            fix_code: El codigo corregido que funciono

        Returns:
            dict del error registrado
        """
        # Extraer la esencia del error (tipo + mensaje principal)
        error_signature = self._extract_signature(error_text)

        # Verificar si ya existe un error similar
        existing = self._find_similar(error_signature)
        if existing:
            existing["occurrences"] += 1
            existing["last_seen"] = time.time()
            if fix and not existing.get("fix"):
                existing["fix"] = fix
                existing["fix_code"] = fix_code[:2000]
                existing["resolved"] = True
            self._save()
            return existing

        # Nuevo error
        entry = {
            "error_signature": error_signature,
            "error_full": error_text[:1000],
            "code_snippet": code[:1000],
            "fix": fix,
            "fix_code": fix_code[:2000],
            "resolved": bool(fix),
            "occurrences": 1,
            "created": time.time(),
            "last_seen": time.time(),
        }

        self.errors.append(entry)

        # Limitar a 200 errores
        if len(self.errors) > 200:
            # Eliminar los mas viejos no resueltos
            self.errors.sort(key=lambda e: (e["resolved"], e["occurrences"]), reverse=True)
            self.errors = self.errors[:200]

        self._save()
        return entry

    def record_fix(self, error_text: str, fix_code: str):
        """
        Registra la solucion de un error cuando el codigo funciona
        despues de un reintento.
        """
        signature = self._extract_signature(error_text)
        existing = self._find_similar(signature)
        if existing:
            existing["fix"] = f"Codigo corregido automaticamente"
            existing["fix_code"] = fix_code[:2000]
            existing["resolved"] = True
            self._save()

    def find_solution(self, error_text: str) -> Optional[dict]:
        """
        Busca si ya vimos un error similar y tenemos solucion.

        Returns:
            dict con fix y fix_code si encontro solucion, None si no
        """
        signature = self._extract_signature(error_text)
        existing = self._find_similar(signature)

        if existing and existing.get("resolved") and existing.get("fix_code"):
            existing["occurrences"] += 1
            existing["last_seen"] = time.time()
            self._save()
            return existing

        return None

    def get_context_for_prompt(self, error_text: str) -> str:
        """
        Genera contexto de errores conocidos para inyectar en el prompt.
        Si el error actual se parece a uno que ya resolvimos, le dice
        al LLM como arreglarlo.
        """
        solution = self.find_solution(error_text)
        if not solution:
            return ""

        lines = [
            "[ERROR CONOCIDO — Ya resolviste este error antes:]",
            f"- Error: {solution['error_signature']}",
            f"- Solucion anterior: {solution['fix']}",
        ]

        if solution.get("fix_code"):
            # Mostrar solo las primeras lineas del fix
            fix_preview = "\n".join(solution["fix_code"].split("\n")[:15])
            lines.append(f"- Codigo que funciono:\n```python\n{fix_preview}\n```")

        lines.append("INSTRUCCION: Aplica esta solucion conocida. No experimentes.")

        return "\n".join(lines)

    def get_common_errors_context(self) -> str:
        """
        Genera un resumen de errores comunes para inyectar en el prompt.
        Le recuerda a Genesis que errores evitar.
        """
        # Obtener errores frecuentes resueltos
        frequent = [e for e in self.errors if e["occurrences"] >= 2 and e["resolved"]]
        frequent.sort(key=lambda e: e["occurrences"], reverse=True)

        if not frequent:
            return ""

        lines = ["[ERRORES COMUNES QUE YA SABES RESOLVER:]"]
        for err in frequent[:5]:
            lines.append(
                f"- {err['error_signature']} (visto {err['occurrences']}x) "
                f"→ {err['fix'][:100]}"
            )

        return "\n".join(lines)

    def _extract_signature(self, error_text: str) -> str:
        """
        Extrae la 'firma' unica del error — tipo + mensaje principal.
        Esto permite comparar errores de manera flexible.
        """
        # Buscar patron tipico de Python: ExceptionType: message
        match = re.search(
            r'(\w*Error|\w*Exception|\w*Warning):\s*(.+?)(?:\n|$)',
            error_text
        )
        if match:
            error_type = match.group(1)
            message = match.group(2).strip()
            # Normalizar: quitar paths, numeros de linea, nombres especificos
            message = re.sub(r"'[^']*'", "'...'", message)
            message = re.sub(r'"[^"]*"', '"..."', message)
            message = re.sub(r'line \d+', 'line N', message)
            message = re.sub(r'File "[^"]*"', 'File "..."', message)
            return f"{error_type}: {message[:150]}"

        # Si no es un patron de Python, usar las primeras palabras clave
        # Limpiar y tomar lo esencial
        clean = error_text.strip().split("\n")[-1][:200]
        return clean

    def _find_similar(self, signature: str) -> Optional[dict]:
        """Busca un error con firma similar."""
        if not signature:
            return None

        # Busqueda exacta primero
        for err in self.errors:
            if err["error_signature"] == signature:
                return err

        # Busqueda por similitud (tipo de error igual)
        sig_type = signature.split(":")[0] if ":" in signature else ""
        if sig_type:
            for err in self.errors:
                err_type = err["error_signature"].split(":")[0]
                if err_type == sig_type:
                    # Verificar que el mensaje sea similar
                    sig_words = set(signature.lower().split())
                    err_words = set(err["error_signature"].lower().split())
                    overlap = len(sig_words & err_words) / max(len(sig_words | err_words), 1)
                    if overlap > 0.6:
                        return err

        return None

    def format_stats(self) -> str:
        """Formatea estadisticas para mostrar."""
        if not self.errors:
            return "  Sin errores registrados."

        total = len(self.errors)
        resolved = sum(1 for e in self.errors if e["resolved"])
        unresolved = total - resolved
        total_occurrences = sum(e["occurrences"] for e in self.errors)

        lines = [
            f"  Errores unicos: {total}",
            f"  Resueltos: {resolved}",
            f"  Sin resolver: {unresolved}",
            f"  Ocurrencias totales: {total_occurrences}",
        ]

        # Top 3 errores mas frecuentes
        top = sorted(self.errors, key=lambda e: e["occurrences"], reverse=True)[:3]
        if top and top[0]["occurrences"] > 1:
            lines.append(f"\n  Mas frecuentes:")
            for err in top:
                status = "✅" if err["resolved"] else "❌"
                lines.append(
                    f"    {status} {err['error_signature'][:60]} ({err['occurrences']}x)"
                )

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen corto para /status."""
        if not self.errors:
            return "  Sin errores registrados"
        total = len(self.errors)
        resolved = sum(1 for e in self.errors if e["resolved"])
        return f"  Errores: {total} registrados, {resolved} resueltos"
