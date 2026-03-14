"""
GENESIS — Ethical Reasoner (v4.2)

Razonamiento ético multi-framework. Evalúa acciones a través de
cuatro marcos éticos (utilitarismo, deontología, ética de virtudes,
ética del cuidado), detecta dilemas morales y genera guía ética
contextual para las respuestas.

Componentes:
- EthicalFramework: definición de un marco ético con criterios
- EthicalEvaluation: resultado de evaluación multi-framework
- DilemmaDetector: detección de dilemas éticos por keywords
- EthicalReasoner: coordinador con evaluación y persistencia
"""
import time
import json
import re
import math
from pathlib import Path
from collections import defaultdict


class EthicalFramework:
    """Definición de un marco ético con criterios de evaluación."""

    FRAMEWORKS = {
        "utilitarian": {
            "description": "Maximizar el bienestar general. Una accion es etica si produce el mayor bien para el mayor numero.",
            "key_principle": "El mayor bien para el mayor numero",
            "evaluation_criteria": [
                "beneficio_neto",
                "numero_de_afectados",
                "consecuencias_largo_plazo",
                "distribucion_equitativa",
            ],
        },
        "deontological": {
            "description": "Actuar segun reglas morales universales. Una accion es etica si respeta deberes y derechos fundamentales.",
            "key_principle": "Actua solo segun maximas que puedas querer como ley universal",
            "evaluation_criteria": [
                "respeta_autonomia",
                "cumple_deber",
                "no_instrumentaliza",
                "universalizable",
            ],
        },
        "virtue_ethics": {
            "description": "Cultivar el caracter virtuoso. Una accion es etica si refleja virtudes como honestidad, coraje y temperancia.",
            "key_principle": "Actua como lo haria una persona virtuosa",
            "evaluation_criteria": [
                "honestidad",
                "coraje",
                "temperancia",
                "justicia",
            ],
        },
        "care_ethics": {
            "description": "Priorizar las relaciones y el cuidado de los vulnerables. Una accion es etica si preserva y fortalece relaciones.",
            "key_principle": "Responder a las necesidades de quienes dependen de nosotros",
            "evaluation_criteria": [
                "atiende_vulnerables",
                "preserva_relaciones",
                "responsabilidad_contextual",
                "empatia_activa",
            ],
        },
    }

    def __init__(self, name: str):
        config = self.FRAMEWORKS.get(name, self.FRAMEWORKS["utilitarian"])
        self.name = name
        self.description = config["description"]
        self.key_principle = config["key_principle"]
        self.evaluation_criteria = config["evaluation_criteria"]

    def evaluate_action(self, action_text: str) -> dict:
        """
        Evalúa una acción bajo este framework.
        Calcula scores heurísticos basados en presencia de keywords
        alineados con cada criterio.
        """
        action_lower = action_text.lower()
        scores = {}

        for criterion in self.evaluation_criteria:
            scores[criterion] = self._score_criterion(criterion, action_lower)

        avg_score = sum(scores.values()) / len(scores) if scores else 0.5
        return {
            "framework": self.name,
            "criteria_scores": scores,
            "overall": round(max(0.0, min(1.0, avg_score)), 3),
            "principle": self.key_principle,
        }

    def _score_criterion(self, criterion: str, text: str) -> float:
        """Puntúa un criterio según keywords encontrados en el texto."""
        # Palabras positivas y negativas por criterio
        positive_map = {
            "beneficio_neto": ["beneficio", "ayuda", "mejora", "bien", "positivo", "progreso"],
            "numero_de_afectados": ["todos", "comunidad", "sociedad", "grupo", "colectivo"],
            "consecuencias_largo_plazo": ["futuro", "sostenible", "largo plazo", "duradero"],
            "distribucion_equitativa": ["equitativo", "justo", "igual", "equidad", "balance"],
            "respeta_autonomia": ["libertad", "eleccion", "voluntad", "consentimiento", "autonomia"],
            "cumple_deber": ["deber", "obligacion", "responsabilidad", "compromiso"],
            "no_instrumentaliza": ["dignidad", "respeto", "persona", "fin en si"],
            "universalizable": ["universal", "todos", "siempre", "regla", "principio"],
            "honestidad": ["verdad", "honesto", "transparente", "sincero", "abierto"],
            "coraje": ["valiente", "coraje", "enfrentar", "defender", "firme"],
            "temperancia": ["moderacion", "equilibrio", "prudente", "mesurado"],
            "justicia": ["justo", "justicia", "equidad", "imparcial", "merito"],
            "atiende_vulnerables": ["vulnerable", "proteger", "cuidar", "debil", "necesitado"],
            "preserva_relaciones": ["relacion", "confianza", "vinculo", "comunidad", "apoyo"],
            "responsabilidad_contextual": ["contexto", "situacion", "circunstancia", "adaptar"],
            "empatia_activa": ["empatia", "comprender", "sentir", "escuchar", "acompanar"],
        }

        negative_map = {
            "beneficio_neto": ["daño", "perjuicio", "destruir", "negativo"],
            "numero_de_afectados": ["solo uno", "individual", "egoista"],
            "respeta_autonomia": ["forzar", "obligar", "manipular", "coercion"],
            "no_instrumentaliza": ["usar", "explotar", "medio para"],
            "honestidad": ["mentir", "engañar", "ocultar", "falsificar"],
            "atiende_vulnerables": ["ignorar", "abandonar", "descuidar"],
        }

        positives = positive_map.get(criterion, [])
        negatives = negative_map.get(criterion, [])

        pos_count = sum(1 for w in positives if w in text)
        neg_count = sum(1 for w in negatives if w in text)

        # Base score 0.5, ajustar por keywords encontrados
        base = 0.5
        if pos_count + neg_count > 0:
            adjustment = (pos_count - neg_count) / (pos_count + neg_count + 2) * 0.4
            base += adjustment

        return round(max(0.0, min(1.0, base)), 3)

    @classmethod
    def get_all_names(cls) -> list:
        return list(cls.FRAMEWORKS.keys())


