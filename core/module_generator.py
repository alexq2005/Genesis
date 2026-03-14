"""
GENESIS — Module Generator (v4.0)

Genesis crea sus propios módulos nuevos: detecta gaps en la
arquitectura, genera templates con el patrón coordinator estándar,
y produce código Python funcional listo para integrar.

Componentes:
- ModuleTemplate: template de un módulo con nombre, componentes y métodos
- GapDetector: analiza módulos existentes y detecta capacidades faltantes
- CodeTemplate: genera código Python boilerplate con patrón coordinator
- ModuleGenerator: coordinador con persistencia y generación autónoma
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class ModuleTemplate:
    """Template de un módulo a generar."""

    def __init__(self, name: str, description: str = "",
                 components: list = None, methods: list = None,
                 estimated_lines: int = 200):
        self.template_id = hashlib.md5(
            f"tmpl_{name}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.name = name.lower().strip().replace(" ", "_")
        self.description = description
        self.components = components or []       # Nombres de clases helper
        self.methods = methods or []             # Métodos del coordinator
        self.estimated_lines = estimated_lines
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.template_id,
            "name": self.name,
            "description": self.description,
            "components": self.components[:10],
            "methods": self.methods[:20],
            "estimated_lines": self.estimated_lines,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleTemplate":
        t = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            components=data.get("components", []),
            methods=data.get("methods", []),
            estimated_lines=data.get("estimated_lines", 200),
        )
        t.template_id = data.get("id", t.template_id)
        t.created_at = data.get("created_at", time.time())
        return t


class GapDetector:
    """Analiza módulos existentes y detecta capacidades faltantes."""

    # Capacidades comunes que un sistema de IA debería tener
    CAPABILITY_PATTERNS = {
        "memory": ["memory", "remember", "recall", "store", "persist"],
        "learning": ["learn", "train", "adapt", "improve", "optimize"],
        "reasoning": ["reason", "logic", "infer", "deduce", "analyze"],
        "planning": ["plan", "schedule", "goal", "strategy", "task"],
        "monitoring": ["monitor", "health", "metric", "anomaly", "alert"],
        "communication": ["dialog", "conversation", "chat", "message", "voice"],
        "creativity": ["creative", "generate", "synthesize", "dream", "story"],
        "evaluation": ["evaluate", "score", "quality", "feedback", "assess"],
        "security": ["security", "auth", "permission", "safe", "encrypt"],
        "integration": ["api", "webhook", "plugin", "connect", "bridge"],
        "visualization": ["dashboard", "chart", "graph", "display", "render"],
        "collaboration": ["team", "multi_agent", "coordinate", "collaborate", "delegate"],
        "debugging": ["debug", "trace", "log", "diagnose", "profile"],
        "testing": ["test", "validate", "verify", "assert", "benchmark"],
        "versioning": ["version", "history", "snapshot", "rollback", "migrate"],
        "caching": ["cache", "memoize", "buffer", "precompute", "index"],
    }

    def detect_gaps(self, existing_modules: list) -> list:
        """
        Analiza nombres de módulos existentes y detecta capacidades faltantes.

        Args:
            existing_modules: lista de nombres de módulos existentes

        Returns:
            Lista de dicts con 'capability', 'keywords', 'coverage',
            'suggestion'
        """
        # Normalizar nombres existentes y extraer todas las keywords
        existing_lower = [m.lower().replace("_", " ") for m in existing_modules]
        all_text = " ".join(existing_lower)

        gaps = []
        for capability, keywords in self.CAPABILITY_PATTERNS.items():
            # Contar cuántas keywords están cubiertas
            covered = sum(1 for kw in keywords if kw in all_text)
            coverage = covered / len(keywords) if keywords else 0

            if coverage < 0.3:
                # Gap detectado: baja cobertura de esta capacidad
                missing_kws = [kw for kw in keywords if kw not in all_text]
                gaps.append({
                    "capability": capability,
                    "keywords": keywords,
                    "missing_keywords": missing_kws[:5],
                    "coverage": round(coverage, 2),
                    "suggestion": self._suggest_module(capability, missing_kws),
                })

        # Ordenar por menor cobertura (gaps más grandes primero)
        gaps.sort(key=lambda g: g["coverage"])
        return gaps[:10]

    def find_clusters(self, existing_modules: list) -> dict:
        """
        Agrupa módulos existentes por capacidad para ver concentraciones.

        Returns:
            dict capability -> list of matching module names
        """
        clusters = defaultdict(list)
        for mod in existing_modules:
            mod_lower = mod.lower()
            for capability, keywords in self.CAPABILITY_PATTERNS.items():
                if any(kw in mod_lower for kw in keywords):
                    clusters[capability].append(mod)
        return dict(clusters)

    def _suggest_module(self, capability: str, missing_keywords: list) -> str:
        """Genera una sugerencia de módulo para cubrir un gap."""
        suggestions = {
            "memory": "persistent_memory_manager — gestión unificada de memoria",
            "learning": "adaptive_learner — aprendizaje continuo de patrones",
            "reasoning": "logic_engine — motor de razonamiento formal",
            "planning": "goal_planner — planificación jerárquica de objetivos",
            "monitoring": "system_monitor — monitoreo integral del sistema",
            "communication": "message_broker — comunicación entre componentes",
            "creativity": "creative_engine — generación de contenido creativo",
            "evaluation": "quality_evaluator — evaluación de calidad de respuestas",
            "security": "security_manager — gestión de seguridad y permisos",
            "integration": "api_gateway — gateway para integraciones externas",
            "visualization": "visual_engine — motor de visualización de datos",
            "collaboration": "multi_agent_coordinator — coordinación multi-agente",
            "debugging": "debug_tracer — tracing y diagnóstico de errores",
            "testing": "test_harness — framework de testing automatizado",
            "versioning": "version_manager — control de versiones y snapshots",
            "caching": "cache_engine — motor de caché inteligente",
        }
        return suggestions.get(capability, f"{capability}_module — auto-generated")


class CodeTemplate:
    """Genera código Python boilerplate con patrón coordinator."""

    COORDINATOR_METHODS = [
        "save", "_load", "clear", "status",
        "generate_report", "get_stats", "get_context_for_prompt",
    ]

    def generate(self, template: ModuleTemplate) -> str:
        """
        Genera código Python completo desde un ModuleTemplate.

        Returns:
            String con código Python listo para guardar.
        """
        lines = []

        # Docstring del módulo
        class_name = self._to_class_name(template.name)
        lines.append('"""')
        lines.append(f"GENESIS — {class_name} (v4.0)")
        lines.append("")
        if template.description:
            lines.append(template.description)
            lines.append("")
        lines.append("Componentes:")
        for comp in template.components:
            lines.append(f"- {comp}")
        lines.append(f"- {class_name}: coordinador con persistencia")
        lines.append('"""')

        # Imports
        lines.append("import time")
        lines.append("import json")
        lines.append("from pathlib import Path")
        lines.append("")
        lines.append("")

        # Helper classes
        for comp in template.components:
            lines.extend(self._generate_helper_class(comp))
            lines.append("")
            lines.append("")

        # Coordinator class
        lines.extend(self._generate_coordinator(template, class_name))

        return "\n".join(lines)

    def _to_class_name(self, name: str) -> str:
        """Convierte snake_case a PascalCase."""
        parts = name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts if p)

    def _generate_helper_class(self, class_name: str) -> list:
        """Genera una clase helper con to_dict y from_dict."""
        lines = []
        lines.append(f"class {class_name}:")
        lines.append(f'    """{class_name} data container."""')
        lines.append("")
        lines.append(f"    def __init__(self, name: str = \"\", data: dict = None):")
        lines.append(f"        self.name = name")
        lines.append(f"        self.data = data or {{}}")
        lines.append(f"        self.created_at = time.time()")
        lines.append("")
        lines.append(f"    def to_dict(self) -> dict:")
        lines.append(f"        return {{")
        lines.append(f'            "name": self.name,')
        lines.append(f'            "data": self.data,')
        lines.append(f'            "created_at": self.created_at,')
        lines.append(f"        }}")
        lines.append("")
        lines.append(f"    @classmethod")
        lines.append(f'    def from_dict(cls, d: dict) -> "{class_name}":')
        lines.append(f'        obj = cls(name=d.get("name", ""), data=d.get("data", {{}}))')
        lines.append(f'        obj.created_at = d.get("created_at", time.time())')
        lines.append(f"        return obj")
        return lines

    def _generate_coordinator(self, template: ModuleTemplate,
                              class_name: str) -> list:
        """Genera la clase coordinator con métodos estándar."""
        snake = template.name
        lines = []

        lines.append(f"class {class_name}:")
        lines.append(f'    """')
        lines.append(f"    Coordinador de {snake.replace('_', ' ')}.")
        if template.description:
            lines.append(f"    {template.description[:100]}")
        lines.append(f'    """')
        lines.append("")

        # __init__
        lines.append(f"    def __init__(self, base_dir: str = None):")
        lines.append(f'        self.base_dir = Path(base_dir) if base_dir else Path("data/{snake}")')
        lines.append(f'        self.data_file = self.base_dir / "{snake}_state.json"')
        lines.append(f"        self.base_dir.mkdir(parents=True, exist_ok=True)")
        lines.append("")
        lines.append(f"        self.items = []")
        lines.append(f"        self.total_processed = 0")
        lines.append(f"        self.max_items = 200")
        lines.append(f"        self.enabled = True")
        lines.append("")
        lines.append(f"        self._load()")
        lines.append("")

        # Custom methods from template
        for method in template.methods:
            if method not in self.COORDINATOR_METHODS:
                lines.append(f"    def {method}(self, *args, **kwargs):")
                lines.append(f'        """{method.replace("_", " ").capitalize()}."""')
                lines.append(f"        if not self.enabled:")
                lines.append(f"            return None")
                lines.append(f"        self.total_processed += 1")
                lines.append(f"        return None  # TODO: implement")
                lines.append("")

        # save
        lines.append(f"    def save(self):")
        lines.append(f'        """Persiste el estado completo."""')
        lines.append(f"        data = {{")
        lines.append(f'            "total_processed": self.total_processed,')
        lines.append(f'            "items": self.items[-self.max_items:],')
        lines.append(f'            "enabled": self.enabled,')
        lines.append(f"        }}")
        lines.append(f"        try:")
        lines.append(f"            self.base_dir.mkdir(parents=True, exist_ok=True)")
        lines.append(f"            self.data_file.write_text(")
        lines.append(f'                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"')
        lines.append(f"            )")
        lines.append(f"        except Exception:")
        lines.append(f"            pass")
        lines.append("")

        # _load
        lines.append(f"    def _load(self):")
        lines.append(f'        """Carga estado previo si existe."""')
        lines.append(f"        if not self.data_file.exists():")
        lines.append(f"            return")
        lines.append(f"        try:")
        lines.append(f'            data = json.loads(self.data_file.read_text(encoding="utf-8"))')
        lines.append(f'            self.total_processed = data.get("total_processed", 0)')
        lines.append(f'            self.items = data.get("items", [])')
        lines.append(f'            self.enabled = data.get("enabled", True)')
        lines.append(f"        except Exception:")
        lines.append(f"            pass")
        lines.append("")

        # clear
        lines.append(f"    def clear(self):")
        lines.append(f'        """Resetea todo el estado."""')
        lines.append(f"        self.items = []")
        lines.append(f"        self.total_processed = 0")
        lines.append(f"        if self.data_file.exists():")
        lines.append(f"            self.data_file.unlink()")
        lines.append("")

        # status
        lines.append(f"    def status(self) -> str:")
        lines.append(f'        """Status string para /status."""')
        lines.append(f'        return (f"Items: {{len(self.items)}} | "')
        lines.append(f'                f"Processed: {{self.total_processed}} | "')
        lines.append(f'                f"Enabled: {{self.enabled}}")')
        lines.append("")

        # generate_report
        lines.append(f"    def generate_report(self) -> str:")
        lines.append(f'        """Reporte completo."""')
        lines.append(f'        lines = ["=== {class_name.upper()} REPORT ==="]')
        lines.append(f'        lines.append(f"Total processed: {{self.total_processed}}")')
        lines.append(f'        lines.append(f"Stored items: {{len(self.items)}}")')
        lines.append(f'        lines.append(f"Enabled: {{self.enabled}}")')
        lines.append(f'        return "\\n".join(lines)')
        lines.append("")

        # get_stats
        lines.append(f"    def get_stats(self) -> dict:")
        lines.append(f'        """Estadísticas completas."""')
        lines.append(f"        return {{")
        lines.append(f'            "total_processed": self.total_processed,')
        lines.append(f'            "stored_items": len(self.items),')
        lines.append(f'            "enabled": self.enabled,')
        lines.append(f"        }}")
        lines.append("")

        # get_context_for_prompt
        lines.append(f"    def get_context_for_prompt(self, max_chars: int = 400) -> str:")
        lines.append(f'        """Genera contexto para inyectar en prompt."""')
        lines.append(f"        if not self.enabled or not self.items:")
        lines.append(f'            return ""')
        lines.append(f'        return f"[{class_name.upper()}] Items: {{len(self.items)}}"[:max_chars]')

        return lines


