"""
GENESIS — Bias Detector (v4.2)

Detección de sesgos en respuestas generadas. Escanea texto por
señales de sesgo de género, cultural, técnico, confirmación y
autoridad. Genera reportes, sugerencias de neutralidad y
auditorías retrospectivas.

Componentes:
- BiasType: definición de tipo de sesgo con signal words
- BiasReport: reporte de escaneo con sesgos encontrados
- BiasScanner: motor de escaneo multi-tipo
- BiasDetector: coordinador con auditoría y persistencia
"""
import time
import json
import re
import math
from pathlib import Path
from collections import defaultdict


class BiasType:
    """Definición de un tipo de sesgo con palabras señal."""

    TYPES = {
        "gender": {
            "description": "Sesgo de genero: asunciones o estereotipos basados en genero",
            "signal_words": [
                "obviously he", "obviously she", "como mujer", "como hombre",
                "las mujeres suelen", "los hombres suelen", "tipico de",
                "es cosa de hombres", "es cosa de mujeres", "sexo debil",
                "histerico", "histerica", "mandona", "agresivo",
                "for a woman", "for a man", "boys will be",
                "naturally women", "naturally men",
            ],
        },
        "cultural": {
            "description": "Sesgo cultural: asunciones basadas en origen, cultura o etnia",
            "signal_words": [
                "esa cultura", "esos paises", "en el tercer mundo",
                "los de alla", "gente civilizada", "primitivo",
                "como todo latino", "como todo asiatico", "tipico de",
                "those people", "third world", "uncivilized",
                "backward", "exotic", "all of them",
            ],
        },
        "technical": {
            "description": "Sesgo tecnico: asumir nivel tecnico por demografia o contexto",
            "signal_words": [
                "es obvio que", "cualquiera sabe", "basico",
                "esto es trivial", "facil de entender", "elemental",
                "no necesita explicacion", "todo el mundo sabe",
                "obviously", "trivial", "everyone knows",
                "any developer knows", "simple enough",
            ],
        },
        "confirmation": {
            "description": "Sesgo de confirmacion: reforzar creencias existentes sin evidencia",
            "signal_words": [
                "como siempre", "como era de esperar", "tal como dije",
                "esto confirma", "es evidente", "nadie puede negar",
                "esta claro que", "sin duda alguna", "indiscutible",
                "as expected", "this proves", "undeniable",
                "clearly shows", "no one can deny",
            ],
        },
        "authority": {
            "description": "Sesgo de autoridad: apelar a autoridad sin evidencia sustantiva",
            "signal_words": [
                "los expertos dicen", "segun la ciencia", "esta demostrado",
                "todos los estudios", "la mayoria de expertos",
                "experts say", "studies show", "science says",
                "it's been proven", "research proves",
                "authorities agree", "consensus says",
            ],
        },
    }

    def __init__(self, name: str):
        config = self.TYPES.get(name, self.TYPES["confirmation"])
        self.name = name
        self.description = config["description"]
        self.signal_words = config["signal_words"]

    @classmethod
    def get_all_names(cls) -> list:
        return list(cls.TYPES.keys())


class BiasReport:
    """Reporte de escaneo de sesgos."""

    def __init__(self, text: str, biases_found: list,
                 overall_bias_score: float, suggestions: list):
        self.text = text[:300]
        self.biases_found = biases_found  # [{type, evidence, severity}]
        self.overall_bias_score = round(max(0.0, min(1.0, overall_bias_score)), 3)
        self.suggestions = suggestions[:10]
        self.timestamp = time.time()

    @property
    def is_biased(self) -> bool:
        return self.overall_bias_score > 0.2

    @property
    def bias_count(self) -> int:
        return len(self.biases_found)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "biases_found": self.biases_found,
            "overall_bias_score": self.overall_bias_score,
            "suggestions": self.suggestions,
            "is_biased": self.is_biased,
            "bias_count": self.bias_count,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BiasReport":
        report = cls(
            text=d.get("text", ""),
            biases_found=d.get("biases_found", []),
            overall_bias_score=d.get("overall_bias_score", 0.0),
            suggestions=d.get("suggestions", []),
        )
        report.timestamp = d.get("timestamp", time.time())
        return report