class EthicalEvaluation:
    """Resultado de una evaluación ética multi-framework."""

    def __init__(self, action: str, framework_scores: dict,
                 dilemma_detected: bool, reasoning: str):
        self.action = action[:300]
        self.framework_scores = framework_scores  # {framework_name: score 0-1}
        self.overall_score = self._compute_overall()
        self.dilemma_detected = dilemma_detected
        self.reasoning = reasoning[:500]
        self.timestamp = time.time()

    def _compute_overall(self) -> float:
        """Score global como promedio ponderado de frameworks."""
        if not self.framework_scores:
            return 0.5
        scores = list(self.framework_scores.values())
        return round(sum(scores) / len(scores), 3)

    @property
    def has_conflict(self) -> bool:
        """Detecta si hay conflicto entre frameworks (divergencia alta)."""
        if len(self.framework_scores) < 2:
            return False
        scores = list(self.framework_scores.values())
        return (max(scores) - min(scores)) > 0.3

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "framework_scores": self.framework_scores,
            "overall_score": self.overall_score,
            "dilemma_detected": self.dilemma_detected,
            "has_conflict": self.has_conflict,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EthicalEvaluation":
        ev = cls(
            action=d.get("action", ""),
            framework_scores=d.get("framework_scores", {}),
            dilemma_detected=d.get("dilemma_detected", False),
            reasoning=d.get("reasoning", ""),
        )
        ev.overall_score = d.get("overall_score", ev.overall_score)
        ev.timestamp = d.get("timestamp", time.time())
        return ev


