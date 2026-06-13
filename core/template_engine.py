import os
import re
import json
import threading
from datetime import datetime
from typing import Optional
from difflib import SequenceMatcher


class TemplateEngine:
    """Motor de templates de texto con variables."""

    # Templates predefinidos
    BUILTIN = {
        "email_formal": {
            "description": "Email formal / profesional",
            "content": "Estimado/a {destinatario},\n\n{cuerpo}\n\nQuedo a su disposición para cualquier consulta.\n\nSaludos cordiales,\n{remitente}",
            "variables": ["destinatario", "cuerpo", "remitente"]
        },
        "email_seguimiento": {
            "description": "Email de seguimiento / follow-up",
            "content": "Hola {destinatario},\n\nLe escribo para dar seguimiento a {tema}.\n\n{detalle}\n\nQuedo atento a su respuesta.\n\nSaludos,\n{remitente}",
            "variables": ["destinatario", "tema", "detalle", "remitente"]
        },
        "bug_report": {
            "description": "Reporte de bug / error",
            "content": "## Bug Report\n\n**Título:** {titulo}\n**Severidad:** {severidad}\n**Fecha:** {fecha}\n\n### Descripción\n{descripcion}\n\n### Pasos para reproducir\n{pasos}\n\n### Resultado esperado\n{esperado}\n\n### Resultado actual\n{actual}\n\n### Entorno\n{entorno}",
            "variables": ["titulo", "severidad", "fecha", "descripcion", "pasos", "esperado", "actual", "entorno"]
        },
        "acta_reunion": {
            "description": "Acta de reunión",
            "content": "# Acta de Reunión\n\n**Fecha:** {fecha}\n**Asistentes:** {asistentes}\n**Tema:** {tema}\n\n## Puntos Tratados\n{puntos}\n\n## Decisiones\n{decisiones}\n\n## Próximos Pasos\n{proximos_pasos}\n\n---\nRedactado por {autor}",
            "variables": ["fecha", "asistentes", "tema", "puntos", "decisiones", "proximos_pasos", "autor"]
        },
        "changelog": {
            "description": "Entrada de changelog / release notes",
            "content": "## [{version}] — {fecha}\n\n### Agregado\n{agregado}\n\n### Cambiado\n{cambiado}\n\n### Corregido\n{corregido}",
            "variables": ["version", "fecha", "agregado", "cambiado", "corregido"]
        },
    }

    def __init__(self, data_dir: str = "memory_data"):
        self._templates: dict[str, dict] = {}  # name -> {content, description, variables, created, uses}
        self._lock = threading.RLock()
        self._data_file = os.path.join(data_dir, "templates.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ─────────────────────────────────
    def _load(self):
        """Carga templates personalizados desde disco."""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    self._templates = json.load(f)
        except Exception:
            pass

    def save(self):
        """Guarda templates a disco."""
        with self._lock:
            try:
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(self._templates, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── Obtener template (custom + builtin) ──────────
    def _get_template(self, name: str) -> Optional[dict]:
        """Busca template en custom primero, luego builtin."""
        name = name.strip().lower()
        if name in self._templates:
            return self._templates[name]
        if name in self.BUILTIN:
            return self.BUILTIN[name]
        return None

    # ── CRUD ─────────────────────────────────────────
    def create(self, name: str, content: str, description: str = "") -> str:
        """Crea un template personalizado."""
        if not name or not name.strip():
            return "📝 Necesita un nombre para el template."
        if not content or not content.strip():
            return "📝 Necesita contenido para el template."

        name = name.strip().lower()

        # Extraer variables del contenido
        variables = re.findall(r'\{(\w+)\}', content)
        variables = list(dict.fromkeys(variables))  # dedup preservando orden

        with self._lock:
            is_update = name in self._templates
            self._templates[name] = {
                "content": content,
                "description": description or f"Template personalizado: {name}",
                "variables": variables,
                "created": datetime.now().isoformat(),
                "uses": self._templates.get(name, {}).get("uses", 0)
            }
            self.save()

        action = "actualizado" if is_update else "creado"
        vars_str = ", ".join(f"{{{v}}}" for v in variables) if variables else "sin variables"
        return (f"📝 **Template '{name}' {action}**\n"
                f"  📋 Variables: {vars_str}\n"
                f"  📄 Preview: {content[:80]}...")

    def remove(self, name: str) -> str:
        """Elimina un template personalizado."""
        name = name.strip().lower()

        with self._lock:
            if name in self._templates:
                del self._templates[name]
                self.save()
                return f"📝 Template '{name}' eliminado."

            if name in self.BUILTIN:
                return f"📝 '{name}' es un template predefinido — no se puede eliminar."

            return f"📝 No encontré el template '{name}'."

    # ── Aplicar template ─────────────────────────────
    def apply(self, name: str, values: Optional[dict] = None) -> str:
        """Aplica un template con los valores dados."""
        tmpl = self._get_template(name.strip().lower())
        if not tmpl:
            # Fuzzy search
            match = self._fuzzy_find(name.strip().lower())
            if match:
                return f"📝 No encontré '{name}'. ¿Quisiste decir '{match}'?"
            return f"📝 No encontré el template '{name}'."

        content = tmpl["content"]
        values = values or {}

        # Reemplazar variables, dejar las no proporcionadas como están
        for var in tmpl.get("variables", []):
            if var in values:
                content = content.replace(f"{{{var}}}", str(values[var]))

        # Auto-fill fecha si existe y no fue proporcionada
        if "{fecha}" in content and "fecha" not in values:
            content = content.replace("{fecha}", datetime.now().strftime("%Y-%m-%d"))

        # Incrementar usos
        name_key = name.strip().lower()
        with self._lock:
            if name_key in self._templates:
                self._templates[name_key]["uses"] = self._templates[name_key].get("uses", 0) + 1
                self.save()

        return f"📝 **Template '{name}' aplicado:**\n\n{content}"

    def preview(self, name: str) -> str:
        """Muestra preview de un template con sus variables."""
        tmpl = self._get_template(name.strip().lower())
        if not tmpl:
            return f"📝 No encontré el template '{name}'."

        vars_list = tmpl.get("variables", [])
        vars_str = "\n".join(f"  • {{{v}}}" for v in vars_list) if vars_list else "  (sin variables)"

        return (f"📝 **Template: {name}**\n"
                f"  📋 {tmpl.get('description', '')}\n\n"
                f"  **Variables:**\n{vars_str}\n\n"
                f"  **Contenido:**\n{tmpl['content']}")

    # ── Listado ──────────────────────────────────────
    def list_templates(self) -> str:
        """Lista todos los templates (custom + builtin)."""
        lines = ["📝 **TEMPLATES DISPONIBLES**\n"]

        # Predefinidos
        lines.append("  **PREDEFINIDOS:**")
        for name, tmpl in self.BUILTIN.items():
            vars_count = len(tmpl.get("variables", []))
            lines.append(f"    📋 **{name}** — {tmpl['description']} ({vars_count} vars)")

        # Personalizados
        with self._lock:
            if self._templates:
                lines.append("\n  **PERSONALIZADOS:**")
                for name, tmpl in sorted(self._templates.items()):
                    vars_count = len(tmpl.get("variables", []))
                    uses = tmpl.get("uses", 0)
                    lines.append(f"    📌 **{name}** — {tmpl['description']} ({vars_count} vars, {uses} usos)")

        total = len(self.BUILTIN) + len(self._templates)
        lines.insert(1, f"  Total: {total} templates\n")
        return "\n".join(lines)

    # ── Fuzzy matching ───────────────────────────────
    def _fuzzy_find(self, query: str) -> Optional[str]:
        """Busca template por nombre aproximado."""
        best_score = 0.0
        best_match = None
        all_names = list(self._templates.keys()) + list(self.BUILTIN.keys())
        for name in all_names:
            score = SequenceMatcher(None, query, name).ratio()
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = name
        return best_match

    # ── Status ───────────────────────────────────────
    def status(self) -> dict:
        """Estado del motor de templates."""
        with self._lock:
            return {
                "builtin_templates": len(self.BUILTIN),
                "custom_templates": len(self._templates),
                "total_templates": len(self.BUILTIN) + len(self._templates),
                "total_uses": sum(t.get("uses", 0) for t in self._templates.values())
            }


# Singleton
template_engine = TemplateEngine()