class BiasScanner:
    """Motor de escaneo de sesgos multi-tipo."""

    def __init__(self):
        self.bias_types = {name: BiasType(name)
                           for name in BiasType.get_all_names()}

    def scan(self, text: str) -> BiasReport:
        """Escanea texto por todos los tipos de sesgo."""
        text_lower = text.lower()
        biases_found = []
        suggestions = []

        for type_name, bias_type in self.bias_types.items():
            matches = self._find_matches(text_lower, bias_type)
            for match in matches:
                severity = self._calculate_severity(
                    match, text_lower, len(matches)
                )
                biases_found.append({
                    "type": type_name,
                    "evidence": match,
                    "severity": round(severity, 3),
                })
                suggestion = self._generate_suggestion(type_name, match)
                if suggestion:
                    suggestions.append(suggestion)

        # Score global
        if biases_found:
            total_severity = sum(b["severity"] for b in biases_found)
            overall = min(1.0, total_severity / max(1, len(biases_found)) *
                          (1 + math.log(1 + len(biases_found)) * 0.3))
        else:
            overall = 0.0

        return BiasReport(
            text=text,
            biases_found=biases_found,
            overall_bias_score=overall,
            suggestions=suggestions,
        )

    def _find_matches(self, text_lower: str, bias_type: BiasType) -> list:
        """Encuentra signal words presentes en el texto."""
        found = []
        for word in bias_type.signal_words:
            if word.lower() in text_lower:
                found.append(word)
        return found

    def _calculate_severity(self, match: str, text: str,
                            total_matches: int) -> float:
        """Calcula severidad de un sesgo encontrado."""
        # Base severity por longitud del match (frases más largas = más severas)
        base = min(1.0, len(match.split()) / 5 * 0.6 + 0.2)

        # Ajustar por frecuencia: múltiples matches en el mismo texto
        frequency_boost = min(0.3, total_matches * 0.05)

        # Ajustar por posición: al inicio del texto es más severo
        position = text.find(match.lower())
        position_factor = 0.1 if position < len(text) * 0.2 else 0.0

        return min(1.0, base + frequency_boost + position_factor)

    def _generate_suggestion(self, bias_type: str, evidence: str) -> str:
        """Genera sugerencia para neutralizar un sesgo."""
        suggestions_map = {
            "gender": f"Evitar '{evidence}' — usar lenguaje neutro en genero",
            "cultural": f"Evitar '{evidence}' — evitar generalizaciones culturales",
            "technical": f"Evitar '{evidence}' — no asumir nivel tecnico del interlocutor",
            "confirmation": f"Evitar '{evidence}' — presentar evidencia, no certezas absolutas",
            "authority": f"Evitar '{evidence}' — citar fuentes especificas, no apelar a autoridad generica",
        }
        return suggestions_map.get(bias_type, f"Revisar uso de '{evidence}'")