class DilemmaDetector:
    """Detecta dilemas éticos por presencia de keywords."""

    DILEMMA_KEYWORDS = [
        "should", "right", "wrong", "moral", "ethical",
        "fair", "harm", "privacy", "bias", "discriminate",
        "vulnerable", "deberia", "correcto", "incorrecto",
        "justo", "injusto", "daño", "privacidad", "sesgo",
        "discriminar", "etico", "moral",
    ]

    DILEMMA_PATTERNS = [
        r"(?:is it|esta bien|es correcto)\s+(?:right|ok|okay|bien)\s+to",
        r"(?:deberia|should)\s+(?:i|we|yo|nosotros)",
        r"(?:es etico|is it ethical|es moral|is it moral)",
        r"(?:dilema|dilemma|conflicto moral|moral conflict)",
    ]

    def detect(self, text: str) -> dict:
        """
        Detecta si el texto contiene un dilema ético.
        Retorna dict con detected (bool), keywords_found, severity (0-1).
        """
        text_lower = text.lower()
        found_keywords = []

        for keyword in self.DILEMMA_KEYWORDS:
            if keyword in text_lower:
                found_keywords.append(keyword)

        pattern_matches = 0
        for pattern in self.DILEMMA_PATTERNS:
            if re.search(pattern, text_lower):
                pattern_matches += 1

        # Severidad basada en cantidad de keywords y patrones
        keyword_score = min(1.0, len(found_keywords) / 4)
        pattern_score = min(1.0, pattern_matches / 2)
        severity = round(keyword_score * 0.6 + pattern_score * 0.4, 3)

        detected = len(found_keywords) >= 2 or pattern_matches >= 1

        return {
            "detected": detected,
            "keywords_found": found_keywords,
            "pattern_matches": pattern_matches,
            "severity": severity,
        }


