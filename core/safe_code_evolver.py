"""
GENESIS — Safe Code Evolver (v4.0)

Evolución de código con validación AST y evaluación de fitness.
Genera mutaciones seguras (rename, refactor, optimize, simplify),
valida sintaxis via ast.parse() y acepta solo si el fitness mejora.

Componentes:
- CodeMutation: registro de una mutación de código
- MutationValidator: valida mutaciones usando ast.parse() y heurísticas
- FitnessFunction: evalúa código en syntax_valid, complexity, readability
- SafeCodeEvolver: coordinador con persistencia y evolución autónoma
"""
import time
import json
import ast
import re
import hashlib
from pathlib import Path


class CodeMutation:
    """Registro de una mutación de código."""

    def __init__(self, original_code: str, mutated_code: str,
                 mutation_type: str = "auto", description: str = ""):
        self.mutation_id = hashlib.md5(
            f"mut_{time.time()}_{mutation_type}".encode()
        ).hexdigest()[:10]
        self.original_code = original_code
        self.mutated_code = mutated_code
        self.mutation_type = mutation_type  # rename, refactor, optimize, simplify
        self.description = description
        self.fitness_delta = 0.0
        self.accepted = False
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.mutation_id,
            "mutation_type": self.mutation_type,
            "description": self.description,
            "fitness_delta": round(self.fitness_delta, 4),
            "accepted": self.accepted,
            "created_at": self.created_at,
            "original_lines": self.original_code.count("\n") + 1,
            "mutated_lines": self.mutated_code.count("\n") + 1,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CodeMutation":
        m = cls(
            original_code="",
            mutated_code="",
            mutation_type=data.get("mutation_type", "auto"),
            description=data.get("description", ""),
        )
        m.mutation_id = data.get("id", m.mutation_id)
        m.fitness_delta = data.get("fitness_delta", 0.0)
        m.accepted = data.get("accepted", False)
        m.created_at = data.get("created_at", time.time())
        return m


class MutationValidator:
    """Valida mutaciones usando ast.parse() para verificar sintaxis."""

    def validate(self, original: str, mutated: str) -> dict:
        """
        Valida que la mutación sea segura.

        Returns:
            dict con 'valid' (bool), 'reason' (str), 'details' (dict)
        """
        result = {"valid": True, "reason": "ok", "details": {}}

        # 1. Verificar que el código mutado sea parseable
        original_valid = self._is_syntax_valid(original)
        mutated_valid = self._is_syntax_valid(mutated)

        if not mutated_valid:
            return {
                "valid": False,
                "reason": "mutated_code_syntax_error",
                "details": {"original_valid": original_valid, "mutated_valid": False},
            }

        # 2. Verificar que no sea idéntico al original
        if original.strip() == mutated.strip():
            return {
                "valid": False,
                "reason": "no_change_detected",
                "details": {"original_valid": original_valid, "mutated_valid": mutated_valid},
            }

        # 3. Verificar que no sea vacío
        if not mutated.strip():
            return {
                "valid": False,
                "reason": "empty_mutation",
                "details": {},
            }

        # 4. Verificar ratio de cambio (no más del 80% de cambio)
        original_lines = set(original.strip().splitlines())
        mutated_lines = set(mutated.strip().splitlines())
        total = max(len(original_lines), 1)
        changed = len(original_lines.symmetric_difference(mutated_lines))
        change_ratio = changed / total

        if change_ratio > 0.8:
            return {
                "valid": False,
                "reason": "excessive_change",
                "details": {"change_ratio": round(change_ratio, 2)},
            }

        # 5. Verificar que no se eliminen todas las funciones/clases
        original_defs = self._count_definitions(original)
        mutated_defs = self._count_definitions(mutated)

        if original_defs > 0 and mutated_defs == 0:
            return {
                "valid": False,
                "reason": "all_definitions_removed",
                "details": {"original_defs": original_defs, "mutated_defs": mutated_defs},
            }

        result["details"] = {
            "original_valid": original_valid,
            "mutated_valid": mutated_valid,
            "change_ratio": round(change_ratio, 2),
            "original_defs": original_defs,
            "mutated_defs": mutated_defs,
        }
        return result

    def _is_syntax_valid(self, code: str) -> bool:
        """Verifica si el código es sintácticamente válido."""
        try:
            ast.parse(code)
            return True
        except (SyntaxError, ValueError):
            return False

    def _count_definitions(self, code: str) -> int:
        """Cuenta funciones y clases definidas en el código."""
        try:
            tree = ast.parse(code)
            count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    count += 1
            return count
        except (SyntaxError, ValueError):
            return 0


