"""
GENESIS — Architecture Evolver (v4.0)

Evolución de la propia arquitectura de Genesis: analiza módulos,
detecta redundancias, propone evoluciones (merge, split, deprecate,
optimize) y simula impacto antes de aplicar cambios.

Componentes:
- ModuleProfile: perfil de un módulo con métricas de uso y dependencias
- RedundancyDetector: detecta módulos similares/redundantes por keywords
- EvolutionProposal: propuesta de cambio arquitectónico con impacto
- ArchitectureEvolver: coordinador con persistencia y análisis
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class ModuleProfile:
    """Perfil de un módulo con métricas de uso y dependencias."""

    def __init__(self, name: str, import_count: int = 0, usage_count: int = 0,
                 line_count: int = 0, dependencies: list = None):
        self.profile_id = hashlib.md5(
            f"mod_{name}".encode()
        ).hexdigest()[:10]
        self.name = name.lower().strip()
        self.import_count = import_count
        self.usage_count = usage_count
        self.line_count = line_count
        self.dependencies = dependencies or []
        self.last_used = time.time()
        self.created_at = time.time()
        self.keywords = self._extract_keywords(name)

    def _extract_keywords(self, name: str) -> list:
        """Extrae keywords del nombre del módulo."""
        # Separar por _ y camelCase
        parts = re.split(r'[_\-.]', name.lower())
        # También separar camelCase
        expanded = []
        for part in parts:
            sub = re.findall(r'[a-z]+', part)
            expanded.extend(sub)
        # Filtrar palabras muy cortas
        return [w for w in expanded if len(w) > 2]

    def keyword_overlap(self, other: "ModuleProfile") -> float:
        """
        Calcula overlap de keywords con otro módulo.
        Usa containment: |A ∩ B| / min(|A|, |B|)
        """
        set_a = set(self.keywords)
        set_b = set(other.keywords)
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        min_size = min(len(set_a), len(set_b))
        return len(intersection) / min_size if min_size > 0 else 0.0

    def dependency_overlap(self, other: "ModuleProfile") -> float:
        """Calcula overlap de dependencias con otro módulo."""
        set_a = set(self.dependencies)
        set_b = set(other.dependencies)
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        min_size = min(len(set_a), len(set_b))
        return len(intersection) / min_size if min_size > 0 else 0.0

    def health_score(self) -> float:
        """
        Score de salud del módulo (0-1).
        Considera: uso, tamaño, dependencias.
        """
        # Factor de uso: más usado = más sano
        usage_factor = min(1.0, (self.usage_count + self.import_count) / 20)

        # Factor de tamaño: ni muy grande ni muy pequeño
        if self.line_count == 0:
            size_factor = 0.3
        elif self.line_count < 20:
            size_factor = 0.5
        elif self.line_count <= 500:
            size_factor = 1.0
        elif self.line_count <= 1000:
            size_factor = 0.7
        else:
            size_factor = 0.4

        # Factor de dependencias: menos = mejor
        dep_count = len(self.dependencies)
        if dep_count <= 3:
            dep_factor = 1.0
        elif dep_count <= 8:
            dep_factor = 0.7
        elif dep_count <= 15:
            dep_factor = 0.4
        else:
            dep_factor = 0.2

        return round(usage_factor * 0.4 + size_factor * 0.3 + dep_factor * 0.3, 3)

    def to_dict(self) -> dict:
        return {
            "id": self.profile_id,
            "name": self.name,
            "import_count": self.import_count,
            "usage_count": self.usage_count,
            "line_count": self.line_count,
            "dependencies": self.dependencies[:30],
            "keywords": self.keywords,
            "last_used": self.last_used,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModuleProfile":
        m = cls(
            name=data.get("name", ""),
            import_count=data.get("import_count", 0),
            usage_count=data.get("usage_count", 0),
            line_count=data.get("line_count", 0),
            dependencies=data.get("dependencies", []),
        )
        m.profile_id = data.get("id", m.profile_id)
        m.keywords = data.get("keywords", m.keywords)
        m.last_used = data.get("last_used", time.time())
        m.created_at = data.get("created_at", time.time())
        return m


class RedundancyDetector:
    """Detecta módulos similares/redundantes por overlap de keywords."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold  # Containment mínimo para considerar redundante

    def detect(self, profiles: list) -> list:
        """
        Detecta pares de módulos potencialmente redundantes.

        Returns:
            Lista de dicts con 'module_a', 'module_b', 'keyword_overlap',
            'dependency_overlap', 'combined_score'
        """
        redundancies = []

        for i, a in enumerate(profiles):
            for b in profiles[i + 1:]:
                kw_overlap = a.keyword_overlap(b)
                dep_overlap = a.dependency_overlap(b)

                # Combinar ambos overlaps
                combined = kw_overlap * 0.6 + dep_overlap * 0.4

                if kw_overlap >= self.threshold or combined >= self.threshold:
                    redundancies.append({
                        "module_a": a.name,
                        "module_b": b.name,
                        "keyword_overlap": round(kw_overlap, 3),
                        "dependency_overlap": round(dep_overlap, 3),
                        "combined_score": round(combined, 3),
                        "shared_keywords": sorted(set(a.keywords) & set(b.keywords)),
                        "shared_deps": sorted(set(a.dependencies) & set(b.dependencies)),
                    })

        redundancies.sort(key=lambda r: r["combined_score"], reverse=True)
        return redundancies[:20]

    def find_isolated_modules(self, profiles: list) -> list:
        """Encuentra módulos sin dependencias ni dependientes (posibles candidatos a deprecar)."""
        all_deps = set()
        for p in profiles:
            all_deps.update(p.dependencies)

        isolated = []
        for p in profiles:
            is_dependency = p.name in all_deps
            has_deps = len(p.dependencies) > 0
            if not is_dependency and not has_deps and p.usage_count < 3:
                isolated.append({
                    "module": p.name,
                    "usage_count": p.usage_count,
                    "line_count": p.line_count,
                    "health": p.health_score(),
                })

        return sorted(isolated, key=lambda x: x["usage_count"])


