"""
GENESIS — Entity Extractor.

Extrae entidades de documentos usando regex y opcionalmente LLM.
Detecta: emails, teléfonos, fechas, montos, URLs, CUIT/CUIL, DNI, etc.
"""
import json
import re


class EntityExtractor:
    """Extrae entidades de documentos usando regex y opcionalmente LLM."""

    # Patrones regex para entidades comunes
    ENTITY_PATTERNS = {
        "emails": r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        "telefonos": r'(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}',
        "fechas": r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}',
        "montos": r'[\$€£]\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:pesos|dolares|euros|USD|ARS|EUR|usd|ars)',
        "porcentajes": r'\d+[.,]?\d*\s*%',
        "cuit_cuil": r'\b\d{2}\-\d{7,8}\-\d\b',
        "dni": r'\b\d{2}\.?\d{3}\.?\d{3}\b',
        "urls": r'https?://[^\s<>"]+',
        "ips": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }

    def extract_regex(self, text: str) -> dict:
        """
        Extraccion rapida por regex — sin LLM, instantanea.

        Returns:
            Dict con tipo de entidad -> lista de valores unicos
        """
        entities = {}
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                # Deduplicar manteniendo orden
                unique = list(dict.fromkeys(matches))
                entities[entity_type] = unique
        return entities

    def extract_with_llm(self, chunk_text: str, brain, entity_types: list = None) -> dict:
        """
        Extraccion profunda usando LLM para entidades semanticas.

        Args:
            chunk_text: Texto del chunk a analizar
            brain: Instancia de Brain para llamar al LLM
            entity_types: Lista de tipos a extraer (None = todos)

        Returns:
            Dict con entidades extraidas
        """
        if not brain:
            return {}

        types_str = ", ".join(entity_types) if entity_types else "personas, organizaciones, lugares, fechas_con_contexto, temas_clave, productos, cantidades"

        prompt = f"""Analiza el siguiente texto y extrae las entidades mencionadas.
Tipos a extraer: {types_str}

REGLAS:
- Retorna SOLO un JSON valido, sin texto adicional
- Cada tipo es una lista de strings
- Si no hay entidades de un tipo, usa lista vacia []
- NO inventes entidades que no esten en el texto

Texto a analizar:
---
{chunk_text[:5000]}
---

Responde SOLO con el JSON:"""

        try:
            response = brain.think(
                system_prompt="Eres un extractor de entidades. Responde SOLO con JSON valido.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )

            # Intentar parsear JSON de la respuesta
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
        except (json.JSONDecodeError, ValueError, RuntimeError, KeyError) as e:
            pass  # LLM response may not contain valid JSON; return empty

        return {}

    def extract_tables_from_text(self, text: str) -> list:
        """Detecta tablas en texto plano (delimitadores, alineacion)."""
        tables = []
        lines = text.split("\n")
        current_table = []

        for line in lines:
            # Detectar lineas con separadores de tabla
            if "|" in line and line.count("|") >= 2:
                # Ignorar lineas separadoras (---|---|---)
                if re.match(r'^[\s|:\-]+$', line):
                    continue
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells:
                    current_table.append(cells)
            else:
                if len(current_table) >= 2:
                    tables.append({
                        "rows": len(current_table),
                        "cols": len(current_table[0]) if current_table else 0,
                        "headers": current_table[0],
                        "data": current_table[1:],
                    })
                current_table = []

        # Ultima tabla pendiente
        if len(current_table) >= 2:
            tables.append({
                "rows": len(current_table),
                "cols": len(current_table[0]) if current_table else 0,
                "headers": current_table[0],
                "data": current_table[1:],
            })

        return tables