class FitnessFunction:
    """
    Evalúa código en tres criterios:
    - syntax_valid: 1 si parseable, 0 si no (via ast.parse)
    - complexity: menor es mejor (cuenta nodos AST, normalizado)
    - readability: ratio líneas / funciones (óptimo entre 5-20)
    """

    def evaluate(self, code: str) -> dict:
        """
        Evalúa el fitness de un fragmento de código.

        Returns:
            dict con 'overall' (0.0-1.0) y scores individuales.
        """
        scores = {}

        # 1. Sintaxis válida (binario)
        try:
            tree = ast.parse(code)
            scores["syntax_valid"] = 1.0
        except (SyntaxError, ValueError):
            return {
                "overall": 0.0,
                "scores": {"syntax_valid": 0.0, "complexity": 0.0, "readability": 0.0},
            }

        # 2. Complejidad (basada en conteo de nodos AST)
        scores["complexity"] = self._score_complexity(tree, code)

        # 3. Legibilidad (ratio de líneas por función)
        scores["readability"] = self._score_readability(tree, code)

        # Overall: promedio ponderado
        weights = {"syntax_valid": 0.35, "complexity": 0.35, "readability": 0.30}
        overall = sum(scores[k] * weights[k] for k in weights)

        return {
            "overall": round(overall, 4),
            "scores": {k: round(v, 4) for k, v in scores.items()},
        }

    def _score_complexity(self, tree: ast.AST, code: str) -> float:
        """
        Complejidad basada en nodos AST por línea.
        Menos nodos por línea = código más simple = mejor score.
        """
        node_count = sum(1 for _ in ast.walk(tree))
        line_count = max(len(code.strip().splitlines()), 1)
        nodes_per_line = node_count / line_count

        # Óptimo: 2-5 nodos por línea
        # < 2: posiblemente trivial
        # > 10: demasiado denso
        if nodes_per_line <= 1:
            return 0.6  # Muy simple, posiblemente solo comentarios
        elif nodes_per_line <= 3:
            return 1.0  # Ideal: limpio
        elif nodes_per_line <= 5:
            return 0.9  # Bueno
        elif nodes_per_line <= 8:
            return 0.7  # Aceptable
        elif nodes_per_line <= 12:
            return 0.4  # Denso
        else:
            return 0.2  # Demasiado complejo

    def _score_readability(self, tree: ast.AST, code: str) -> float:
        """
        Legibilidad basada en ratio de líneas por función.
        Funciones de 5-20 líneas son ideales.
        """
        functions = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        if not functions:
            # Sin funciones: evaluar por longitud total
            line_count = len(code.strip().splitlines())
            if line_count <= 20:
                return 0.8
            elif line_count <= 50:
                return 0.6
            else:
                return 0.4

        total_lines = len(code.strip().splitlines())
        avg_lines_per_func = total_lines / len(functions)

        # Ideal: 5-20 líneas por función
        if 5 <= avg_lines_per_func <= 20:
            return 1.0
        elif 3 <= avg_lines_per_func < 5:
            return 0.8
        elif 20 < avg_lines_per_func <= 40:
            return 0.7
        elif avg_lines_per_func < 3:
            return 0.5  # Funciones demasiado cortas
        else:
            return 0.3  # Funciones demasiado largas