class BiasDetector:
    """Coordinador de detección de sesgos con auditoría y persistencia."""

    def __init__(self, base_dir: str = "data/bias"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.scanner = BiasScanner()
        self.reports = []            # Historial de reportes
        self.max_reports = 200
        self.total_scans = 0
        self.biases_found_count = 0
        self.self_audits_count = 0
        self.bias_type_counts = defaultdict(int)  # Conteo por tipo
        self.enabled = True

        self._load()

    def scan(self, text: str) -> BiasReport:
        """Escanea un texto por sesgos. Retorna BiasReport."""
        if not text:
            return BiasReport("", [], 0.0, [])

        report = self.scanner.scan(text)
        self.total_scans += 1
        self.biases_found_count += report.bias_count

        # Registrar conteo por tipo
        for bias in report.biases_found:
            self.bias_type_counts[bias["type"]] += 1

        # Almacenar reporte
        self.reports.append(report)
        if len(self.reports) > self.max_reports:
            self.reports = self.reports[-self.max_reports:]

        return report

    def self_audit(self, responses: list) -> dict:
        """Audita una lista de respuestas pasadas. Retorna reporte agregado."""
        self.self_audits_count += 1

        if not responses:
            return {
                "total_responses": 0,
                "biased_responses": 0,
                "bias_rate": 0.0,
                "dominant_bias_type": None,
                "avg_bias_score": 0.0,
                "recommendations": ["Sin respuestas para auditar"],
            }

        reports = []
        for response in responses:
            text = response if isinstance(response, str) else str(response)
            report = self.scanner.scan(text)
            reports.append(report)

        # Agregar estadísticas
        biased = [r for r in reports if r.is_biased]
        type_counts = defaultdict(int)
        for r in reports:
            for b in r.biases_found:
                type_counts[b["type"]] += 1

        dominant = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        avg_score = sum(r.overall_bias_score for r in reports) / len(reports)

        # Recomendaciones
        recommendations = []
        if avg_score > 0.5:
            recommendations.append("Nivel de sesgo alto. Revisar patrones de lenguaje sistematicamente.")
        elif avg_score > 0.2:
            recommendations.append("Sesgo moderado detectado. Prestar atencion a los tipos dominantes.")
        else:
            recommendations.append("Nivel de sesgo bajo. Mantener buenas practicas.")

        if dominant:
            bias_type = self.scanner.bias_types.get(dominant)
            if bias_type:
                recommendations.append(
                    f"Sesgo dominante: {dominant} — {bias_type.description[:80]}"
                )

        return {
            "total_responses": len(responses),
            "biased_responses": len(biased),
            "bias_rate": round(len(biased) / len(responses), 3),
            "dominant_bias_type": dominant,
            "avg_bias_score": round(avg_score, 3),
            "type_breakdown": dict(type_counts),
            "recommendations": recommendations,
        }

    def suggest_neutral(self, text: str, bias_type: str) -> list:
        """Sugiere reformulaciones neutrales para un tipo de sesgo específico."""
        bt = self.scanner.bias_types.get(bias_type)
        if not bt:
            return [f"Tipo de sesgo '{bias_type}' no reconocido"]

        text_lower = text.lower()
        suggestions = []

        neutralization_map = {
            "gender": {
                "obviously he": "la persona",
                "obviously she": "la persona",
                "como mujer": "(eliminar referencia de genero)",
                "como hombre": "(eliminar referencia de genero)",
                "las mujeres suelen": "algunas personas suelen",
                "los hombres suelen": "algunas personas suelen",
                "histerico": "alterado/a",
                "histerica": "alterada",
                "mandona": "con liderazgo firme",
            },
            "cultural": {
                "esa cultura": "en ese contexto",
                "esos paises": "en esas regiones",
                "en el tercer mundo": "en paises en desarrollo",
                "gente civilizada": "personas con ese contexto",
                "primitivo": "tradicional",
            },
            "technical": {
                "es obvio que": "vale la pena notar que",
                "cualquiera sabe": "es util saber que",
                "esto es trivial": "esto se puede resolver asi",
                "elemental": "fundamental",
                "no necesita explicacion": "brevemente explicado",
            },
            "confirmation": {
                "como siempre": "en esta ocasion",
                "es evidente": "los datos sugieren",
                "nadie puede negar": "la evidencia indica",
                "esta claro que": "segun los datos",
                "sin duda alguna": "con alta probabilidad",
                "indiscutible": "respaldado por evidencia",
            },
            "authority": {
                "los expertos dicen": "segun [fuente especifica]",
                "segun la ciencia": "segun [estudio/publicacion]",
                "esta demostrado": "existe evidencia de que",
                "todos los estudios": "varios estudios (citar)",
            },
        }

        replacements = neutralization_map.get(bias_type, {})
        for signal, neutral in replacements.items():
            if signal.lower() in text_lower:
                suggestions.append(
                    f"Reemplazar '{signal}' por '{neutral}'"
                )

        if not suggestions:
            suggestions.append(
                f"No se encontraron señales de sesgo '{bias_type}' en el texto"
            )

        return suggestions

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Inyecta recordatorios anti-sesgo si escaneos recientes encontraron sesgo."""
        if not self.enabled:
            return ""

        # Revisar últimos 5 reportes
        recent = self.reports[-5:] if self.reports else []
        if not recent:
            return ""

        recent_biased = [r for r in recent if r.is_biased]
        if not recent_biased:
            return ""

        # Encontrar tipos dominantes en reportes recientes
        recent_types = defaultdict(int)
        for r in recent_biased:
            for b in r.biases_found:
                recent_types[b["type"]] += 1

        if not recent_types:
            return ""

        dominant = max(recent_types.items(), key=lambda x: x[1])[0]
        bt = self.scanner.bias_types.get(dominant)

        parts = ["[ANTI-SESGO]"]
        parts.append(
            f"Atencion: sesgo de tipo '{dominant}' detectado en respuestas recientes."
        )
        if bt:
            parts.append(f"Evitar: {bt.description[:60]}.")
        parts.append("Usar lenguaje neutro e inclusivo.")

        return " ".join(parts)[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_scans": self.total_scans,
            "biases_found_count": self.biases_found_count,
            "self_audits_count": self.self_audits_count,
            "reports_stored": len(self.reports),
            "bias_type_counts": dict(self.bias_type_counts),
            "avg_bias_score": round(
                sum(r.overall_bias_score for r in self.reports) / len(self.reports), 3
            ) if self.reports else 0.0,
            "recent_bias_rate": round(
                sum(1 for r in self.reports[-20:] if r.is_biased) /
                max(1, len(self.reports[-20:])), 3
            ),
        }

    def status(self) -> str:
        avg = 0.0
        if self.reports:
            avg = sum(r.overall_bias_score for r in self.reports) / len(self.reports)
        return (f"  Scans: {self.total_scans} | "
                f"Sesgos: {self.biases_found_count} | "
                f"Auditorias: {self.self_audits_count} | "
                f"Score promedio: {avg:.0%}")

    def generate_report(self) -> str:
        lines = [
            "=== BIAS DETECTOR REPORT ===",
            f"Total escaneos: {self.total_scans}",
            f"Sesgos encontrados: {self.biases_found_count}",
            f"Auto-auditorias: {self.self_audits_count}",
            f"Reportes almacenados: {len(self.reports)}",
            "",
            "Conteo por tipo de sesgo:",
        ]
        for btype in BiasType.get_all_names():
            count = self.bias_type_counts.get(btype, 0)
            bt = self.scanner.bias_types[btype]
            lines.append(f"  {btype}: {count} — {bt.description[:50]}")

        if self.reports:
            lines.append("")
            avg = sum(r.overall_bias_score for r in self.reports) / len(self.reports)
            lines.append(f"Score de sesgo promedio: {avg:.0%}")

            biased = [r for r in self.reports if r.is_biased]
            lines.append(
                f"Tasa de sesgo: {len(biased)}/{len(self.reports)} "
                f"({len(biased)/len(self.reports):.0%})"
            )

            lines.append("")
            lines.append("Ultimos 5 escaneos:")
            for r in self.reports[-5:]:
                bias_tag = f" [{r.bias_count} sesgos]" if r.is_biased else " [limpio]"
                lines.append(
                    f"  '{r.text[:40]}...' -> score={r.overall_bias_score:.0%}{bias_tag}"
                )

        return "\n".join(lines)

    def save(self):
        data = {
            "total_scans": self.total_scans,
            "biases_found_count": self.biases_found_count,
            "self_audits_count": self.self_audits_count,
            "bias_type_counts": dict(self.bias_type_counts),
            "reports": [r.to_dict() for r in self.reports[-100:]],
        }
        path = self.base_dir / "bias_detector.json"
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "bias_detector.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_scans = data.get("total_scans", 0)
            self.biases_found_count = data.get("biases_found_count", 0)
            self.self_audits_count = data.get("self_audits_count", 0)
            self.bias_type_counts = defaultdict(
                int, data.get("bias_type_counts", {})
            )
            self.reports = [
                BiasReport.from_dict(d)
                for d in data.get("reports", [])
            ]
        except Exception:
            pass

    def clear(self):
        self.reports = []
        self.total_scans = 0
        self.biases_found_count = 0
        self.self_audits_count = 0
        self.bias_type_counts = defaultdict(int)
        self.save()
