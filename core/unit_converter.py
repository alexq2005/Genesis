"""
GENESIS Unit Converter — Conversiones de unidades por lenguaje natural.
Soporta: temperatura, distancia, peso, datos, tiempo, volumen, velocidad.
"""
import re
from typing import Optional, Tuple


class UnitConverter:
    """Conversor de unidades con parsing de lenguaje natural."""

    # ── Tablas de conversión (todo relativo a una unidad base) ──

    # Distancia → metros
    DISTANCE = {
        "m": 1, "metro": 1, "metros": 1,
        "km": 1000, "kilometro": 1000, "kilometros": 1000, "kilómetro": 1000, "kilómetros": 1000,
        "cm": 0.01, "centimetro": 0.01, "centimetros": 0.01, "centímetro": 0.01, "centímetros": 0.01,
        "mm": 0.001, "milimetro": 0.001, "milimetros": 0.001, "milímetro": 0.001, "milímetros": 0.001,
        "mi": 1609.344, "milla": 1609.344, "millas": 1609.344,
        "yd": 0.9144, "yarda": 0.9144, "yardas": 0.9144,
        "ft": 0.3048, "pie": 0.3048, "pies": 0.3048,
        "in": 0.0254, "pulgada": 0.0254, "pulgadas": 0.0254,
        "nmi": 1852, "milla nautica": 1852, "millas nauticas": 1852,
    }

    # Peso → gramos
    WEIGHT = {
        "g": 1, "gramo": 1, "gramos": 1,
        "kg": 1000, "kilo": 1000, "kilos": 1000, "kilogramo": 1000, "kilogramos": 1000,
        "mg": 0.001, "miligramo": 0.001, "miligramos": 0.001,
        "lb": 453.592, "libra": 453.592, "libras": 453.592,
        "oz": 28.3495, "onza": 28.3495, "onzas": 28.3495,
        "t": 1_000_000, "tonelada": 1_000_000, "toneladas": 1_000_000,
        "st": 6350.29, "stone": 6350.29,
    }

    # Datos → bytes
    DATA = {
        "b": 1, "byte": 1, "bytes": 1,
        "kb": 1024, "kilobyte": 1024, "kilobytes": 1024,
        "mb": 1024**2, "megabyte": 1024**2, "megabytes": 1024**2,
        "gb": 1024**3, "gigabyte": 1024**3, "gigabytes": 1024**3,
        "tb": 1024**4, "terabyte": 1024**4, "terabytes": 1024**4,
        "pb": 1024**5, "petabyte": 1024**5, "petabytes": 1024**5,
    }

    # Tiempo → segundos
    TIME = {
        "s": 1, "seg": 1, "segundo": 1, "segundos": 1,
        "min": 60, "minuto": 60, "minutos": 60,
        "h": 3600, "hora": 3600, "horas": 3600,
        "dia": 86400, "días": 86400, "dias": 86400, "día": 86400,
        "semana": 604800, "semanas": 604800,
        "mes": 2_592_000, "meses": 2_592_000,
        "año": 31_536_000, "años": 31_536_000, "anio": 31_536_000,
    }

    # Volumen → litros
    VOLUME = {
        "l": 1, "litro": 1, "litros": 1,
        "ml": 0.001, "mililitro": 0.001, "mililitros": 0.001,
        "gal": 3.78541, "galon": 3.78541, "galón": 3.78541, "galones": 3.78541,
        "qt": 0.946353, "cuarto": 0.946353,
        "pt": 0.473176, "pinta": 0.473176, "pintas": 0.473176,
        "cup": 0.236588, "taza": 0.236588, "tazas": 0.236588,
        "fl oz": 0.0295735, "onza liquida": 0.0295735,
    }

    # Velocidad → m/s
    SPEED = {
        "m/s": 1, "metros/s": 1,
        "km/h": 0.277778, "kmh": 0.277778, "kph": 0.277778,
        "mph": 0.44704, "mi/h": 0.44704, "millas/h": 0.44704,
        "nudos": 0.514444, "knots": 0.514444, "kt": 0.514444,
        "ft/s": 0.3048,
    }

    # Categorías agrupadas
    CATEGORIES = {
        "distancia": DISTANCE,
        "peso": WEIGHT,
        "datos": DATA,
        "tiempo": TIME,
        "volumen": VOLUME,
        "velocidad": SPEED,
    }

    # ── Temperatura (casos especiales, no lineales) ───
    @staticmethod
    def _convert_temp(value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """Convierte temperatura entre C, F, K."""
        # Normalizar
        from_u = from_unit.lower().replace("°", "").strip()
        to_u = to_unit.lower().replace("°", "").strip()

        c_aliases = {"c", "celsius", "centigrados", "centígrados", "grados"}
        f_aliases = {"f", "fahrenheit"}
        k_aliases = {"k", "kelvin"}

        # Determinar from
        if from_u in c_aliases:
            celsius = value
        elif from_u in f_aliases:
            celsius = (value - 32) * 5 / 9
        elif from_u in k_aliases:
            celsius = value - 273.15
        else:
            return None

        # Determinar to
        if to_u in c_aliases:
            return celsius
        elif to_u in f_aliases:
            return celsius * 9 / 5 + 32
        elif to_u in k_aliases:
            return celsius + 273.15
        return None

    # ── Parsing de lenguaje natural ───────────────────
    @staticmethod
    def _parse_conversion(text: str) -> Optional[Tuple[float, str, str]]:
        """Extrae (valor, unidad_origen, unidad_destino) del texto natural.
        Soporta: '10 km a millas', 'cuantos metros son 5 pies', '30°C en fahrenheit'
        """
        t = text.lower().strip()

        # Patrón: "X unidad a/en unidad"
        m = re.search(
            r'(-?\d+[.,]?\d*)\s*°?\s*([a-záéíóúñ/]+(?:\s+[a-záéíóúñ]+)?)\s+'
            r'(?:a|en|to|in|son|es)\s+'
            r'°?\s*([a-záéíóúñ/]+(?:\s+[a-záéíóúñ]+)?)',
            t
        )
        if m:
            value = float(m.group(1).replace(",", "."))
            return value, m.group(2).strip(), m.group(3).strip()

        # Patrón: "cuantos/cuántos X son Y unidad"
        m2 = re.search(
            r'(?:cuantos?|cuántos?|cuantas?|cuántas?)\s+'
            r'([a-záéíóúñ/]+(?:\s+[a-záéíóúñ]+)?)\s+'
            r'(?:son|hay en|tiene)\s+'
            r'(-?\d+[.,]?\d*)\s*°?\s*'
            r'([a-záéíóúñ/]+(?:\s+[a-záéíóúñ]+)?)',
            t
        )
        if m2:
            value = float(m2.group(2).replace(",", "."))
            return value, m2.group(3).strip(), m2.group(1).strip()

        return None

    def _find_category(self, unit: str) -> Optional[Tuple[str, dict]]:
        """Encuentra la categoría de una unidad."""
        for cat_name, cat_table in self.CATEGORIES.items():
            if unit in cat_table:
                return cat_name, cat_table
        return None

    # ── Conversión principal ──────────────────────────
    def convert(self, text: str) -> str:
        """Convierte unidades parseando lenguaje natural."""
        parsed = self._parse_conversion(text)
        if not parsed:
            return ("❌ No entendí la conversión. Ejemplos:\n"
                    "  • `10 km a millas`\n"
                    "  • `30°C a fahrenheit`\n"
                    "  • `cuantos metros son 5 pies`\n"
                    "  • `100 gb a mb`\n"
                    "  • `2 horas a minutos`")

        value, from_unit, to_unit = parsed

        # Intentar temperatura primero
        temp_result = self._convert_temp(value, from_unit, to_unit)
        if temp_result is not None:
            return (f"🌡️ **Conversión de temperatura:**\n\n"
                    f"  {value}° {from_unit.upper()} = **{temp_result:.2f}° {to_unit.upper()}**")

        # Buscar en categorías
        from_cat = self._find_category(from_unit)
        to_cat = self._find_category(to_unit)

        if not from_cat:
            return f"❌ No reconozco la unidad: '{from_unit}'"
        if not to_cat:
            return f"❌ No reconozco la unidad: '{to_unit}'"

        cat_name_from, table_from = from_cat
        cat_name_to, table_to = to_cat

        if cat_name_from != cat_name_to:
            return f"❌ No puedo convertir {cat_name_from} a {cat_name_to} — son categorías diferentes."

        # Convertir: valor → unidad base → unidad destino
        base_value = value * table_from[from_unit]
        result = base_value / table_to[to_unit]

        # Formatear resultado
        if result == int(result) and abs(result) < 1e15:
            result_str = f"{int(result):,}"
        elif abs(result) >= 1000:
            result_str = f"{result:,.2f}"
        elif abs(result) < 0.01:
            result_str = f"{result:.6f}"
        else:
            result_str = f"{result:.4f}".rstrip('0').rstrip('.')

        emoji = {
            "distancia": "📏", "peso": "⚖️", "datos": "💾",
            "tiempo": "⏱️", "volumen": "🧪", "velocidad": "🏎️"
        }.get(cat_name_from, "🔄")

        return (f"{emoji} **Conversión de {cat_name_from}:**\n\n"
                f"  {value:g} {from_unit} = **{result_str} {to_unit}**")

    def list_categories(self) -> str:
        """Lista todas las categorías y unidades disponibles."""
        lines = ["🔄 **UNIDADES DISPONIBLES**\n"]
        for cat_name, table in self.CATEGORIES.items():
            # Unique canonical units (skip aliases)
            seen_factors = {}
            for unit, factor in table.items():
                if factor not in seen_factors:
                    seen_factors[factor] = unit
            units = ", ".join(sorted(seen_factors.values()))
            emoji = {"distancia": "📏", "peso": "⚖️", "datos": "💾",
                     "tiempo": "⏱️", "volumen": "🧪", "velocidad": "🏎️"}.get(cat_name, "🔄")
            lines.append(f"  {emoji} **{cat_name.title()}**: {units}")

        lines.append("  🌡️ **Temperatura**: celsius, fahrenheit, kelvin")
        return "\n".join(lines)


# Singleton
unit_converter = UnitConverter()
