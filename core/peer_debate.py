"""
GENESIS — Peer Debate (v3.4)

Debate multi-instancia estructurado entre roles internos.
Cada debate tiene proponente, oponente y mediador que argumentan
con fuerza variable. El consenso se calcula por peso de rol y
fuerza de argumentos.

Componentes:
- DebateRole: definicion de roles con peso de scoring
- DebateArgument: argumento individual con fuerza y rebuttal
- DebateRound: ronda con argumentos y consensus score
- PeerDebate: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class DebateRole:
    """Definicion de un rol de debate con peso de scoring."""

    ROLES = {
        "proponent": {
            "description": "Defiende la posicion principal, presenta evidencia a favor",
            "scoring_weight": 1.0,
        },
        "opponent": {
            "description": "Cuestiona y ataca la posicion, busca debilidades y contraejemplos",
            "scoring_weight": 0.8,
        },
        "mediator": {
            "description": "Busca puntos medios, sintetiza posiciones y propone compromisos",
            "scoring_weight": 1.2,
        },
    }

    def __init__(self, name: str):
        config = self.ROLES.get(name, self.ROLES["proponent"])
        self.name = name
        self.description = config["description"]
        self.scoring_weight = config["scoring_weight"]

    @classmethod
    def get_all(cls) -> list:
        return list(cls.ROLES.keys())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "scoring_weight": self.scoring_weight,
        }


class DebateArgument:
    """Argumento individual en un debate."""

    def __init__(self, role: str, content: str, strength: float = 0.5,
                 rebuttal_to: str = None):
        self.arg_id = hashlib.md5(
            f"arg_{role}_{time.time()}_{content[:20]}".encode()
        ).hexdigest()[:10]
        self.role = role
        self.content = content[:500]
        self.strength = max(0.0, min(1.0, strength))
        self.timestamp = time.time()
        self.rebuttal_to = rebuttal_to  # arg_id del argumento refutado

    def is_rebuttal(self) -> bool:
        """Es este argumento una refutacion de otro?"""
        return self.rebuttal_to is not None

    def effective_strength(self) -> float:
        """Fuerza efectiva considerando el peso del rol."""
        role_obj = DebateRole(self.role)
        return self.strength * role_obj.scoring_weight

    def to_dict(self) -> dict:
        return {
            "id": self.arg_id,
            "role": self.role,
            "content": self.content,
            "strength": round(self.strength, 3),
            "timestamp": self.timestamp,
            "rebuttal_to": self.rebuttal_to,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DebateArgument":
        a = cls(
            role=data.get("role", "proponent"),
            content=data.get("content", ""),
            strength=data.get("strength", 0.5),
            rebuttal_to=data.get("rebuttal_to"),
        )
        a.arg_id = data.get("id", a.arg_id)
        a.timestamp = data.get("timestamp", time.time())
        return a


class DebateRound:
    """Ronda de debate con argumentos y consensus score."""

    def __init__(self, round_number: int):
        self.round_number = round_number
        self.arguments = []       # lista de DebateArgument
        self.consensus_score = 0.0
        self.started_at = time.time()

    def add_argument(self, argument: DebateArgument):
        """Agrega argumento y recalcula consensus."""
        self.arguments.append(argument)
        self.consensus_score = self._calculate_consensus()

    def _calculate_consensus(self) -> float:
        """Calcula consensus score de la ronda.

        Promedio ponderado de fuerzas efectivas. Si hay rebuttals,
        la fuerza del argumento refutado se reduce.
        """
        if not self.arguments:
            return 0.0

        # Mapear refutaciones para ajustar fuerzas
        rebutted = {}
        for arg in self.arguments:
            if arg.rebuttal_to:
                rebutted[arg.rebuttal_to] = arg.strength

        total_weight = 0.0
        weighted_sum = 0.0

        for arg in self.arguments:
            role_obj = DebateRole(arg.role)
            weight = role_obj.scoring_weight

            effective = arg.strength
            # Si este argumento fue refutado, reducir su fuerza
            if arg.arg_id in rebutted:
                rebuttal_strength = rebutted[arg.arg_id]
                effective = effective * (1.0 - rebuttal_strength * 0.5)

            weighted_sum += effective * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def get_strongest_argument(self) -> DebateArgument:
        """Retorna el argumento mas fuerte de la ronda."""
        if not self.arguments:
            return None
        return max(self.arguments, key=lambda a: a.effective_strength())

    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "arguments": [a.to_dict() for a in self.arguments],
            "consensus_score": round(self.consensus_score, 3),
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DebateRound":
        r = cls(round_number=data.get("round_number", 0))
        r.started_at = data.get("started_at", time.time())
        r.arguments = [DebateArgument.from_dict(ad) for ad in data.get("arguments", [])]
        r.consensus_score = data.get("consensus_score", 0.0)
        return r


class PeerDebate:
    """Coordinador de debates multi-instancia con persistencia."""

    def __init__(self, base_dir: str = "data/peer_debate"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.debates = []            # lista de debate dicts
        self.current_debate = None   # debate activo (dict con topic, rounds, etc.)
        self.total_debates = 0
        self.total_arguments = 0
        self.enabled = True

        self._load()

    def start_debate(self, topic: str) -> dict:
        """Inicia un nuevo debate con un tema dado."""
        # Cerrar debate previo si existe
        if self.current_debate:
            self._close_current_debate()

        debate_id = hashlib.md5(
            f"debate_{topic}_{time.time()}".encode()
        ).hexdigest()[:10]

        self.current_debate = {
            "id": debate_id,
            "topic": topic[:300],
            "rounds": [DebateRound(round_number=1)],
            "current_round": 1,
            "started_at": time.time(),
            "concluded": False,
            "conclusion": "",
        }
        self.total_debates += 1

        return {
            "debate_id": debate_id,
            "topic": topic,
            "round": 1,
            "status": "started",
        }

    def add_argument(self, role: str, content: str, strength: float = 0.5,
                     rebuttal_to: str = None) -> dict:
        """Agrega un argumento al debate activo."""
        if not self.current_debate:
            return {"error": "No hay debate activo"}

        if role not in DebateRole.ROLES:
            role = "proponent"

        argument = DebateArgument(
            role=role,
            content=content,
            strength=strength,
            rebuttal_to=rebuttal_to,
        )

        current_round = self.current_debate["rounds"][-1]
        current_round.add_argument(argument)
        self.total_arguments += 1

        return {
            "arg_id": argument.arg_id,
            "role": role,
            "strength": argument.strength,
            "effective_strength": argument.effective_strength(),
            "round_consensus": current_round.consensus_score,
            "is_rebuttal": argument.is_rebuttal(),
        }

    def advance_round(self) -> dict:
        """Avanza a la siguiente ronda del debate."""
        if not self.current_debate:
            return {"error": "No hay debate activo"}

        current_round = self.current_debate["rounds"][-1]
        if not current_round.arguments:
            return {"error": "Ronda actual sin argumentos"}

        new_round_num = self.current_debate["current_round"] + 1
        new_round = DebateRound(round_number=new_round_num)
        self.current_debate["rounds"].append(new_round)
        self.current_debate["current_round"] = new_round_num

        return {
            "round": new_round_num,
            "previous_consensus": current_round.consensus_score,
            "total_arguments_so_far": sum(
                len(r.arguments) for r in self.current_debate["rounds"]
            ),
        }

    def calculate_consensus(self) -> float:
        """Calcula consenso global del debate activo.

        Promedio ponderado de consensus scores de todas las rondas,
        dando mas peso a rondas recientes.
        """
        if not self.current_debate:
            return 0.0

        rounds = self.current_debate["rounds"]
        if not rounds:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for i, rnd in enumerate(rounds):
            if not rnd.arguments:
                continue
            # Rondas posteriores pesan mas (recency weighting)
            weight = 1.0 + i * 0.3
            weighted_sum += rnd.consensus_score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def get_conclusion(self) -> str:
        """Genera conclusion textual del debate activo."""
        if not self.current_debate:
            return "No hay debate activo."

        rounds = self.current_debate["rounds"]
        all_args = []
        for rnd in rounds:
            all_args.extend(rnd.arguments)

        if not all_args:
            return f"Debate sobre '{self.current_debate['topic']}' sin argumentos."

        # Encontrar argumentos mas fuertes por rol
        by_role = defaultdict(list)
        for arg in all_args:
            by_role[arg.role].append(arg)

        strongest = {}
        for role, args in by_role.items():
            strongest[role] = max(args, key=lambda a: a.effective_strength())

        consensus = self.calculate_consensus()

        # Construir conclusion
        lines = [f"Conclusion del debate: '{self.current_debate['topic']}'"]
        lines.append(f"Rondas: {len(rounds)} | Argumentos: {len(all_args)} | "
                     f"Consenso: {consensus:.0%}")

        if "proponent" in strongest:
            lines.append(f"  Posicion principal: {strongest['proponent'].content[:150]}")
        if "opponent" in strongest:
            lines.append(f"  Objecion principal: {strongest['opponent'].content[:150]}")
        if "mediator" in strongest:
            lines.append(f"  Mediacion: {strongest['mediator'].content[:150]}")

        if consensus >= 0.7:
            lines.append("Resultado: Alto consenso alcanzado.")
        elif consensus >= 0.4:
            lines.append("Resultado: Consenso parcial, posiciones divergentes persisten.")
        else:
            lines.append("Resultado: Bajo consenso, debate no resuelto.")

        conclusion = "\n".join(lines)
        self.current_debate["conclusion"] = conclusion
        return conclusion

    def _close_current_debate(self):
        """Cierra el debate actual y lo archiva."""
        if not self.current_debate:
            return

        if not self.current_debate.get("conclusion"):
            self.get_conclusion()

        self.current_debate["concluded"] = True
        self.current_debate["ended_at"] = time.time()

        # Serializar rounds para almacenamiento
        archived = {
            "id": self.current_debate["id"],
            "topic": self.current_debate["topic"],
            "rounds": [r.to_dict() for r in self.current_debate["rounds"]],
            "current_round": self.current_debate["current_round"],
            "started_at": self.current_debate["started_at"],
            "ended_at": self.current_debate.get("ended_at", time.time()),
            "concluded": True,
            "conclusion": self.current_debate.get("conclusion", ""),
            "final_consensus": self.calculate_consensus(),
        }
        self.debates.append(archived)

        # Limitar historial
        if len(self.debates) > 50:
            self.debates = self.debates[-50:]

        self.current_debate = None

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de debate para inyectar en prompt."""
        if not self.enabled or not self.current_debate:
            return ""

        rounds = self.current_debate["rounds"]
        if not rounds:
            return ""

        # Solo inyectar si hay argumentos
        all_args = []
        for rnd in rounds:
            all_args.extend(rnd.arguments)

        if not all_args:
            return ""

        consensus = self.calculate_consensus()
        parts = [f"[DEBATE ACTIVO: '{self.current_debate['topic'][:80]}']"]
        parts.append(f"Consenso actual: {consensus:.0%} | Ronda: {self.current_debate['current_round']}")

        # Incluir argumentos mas fuertes
        top_args = sorted(all_args, key=lambda a: a.effective_strength(), reverse=True)[:3]
        for arg in top_args:
            parts.append(f"  [{arg.role}] ({arg.strength:.0%}): {arg.content[:100]}")

        result = "\n".join(parts)
        return result[:max_chars]

    def get_stats(self) -> dict:
        active_topic = ""
        active_consensus = 0.0
        if self.current_debate:
            active_topic = self.current_debate["topic"][:80]
            active_consensus = self.calculate_consensus()

        return {
            "total_debates": self.total_debates,
            "total_arguments": self.total_arguments,
            "active_debate": active_topic,
            "active_consensus": round(active_consensus, 3),
            "archived_debates": len(self.debates),
            "has_active_debate": self.current_debate is not None,
        }

    def status(self) -> str:
        active = "si" if self.current_debate else "no"
        consensus = ""
        if self.current_debate:
            consensus = f" | Consenso: {self.calculate_consensus():.0%}"
        return (f"  Debates: {self.total_debates} | "
                f"Argumentos: {self.total_arguments} | "
                f"Activo: {active}{consensus}")

    def generate_report(self) -> str:
        lines = [
            "=== PEER DEBATE ===",
            f"Total debates: {self.total_debates}",
            f"Total argumentos: {self.total_arguments}",
            f"Debates archivados: {len(self.debates)}",
        ]

        if self.current_debate:
            lines.append(f"\nDebate activo: '{self.current_debate['topic'][:100]}'")
            lines.append(f"  Ronda actual: {self.current_debate['current_round']}")
            lines.append(f"  Consenso: {self.calculate_consensus():.0%}")
            for rnd in self.current_debate["rounds"]:
                lines.append(f"  Ronda {rnd.round_number}: {len(rnd.arguments)} args, "
                             f"consenso {rnd.consensus_score:.0%}")

        if self.debates:
            lines.append(f"\nUltimos debates:")
            for d in self.debates[-5:]:
                lines.append(f"  '{d['topic'][:60]}' — consenso: "
                             f"{d.get('final_consensus', 0):.0%}, "
                             f"{d.get('current_round', 0)} rondas")

        return "\n".join(lines)

    def save(self):
        # Serializar debate actual si existe
        current_data = None
        if self.current_debate:
            current_data = {
                "id": self.current_debate["id"],
                "topic": self.current_debate["topic"],
                "rounds": [r.to_dict() for r in self.current_debate["rounds"]],
                "current_round": self.current_debate["current_round"],
                "started_at": self.current_debate["started_at"],
                "concluded": self.current_debate.get("concluded", False),
                "conclusion": self.current_debate.get("conclusion", ""),
            }

        data = {
            "total_debates": self.total_debates,
            "total_arguments": self.total_arguments,
            "current_debate": current_data,
            "debates": self.debates[-50:],
        }
        path = self.base_dir / "peer_debate.json"
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "peer_debate.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_debates = data.get("total_debates", 0)
            self.total_arguments = data.get("total_arguments", 0)
            self.debates = data.get("debates", [])

            # Restaurar debate activo
            cd = data.get("current_debate")
            if cd and not cd.get("concluded", False):
                self.current_debate = {
                    "id": cd["id"],
                    "topic": cd["topic"],
                    "rounds": [DebateRound.from_dict(rd) for rd in cd.get("rounds", [])],
                    "current_round": cd.get("current_round", 1),
                    "started_at": cd.get("started_at", time.time()),
                    "concluded": False,
                    "conclusion": cd.get("conclusion", ""),
                }
        except Exception:
            pass

    def clear(self):
        self.debates = []
        self.current_debate = None
        self.total_debates = 0
        self.total_arguments = 0
        self.save()
