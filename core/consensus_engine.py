"""
GENESIS — Consensus Engine (v3.4)

Busqueda de consenso entre agentes mediante proceso Delphi iterativo.
Los agentes emiten opiniones con confianza variable, se calcula agreement
por overlap de keywords y se itera hasta consenso o deadlock.

Componentes:
- Opinion: opinion individual de un agente
- DelphiRound: ronda Delphi con opiniones y agreement score
- AgreementMetric: calcula agreement por overlap de posiciones
- ConsensusEngine: coordinador con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class Opinion:
    """Opinion individual de un agente."""

    def __init__(self, agent_name: str, position: str,
                 confidence: float = 0.5, round_number: int = 1):
        self.opinion_id = hashlib.md5(
            f"op_{agent_name}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.agent_name = agent_name
        self.position = position[:500]
        self.confidence = max(0.0, min(1.0, confidence))
        self.round_number = round_number
        self.timestamp = time.time()

    def get_keywords(self) -> set:
        """Extrae keywords significativas de la posicion."""
        words = re.findall(r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}\b', self.position.lower())
        # Filtrar stopwords comunes
        stopwords = {
            "para", "como", "este", "esta", "esos", "esas",
            "pero", "sino", "aunque", "porque", "donde", "cuando",
            "todos", "toda", "cada", "otro", "otra", "entre",
            "desde", "hasta", "sobre", "bajo", "durante",
            "that", "this", "with", "from", "have", "been",
            "they", "their", "which", "would", "could", "should",
        }
        return set(w for w in words if w not in stopwords)

    def to_dict(self) -> dict:
        return {
            "id": self.opinion_id,
            "agent_name": self.agent_name,
            "position": self.position,
            "confidence": round(self.confidence, 3),
            "round_number": self.round_number,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Opinion":
        o = cls(
            agent_name=data.get("agent_name", "unknown"),
            position=data.get("position", ""),
            confidence=data.get("confidence", 0.5),
            round_number=data.get("round_number", 1),
        )
        o.opinion_id = data.get("id", o.opinion_id)
        o.timestamp = data.get("timestamp", time.time())
        return o


class AgreementMetric:
    """Calcula agreement entre opiniones por overlap de keywords."""

    @staticmethod
    def calculate_pairwise(op_a: Opinion, op_b: Opinion) -> float:
        """Agreement entre dos opiniones por overlap de keywords."""
        kw_a = op_a.get_keywords()
        kw_b = op_b.get_keywords()

        if not kw_a or not kw_b:
            return 0.0

        intersection = kw_a & kw_b
        min_size = min(len(kw_a), len(kw_b))

        if min_size == 0:
            return 0.0

        # Overlap normalizado por el menor set
        overlap = len(intersection) / min_size
        # Ponderar por confianza de ambos
        confidence_factor = (op_a.confidence + op_b.confidence) / 2.0
        return overlap * confidence_factor

    @staticmethod
    def calculate_group(opinions: list) -> float:
        """Agreement grupal: promedio de pairwise agreements."""
        if len(opinions) < 2:
            return 1.0 if opinions else 0.0

        total = 0.0
        count = 0

        for i, op_a in enumerate(opinions):
            for op_b in opinions[i + 1:]:
                total += AgreementMetric.calculate_pairwise(op_a, op_b)
                count += 1

        return total / count if count > 0 else 0.0


class DelphiRound:
    """Ronda Delphi con opiniones y agreement score."""

    def __init__(self, round_number: int):
        self.round_number = round_number
        self.opinions = []        # lista de Opinion
        self.agreement_score = 0.0
        self.started_at = time.time()

    def add_opinion(self, opinion: Opinion):
        """Agrega opinion y recalcula agreement."""
        opinion.round_number = self.round_number
        self.opinions.append(opinion)
        self.agreement_score = AgreementMetric.calculate_group(self.opinions)

    def get_majority_position(self) -> str:
        """Retorna la posicion con mayor confianza."""
        if not self.opinions:
            return ""
        best = max(self.opinions, key=lambda o: o.confidence)
        return best.position

    def get_agents(self) -> list:
        """Lista de agentes que participaron."""
        return list(set(o.agent_name for o in self.opinions))

    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "opinions": [o.to_dict() for o in self.opinions],
            "agreement_score": round(self.agreement_score, 3),
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DelphiRound":
        r = cls(round_number=data.get("round_number", 1))
        r.started_at = data.get("started_at", time.time())
        r.opinions = [Opinion.from_dict(od) for od in data.get("opinions", [])]
        r.agreement_score = data.get("agreement_score", 0.0)
        return r


class ConsensusEngine:
    """Coordinador de busqueda de consenso con persistencia."""

    AGREEMENT_THRESHOLD = 0.7
    MAX_ROUNDS = 10

    def __init__(self, base_dir: str = "data/consensus"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.consensuses = []       # lista de consensus dicts (archivados)
        self.current_process = None # proceso activo
        self.total_consensuses = 0
        self.total_deadlocks = 0
        self.enabled = True

        self._load()

    def start_consensus(self, question: str) -> dict:
        """Inicia un proceso Delphi para una pregunta."""
        # Cerrar proceso previo
        if self.current_process:
            self._close_current_process()

        process_id = hashlib.md5(
            f"cons_{question}_{time.time()}".encode()
        ).hexdigest()[:10]

        self.current_process = {
            "id": process_id,
            "question": question[:300],
            "rounds": [DelphiRound(round_number=1)],
            "current_round": 1,
            "started_at": time.time(),
            "resolved": False,
            "deadlocked": False,
            "final_position": "",
        }
        self.total_consensuses += 1

        return {
            "process_id": process_id,
            "question": question,
            "round": 1,
            "status": "started",
        }

    def submit_opinion(self, agent: str, position: str,
                       confidence: float = 0.5) -> dict:
        """Registra una opinion de un agente en la ronda actual."""
        if not self.current_process:
            return {"error": "No hay proceso de consenso activo"}

        opinion = Opinion(
            agent_name=agent,
            position=position,
            confidence=confidence,
            round_number=self.current_process["current_round"],
        )

        current_round = self.current_process["rounds"][-1]
        current_round.add_opinion(opinion)

        return {
            "opinion_id": opinion.opinion_id,
            "agent": agent,
            "confidence": opinion.confidence,
            "round_agreement": current_round.agreement_score,
            "consensus_reached": current_round.agreement_score >= self.AGREEMENT_THRESHOLD,
        }

    def run_round(self) -> dict:
        """Evalua la ronda actual. Si agreement < threshold, abre nueva ronda."""
        if not self.current_process:
            return {"error": "No hay proceso de consenso activo"}

        current_round = self.current_process["rounds"][-1]

        if not current_round.opinions:
            return {"error": "Ronda actual sin opiniones"}

        agreement = current_round.agreement_score

        # Consenso alcanzado
        if agreement >= self.AGREEMENT_THRESHOLD:
            self.current_process["resolved"] = True
            self.current_process["final_position"] = current_round.get_majority_position()
            return {
                "status": "consensus_reached",
                "agreement": round(agreement, 3),
                "position": self.current_process["final_position"][:200],
                "round": current_round.round_number,
            }

        # Verificar deadlock
        if self.is_deadlocked():
            self.current_process["deadlocked"] = True
            self.total_deadlocks += 1
            return {
                "status": "deadlocked",
                "agreement": round(agreement, 3),
                "round": current_round.round_number,
                "message": "Agreement no ha mejorado en 2+ rondas",
            }

        # Limite de rondas
        if self.current_process["current_round"] >= self.MAX_ROUNDS:
            self.current_process["deadlocked"] = True
            self.total_deadlocks += 1
            return {
                "status": "max_rounds_reached",
                "agreement": round(agreement, 3),
                "round": current_round.round_number,
            }

        # Abrir nueva ronda
        new_round_num = self.current_process["current_round"] + 1
        new_round = DelphiRound(round_number=new_round_num)
        self.current_process["rounds"].append(new_round)
        self.current_process["current_round"] = new_round_num

        return {
            "status": "new_round",
            "previous_agreement": round(agreement, 3),
            "new_round": new_round_num,
            "majority_position": current_round.get_majority_position()[:150],
        }

    def get_consensus(self) -> dict:
        """Retorna el consenso final o el estado actual."""
        if not self.current_process:
            return {"status": "no_active_process"}

        if self.current_process.get("resolved"):
            return {
                "status": "resolved",
                "position": self.current_process["final_position"],
                "rounds_needed": self.current_process["current_round"],
            }

        if self.current_process.get("deadlocked"):
            # Retornar posicion con mayor confianza como best-effort
            all_opinions = []
            for rnd in self.current_process["rounds"]:
                all_opinions.extend(rnd.opinions)

            best = max(all_opinions, key=lambda o: o.confidence) if all_opinions else None
            return {
                "status": "deadlocked",
                "best_effort_position": best.position[:200] if best else "",
                "best_confidence": best.confidence if best else 0.0,
                "rounds_attempted": self.current_process["current_round"],
            }

        # En progreso
        current_round = self.current_process["rounds"][-1]
        return {
            "status": "in_progress",
            "current_agreement": round(current_round.agreement_score, 3),
            "round": self.current_process["current_round"],
            "opinions_this_round": len(current_round.opinions),
        }

    def is_deadlocked(self) -> bool:
        """True si el agreement no ha mejorado en 2+ rondas consecutivas."""
        if not self.current_process:
            return False

        rounds = self.current_process["rounds"]
        if len(rounds) < 3:
            return False

        # Comparar agreement de las ultimas 3 rondas
        scores = [r.agreement_score for r in rounds[-3:] if r.opinions]
        if len(scores) < 3:
            return False

        # Si no hubo mejora significativa (< 0.05) en 2 transiciones
        improvement_1 = scores[1] - scores[0]
        improvement_2 = scores[2] - scores[1]

        return improvement_1 < 0.05 and improvement_2 < 0.05

    def _close_current_process(self):
        """Cierra el proceso actual y lo archiva."""
        if not self.current_process:
            return

        archived = {
            "id": self.current_process["id"],
            "question": self.current_process["question"],
            "rounds": [r.to_dict() for r in self.current_process["rounds"]],
            "current_round": self.current_process["current_round"],
            "started_at": self.current_process["started_at"],
            "ended_at": time.time(),
            "resolved": self.current_process.get("resolved", False),
            "deadlocked": self.current_process.get("deadlocked", False),
            "final_position": self.current_process.get("final_position", ""),
        }
        self.consensuses.append(archived)

        if len(self.consensuses) > 50:
            self.consensuses = self.consensuses[-50:]

        self.current_process = None

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de consenso para inyectar en prompt."""
        if not self.enabled or not self.current_process:
            return ""

        rounds = self.current_process["rounds"]
        all_opinions = []
        for rnd in rounds:
            all_opinions.extend(rnd.opinions)

        if not all_opinions:
            return ""

        current_round = rounds[-1]
        parts = [f"[CONSENSO ACTIVO: '{self.current_process['question'][:80]}']"]
        parts.append(f"Ronda: {self.current_process['current_round']} | "
                     f"Agreement: {current_round.agreement_score:.0%}")

        # Incluir opiniones con mayor confianza
        top_opinions = sorted(all_opinions, key=lambda o: o.confidence, reverse=True)[:3]
        for op in top_opinions:
            parts.append(f"  [{op.agent_name}] ({op.confidence:.0%}): {op.position[:100]}")

        if self.is_deadlocked():
            parts.append("  ALERTA: Proceso estancado, considerar resolucion forzada.")

        result = "\n".join(parts)
        return result[:max_chars]

    def get_stats(self) -> dict:
        active_question = ""
        active_agreement = 0.0
        if self.current_process:
            active_question = self.current_process["question"][:80]
            current_round = self.current_process["rounds"][-1]
            active_agreement = current_round.agreement_score

        return {
            "total_consensuses": self.total_consensuses,
            "total_deadlocks": self.total_deadlocks,
            "active_question": active_question,
            "active_agreement": round(active_agreement, 3),
            "archived": len(self.consensuses),
            "has_active_process": self.current_process is not None,
            "deadlock_rate": round(
                self.total_deadlocks / max(1, self.total_consensuses), 3
            ),
        }

    def status(self) -> str:
        active = "si" if self.current_process else "no"
        agreement = ""
        if self.current_process:
            current_round = self.current_process["rounds"][-1]
            agreement = f" | Agreement: {current_round.agreement_score:.0%}"
        dl = f" | Deadlocks: {self.total_deadlocks}" if self.total_deadlocks else ""
        return (f"  Consensos: {self.total_consensuses} | "
                f"Activo: {active}{agreement}{dl}")

    def generate_report(self) -> str:
        lines = [
            "=== CONSENSUS ENGINE ===",
            f"Total procesos: {self.total_consensuses}",
            f"Deadlocks: {self.total_deadlocks}",
            f"Archivados: {len(self.consensuses)}",
        ]

        if self.current_process:
            lines.append(f"\nProceso activo: '{self.current_process['question'][:100]}'")
            lines.append(f"  Ronda actual: {self.current_process['current_round']}")
            for rnd in self.current_process["rounds"]:
                agents = ", ".join(o.agent_name for o in rnd.opinions)
                lines.append(f"  Ronda {rnd.round_number}: {len(rnd.opinions)} opiniones, "
                             f"agreement {rnd.agreement_score:.0%} [{agents}]")
            if self.is_deadlocked():
                lines.append("  ESTADO: DEADLOCKED")

        if self.consensuses:
            lines.append(f"\nUltimos procesos:")
            for c in self.consensuses[-5:]:
                status = "resuelto" if c.get("resolved") else (
                    "deadlock" if c.get("deadlocked") else "cerrado")
                lines.append(f"  '{c['question'][:60]}' — {status}, "
                             f"{c.get('current_round', 0)} rondas")

        return "\n".join(lines)

    def save(self):
        current_data = None
        if self.current_process:
            current_data = {
                "id": self.current_process["id"],
                "question": self.current_process["question"],
                "rounds": [r.to_dict() for r in self.current_process["rounds"]],
                "current_round": self.current_process["current_round"],
                "started_at": self.current_process["started_at"],
                "resolved": self.current_process.get("resolved", False),
                "deadlocked": self.current_process.get("deadlocked", False),
                "final_position": self.current_process.get("final_position", ""),
            }

        data = {
            "total_consensuses": self.total_consensuses,
            "total_deadlocks": self.total_deadlocks,
            "current_process": current_data,
            "consensuses": self.consensuses[-50:],
        }
        path = self.base_dir / "consensus_engine.json"
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "consensus_engine.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_consensuses = data.get("total_consensuses", 0)
            self.total_deadlocks = data.get("total_deadlocks", 0)
            self.consensuses = data.get("consensuses", [])

            cd = data.get("current_process")
            if cd and not cd.get("resolved") and not cd.get("deadlocked"):
                self.current_process = {
                    "id": cd["id"],
                    "question": cd["question"],
                    "rounds": [DelphiRound.from_dict(rd) for rd in cd.get("rounds", [])],
                    "current_round": cd.get("current_round", 1),
                    "started_at": cd.get("started_at", time.time()),
                    "resolved": False,
                    "deadlocked": False,
                    "final_position": cd.get("final_position", ""),
                }
        except Exception:
            pass

    def clear(self):
        self.consensuses = []
        self.current_process = None
        self.total_consensuses = 0
        self.total_deadlocks = 0
        self.save()
