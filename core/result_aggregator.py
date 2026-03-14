"""
GENESIS — Result Aggregator (v4.4)

Agregación de resultados: Genesis recoge resultados parciales de múltiples
workers, aplica votación por mayoría para consenso, y combina resultados
finales con fallback local.

Componentes:
- PartialResult: resultado parcial de un worker para una tarea
- VotingMechanism: votación por mayoría con similitud de contenido
- ResultAggregator: coordinador con agregación y persistencia
"""
import time
import json
import hashlib
import re
from pathlib import Path
from collections import defaultdict


class PartialResult:
    """Resultado parcial de un worker."""

    def __init__(self, task_id: str, worker_id: str, data: dict = None,
                 quality: float = 0.5, result_id: str = None):
        self.result_id = result_id or hashlib.md5(
            f"{task_id}:{worker_id}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.task_id = task_id
        self.worker_id = worker_id
        self.data = data or {}
        self.quality = max(0.0, min(1.0, quality))
        self.received_at = time.time()
        self.used_in_aggregation = False

    @property
    def text_content(self) -> str:
        """Extrae contenido textual del resultado para comparación."""
        if "text" in self.data:
            return str(self.data["text"])
        if "result" in self.data:
            return str(self.data["result"])
        if "output" in self.data:
            return str(self.data["output"])
        return json.dumps(self.data, sort_keys=True)

    def to_dict(self) -> dict:
        return {
            "id": self.result_id,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "data": self.data,
            "quality": round(self.quality, 4),
            "received_at": self.received_at,
            "used_in_aggregation": self.used_in_aggregation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PartialResult":
        result = cls(
            task_id=data.get("task_id", ""),
            worker_id=data.get("worker_id", ""),
            data=data.get("data", {}),
            quality=data.get("quality", 0.5),
            result_id=data.get("id"),
        )
        result.received_at = data.get("received_at", time.time())
        result.used_in_aggregation = data.get("used_in_aggregation", False)
        return result


class VotingMechanism:
    """Votación por mayoría con similitud de contenido."""

    SIMILARITY_THRESHOLD = 0.7

    def content_similarity(self, text_a: str, text_b: str) -> float:
        """
        Calcula similitud de contenido entre dos textos.
        Basado en containment de palabras (Jaccard-like).
        """
        words_a = set(self._tokenize(text_a))
        words_b = set(self._tokenize(text_b))
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def majority_vote(self, results: list) -> dict:
        """
        Votación por mayoría: si 2+ resultados son similares
        (similarity > threshold), acepta el grupo más grande.

        Retorna dict con:
        - accepted: bool
        - winning_group: list of PartialResult
        - consensus_score: float
        - best_result: PartialResult (highest quality in winning group)
        """
        if not results:
            return {"accepted": False, "winning_group": [],
                    "consensus_score": 0.0, "best_result": None}

        if len(results) == 1:
            return {
                "accepted": results[0].quality >= 0.5,
                "winning_group": results,
                "consensus_score": results[0].quality,
                "best_result": results[0],
            }

        # Agrupar resultados similares
        groups = self._cluster_results(results)

        if not groups:
            return {"accepted": False, "winning_group": [],
                    "consensus_score": 0.0, "best_result": None}

        # Encontrar el grupo más grande
        largest_group = max(groups, key=len)
        consensus_score = len(largest_group) / len(results)

        # Aceptar si 2+ workers concuerdan
        accepted = len(largest_group) >= 2 and consensus_score >= 0.5

        # Mejor resultado del grupo ganador (mayor quality)
        best = max(largest_group, key=lambda r: r.quality) if largest_group else None

        return {
            "accepted": accepted,
            "winning_group": largest_group,
            "consensus_score": round(consensus_score, 3),
            "best_result": best,
        }

    def _cluster_results(self, results: list) -> list:
        """Agrupa resultados por similitud de contenido."""
        if not results:
            return []

        groups = []
        assigned = set()

        for i, result_a in enumerate(results):
            if i in assigned:
                continue
            group = [result_a]
            assigned.add(i)

            for j, result_b in enumerate(results):
                if j in assigned:
                    continue
                sim = self.content_similarity(
                    result_a.text_content,
                    result_b.text_content,
                )
                if sim >= self.SIMILARITY_THRESHOLD:
                    group.append(result_b)
                    assigned.add(j)

            groups.append(group)

        return groups

    def _tokenize(self, text: str) -> list:
        """Tokeniza texto en palabras significativas."""
        return [
            w for w in re.findall(r'\b\w+\b', text.lower())
            if len(w) > 2
        ]


class ResultAggregator:
    """
    Coordinador de agregación de resultados.
    Recoge resultados parciales, aplica votación, y produce
    resultados finales con fallback local.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/result_aggregator")
        self.data_file = self.base_dir / "result_aggregator_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.partial_results = {}   # result_id -> PartialResult
        self.task_results = defaultdict(list)  # task_id -> [result_ids]
        self.final_results = {}     # task_id -> dict
        self.voting = VotingMechanism()
        self.max_results = 1000
        self.total_aggregated = 0
        self.consensus_count = 0
        self.fallback_count = 0
        self.enabled = True

        self._load()

    @property
    def consensus_rate(self) -> float:
        """Tasa de consenso logrado."""
        if self.total_aggregated == 0:
            return 0.0
        return self.consensus_count / self.total_aggregated

    def submit_result(self, task_id: str, worker_id: str,
                      data: dict = None, quality: float = 0.5) -> str:
        """Envía un resultado parcial."""
        if not self.enabled:
            return ""

        result = PartialResult(
            task_id=task_id,
            worker_id=worker_id,
            data=data or {},
            quality=quality,
        )
        self.partial_results[result.result_id] = result
        self.task_results[task_id].append(result.result_id)

        # Trim si excede máximo
        if len(self.partial_results) > self.max_results:
            self._evict()

        return result.result_id

    def aggregate(self, task_id: str) -> dict:
        """
        Agrega resultados parciales de una tarea por votación.
        Retorna resultado de la votación.
        """
        if not self.enabled:
            return {"status": "disabled"}

        result_ids = self.task_results.get(task_id, [])
        results = [
            self.partial_results[rid]
            for rid in result_ids
            if rid in self.partial_results
        ]

        if not results:
            return {"status": "no_results", "task_id": task_id}

        self.total_aggregated += 1
        vote = self.voting.majority_vote(results)

        if vote["accepted"]:
            self.consensus_count += 1
            # Marcar resultados usados
            for r in vote["winning_group"]:
                r.used_in_aggregation = True

            best = vote["best_result"]
            final = {
                "task_id": task_id,
                "status": "consensus",
                "data": best.data if best else {},
                "quality": best.quality if best else 0.0,
                "consensus_score": vote["consensus_score"],
                "voters": len(vote["winning_group"]),
                "total_results": len(results),
                "aggregated_at": time.time(),
            }
            self.final_results[task_id] = final
            return final

        # No consensus
        return {
            "task_id": task_id,
            "status": "no_consensus",
            "consensus_score": vote["consensus_score"],
            "total_results": len(results),
        }

    def get_final_result(self, task_id: str) -> dict:
        """Obtiene el resultado final agregado de una tarea."""
        return self.final_results.get(task_id, {})

    def fallback_to_local(self, task_id: str,
                          local_result: dict = None) -> dict:
        """
        Fallback: usa resultado local cuando no hay consenso.
        """
        self.fallback_count += 1
        final = {
            "task_id": task_id,
            "status": "fallback_local",
            "data": local_result or {},
            "quality": 0.3,
            "consensus_score": 0.0,
            "voters": 0,
            "total_results": len(self.task_results.get(task_id, [])),
            "aggregated_at": time.time(),
        }
        self.final_results[task_id] = final
        return final

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de agregación para el prompt."""
        if not self.enabled or self.total_aggregated == 0:
            return ""

        # Solo inyectar si hay resultados recientes sin consenso
        recent_no_consensus = [
            tid for tid, final in self.final_results.items()
            if final.get("status") == "no_consensus"
            and time.time() - final.get("aggregated_at", 0) < 3600
        ]

        if not recent_no_consensus:
            return ""

        lines = ["[AGREGACION DE RESULTADOS]"]
        lines.append(
            f"Consenso general: {self.consensus_rate:.0%} "
            f"({self.consensus_count}/{self.total_aggregated})"
        )
        lines.append(
            f"{len(recent_no_consensus)} tareas recientes sin consenso"
        )

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_partial": len(self.partial_results),
            "total_final": len(self.final_results),
            "total_aggregated": self.total_aggregated,
            "consensus_count": self.consensus_count,
            "consensus_rate": round(self.consensus_rate, 3),
            "fallback_count": self.fallback_count,
        }

    def status(self) -> str:
        return (f"Parciales: {len(self.partial_results)} | "
                f"Finales: {len(self.final_results)} | "
                f"Consenso: {self.consensus_rate:.0%}")

    def generate_report(self) -> str:
        lines = ["=== RESULT AGGREGATOR REPORT ==="]
        lines.append(f"Resultados parciales: {len(self.partial_results)}")
        lines.append(f"Resultados finales: {len(self.final_results)}")
        lines.append(f"Total agregaciones: {self.total_aggregated}")
        lines.append(f"Con consenso: {self.consensus_count}")
        lines.append(f"Sin consenso (fallback): {self.fallback_count}")
        if self.total_aggregated > 0:
            lines.append(f"Tasa de consenso: {self.consensus_rate:.1%}")

        # Resultados finales recientes
        if self.final_results:
            recent = sorted(
                self.final_results.items(),
                key=lambda x: x[1].get("aggregated_at", 0),
                reverse=True,
            )[:10]
            lines.append(f"\nResultados recientes:")
            for tid, final in recent:
                lines.append(
                    f"  {tid}: {final.get('status', '?')} "
                    f"(consenso={final.get('consensus_score', 0):.0%}, "
                    f"votantes={final.get('voters', 0)}/"
                    f"{final.get('total_results', 0)})"
                )

        # Por worker
        worker_counts = defaultdict(int)
        for result in self.partial_results.values():
            worker_counts[result.worker_id] += 1
        if worker_counts:
            lines.append(f"\nResultados por worker:")
            for wid, count in sorted(worker_counts.items(),
                                      key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"  {wid}: {count} resultados")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_aggregated": self.total_aggregated,
            "consensus_count": self.consensus_count,
            "fallback_count": self.fallback_count,
            "partial_results": {
                rid: r.to_dict()
                for rid, r in self.partial_results.items()
            },
            "task_results": dict(self.task_results),
            "final_results": self.final_results,
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
            self.total_aggregated = data.get("total_aggregated", 0)
            self.consensus_count = data.get("consensus_count", 0)
            self.fallback_count = data.get("fallback_count", 0)
            for rid, rdata in data.get("partial_results", {}).items():
                self.partial_results[rid] = PartialResult.from_dict(rdata)
            self.task_results = defaultdict(list, data.get("task_results", {}))
            self.final_results = data.get("final_results", {})
        except Exception:
            pass

    def clear(self):
        self.partial_results = {}
        self.task_results = defaultdict(list)
        self.final_results = {}
        self.total_aggregated = 0
        self.consensus_count = 0
        self.fallback_count = 0

    def _evict(self):
        """Elimina resultados parciales más antiguos."""
        if len(self.partial_results) <= self.max_results:
            return
        sorted_results = sorted(
            self.partial_results.items(),
            key=lambda x: x[1].received_at,
        )
        to_remove = len(self.partial_results) - self.max_results
        for rid, _ in sorted_results[:to_remove]:
            del self.partial_results[rid]
            # Clean task_results references
            for tid, rids in self.task_results.items():
                if rid in rids:
                    rids.remove(rid)