class EvolutionProposal:
    """Propuesta de cambio arquitectónico."""

    VALID_TYPES = ("merge", "split", "deprecate", "optimize")

    def __init__(self, proposal_type: str, target_modules: list = None,
                 rationale: str = "", impact_score: float = 0.0):
        self.proposal_id = hashlib.md5(
            f"prop_{time.time()}_{proposal_type}".encode()
        ).hexdigest()[:10]
        self.type = proposal_type if proposal_type in self.VALID_TYPES else "optimize"
        self.target_modules = target_modules or []
        self.rationale = rationale
        self.impact_score = max(0.0, min(1.0, impact_score))
        self.proposed_at = time.time()
        self.status = "pending"  # pending, accepted, rejected, implemented

    def to_dict(self) -> dict:
        return {
            "id": self.proposal_id,
            "type": self.type,
            "target_modules": self.target_modules,
            "rationale": self.rationale[:300],
            "impact_score": round(self.impact_score, 3),
            "proposed_at": self.proposed_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvolutionProposal":
        p = cls(
            proposal_type=data.get("type", "optimize"),
            target_modules=data.get("target_modules", []),
            rationale=data.get("rationale", ""),
            impact_score=data.get("impact_score", 0.0),
        )
        p.proposal_id = data.get("id", p.proposal_id)
        p.proposed_at = data.get("proposed_at", time.time())
        p.status = data.get("status", "pending")
        return p

    def __repr__(self):
        return (f"Proposal({self.type}: {', '.join(self.target_modules[:3])} "
                f"impact={self.impact_score:.2f} [{self.status}])")


class ArchitectureEvolver:
    """
    Coordinador de evolución arquitectónica.
    Perfila módulos, detecta redundancias, propone evoluciones.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/arch_evolver")
        self.data_file = self.base_dir / "arch_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.profiles = {}             # name -> ModuleProfile
        self.proposals = []            # Lista de EvolutionProposal
        self.redundancy_detector = RedundancyDetector()
        self.max_proposals = 100
        self.total_proposals = 0
        self.accepted_proposals = 0
        self.enabled = True

        self._load()

    def profile_module(self, name: str, imports: int = 0, usages: int = 0,
                       lines: int = 0, deps: list = None) -> ModuleProfile:
        """
        Registra o actualiza el perfil de un módulo.

        Args:
            name: nombre del módulo
            imports: cuántas veces es importado por otros
            usages: cuántas veces se usa activamente
            lines: cantidad de líneas de código
            deps: lista de dependencias (otros módulos)
        """
        name_key = name.lower().strip()

        if name_key in self.profiles:
            # Actualizar existente
            p = self.profiles[name_key]
            p.import_count = imports
            p.usage_count = usages
            p.line_count = lines
            if deps is not None:
                p.dependencies = deps
            p.last_used = time.time()
        else:
            p = ModuleProfile(
                name=name_key,
                import_count=imports,
                usage_count=usages,
                line_count=lines,
                dependencies=deps,
            )
            self.profiles[name_key] = p

        return p

    def detect_redundancies(self) -> list:
        """Encuentra módulos similares/redundantes."""
        if len(self.profiles) < 2:
            return []
        profiles_list = list(self.profiles.values())
        return self.redundancy_detector.detect(profiles_list)

    def propose_evolution(self, target: str, proposal_type: str,
                          rationale: str = "") -> EvolutionProposal:
        """
        Crea una propuesta de evolución.

        Args:
            target: módulo(s) objetivo (puede ser "mod_a,mod_b" para merge)
            proposal_type: 'merge', 'split', 'deprecate', 'optimize'
            rationale: justificación

        Returns:
            EvolutionProposal creada
        """
        target_modules = [t.strip() for t in target.split(",") if t.strip()]

        # Auto-generar rationale si no se provee
        if not rationale:
            rationale = self._auto_rationale(target_modules, proposal_type)

        # Calcular impacto
        impact = self._estimate_impact_for_modules(target_modules)

        proposal = EvolutionProposal(
            proposal_type=proposal_type,
            target_modules=target_modules,
            rationale=rationale,
            impact_score=impact,
        )

        self.proposals.append(proposal)
        self.total_proposals += 1

        if len(self.proposals) > self.max_proposals:
            self.proposals = self.proposals[-self.max_proposals:]

        return proposal

    def simulate_impact(self, proposal: EvolutionProposal) -> dict:
        """
        Simula el impacto de una propuesta antes de aplicarla.

        Returns:
            dict con 'impact_score' (0-1), 'affected_modules',
            'risk_level', 'details'
        """
        affected = set()
        total_usage = 0
        total_imports = 0

        for mod_name in proposal.target_modules:
            profile = self.profiles.get(mod_name)
            if not profile:
                continue

            total_usage += profile.usage_count
            total_imports += profile.import_count

            # Módulos que dependen de este
            for p in self.profiles.values():
                if mod_name in p.dependencies:
                    affected.add(p.name)

            # Dependencias del módulo
            for dep in profile.dependencies:
                affected.add(dep)

        # Calcular impact score
        total_modules = max(len(self.profiles), 1)
        dependency_factor = len(affected) / total_modules
        usage_factor = min(1.0, (total_usage + total_imports) / 50)

        impact_score = dependency_factor * 0.5 + usage_factor * 0.5
        impact_score = min(1.0, max(0.0, impact_score))

        # Risk level
        if impact_score >= 0.7:
            risk_level = "high"
        elif impact_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Actualizar el proposal
        proposal.impact_score = round(impact_score, 3)

        return {
            "impact_score": round(impact_score, 3),
            "affected_modules": sorted(affected),
            "affected_count": len(affected),
            "risk_level": risk_level,
            "total_usage": total_usage,
            "total_imports": total_imports,
            "details": {
                "dependency_factor": round(dependency_factor, 3),
                "usage_factor": round(usage_factor, 3),
            },
        }

    def accept_proposal(self, proposal_id: str) -> bool:
        """Marca una propuesta como aceptada."""
        for p in self.proposals:
            if p.proposal_id == proposal_id:
                p.status = "accepted"
                self.accepted_proposals += 1
                return True
        return False

    def reject_proposal(self, proposal_id: str) -> bool:
        """Marca una propuesta como rechazada."""
        for p in self.proposals:
            if p.proposal_id == proposal_id:
                p.status = "rejected"
                return True
        return False

    def auto_propose(self) -> list:
        """
        Genera propuestas automáticas basadas en el análisis actual.
        Busca redundancias, módulos aislados, y módulos grandes.
        """
        new_proposals = []

        # 1. Propuestas de merge para módulos redundantes
        redundancies = self.detect_redundancies()
        for r in redundancies[:3]:
            if r["combined_score"] >= 0.7:
                target = f"{r['module_a']},{r['module_b']}"
                shared = ", ".join(r["shared_keywords"][:3])
                rationale = (f"High overlap ({r['combined_score']:.0%}): "
                             f"shared keywords [{shared}]")
                prop = self.propose_evolution(target, "merge", rationale)
                new_proposals.append(prop)

        # 2. Propuestas de deprecate para módulos aislados
        profiles_list = list(self.profiles.values())
        isolated = self.redundancy_detector.find_isolated_modules(profiles_list)
        for iso in isolated[:2]:
            if iso["health"] < 0.4:
                prop = self.propose_evolution(
                    iso["module"], "deprecate",
                    f"Low health ({iso['health']:.2f}), usage={iso['usage_count']}, isolated"
                )
                new_proposals.append(prop)

        # 3. Propuestas de split para módulos muy grandes
        for p in self.profiles.values():
            if p.line_count > 800 and p.usage_count > 5:
                prop = self.propose_evolution(
                    p.name, "split",
                    f"Large module ({p.line_count} lines) with high usage ({p.usage_count})"
                )
                new_proposals.append(prop)

        return new_proposals

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Inyecta sugerencias de arquitectura si hay propuestas pendientes."""
        if not self.enabled:
            return ""

        pending = [p for p in self.proposals if p.status == "pending"]
        if not pending:
            return ""

        lines = ["[ARCHITECTURE EVOLUTION PROPOSALS]"]
        total = 0
        for p in pending[:3]:
            text = (f"  [{p.type.upper()}] {', '.join(p.target_modules[:2])}: "
                    f"{p.rationale[:80]} (impact={p.impact_score:.2f})")
            if total + len(text) > max_chars:
                break
            lines.append(text)
            total += len(text)

        return "\n".join(lines) if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        """Estadísticas completas."""
        healths = [p.health_score() for p in self.profiles.values()]
        avg_health = sum(healths) / max(len(healths), 1) if healths else 0.0

        return {
            "total_modules": len(self.profiles),
            "total_proposals": self.total_proposals,
            "accepted_proposals": self.accepted_proposals,
            "pending_proposals": len([p for p in self.proposals if p.status == "pending"]),
            "avg_health": round(avg_health, 3),
            "redundancies": len(self.detect_redundancies()),
            "enabled": self.enabled,
        }

    def status(self) -> str:
        """Status string para /status."""
        pending = len([p for p in self.proposals if p.status == "pending"])
        return (f"Módulos: {len(self.profiles)} | "
                f"Propuestas: {self.total_proposals} (pendientes: {pending}) | "
                f"Aceptadas: {self.accepted_proposals}")

    def generate_report(self) -> str:
        """Reporte completo de arquitectura."""
        lines = ["=== ARCHITECTURE EVOLVER REPORT ==="]
        lines.append(f"Módulos perfilados: {len(self.profiles)}")
        lines.append(f"Total propuestas: {self.total_proposals}")
        lines.append(f"Aceptadas: {self.accepted_proposals}")

        # Health por módulo
        if self.profiles:
            lines.append(f"\nSalud de módulos:")
            sorted_profiles = sorted(
                self.profiles.values(),
                key=lambda p: p.health_score(), reverse=True
            )
            for p in sorted_profiles[:15]:
                health = p.health_score()
                indicator = "OK" if health >= 0.7 else "WARN" if health >= 0.4 else "CRIT"
                lines.append(f"  [{indicator}] {p.name}: health={health:.2f} "
                             f"lines={p.line_count} imports={p.import_count} "
                             f"usage={p.usage_count} deps={len(p.dependencies)}")

        # Redundancias
        redundancies = self.detect_redundancies()
        if redundancies:
            lines.append(f"\nRedundancias detectadas ({len(redundancies)}):")
            for r in redundancies[:5]:
                lines.append(f"  {r['module_a']} <-> {r['module_b']}: "
                             f"overlap={r['combined_score']:.0%} "
                             f"keywords=[{', '.join(r['shared_keywords'][:3])}]")

        # Propuestas pendientes
        pending = [p for p in self.proposals if p.status == "pending"]
        if pending:
            lines.append(f"\nPropuestas pendientes ({len(pending)}):")
            for p in pending[-5:]:
                lines.append(f"  [{p.type.upper()}] {', '.join(p.target_modules[:2])}: "
                             f"{p.rationale[:80]} (impact={p.impact_score:.2f})")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado completo."""
        data = {
            "total_proposals": self.total_proposals,
            "accepted_proposals": self.accepted_proposals,
            "profiles": {n: p.to_dict() for n, p in self.profiles.items()},
            "proposals": [p.to_dict() for p in self.proposals[-self.max_proposals:]],
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
            self.total_proposals = data.get("total_proposals", 0)
            self.accepted_proposals = data.get("accepted_proposals", 0)
            self.enabled = data.get("enabled", True)
            for name, pd in data.get("profiles", {}).items():
                self.profiles[name] = ModuleProfile.from_dict(pd)
            self.proposals = [
                EvolutionProposal.from_dict(pd)
                for pd in data.get("proposals", [])
            ]
        except Exception:
            pass

    def clear(self):
        """Resetea todo el estado."""
        self.profiles = {}
        self.proposals = []
        self.total_proposals = 0
        self.accepted_proposals = 0
        if self.data_file.exists():
            self.data_file.unlink()

    def _auto_rationale(self, target_modules: list, proposal_type: str) -> str:
        """Genera rationale automático basado en los perfiles."""
        if proposal_type == "merge":
            if len(target_modules) >= 2:
                a = self.profiles.get(target_modules[0])
                b = self.profiles.get(target_modules[1])
                if a and b:
                    overlap = a.keyword_overlap(b)
                    return (f"Keyword overlap {overlap:.0%} between "
                            f"{a.name} and {b.name}")
            return "Modules have similar functionality"

        elif proposal_type == "split":
            mod = self.profiles.get(target_modules[0]) if target_modules else None
            if mod:
                return f"Module {mod.name} has {mod.line_count} lines, consider splitting"
            return "Module is too large"

        elif proposal_type == "deprecate":
            mod = self.profiles.get(target_modules[0]) if target_modules else None
            if mod:
                return (f"Module {mod.name} has low usage ({mod.usage_count}) "
                        f"and health ({mod.health_score():.2f})")
            return "Module has low usage"

        return f"Optimize {', '.join(target_modules[:2])}"

    def _estimate_impact_for_modules(self, target_modules: list) -> float:
        """Estima impacto basado en dependencias y uso."""
        total_deps = 0
        total_usage = 0

        for name in target_modules:
            profile = self.profiles.get(name)
            if profile:
                total_deps += len(profile.dependencies)
                total_usage += profile.usage_count + profile.import_count

        total_modules = max(len(self.profiles), 1)
        dep_factor = min(1.0, total_deps / (total_modules * 2))
        usage_factor = min(1.0, total_usage / 30)

        return round(dep_factor * 0.5 + usage_factor * 0.5, 3)