class ModuleGenerator:
    """
    Coordinador de generación de módulos.
    Detecta gaps, genera templates y produce código Python.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/module_gen")
        self.data_file = self.base_dir / "generator_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.gap_detector = GapDetector()
        self.code_template = CodeTemplate()

        self.generated_modules = []    # Lista de ModuleTemplate generados
        self.detected_gaps = []        # Último resultado de gap detection
        self.max_generated = 100
        self.total_generated = 0
        self.enabled = True

        self._load()

    def detect_gaps(self, existing_modules: list) -> list:
        """
        Analiza módulos existentes y sugiere capacidades faltantes.

        Args:
            existing_modules: lista de nombres de módulos

        Returns:
            Lista de gaps detectados
        """
        self.detected_gaps = self.gap_detector.detect_gaps(existing_modules)
        return self.detected_gaps

    def generate_template(self, name: str, description: str = "",
                          components: list = None) -> ModuleTemplate:
        """
        Crea un ModuleTemplate con boilerplate.

        Args:
            name: nombre del módulo (snake_case)
            description: descripción breve
            components: lista de nombres de clases helper

        Returns:
            ModuleTemplate con métodos estándar
        """
        if not components:
            # Auto-generar basado en el nombre
            class_name = self.code_template._to_class_name(name)
            components = [
                f"{class_name}Item",
                f"{class_name}Analyzer",
            ]

        # Métodos estándar del coordinator + extras basados en el nombre
        methods = list(CodeTemplate.COORDINATOR_METHODS)
        # Agregar métodos específicos según la naturaleza del módulo
        name_lower = name.lower()
        if "monitor" in name_lower or "detect" in name_lower:
            methods.extend(["check", "alert"])
        elif "learn" in name_lower or "train" in name_lower:
            methods.extend(["learn", "predict"])
        elif "manage" in name_lower or "coordinate" in name_lower:
            methods.extend(["register", "dispatch"])
        elif "engine" in name_lower or "generate" in name_lower:
            methods.extend(["process", "generate_output"])
        else:
            methods.extend(["process", "analyze"])

        # Estimar líneas
        estimated = 80 + len(components) * 40 + len(methods) * 12

        template = ModuleTemplate(
            name=name,
            description=description,
            components=components,
            methods=methods,
            estimated_lines=estimated,
        )
        return template

    def generate_code(self, template: ModuleTemplate) -> str:
        """
        Genera código Python real desde un ModuleTemplate.

        Args:
            template: ModuleTemplate con especificaciones

        Returns:
            String con código Python completo
        """
        code = self.code_template.generate(template)

        # Registrar
        self.generated_modules.append(template)
        self.total_generated += 1

        if len(self.generated_modules) > self.max_generated:
            self.generated_modules = self.generated_modules[-self.max_generated:]

        # Persistir
        if self.total_generated % 5 == 0:
            self.save()

        return code

    def auto_generate_from_gaps(self, existing_modules: list) -> list:
        """
        Pipeline completo: detectar gaps -> generar templates -> producir código.

        Args:
            existing_modules: lista de nombres de módulos existentes

        Returns:
            Lista de dicts con 'gap', 'template', 'code' para cada módulo generado
        """
        gaps = self.detect_gaps(existing_modules)
        results = []

        for gap in gaps[:3]:  # Máximo 3 módulos por ciclo
            suggestion = gap["suggestion"]
            # Extraer nombre del módulo de la sugerencia
            if " — " in suggestion:
                mod_name, desc = suggestion.split(" — ", 1)
            else:
                mod_name = gap["capability"] + "_module"
                desc = suggestion

            mod_name = mod_name.strip().replace(" ", "_")

            template = self.generate_template(
                name=mod_name,
                description=desc,
            )
            code = self.generate_code(template)

            results.append({
                "gap": gap["capability"],
                "coverage": gap["coverage"],
                "template": template.to_dict(),
                "code_length": len(code),
                "code_lines": code.count("\n") + 1,
            })

        return results

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Inyecta análisis de gaps si se detectaron."""
        if not self.enabled or not self.detected_gaps:
            return ""

        lines = ["[MODULE GAP ANALYSIS]"]
        total = 0
        for gap in self.detected_gaps[:3]:
            text = (f"  Gap: {gap['capability']} (coverage: {gap['coverage']:.0%}) "
                    f"-> {gap['suggestion'][:60]}")
            if total + len(text) > max_chars:
                break
            lines.append(text)
            total += len(text)

        if len(lines) > 1:
            lines.append(f"  Generated modules so far: {self.total_generated}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        """Estadísticas completas."""
        return {
            "total_generated": self.total_generated,
            "stored_modules": len(self.generated_modules),
            "detected_gaps": len(self.detected_gaps),
            "gap_capabilities": [g["capability"] for g in self.detected_gaps[:5]],
            "latest_module": self.generated_modules[-1].name if self.generated_modules else "",
            "enabled": self.enabled,
        }

    def status(self) -> str:
        """Status string para /status."""
        return (f"Generados: {self.total_generated} | "
                f"Gaps detectados: {len(self.detected_gaps)} | "
                f"Almacenados: {len(self.generated_modules)}")

    def generate_report(self) -> str:
        """Reporte completo de generación."""
        lines = ["=== MODULE GENERATOR REPORT ==="]
        lines.append(f"Total generados: {self.total_generated}")
        lines.append(f"Almacenados: {len(self.generated_modules)}")

        # Gaps
        if self.detected_gaps:
            lines.append(f"\nGaps detectados ({len(self.detected_gaps)}):")
            for gap in self.detected_gaps[:5]:
                lines.append(f"  [{gap['capability']}] coverage={gap['coverage']:.0%} "
                             f"-> {gap['suggestion'][:70]}")

        # Módulos generados
        if self.generated_modules:
            lines.append(f"\nÚltimos módulos generados:")
            for t in self.generated_modules[-5:]:
                lines.append(f"  {t.name}: {len(t.components)} components, "
                             f"{len(t.methods)} methods, ~{t.estimated_lines} lines")
                if t.description:
                    lines.append(f"    desc: {t.description[:80]}")

        # Clusters
        if self.detected_gaps:
            covered = [g["capability"] for g in self.detected_gaps if g["coverage"] > 0]
            uncovered = [g["capability"] for g in self.detected_gaps if g["coverage"] == 0]
            if uncovered:
                lines.append(f"\nCapacidades sin cobertura: {', '.join(uncovered[:5])}")
            if covered:
                lines.append(f"Capacidades parciales: {', '.join(covered[:5])}")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado completo."""
        data = {
            "total_generated": self.total_generated,
            "generated_modules": [t.to_dict() for t in self.generated_modules[-self.max_generated:]],
            "detected_gaps": self.detected_gaps[:20],
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
            self.total_generated = data.get("total_generated", 0)
            self.detected_gaps = data.get("detected_gaps", [])
            self.enabled = data.get("enabled", True)
            self.generated_modules = [
                ModuleTemplate.from_dict(td)
                for td in data.get("generated_modules", [])
            ]
        except Exception:
            pass

    def clear(self):
        """Resetea todo el estado."""
        self.generated_modules = []
        self.detected_gaps = []
        self.total_generated = 0
        if self.data_file.exists():
            self.data_file.unlink()
