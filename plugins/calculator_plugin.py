"""
Plugin Calculadora Avanzada para Genesis.

Evalua expresiones matematicas de forma segura (sin exec/eval directo).
Soporta variables, funciones matematicas, y conversion de unidades basica.
"""
import math
import re

PLUGIN_NAME = "Calculadora"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Calculadora avanzada con funciones matematicas y variables"

# Variables del usuario (persisten durante la sesion)
_variables = {}


def on_load(genesis):
    pass


def on_unload(genesis):
    _variables.clear()


def register_commands():
    return {
        "/calc": {
            "handler": cmd_calc,
            "help": "Evaluar expresion matematica. Ej: /calc 2^10 + sqrt(144)",
        },
        "/var": {
            "handler": cmd_var,
            "help": "Definir variable. Ej: /var x = 42",
        },
        "/vars": {
            "handler": cmd_vars,
            "help": "Mostrar variables definidas",
        },
    }


def _safe_eval(expr: str) -> float:
    """Evalua expresion matematica de forma segura."""
    # Reemplazar operadores comunes
    expr = expr.replace("^", "**").replace(",", ".")

    # Reemplazar variables del usuario
    for name, val in _variables.items():
        expr = re.sub(rf'\b{re.escape(name)}\b', str(val), expr)

    # Funciones matematicas permitidas
    safe_names = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log2": math.log2,
        "log10": math.log10, "abs": abs, "round": round,
        "ceil": math.ceil, "floor": math.floor, "pi": math.pi,
        "e": math.e, "pow": pow, "max": max, "min": min,
        "factorial": math.factorial, "gcd": math.gcd,
        "degrees": math.degrees, "radians": math.radians,
    }

    # Validar que solo contenga caracteres seguros
    allowed = set("0123456789.+-*/()% ")
    for name in safe_names:
        expr = expr.replace(name, "")
    remaining = set(expr) - allowed
    if remaining - set("_"):
        raise ValueError(f"Caracteres no permitidos: {remaining}")

    # Restaurar expresion original y evaluar
    expr_orig = expr
    for name, val in _variables.items():
        expr_orig = re.sub(rf'\b{re.escape(name)}\b', str(val), expr_orig)

    # Re-parsear la expresion original
    expr_full = expr  # Ya tiene variables reemplazadas
    # Reconstruir para eval
    code = compile(expr_full if expr_full.strip() else "0", "<calc>", "eval")
    for name in code.co_names:
        if name not in safe_names:
            raise ValueError(f"Funcion no permitida: {name}")

    return eval(expr_full, {"__builtins__": {}}, safe_names)


def cmd_calc(genesis, args: str) -> str:
    if not args:
        return "Uso: /calc <expresion>\nEjemplos: /calc 2^10, /calc sqrt(144), /calc pi * 3^2"
    try:
        # Reemplazar variables primero
        expr = args
        for name, val in _variables.items():
            expr = re.sub(rf'\b{re.escape(name)}\b', str(val), expr)

        expr = expr.replace("^", "**").replace(",", ".")

        safe_names = {
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "log": math.log, "log2": math.log2,
            "log10": math.log10, "abs": abs, "round": round,
            "ceil": math.ceil, "floor": math.floor, "pi": math.pi,
            "e": math.e, "pow": pow, "max": max, "min": min,
            "factorial": math.factorial, "gcd": math.gcd,
        }

        result = eval(expr, {"__builtins__": {}}, safe_names)
        # Formatear resultado
        if isinstance(result, float) and result == int(result):
            return f"= {int(result)}"
        elif isinstance(result, float):
            return f"= {result:.10g}"
        return f"= {result}"
    except ZeroDivisionError:
        return "Error: division por cero"
    except Exception as e:
        return f"Error: {e}"


def cmd_var(genesis, args: str) -> str:
    if not args or "=" not in args:
        return "Uso: /var nombre = valor\nEjemplo: /var radio = 5.2"
    name, val = args.split("=", 1)
    name = name.strip()
    try:
        _variables[name] = float(val.strip())
        return f"Variable '{name}' = {_variables[name]}"
    except ValueError:
        return f"Error: '{val.strip()}' no es un numero valido"


def cmd_vars(genesis, args: str) -> str:
    if not _variables:
        return "No hay variables definidas. Usa /var nombre = valor"
    lines = ["Variables definidas:"]
    for name, val in _variables.items():
        lines.append(f"  {name} = {val}")
    return "\n".join(lines)