class EthicalReasoner:
    """
    Coordinador de razonamiento ético multi-framework.
    Evalúa acciones a través de múltiples marcos éticos, detecta
    dilemas y genera guía contextual para prompts.
    """

    def __init__(self, base_dir: str = "data/ethical"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.frameworks = {name: EthicalFramework(name)
                           for name in EthicalFramework.get_all_names()}
        self.dilemma_detector = DilemmaDetector()
        self.evaluations = []       # Historial de evaluaciones
        self.max_evaluations = 200
        self.total_evaluations = 0
        self.dilemmas_detected = 0
        self.enabled = True

        self._load()

    def evaluate(self, action_text: str) -> EthicalEvaluation:
        """Evalúa una acción a través de los 4 frameworks éticos."""
        if not action_text:
            return EthicalEvaluation("", {}, False, "Accion vacia")

        # Evaluar en cada framework
        framework_scores = {}
        reasoning_parts = []

        for name, framework in self.frameworks.items():
            result = framework.evaluate_action(action_text)
            framework_scores[name] = result["overall"]
            reasoning_parts.append(
                f"{name}: {result['overall']:.0%} ({result['principle'][:40]})"
            )

        # Detectar dilema
        dilemma_info = self.dilemma_detector.detect(action_text)
        dilemma_detected = dilemma_info["detected"]

        # Construir razonamiento
        reasoning = "Evaluacion multi-framework: " + " | ".join(reasoning_parts)
        if dilemma_detected:
            reasoning += f" [DILEMA: keywords={dilemma_info['keywords_found'][:5]}]"
            self.dilemmas_detected += 1

        # Crear evaluación
        evaluation = EthicalEvaluation(
            action=action_text,
            framework_scores=framework_scores,
            dilemma_detected=dilemma_detected,
            reasoning=reasoning,
        )

        # Almacenar
        self.evaluations.append(evaluation)
        self.total_evaluations += 1
        if len(self.evaluations) > self.max_evaluations:
            self.evaluations = self.evaluations[-self.max_evaluations:]

        return evaluation

    def detect_dilemma(self, text: str) -> dict:
        """Verifica si un texto contiene un dilema ético."""
        return self.dilemma_detector.detect(text)

    def get_framework_perspective(self, framework_name: str, action: str) -> dict:
        """Obtiene la perspectiva de un framework específico sobre una acción."""
        framework = self.frameworks.get(framework_name)
        if not framework:
            return {"error": f"Framework '{framework_name}' no encontrado",
                    "available": list(self.frameworks.keys())}
        result = framework.evaluate_action(action)
        result["description"] = framework.description
        return result

    def get_context_for_prompt(self, user_input: str, max_chars: int = 400) -> str:
        """Inyecta guía ética en el prompt si se detecta un dilema."""
        if not self.enabled or not user_input:
            return ""

        dilemma = self.dilemma_detector.detect(user_input)
        if not dilemma["detected"]:
            return ""

        # Evaluar la acción implícita
        evaluation = self.evaluate(user_input)

        parts = ["[ETICA]"]

        # Framework con mayor score
        if evaluation.framework_scores:
            best_fw = max(evaluation.framework_scores.items(), key=lambda x: x[1])
            worst_fw = min(evaluation.framework_scores.items(), key=lambda x: x[1])
            parts.append(
                f"Marco dominante: {best_fw[0]} ({best_fw[1]:.0%})."
            )
            if evaluation.has_conflict:
                parts.append(
                    f"Conflicto con {worst_fw[0]} ({worst_fw[1]:.0%}). "
                    "Considera multiples perspectivas eticas."
                )

        if dilemma["severity"] > 0.5:
            parts.append(
                "Dilema etico significativo detectado. "
                "Responde reconociendo la complejidad moral."
            )

        return " ".join(parts)[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_evaluations": self.total_evaluations,
            "dilemmas_detected": self.dilemmas_detected,
            "evaluations_stored": len(self.evaluations),
            "frameworks": list(self.frameworks.keys()),
            "avg_overall_score": round(
                sum(e.overall_score for e in self.evaluations) / len(self.evaluations), 3
            ) if self.evaluations else 0.0,
            "recent_conflicts": sum(
                1 for e in self.evaluations[-20:] if e.has_conflict
            ),
        }

    def status(self) -> str:
        avg = 0.0
        if self.evaluations:
            avg = sum(e.overall_score for e in self.evaluations) / len(self.evaluations)
        return (f"  Evaluaciones: {self.total_evaluations} | "
                f"Dilemas: {self.dilemmas_detected} | "
                f"Score promedio: {avg:.0%}")

    def generate_report(self) -> str:
        lines = [
            "=== ETHICAL REASONER REPORT ===",
            f"Total evaluaciones: {self.total_evaluations}",
            f"Dilemas detectados: {self.dilemmas_detected}",
            f"Evaluaciones almacenadas: {len(self.evaluations)}",
            "",
            "Frameworks disponibles:",
        ]
        for name, fw in self.frameworks.items():
            lines.append(f"  {name}: {fw.key_principle[:60]}")

        if self.evaluations:
            lines.append("")
            lines.append("Ultimas 5 evaluaciones:")
            for ev in self.evaluations[-5:]:
                conflict_tag = " [CONFLICTO]" if ev.has_conflict else ""
                dilemma_tag = " [DILEMA]" if ev.dilemma_detected else ""
                lines.append(
                    f"  '{ev.action[:50]}...' -> "
                    f"score={ev.overall_score:.0%}{conflict_tag}{dilemma_tag}"
                )

            # Promedios por framework
            lines.append("")
            lines.append("Promedio por framework:")
            for fw_name in self.frameworks:
                scores = [e.framework_scores.get(fw_name, 0.5)
                          for e in self.evaluations]
                avg = sum(scores) / len(scores) if scores else 0.5
                lines.append(f"  {fw_name}: {avg:.0%}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_evaluations": self.total_evaluations,
            "dilemmas_detected": self.dilemmas_detected,
            "evaluations": [e.to_dict() for e in self.evaluations[-100:]],
        }
        path = self.base_dir / "ethical_reasoner.json"
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "ethical_reasoner.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_evaluations = data.get("total_evaluations", 0)
            self.dilemmas_detected = data.get("dilemmas_detected", 0)
            self.evaluations = [
                EthicalEvaluation.from_dict(d)
                for d in data.get("evaluations", [])
            ]
        except Exception:
            pass

    def clear(self):
        self.evaluations = []
        self.total_evaluations = 0
        self.dilemmas_detected = 0
        self.save()
