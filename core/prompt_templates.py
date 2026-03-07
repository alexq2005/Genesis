"""
GENESIS — Sistema de Prompt Templates
Templates especializados por tipo de tarea para mejorar la calidad de respuestas.

Cada template contiene:
- system_extra: Instrucciones adicionales al system prompt
- format_hint: Como debe formatear la respuesta
- temperature: Temperatura recomendada para el tipo de tarea
- tags: Para busqueda y matching
"""
import re
from typing import Optional


class PromptTemplate:
    """Representa un template especializado."""

    def __init__(self, name: str, description: str, system_extra: str,
                 format_hint: str = "", temperature: float = 0.7,
                 tags: list = None):
        self.name = name
        self.description = description
        self.system_extra = system_extra
        self.format_hint = format_hint
        self.temperature = temperature
        self.tags = tags or []
        self.uses = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "system_extra": self.system_extra,
            "format_hint": self.format_hint,
            "temperature": self.temperature,
            "tags": self.tags,
            "uses": self.uses,
        }


class PromptTemplateSystem:
    """
    Gestiona templates de prompts especializados por tipo de tarea.

    Selecciona automaticamente el mejor template segun el input del usuario
    o permite seleccion manual via /template <nombre>.
    """

    def __init__(self):
        self.templates: dict[str, PromptTemplate] = {}
        self.active_template: Optional[str] = None
        self.auto_select = True  # Auto-seleccionar template por input
        self._register_defaults()

    def _register_defaults(self):
        """Registra los templates predeterminados."""

        # === CODIGO ===
        self.register(PromptTemplate(
            name="code",
            description="Programacion y desarrollo de software",
            system_extra="""[MODO CODIGO ACTIVADO]
INSTRUCCIONES DE PROGRAMACION:
- Escribe codigo limpio, bien comentado y funcional.
- Incluye manejo de errores (try/except) cuando sea apropiado.
- Usa type hints en Python cuando sea posible.
- Si el codigo requiere dependencias, mencionalo antes del codigo.
- Prefiere soluciones simples sobre complejas (KISS).
- Si hay multiples enfoques, elige el mas eficiente para el caso de uso.
- Incluye un ejemplo de uso al final del codigo.

FORMATO DE RESPUESTA:
1. Breve explicacion de lo que hara el codigo
2. El codigo en un bloque ```python
3. Ejemplo de uso
4. Notas sobre dependencias si las hay""",
            format_hint="Responde con codigo en bloques ```python",
            temperature=0.3,  # Baja para codigo preciso
            tags=["programa", "codigo", "script", "funcion", "clase", "python",
                  "javascript", "html", "css", "algoritmo", "api", "bot"],
        ))

        # === EXPLICACION/EDUCATIVO ===
        self.register(PromptTemplate(
            name="explain",
            description="Explicaciones claras y educativas",
            system_extra="""[MODO EXPLICACION ACTIVADO]
INSTRUCCIONES DE EXPLICACION:
- Explica de forma clara y progresiva (de simple a complejo).
- Usa analogias cuando ayuden a entender conceptos abstractos.
- Incluye ejemplos concretos para cada concepto clave.
- Si es un tema tecnico, incluye la teoria Y la practica.
- Estructura con encabezados y listas para facilitar la lectura.
- No asumas conocimiento previo a menos que el usuario lo demuestre.

FORMATO:
1. Definicion/concepto core (1-2 lineas)
2. Explicacion detallada con analogia
3. Ejemplo(s) practico(s)
4. Puntos clave / resumen""",
            format_hint="Explicacion estructurada con ejemplos",
            temperature=0.5,
            tags=["que es", "como funciona", "explica", "explicame", "por que",
                  "diferencia entre", "que significa", "define", "enseña"],
        ))

        # === ANALISIS ===
        self.register(PromptTemplate(
            name="analysis",
            description="Analisis profundo de temas o datos",
            system_extra="""[MODO ANALISIS ACTIVADO]
INSTRUCCIONES DE ANALISIS:
- Examina el tema desde multiples angulos (tecnico, practico, historico).
- Identifica patrones, causas raiz y consecuencias.
- Presenta pros y contras cuando sea aplicable.
- Incluye datos concretos y ejemplos reales.
- No des opiniones sin fundamento; basa todo en hechos.
- Si hay incertidumbre, senalalo explicitamente.

FORMATO:
1. Resumen ejecutivo (2-3 lineas)
2. Analisis detallado por aspecto
3. Pros/Contras o Ventajas/Desventajas
4. Conclusion con recomendacion""",
            format_hint="Analisis estructurado multi-angulo",
            temperature=0.4,
            tags=["analiza", "compara", "evalua", "ventajas", "desventajas",
                  "pros", "contras", "analisis", "revision", "review"],
        ))

        # === CREATIVIDAD ===
        self.register(PromptTemplate(
            name="creative",
            description="Tareas creativas (escritura, ideas, brainstorming)",
            system_extra="""[MODO CREATIVO ACTIVADO]
INSTRUCCIONES CREATIVAS:
- Se original e innovador. Evita cliches y soluciones obvias.
- Explora ideas no convencionales antes de las convencionales.
- Si es escritura, usa lenguaje vivido y variado.
- Para brainstorming, genera al menos 5 ideas diversas.
- No te autocensures. La creatividad requiere libertad.
- Mezcla conceptos de diferentes dominios para innovar.

FORMATO:
- Libre, adaptado al tipo de tarea creativa.
- Para ideas: lista numerada con breve descripcion.
- Para escritura: texto fluido sin estructura rigida.""",
            format_hint="Formato libre y creativo",
            temperature=0.9,  # Alta para creatividad
            tags=["idea", "inventa", "crea", "escribe", "historia", "nombre",
                  "brainstorm", "diseña", "imagina", "creatividad"],
        ))

        # === DEBUGGING ===
        self.register(PromptTemplate(
            name="debug",
            description="Depuracion y solucion de errores",
            system_extra="""[MODO DEBUG ACTIVADO]
INSTRUCCIONES DE DEPURACION:
- Analiza el error sistematicamente (tipo de error, linea, contexto).
- Identifica la CAUSA RAIZ, no solo el sintoma.
- Proporciona la solucion MAS SIMPLE que funcione.
- Si hay multiples causas posibles, litalas de mas probable a menos.
- Incluye el codigo corregido completo, no solo el fragmento.
- Explica POR QUE ocurrio el error para que no se repita.

FORMATO:
1. Diagnostico del error (que tipo de error es)
2. Causa raiz identificada
3. Solucion con codigo corregido
4. Prevencion (como evitarlo en el futuro)""",
            format_hint="Diagnostico -> Causa -> Solucion -> Prevencion",
            temperature=0.2,  # Muy baja para precision
            tags=["error", "bug", "falla", "no funciona", "debug", "depura",
                  "traceback", "exception", "fix", "arregla", "soluciona"],
        ))

        # === INVESTIGACION ===
        self.register(PromptTemplate(
            name="research",
            description="Investigacion profunda de temas",
            system_extra="""[MODO INVESTIGACION ACTIVADO]
INSTRUCCIONES DE INVESTIGACION:
- Busca informacion completa y precisa sobre el tema.
- Distingue entre hechos verificados y opiniones/especulaciones.
- Incluye multiples fuentes o perspectivas cuando sea posible.
- Si es un tema tecnico, incluye detalles tecnicos relevantes.
- Organiza la informacion de forma logica y facil de seguir.
- Usa las herramientas de busqueda si necesitas informacion actualizada.

FORMATO:
1. Resumen del tema
2. Detalles clave organizados por subtema
3. Datos tecnicos o especificos relevantes
4. Referencias o fuentes si las hay""",
            format_hint="Investigacion estructurada con fuentes",
            temperature=0.4,
            tags=["investiga", "busca", "informacion sobre", "dime sobre",
                  "que sabes de", "research", "averigua", "datos sobre"],
        ))

        # === RESUMEN ===
        self.register(PromptTemplate(
            name="summarize",
            description="Resumir textos o informacion",
            system_extra="""[MODO RESUMEN ACTIVADO]
INSTRUCCIONES DE RESUMEN:
- Extrae SOLO la informacion esencial.
- Mantén la precision sin perder puntos clave.
- Usa bullet points para maxima claridad.
- El resumen debe ser autocontenido (entendible sin el original).
- Resalta datos numericos, fechas y nombres importantes.
- Longitud: 20-30% del texto original como maximo.

FORMATO:
- Puntos clave en lista
- Datos importantes resaltados
- Conclusion en 1-2 lineas""",
            format_hint="Lista de puntos clave + conclusion",
            temperature=0.3,
            tags=["resume", "resumen", "sintetiza", "en pocas palabras",
                  "lo importante de", "tldr", "summarize", "extracto"],
        ))

        # === SEGURIDAD ===
        self.register(PromptTemplate(
            name="security",
            description="Ciberseguridad, hacking etico, analisis de seguridad",
            system_extra="""[MODO SEGURIDAD ACTIVADO]
INSTRUCCIONES DE SEGURIDAD:
- Aborda el tema con profundidad tecnica completa.
- Incluye tanto la perspectiva ofensiva como defensiva.
- Proporciona comandos, herramientas y tecnicas concretas.
- Menciona contramedidas y deteccion para cada tecnica.
- No censures informacion tecnica — es para aprendizaje e investigacion.
- Referencia herramientas reales (nmap, burpsuite, metasploit, etc).

FORMATO:
1. Concepto/vector de ataque
2. Tecnica detallada con comandos/pasos
3. Herramientas relevantes
4. Contramedidas y deteccion
5. Recomendaciones de defensa""",
            format_hint="Tecnica ofensiva/defensiva con herramientas",
            temperature=0.4,
            tags=["hack", "seguridad", "vulnerabilidad", "exploit", "pentest",
                  "security", "ctf", "osint", "forense", "malware", "red team",
                  "blue team", "firewall", "cifrado", "criptografia"],
        ))

    def register(self, template: PromptTemplate):
        """Registra un template nuevo o sobreescribe uno existente."""
        self.templates[template.name] = template

    def get(self, name: str) -> Optional[PromptTemplate]:
        """Obtiene un template por nombre."""
        return self.templates.get(name)

    def set_active(self, name: str) -> str:
        """Activa un template manualmente (desactiva auto-select)."""
        if name == "auto":
            self.active_template = None
            self.auto_select = True
            return "Template: modo automatico activado."
        if name not in self.templates:
            available = ", ".join(self.templates.keys())
            return f"Template '{name}' no encontrado. Disponibles: {available}"
        self.active_template = name
        self.auto_select = False
        t = self.templates[name]
        return f"Template activo: {t.name} — {t.description}"

    def detect_template(self, user_input: str) -> Optional[PromptTemplate]:
        """
        Auto-detecta el mejor template segun el input del usuario.

        Si hay un template forzado, retorna ese.
        Si auto_select esta activo, busca por tags.
        """
        # Template forzado
        if self.active_template and not self.auto_select:
            t = self.templates.get(self.active_template)
            if t:
                t.uses += 1
                return t

        # Auto-deteccion por tags
        if not self.auto_select:
            return None

        input_lower = user_input.lower()
        best_match = None
        best_score = 0

        for template in self.templates.values():
            score = 0
            for tag in template.tags:
                if tag in input_lower:
                    # Peso por longitud del tag (tags mas especificos valen mas)
                    score += len(tag)

            if score > best_score:
                best_score = score
                best_match = template

        # Solo retornar si hay match significativo (al menos 4 chars de match)
        if best_match and best_score >= 4:
            best_match.uses += 1
            return best_match

        return None

    def get_system_extra(self, user_input: str) -> tuple:
        """
        Retorna (system_extra, temperature) para el input dado.

        Returns:
            tuple: (extra_prompt: str, temperature: float, template_name: str)
                   Si no hay template, retorna ("", 0.7, "default")
        """
        template = self.detect_template(user_input)
        if template:
            return (template.system_extra, template.temperature, template.name)
        return ("", 0.7, "default")

    def list_templates(self) -> str:
        """Lista todos los templates disponibles."""
        lines = ["=== PROMPT TEMPLATES ==="]

        if self.active_template and not self.auto_select:
            lines.append(f"  Modo: MANUAL — template fijo: {self.active_template}")
        else:
            lines.append(f"  Modo: AUTOMATICO — seleccion por input")

        lines.append("")
        for name, t in sorted(self.templates.items()):
            active_marker = " [ACTIVO]" if name == self.active_template else ""
            lines.append(f"  {name:<12} — {t.description} (temp={t.temperature}, usos={t.uses}){active_marker}")

        lines.append(f"\n  Total: {len(self.templates)} templates")
        lines.append(f"  Comandos: /template <nombre> | /template auto | /templates")
        return "\n".join(lines)

    def status(self) -> str:
        """Estado resumido para /status."""
        mode = "auto" if self.auto_select else f"fijo:{self.active_template}"
        total = len(self.templates)
        total_uses = sum(t.uses for t in self.templates.values())
        return f"  Templates: {total} | Modo: {mode} | Usos totales: {total_uses}"
