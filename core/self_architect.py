"""
GENESIS — Self Architect (v5.0)

Auto-arquitectura: Genesis toma snapshots de su propia arquitectura,
analiza cuellos de botella, propone refactorizaciones, y auto-aprueba
cambios de bajo impacto.

Componentes:
- ArchitectureSnapshot: captura del estado de módulos, dependencias y métricas
- RefactorProposal: propuesta de refactorización con tipo, impacto y auto-aprobación
- SelfArchitect: coordinador con historial de snapshots y persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class ArchitectureSnapshot:
    """Captura del estado arquitectónico en un momento dado."""

    def __init__(self, modules: list = None, dependencies: dict = None,
                 metrics: dict = None, snapshot_id: str = None):
        self.snapshot_id = snapshot_id or hashlib.md5(
            f"snap:{time.time()}".encode()
        ).hexdigest()[:10]
        self.modules = modules or []
        self.dependencies = dependencies or {}   # module -> [dependencies]
        self.metrics = metrics or {
            "total_lines": 0,
            "test_count": 0,
            "module_count": 0,
        }
        self.timestamp = time.time()
        self.notes = ""

    @property
    def module_count(self) -> int:
        return len(self.modules)

    @property
    def dependency_count(self) -> int:
        return sum(len(deps) for deps in self.dependencies.values())

    @property
    def avg_dependencies(self) -> float:
        """Promedio de dependencias por módulo."""
        if not self.modules:
            return 0.0
        return self.dependency_count / len(self.modules)

    def find_bottlenecks(self) -> list:
        """
        Identifica módulos con demasiadas dependencias (cuellos de botella).
        Un módulo es bottleneck si tiene más del doble del promedio de deps.
        """
        avg = self.avg_dependencies
        if avg < 1:
            return []
        threshold = avg * 2
        bottlenecks = []
        for module in self.modules:
            dep_count = len(self.dependencies.get(module, []))
            if dep_count > threshold:
                bottlenecks.append({
                    "module": module,
                    "dependencies": dep_count,
                    "threshold": threshold,
                    "severity": min(1.0, dep_count / (threshold * 2)),
                })
        return sorted(bottlenecks, key=lambda b: b["severity"], reverse=True)

    def find_orphans(self) -> list:
        """Módulos sin dependencias entrantes ni salientes."""
        all_deps = set()
        has_deps = set()
        for module, deps in self.dependencies.items():
            if deps:
                has_deps.add(module)
            for d in deps:
                all_deps.add(d)

        orphans = []
        for module in self.modules:
            if module not in has_deps and module not in all_deps:
                orphans.append(module)
        return orphans

    def compare(self, other: "ArchitectureSnapshot") -> dict:
        """Compara con otro snapshot."""
        added = [m for m in self.modules if m not in other.modules]
        removed = [m for m in other.modules if m not in self.modules]
        return {
            "added_modules": added,
            "removed_modules": removed,
            "module_delta": len(self.modules) - len(other.modules),
            "line_delta": (
                self.metrics.get("total_lines", 0) -
                other.metrics.get("total_lines", 0)
            ),
            "dep_delta": self.dependency_count - other.dependency_count,
        }

    def to_dict(self) -> dict:
        return {
            "id": self.snapshot_id,
            "modules": self.modules,
            "dependencies": self.dependencies,
            "metrics": self.metrics,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchitectureSnapshot":
        snap = cls(
            modules=data.get("modules", []),
            dependencies=data.get("dependencies", {}),
            metrics=data.get("metrics", {}),
            snapshot_id=data.get("id"),
        )
        snap.timestamp = data.get("timestamp", time.time())
        snap.notes = data.get("notes", "")
        return snap


class RefactorProposal:
    """Propuesta de refactorización."""

    VALID_TYPES = ("extract", "inline", "rename", "reorganize")

    def __init__(self, refactor_type: str, target: str, rationale: str,
                 estimated_impact: float = 0.5, proposal_id: str = None):
        self.proposal_id = proposal_id or hashlib.md5(
            f"{refactor_type}:{target}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.type = refactor_type if refactor_type in self.VALID_TYPES else "reorganize"
        self.target = target[:200]
        self.rationale = rationale[:500]
        self.estimated_impact = max(0.0, min(1.0, estimated_impact))
        self.auto_approved = estimated_impact < 0.3
        self.status = "pending"     # pending, approved, rejected, applied
        self.created_at = time.time()
        self.resolved_at = 0.0
        self.result = ""

    def approve(self, reason: str = ""):
        """Aprueba la propuesta."""
        self.status = "approved"
        self.resolved_at = time.time()
        self.result = reason[:200] if reason else "Aprobado"

    def reject(self, reason: str = ""):
        """Rechaza la propuesta."""
        self.status = "rejected"
        self.resolved_at = time.time()
        self.result = reason[:200] if reason else "Rechazado"

    def apply(self, result: str = ""):
        """Marca como aplicada."""
        self.status = "applied"
        self.resolved_at = time.time()
        self.result = result[:200] if result else "Aplicado exitosamente"

    def to_dict(self) -> dict:
        return {
            "id": self.proposal_id,
            "type": self.type,
            "target": self.target,
            "rationale": self.rationale,
            "estimated_impact": round(self.estimated_impact, 4),
            "auto_approved": self.auto_approved,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RefactorProposal":
        prop = cls(
            refactor_type=data.get("type", "reorganize"),
            target=data.get("target", ""),
            rationale=data.get("rationale", ""),
            estimated_impact=data.get("estimated_impact", 0.5),
            proposal_id=data.get("id"),
        )
        prop.auto_approved = data.get("auto_approved", False)
        prop.status = data.get("status", "pending")
        prop.created_at = data.get("created_at", time.time())
        prop.resolved_at = data.get("resolved_at", 0.0)
        prop.result = data.get("result", "")
        return prop


class SelfArchitect:
    """
    Coordinador de auto-arquitectura.
    Toma snapshots, analiza la estructura, propone refactorizaciones,
    y auto-aprueba cambios de bajo impacto.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/self_architect")
        self.data_file = self.base_dir / "self_architect_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.snapshots = []         # list of ArchitectureSnapshot
        self.proposals = {}         # proposal_id -> RefactorProposal
        self.max_snapshots = 50
        self.max_proposals = 200
        self.total_snapshots = 0
        self.total_refactors = 0
        self.applied_count = 0
        self.enabled = True

        self._load()

    def take_snapshot(self, modules: list = None, dependencies: dict = None,
                      metrics: dict = None, notes: str = "") -> ArchitectureSnapshot:
        """Toma un snapshot de la arquitectura actual."""
        if not self.enabled:
            return None

        snap = ArchitectureSnapshot(
            modules=modules or [],
            dependencies=dependencies or {},
            metrics=metrics or {},
        )
        snap.notes = notes

        self.snapshots.append(snap)
        self.total_snapshots += 1

        # Trim snapshots
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        return snap

    def analyze_bottlenecks(self) -> list:
        """Analiza cuellos de botella en el snapshot más reciente."""
        if not self.snapshots:
            return []
        latest = self.snapshots[-1]
        return latest.find_bottlenecks()

    def propose_refactor(self, refactor_type: str, target: str,
                         rationale: str,
                         estimated_impact: float = 0.5) -> RefactorProposal:
        """Crea una propuesta de refactorización."""
        if not self.enabled:
            return None

        proposal = RefactorProposal(
            refactor_type=refactor_type,
            target=target,
            rationale=rationale,
            estimated_impact=estimated_impact,
        )

        # Auto-aprobar si el impacto es bajo
        if proposal.auto_approved:
            proposal.approve("Auto-aprobado: impacto estimado < 0.3")

        self.proposals[proposal.proposal_id] = proposal
        self.total_refactors += 1

        # Trim propuestas
        if len(self.proposals) > self.max_proposals:
            self._evict_proposals()

        return proposal

    def auto_approve(self, proposal_id: str) -> bool:
        """Intenta auto-aprobar una propuesta."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False
        if proposal.estimated_impact < 0.3:
            proposal.approve("Auto-aprobado por bajo impacto")
            return True
        return False

    def apply_proposal(self, proposal_id: str, result: str = "") -> bool:
        """Marca una propuesta como aplicada."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False
        if proposal.status not in ("approved", "pending"):
            return False
        proposal.apply(result)
        self.applied_count += 1
        return True

    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Rechaza una propuesta."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False
        proposal.reject(reason)
        return True

    def get_history(self, limit: int = 10) -> list:
        """Obtiene historial de snapshots."""
        result = []
        for snap in self.snapshots[-limit:]:
            entry = {
                "snapshot_id": snap.snapshot_id,
                "modules": snap.module_count,
                "dependencies": snap.dependency_count,
                "metrics": snap.metrics,
                "timestamp": snap.timestamp,
            }
            result.append(entry)
        return result

    def get_pending_proposals(self) -> list:
        """Obtiene propuestas pendientes."""
        return [
            p for p in self.proposals.values()
            if p.status == "pending"
        ]

    def get_evolution(self) -> dict:
        """Muestra evolución entre el primer y último snapshot."""
        if len(self.snapshots) < 2:
            return {"snapshots": len(self.snapshots)}
        first = self.snapshots[0]
        last = self.snapshots[-1]
        return {
            "snapshots": len(self.snapshots),
            "comparison": last.compare(first),
            "first_timestamp": first.timestamp,
            "last_timestamp": last.timestamp,
            "span_hours": round(
                (last.timestamp - first.timestamp) / 3600, 1
            ),
        }

    def get_context_for_prompt(self, max_chars: int = 500) -> str:
        """Genera contexto arquitectónico para el prompt."""
        if not self.enabled or not self.snapshots:
            return ""

        latest = self.snapshots[-1]
        bottlenecks = latest.find_bottlenecks()
        pending = self.get_pending_proposals()

        if not bottlenecks and not pending:
            return ""

        lines = ["[ARQUITECTURA]"]

        if bottlenecks:
            lines.append(
                f"Cuellos de botella detectados ({len(bottlenecks)}):"
            )
            for bn in bottlenecks[:3]:
                lines.append(
                    f"  - {bn['module']}: {bn['dependencies']} dependencias "
                    f"(severidad={bn['severity']:.0%})"
                )

        if pending:
            lines.append(
                f"Refactorizaciones pendientes: {len(pending)}"
            )
            for p in pending[:2]:
                lines.append(
                    f"  - [{p.type}] {p.target[:40]}: {p.rationale[:40]}..."
                )

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        pending = sum(1 for p in self.proposals.values() if p.status == "pending")
        approved = sum(1 for p in self.proposals.values() if p.status == "approved")
        return {
            "total_snapshots": self.total_snapshots,
            "total_refactors": self.total_refactors,
            "applied_count": self.applied_count,
            "pending_proposals": pending,
            "approved_proposals": approved,
            "current_modules": (
                self.snapshots[-1].module_count if self.snapshots else 0
            ),
        }

    def status(self) -> str:
        pending = sum(1 for p in self.proposals.values() if p.status == "pending")
        return (f"Snapshots: {self.total_snapshots} | "
                f"Refactors: {self.total_refactors} | "
                f"Aplicados: {self.applied_count} | "
                f"Pendientes: {pending}")

    def generate_report(self) -> str:
        lines = ["=== SELF ARCHITECT REPORT ==="]
        lines.append(f"Total snapshots: {self.total_snapshots}")
        lines.append(f"Total propuestas: {self.total_refactors}")
        lines.append(f"Aplicados: {self.applied_count}")

        # Estado actual
        if self.snapshots:
            latest = self.snapshots[-1]
            lines.append(f"\nSnapshot actual:")
            lines.append(f"  Módulos: {latest.module_count}")
            lines.append(f"  Dependencias totales: {latest.dependency_count}")
            lines.append(f"  Avg deps/módulo: {latest.avg_dependencies:.1f}")
            lines.append(f"  Métricas: {latest.metrics}")

            # Bottlenecks
            bottlenecks = latest.find_bottlenecks()
            if bottlenecks:
                lines.append(f"\n  Cuellos de botella:")
                for bn in bottlenecks:
                    lines.append(
                        f"    {bn['module']}: {bn['dependencies']} deps "
                        f"(severidad={bn['severity']:.0%})"
                    )

            # Orphans
            orphans = latest.find_orphans()
            if orphans:
                lines.append(f"\n  Módulos huérfanos: {', '.join(orphans[:10])}")

        # Propuestas
        if self.proposals:
            status_counts = defaultdict(int)
            for p in self.proposals.values():
                status_counts[p.status] += 1
            lines.append(f"\nPropuestas por estado:")
            for status, count in sorted(status_counts.items()):
                lines.append(f"  {status}: {count}")

            pending = [p for p in self.proposals.values() if p.status == "pending"]
            if pending:
                lines.append(f"\nPropuestas pendientes:")
                for p in pending[:5]:
                    lines.append(
                        f"  [{p.type}] {p.target[:40]} "
                        f"(impacto={p.estimated_impact:.0%}) "
                        f"{'AUTO' if p.auto_approved else ''}"
                    )

        # Evolución
        evolution = self.get_evolution()
        if "comparison" in evolution:
            comp = evolution["comparison"]
            lines.append(f"\nEvolución ({evolution['span_hours']:.0f}h):")
            lines.append(f"  Módulos: {comp['module_delta']:+d}")
            lines.append(f"  Líneas: {comp['line_delta']:+d}")
            lines.append(f"  Dependencias: {comp['dep_delta']:+d}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_snapshots": self.total_snapshots,
            "total_refactors": self.total_refactors,
            "applied_count": self.applied_count,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "proposals": {
                pid: p.to_dict() for pid, p in self.proposals.items()
            },
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_snapshots = data.get("total_snapshots", 0)
            self.total_refactors = data.get("total_refactors", 0)
            self.applied_count = data.get("applied_count", 0)
            self.snapshots = [
                ArchitectureSnapshot.from_dict(sd)
                for sd in data.get("snapshots", [])
            ]
            for pid, pdata in data.get("proposals", {}).items():
                self.proposals[pid] = RefactorProposal.from_dict(pdata)
        except Exception:
            pass

    def clear(self):
        self.snapshots = []
        self.proposals = {}
        self.total_snapshots = 0
        self.total_refactors = 0
        self.applied_count = 0

    def _evict_proposals(self):
        """Elimina propuestas resueltas más antiguas."""
        if len(self.proposals) <= self.max_proposals:
            return
        sorted_props = sorted(
            self.proposals.items(),
            key=lambda x: (
                0 if x[1].status in ("applied", "rejected") else 1,
                x[1].created_at,
            ),
        )
        to_remove = len(self.proposals) - self.max_proposals
        for pid, _ in sorted_props[:to_remove]:
            del self.proposals[pid]
