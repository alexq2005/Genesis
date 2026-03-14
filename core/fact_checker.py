"""
GENESIS — Fact Checker (v4.3)

Verificación de hechos: Genesis registra claims con fuentes,
calcula concordancia entre fuentes, y señala información no verificable.

Componentes:
- Claim: una afirmación con fuente, confianza y contradicciones
- SourceConcordance: mide concordancia de fuentes sobre un claim
- FactChecker: coordinador con verificación y persistencia
"""
import time
import json
import hashlib
import re
from pathlib import Path
from collections import defaultdict


class Claim:
    """Una afirmación registrada para verificación."""

    def __init__(self, text: str, source: str = "", confidence: float = 0.5,
                 claim_id: str = None, domain: str = "general"):
        self.claim_id = claim_id or hashlib.md5(
            f"{text[:100]}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.text = text.strip()[:500]
        self.source = source.strip()[:200]
        self.confidence = max(0.0, min(1.0, confidence))
        self.domain = domain
        self.verified = False
        self.contradictions = []    # list of contradicting claim texts
        self.supporting_sources = []  # list of {source, agrees, timestamp}
        self.created_at = time.time()
        self.last_checked = time.time()
        self.check_count = 0

    def add_source(self, source: str, agrees: bool):
        """Registra una fuente que apoya o contradice."""
        self.supporting_sources.append({
            "source": source[:200],
            "agrees": agrees,
            "timestamp": time.time(),
        })
        # Mantener máximo 20 fuentes
        if len(self.supporting_sources) > 20:
            self.supporting_sources = self.supporting_sources[-20:]
        self.last_checked = time.time()
        self.check_count += 1
        self._update_confidence()

    def add_contradiction(self, contradiction_text: str):
        """Registra una contradicción."""
        self.contradictions.append(contradiction_text[:300])
        if len(self.contradictions) > 10:
            self.contradictions = self.contradictions[-10:]
        self._update_confidence()

    def _update_confidence(self):
        """Recalcula confianza basada en fuentes y contradicciones."""
        if not self.supporting_sources:
            return
        agreeing = sum(1 for s in self.supporting_sources if s["agrees"])
        total = len(self.supporting_sources)
        source_ratio = agreeing / total
        # Penalty por contradicciones
        contradiction_penalty = min(0.3, len(self.contradictions) * 0.05)
        self.confidence = max(0.0, min(1.0, source_ratio - contradiction_penalty))
        # Auto-verify si hay suficiente concordancia
        if agreeing >= 3 and source_ratio >= 0.7:
            self.verified = True
        elif source_ratio < 0.3 and total >= 3:
            self.verified = False

    @property
    def concordance_score(self) -> float:
        """Score de concordancia (ratio de fuentes que concuerdan)."""
        if not self.supporting_sources:
            return 0.0
        agreeing = sum(1 for s in self.supporting_sources if s["agrees"])
        return agreeing / len(self.supporting_sources)

    def to_dict(self) -> dict:
        return {
            "id": self.claim_id,
            "text": self.text,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "domain": self.domain,
            "verified": self.verified,
            "contradictions": self.contradictions,
            "supporting_sources": self.supporting_sources,
            "created_at": self.created_at,
            "last_checked": self.last_checked,
            "check_count": self.check_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Claim":
        claim = cls(
            text=data.get("text", ""),
            source=data.get("source", ""),
            confidence=data.get("confidence", 0.5),
            claim_id=data.get("id"),
            domain=data.get("domain", "general"),
        )
        claim.verified = data.get("verified", False)
        claim.contradictions = data.get("contradictions", [])
        claim.supporting_sources = data.get("supporting_sources", [])
        claim.created_at = data.get("created_at", time.time())
        claim.last_checked = data.get("last_checked", time.time())
        claim.check_count = data.get("check_count", 0)
        return claim


class SourceConcordance:
    """Calcula concordancia entre fuentes sobre un claim."""

    SIMILARITY_THRESHOLD = 0.7

    def concordance_score(self, claim: Claim) -> float:
        """Calcula score de concordancia para un claim."""
        return claim.concordance_score

    def find_similar_claims(self, text: str, claims: list,
                            threshold: float = 0.5) -> list:
        """Busca claims similares por containment de palabras."""
        text_words = set(self._tokenize(text))
        if not text_words:
            return []

        results = []
        for claim in claims:
            claim_words = set(self._tokenize(claim.text))
            if not claim_words:
                continue
            intersection = text_words & claim_words
            min_size = min(len(text_words), len(claim_words))
            if min_size == 0:
                continue
            similarity = len(intersection) / min_size
            if similarity >= threshold:
                results.append((similarity, claim))

        results.sort(key=lambda x: x[0], reverse=True)
        return [claim for _, claim in results]

    def aggregate_confidence(self, claims: list) -> float:
        """Agrega confianza de múltiples claims similares."""
        if not claims:
            return 0.0
        # Weighted average by number of sources
        total_weight = 0
        total_confidence = 0
        for claim in claims:
            weight = max(1, len(claim.supporting_sources))
            total_confidence += claim.confidence * weight
            total_weight += weight
        return total_confidence / total_weight if total_weight > 0 else 0.0

    def _tokenize(self, text: str) -> list:
        """Tokeniza texto en palabras significativas."""
        return [
            w for w in re.findall(r'\b\w+\b', text.lower())
            if len(w) > 3
        ]


class FactChecker:
    """
    Coordinador de verificación de hechos.
    Registra claims, verifica con múltiples fuentes,
    y señala información no verificable.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/fact_checker")
        self.data_file = self.base_dir / "fact_checker_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.claims = {}            # claim_id -> Claim
        self.concordance = SourceConcordance()
        self.max_claims = 500
        self.total_checked = 0
        self.verified_count = 0
        self.unverifiable_count = 0
        self.enabled = True

        self._load()

    def check_claim(self, text: str, source: str = "",
                    domain: str = "general") -> dict:
        """
        Registra y verifica un claim.
        Busca claims similares existentes para concordancia.
        """
        if not self.enabled or not text:
            return {"status": "disabled"}

        self.total_checked += 1

        # Buscar claims similares existentes
        existing_claims = list(self.claims.values())
        similar = self.concordance.find_similar_claims(text, existing_claims)

        if similar:
            # Claim similar ya existe: reforzar con nueva fuente
            best_match = similar[0]
            if source:
                best_match.add_source(source, agrees=True)
            if best_match.verified:
                self.verified_count += 1
            return {
                "status": "existing",
                "claim_id": best_match.claim_id,
                "confidence": round(best_match.confidence, 3),
                "verified": best_match.verified,
                "concordance": round(best_match.concordance_score, 3),
                "sources": len(best_match.supporting_sources),
            }

        # Nuevo claim
        claim = Claim(
            text=text, source=source,
            confidence=0.5, domain=domain,
        )
        if source:
            claim.add_source(source, agrees=True)

        self.claims[claim.claim_id] = claim

        # Trim si excede máximo
        if len(self.claims) > self.max_claims:
            self._evict()

        return {
            "status": "new",
            "claim_id": claim.claim_id,
            "confidence": round(claim.confidence, 3),
            "verified": claim.verified,
        }

    def register_source(self, claim_id: str, source: str,
                        agrees: bool) -> bool:
        """Registra una fuente que apoya o contradice un claim."""
        claim = self.claims.get(claim_id)
        if not claim:
            return False

        claim.add_source(source, agrees)
        if not agrees:
            claim.add_contradiction(
                f"Fuente '{source}' contradice este claim"
            )

        if claim.verified:
            self.verified_count += 1
        return True

    def get_verified_claims(self, domain: str = None) -> list:
        """Obtiene claims verificados, opcionalmente filtrados por dominio."""
        results = []
        for claim in self.claims.values():
            if not claim.verified:
                continue
            if domain and claim.domain != domain.lower():
                continue
            results.append(claim)
        return sorted(results, key=lambda c: c.confidence, reverse=True)

    def flag_unverifiable(self, claim_id: str, reason: str = "") -> bool:
        """Marca un claim como no verificable."""
        claim = self.claims.get(claim_id)
        if not claim:
            return False
        claim.verified = False
        claim.confidence = 0.1
        claim.add_contradiction(reason or "Marcado como no verificable")
        self.unverifiable_count += 1
        return True

    def get_claim(self, claim_id: str) -> Claim:
        """Obtiene un claim por ID."""
        return self.claims.get(claim_id)

    def get_context_for_prompt(self, user_input: str = "",
                               max_chars: int = 500) -> str:
        """Genera contexto de verificación para el prompt."""
        if not self.enabled or not self.claims:
            return ""

        # Buscar claims relevantes al input
        if user_input:
            relevant = self.concordance.find_similar_claims(
                user_input, list(self.claims.values()), threshold=0.3
            )
        else:
            relevant = []

        if not relevant:
            # No relevant claims, check for low-confidence warnings
            low_conf = [c for c in self.claims.values()
                        if c.confidence < 0.3 and not c.verified]
            if not low_conf:
                return ""
            lines = ["[ADVERTENCIA DE VERIFICACION]"]
            lines.append(
                f"{len(low_conf)} claims con baja confianza detectados."
            )
            return "\n".join(lines)[:max_chars]

        lines = ["[VERIFICACION DE HECHOS]"]
        for claim in relevant[:3]:
            status = "VERIFICADO" if claim.verified else "NO VERIFICADO"
            lines.append(
                f"  [{status}] {claim.text[:80]}... "
                f"(confianza={claim.confidence:.0%}, "
                f"fuentes={len(claim.supporting_sources)})"
            )
            if claim.contradictions:
                lines.append(
                    f"    Contradicciones: {len(claim.contradictions)}"
                )

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        verified = sum(1 for c in self.claims.values() if c.verified)
        return {
            "total_claims": len(self.claims),
            "total_checked": self.total_checked,
            "verified_count": verified,
            "unverifiable_count": self.unverifiable_count,
            "avg_confidence": round(
                sum(c.confidence for c in self.claims.values()) /
                max(len(self.claims), 1), 3
            ),
        }

    def status(self) -> str:
        verified = sum(1 for c in self.claims.values() if c.verified)
        return (f"Claims: {len(self.claims)} | "
                f"Verificados: {verified} | "
                f"Checked: {self.total_checked}")

    def generate_report(self) -> str:
        lines = ["=== FACT CHECKER REPORT ==="]
        lines.append(f"Claims registrados: {len(self.claims)}")
        lines.append(f"Total verificaciones: {self.total_checked}")
        verified = sum(1 for c in self.claims.values() if c.verified)
        lines.append(f"Claims verificados: {verified}")
        lines.append(f"No verificables: {self.unverifiable_count}")

        if self.claims:
            avg_conf = sum(c.confidence for c in self.claims.values()) / len(self.claims)
            lines.append(f"Confianza promedio: {avg_conf:.1%}")

            # Top claims por confianza
            top = sorted(self.claims.values(),
                         key=lambda c: c.confidence, reverse=True)[:10]
            lines.append(f"\nClaims con mayor confianza:")
            for claim in top:
                status = "OK" if claim.verified else "PENDING"
                lines.append(
                    f"  [{status}] {claim.text[:60]}... "
                    f"conf={claim.confidence:.0%} "
                    f"fuentes={len(claim.supporting_sources)}"
                )

            # Distribución por dominio
            domains = defaultdict(int)
            for claim in self.claims.values():
                domains[claim.domain] += 1
            if domains:
                lines.append(f"\nPor dominio:")
                for dom, count in sorted(domains.items(),
                                          key=lambda x: x[1], reverse=True):
                    lines.append(f"  {dom}: {count} claims")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_checked": self.total_checked,
            "verified_count": self.verified_count,
            "unverifiable_count": self.unverifiable_count,
            "claims": {cid: c.to_dict() for cid, c in self.claims.items()},
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
            self.total_checked = data.get("total_checked", 0)
            self.verified_count = data.get("verified_count", 0)
            self.unverifiable_count = data.get("unverifiable_count", 0)
            for cid, cdata in data.get("claims", {}).items():
                self.claims[cid] = Claim.from_dict(cdata)
        except Exception:
            pass

    def clear(self):
        self.claims = {}
        self.total_checked = 0
        self.verified_count = 0
        self.unverifiable_count = 0

    def _evict(self):
        """Elimina claims con menor confianza y menos fuentes."""
        if len(self.claims) <= self.max_claims:
            return
        scored = sorted(
            self.claims.items(),
            key=lambda x: (x[1].confidence * (len(x[1].supporting_sources) + 1))
        )
        to_remove = len(self.claims) - self.max_claims
        for cid, _ in scored[:to_remove]:
            del self.claims[cid]