class SafeCodeEvolver:
    """
    Coordinador de evolución segura de código.
    Muta, valida, evalúa fitness, y acepta solo mejoras.
    """

    # Patrones de renaming seguros
    RENAME_PREFIXES = ["_internal_", "optimized_", "refined_", "v2_"]
    SIMPLIFY_PATTERNS = [
        # (patrón, reemplazo, descripción)
        (r"if\s+(\w+)\s*==\s*True\b", r"if \1", "simplify bool comparison"),
        (r"if\s+(\w+)\s*==\s*False\b", r"if not \1", "simplify false comparison"),
        (r"return\s+True\s+if\s+(.+?)\s+else\s+False", r"return bool(\1)", "simplify bool return"),
        (r"for\s+\w+\s+in\s+range\(len\((\w+)\)\)", r"for item in \1", "simplify range(len()) loop"),
        (r"(\w+)\s*=\s*\1\s*\+\s*1", r"\1 += 1", "use augmented assignment"),
        (r"(\w+)\s*=\s*\1\s*-\s*1", r"\1 -= 1", "use augmented assignment"),
    ]

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/code_evolver")
        self.data_file = self.base_dir / "evolver_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.validator = MutationValidator()
        self.fitness_fn = FitnessFunction()

        self.mutations = []          # Historial de mutaciones
        self.max_mutations = 200
        self.total_mutations = 0
        self.successful_mutations = 0
        self.rejected_mutations = 0
        self.fitness_history = []    # Lista de (timestamp, overall_score)
        self.max_fitness_history = 100
        self.enabled = True

        self._load()

    def mutate(self, code: str, mutation_type: str = "auto") -> CodeMutation:
        """
        Genera una mutación del código.

        Args:
            code: código fuente original
            mutation_type: 'rename', 'simplify', 'optimize', 'refactor', 'auto'

        Returns:
            CodeMutation con el código mutado
        """
        if not code.strip():
            return None

        if mutation_type == "auto":
            mutation_type = self._select_mutation_type(code)

        mutated = code
        description = ""

        if mutation_type == "rename":
            mutated, description = self._mutate_rename(code)
        elif mutation_type == "simplify":
            mutated, description = self._mutate_simplify(code)
        elif mutation_type == "optimize":
            mutated, description = self._mutate_optimize(code)
        elif mutation_type == "refactor":
            mutated, description = self._mutate_refactor(code)

        if mutated == code:
            description = "no mutation applied"

        mutation = CodeMutation(
            original_code=code,
            mutated_code=mutated,
            mutation_type=mutation_type,
            description=description,
        )
        return mutation

    def validate(self, original: str, mutated: str) -> dict:
        """Ejecuta MutationValidator, retorna {valid, reason, details}."""
        return self.validator.validate(original, mutated)

    def evaluate_fitness(self, code: str) -> dict:
        """Ejecuta FitnessFunction, retorna score dict."""
        return self.fitness_fn.evaluate(code)

    def attempt_evolution(self, code: str, mutation_type: str = "auto") -> dict:
        """
        Pipeline completo: mutate -> validate -> evaluate -> accept/reject.

        Returns:
            dict con 'success', 'mutation', 'original_fitness',
            'mutated_fitness', 'fitness_delta', 'reason'
        """
        if not self.enabled:
            return {"success": False, "reason": "evolver_disabled"}

        # 1. Generar mutación
        mutation = self.mutate(code, mutation_type)
        if not mutation:
            return {"success": False, "reason": "empty_code"}

        # 2. Validar
        validation = self.validate(mutation.original_code, mutation.mutated_code)
        if not validation["valid"]:
            self.rejected_mutations += 1
            self.total_mutations += 1
            mutation.accepted = False
            self._record_mutation(mutation)
            return {
                "success": False,
                "reason": f"validation_failed: {validation['reason']}",
                "mutation": mutation.to_dict(),
                "validation": validation,
            }

        # 3. Evaluar fitness de ambos
        original_fitness = self.evaluate_fitness(mutation.original_code)
        mutated_fitness = self.evaluate_fitness(mutation.mutated_code)

        fitness_delta = mutated_fitness["overall"] - original_fitness["overall"]
        mutation.fitness_delta = fitness_delta

        # 4. Aceptar solo si fitness mejora o se mantiene
        if fitness_delta >= 0:
            mutation.accepted = True
            self.successful_mutations += 1
            self.fitness_history.append((time.time(), mutated_fitness["overall"]))
            if len(self.fitness_history) > self.max_fitness_history:
                self.fitness_history = self.fitness_history[-self.max_fitness_history:]
        else:
            mutation.accepted = False
            self.rejected_mutations += 1

        self.total_mutations += 1
        self._record_mutation(mutation)

        # Persistir periódicamente
        if self.total_mutations % 10 == 0:
            self.save()

        return {
            "success": mutation.accepted,
            "reason": "accepted" if mutation.accepted else "fitness_decreased",
            "mutation": mutation.to_dict(),
            "original_fitness": original_fitness,
            "mutated_fitness": mutated_fitness,
            "fitness_delta": round(fitness_delta, 4),
        }

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Inyecta sugerencias de evolución en el prompt."""
        if not self.enabled or self.total_mutations == 0:
            return ""

        lines = ["[CODE EVOLUTION SUGGESTIONS]"]

        # Tasa de éxito
        if self.total_mutations > 0:
            success_rate = self.successful_mutations / self.total_mutations
            lines.append(f"  Success rate: {success_rate:.0%} "
                         f"({self.successful_mutations}/{self.total_mutations})")

        # Tendencia de fitness
        if len(self.fitness_history) >= 2:
            recent = [f for _, f in self.fitness_history[-5:]]
            older = [f for _, f in self.fitness_history[:5]]
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / len(older)
            trend = "improving" if avg_recent > avg_older else "stable"
            lines.append(f"  Fitness trend: {trend} (current avg: {avg_recent:.3f})")

        # Sugerencias basadas en el historial
        recent_rejected = [
            m for m in self.mutations[-10:]
            if not m.get("accepted", False)
        ]
        if len(recent_rejected) > 5:
            lines.append("  Hint: many mutations rejected, try simpler changes")

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        """Estadísticas completas."""
        avg_fitness = 0.0
        if self.fitness_history:
            avg_fitness = sum(f for _, f in self.fitness_history) / len(self.fitness_history)

        return {
            "total_mutations": self.total_mutations,
            "successful_mutations": self.successful_mutations,
            "rejected_mutations": self.rejected_mutations,
            "success_rate": round(
                self.successful_mutations / max(self.total_mutations, 1), 3
            ),
            "avg_fitness": round(avg_fitness, 4),
            "fitness_samples": len(self.fitness_history),
            "stored_mutations": len(self.mutations),
            "enabled": self.enabled,
        }

    def status(self) -> str:
        """Status string para /status."""
        rate = self.successful_mutations / max(self.total_mutations, 1)
        return (f"Mutaciones: {self.total_mutations} | "
                f"Exitosas: {self.successful_mutations} ({rate:.0%}) | "
                f"Rechazadas: {self.rejected_mutations}")

    def generate_report(self) -> str:
        """Reporte completo de evolución."""
        lines = ["=== SAFE CODE EVOLVER REPORT ==="]
        lines.append(f"Total mutaciones: {self.total_mutations}")
        lines.append(f"Exitosas: {self.successful_mutations}")
        lines.append(f"Rechazadas: {self.rejected_mutations}")
        rate = self.successful_mutations / max(self.total_mutations, 1)
        lines.append(f"Tasa de éxito: {rate:.1%}")

        # Fitness history
        if self.fitness_history:
            scores = [f for _, f in self.fitness_history]
            lines.append(f"\nFitness promedio: {sum(scores) / len(scores):.4f}")
            lines.append(f"Fitness máximo: {max(scores):.4f}")
            lines.append(f"Fitness mínimo: {min(scores):.4f}")

        # Últimas mutaciones
        if self.mutations:
            lines.append(f"\nÚltimas mutaciones:")
            for m in self.mutations[-5:]:
                status = "OK" if m.get("accepted") else "REJECT"
                lines.append(f"  [{status}] {m.get('mutation_type', '?')}: "
                             f"{m.get('description', '')[:60]} "
                             f"(delta={m.get('fitness_delta', 0):.3f})")

        # Por tipo
        type_counts = {}
        for m in self.mutations:
            t = m.get("mutation_type", "unknown")
            if t not in type_counts:
                type_counts[t] = {"total": 0, "accepted": 0}
            type_counts[t]["total"] += 1
            if m.get("accepted"):
                type_counts[t]["accepted"] += 1

        if type_counts:
            lines.append(f"\nPor tipo de mutación:")
            for t, counts in sorted(type_counts.items()):
                rate_t = counts["accepted"] / max(counts["total"], 1)
                lines.append(f"  {t}: {counts['accepted']}/{counts['total']} ({rate_t:.0%})")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado completo."""
        data = {
            "total_mutations": self.total_mutations,
            "successful_mutations": self.successful_mutations,
            "rejected_mutations": self.rejected_mutations,
            "mutations": self.mutations[-self.max_mutations:],
            "fitness_history": self.fitness_history[-self.max_fitness_history:],
            "enabled": self.enabled,
        }
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _load(self):
        """Carga estado previo si existe."""
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_mutations = data.get("total_mutations", 0)
            self.successful_mutations = data.get("successful_mutations", 0)
            self.rejected_mutations = data.get("rejected_mutations", 0)
            self.mutations = data.get("mutations", [])
            self.fitness_history = data.get("fitness_history", [])
            self.enabled = data.get("enabled", True)
        except Exception:
            pass

    def clear(self):
        """Resetea todo el estado."""
        self.mutations = []
        self.fitness_history = []
        self.total_mutations = 0
        self.successful_mutations = 0
        self.rejected_mutations = 0
        if self.data_file.exists():
            self.data_file.unlink()

    # --- Mutation strategies ---

    def _select_mutation_type(self, code: str) -> str:
        """Selecciona el mejor tipo de mutación para el código dado."""
        # Si hay patrones simplificables, preferir simplify
        for pattern, _, _ in self.SIMPLIFY_PATTERNS:
            if re.search(pattern, code):
                return "simplify"

        # Si hay variables de un solo carácter, preferir rename
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and len(node.id) == 1 and node.id not in ("_", "i", "j", "k"):
                    return "rename"
        except (SyntaxError, ValueError):
            pass

        # Si hay funciones largas, preferir refactor
        lines = code.strip().splitlines()
        if len(lines) > 30:
            return "refactor"

        return "optimize"

    def _mutate_rename(self, code: str) -> tuple:
        """Renombra variables de un solo carácter a nombres descriptivos."""
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError):
            return code, "parse_error"

        # Encontrar variables de un solo carácter (excepto i, j, k, _)
        single_char_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and len(node.id) == 1:
                if node.id not in ("_", "i", "j", "k", "x", "y"):
                    single_char_vars.add(node.id)

        if not single_char_vars:
            # Intentar renombrar variables cortas (2 chars)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and len(node.id) == 2:
                    if node.id not in ("os", "re", "io", "db", "fn", "if", "in", "or"):
                        single_char_vars.add(node.id)

        if not single_char_vars:
            return code, "no_renameable_vars"

        mutated = code
        renamed = []
        name_map = {"a": "alpha", "b": "beta", "c": "count", "d": "data",
                     "e": "element", "f": "flag", "g": "group", "h": "handle",
                     "l": "length", "m": "mapping", "n": "number", "o": "obj",
                     "p": "param", "q": "query", "r": "result", "s": "string",
                     "t": "temp", "u": "unit", "v": "value", "w": "weight",
                     "z": "zero"}

        for var in sorted(single_char_vars):
            new_name = name_map.get(var, f"var_{var}")
            # Solo renombrar como palabra completa
            pattern = r'\b' + re.escape(var) + r'\b'
            mutated = re.sub(pattern, new_name, mutated)
            renamed.append(f"{var}->{new_name}")

        desc = f"renamed: {', '.join(renamed[:5])}"
        return mutated, desc

    def _mutate_simplify(self, code: str) -> tuple:
        """Aplica simplificaciones seguras basadas en patrones."""
        mutated = code
        applied = []

        for pattern, replacement, desc in self.SIMPLIFY_PATTERNS:
            new_code = re.sub(pattern, replacement, mutated)
            if new_code != mutated:
                mutated = new_code
                applied.append(desc)

        if not applied:
            return code, "no_simplifications_found"

        return mutated, f"simplified: {', '.join(applied[:3])}"

    def _mutate_optimize(self, code: str) -> tuple:
        """Optimizaciones menores: eliminar pass innecesarios, espacios."""
        mutated = code
        applied = []

        # Eliminar líneas 'pass' redundantes (dentro de bloques que tienen otro contenido)
        lines = mutated.splitlines()
        optimized_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "pass":
                # Verificar si hay más contenido en el bloque
                indent = len(line) - len(line.lstrip())
                has_sibling = False
                for j in range(max(0, i - 3), min(len(lines), i + 3)):
                    if j != i:
                        other = lines[j]
                        other_indent = len(other) - len(other.lstrip())
                        if other_indent == indent and other.strip() and other.strip() != "pass":
                            has_sibling = True
                            break
                if has_sibling:
                    applied.append("removed redundant pass")
                    continue
            optimized_lines.append(line)

        if optimized_lines != lines:
            mutated = "\n".join(optimized_lines)

        # Eliminar múltiples líneas en blanco consecutivas
        while "\n\n\n" in mutated:
            mutated = mutated.replace("\n\n\n", "\n\n")
            if "collapse_blanks" not in applied:
                applied.append("collapse_blanks")

        if not applied:
            return code, "no_optimizations_found"

        return mutated, f"optimized: {', '.join(applied[:3])}"

    def _mutate_refactor(self, code: str) -> tuple:
        """Refactoring: añade docstrings a funciones sin ellas."""
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError):
            return code, "parse_error"

        lines = code.splitlines()
        insertions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Verificar si ya tiene docstring
                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Constant, ast.Str))
                )
                if not has_docstring and node.body:
                    # Calcular indentación del body
                    body_line = node.body[0].lineno - 1
                    if body_line < len(lines):
                        indent = len(lines[body_line]) - len(lines[body_line].lstrip())
                        indent_str = " " * indent
                        # Generar docstring basado en nombre
                        func_name = node.name.replace("_", " ")
                        docstring = f'{indent_str}"""{func_name.capitalize()}."""'
                        insertions.append((body_line, docstring))

        if not insertions:
            return code, "no_refactoring_needed"

        # Insertar docstrings (de abajo hacia arriba para no desplazar indices)
        for line_idx, docstring in sorted(insertions, reverse=True):
            lines.insert(line_idx, docstring)

        mutated = "\n".join(lines)
        return mutated, f"added {len(insertions)} docstring(s)"

    def _record_mutation(self, mutation: CodeMutation):
        """Registra una mutación en el historial."""
        self.mutations.append(mutation.to_dict())
        if len(self.mutations) > self.max_mutations:
            self.mutations = self.mutations[-self.max_mutations:]
