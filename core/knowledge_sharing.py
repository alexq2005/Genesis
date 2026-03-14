"""
GENESIS — Knowledge Sharing (v3.4)

Compartir aprendizaje entre sesiones. Permite exportar, importar
y buscar paquetes de conocimiento con deduplicacion automatica
por similitud de contenido.

Componentes:
- KnowledgePacket: paquete de conocimiento con topic, dominio y calidad
- KnowledgeIndex: indice de busqueda por keywords con scoring
- MergeStrategy: dedup por containment similarity (|A inter B|/min(|A|,|B|))
- KnowledgeSharing: coordinador con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class KnowledgePacket:
    """Paquete de conocimiento compartible entre sesiones."""

    def __init__(self, topic: str, content: str, domain: str = "general",
                 quality: float = 0.5, source_session: str = ""):
        self.packet_id = hashlib.md5(
            f"kp_{topic}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.topic = topic.lower().strip()[:200]
        self.content = content[:2000]
        self.domain = domain.lower().strip()
        self.quality = max(0.0, min(1.0, quality))
        self.source_session = source_session
        self.created_at = time.time()
        self.access_count = 0
        self.last_accessed = 0.0

    def get_keywords(self) -> set:
        """Extrae keywords significativas del topic + content."""
        text = f"{self.topic} {self.content}".lower()
        words = re.findall(r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}\b', text)
        stopwords = {
            "para", "como", "este", "esta", "esos", "esas",
            "pero", "sino", "aunque", "porque", "donde", "cuando",
            "todos", "toda", "cada", "otro", "otra", "entre",
            "desde", "hasta", "sobre", "bajo", "durante", "tiene",
            "puede", "hace", "siendo", "sido", "sera", "fueron",
            "that", "this", "with", "from", "have", "been",
            "they", "their", "which", "would", "could", "should",
        }
        return set(w for w in words if w not in stopwords)

    def get_content_words(self) -> set:
        """Extrae todas las palabras significativas del contenido."""
        words = re.findall(r'\b\w{3,}\b', self.content.lower())
        return set(words)

    def touch(self):
        """Marca como accedido."""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.packet_id,
            "topic": self.topic,
            "content": self.content,
            "domain": self.domain,
            "quality": round(self.quality, 3),
            "source_session": self.source_session,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgePacket":
        kp = cls(
            topic=data.get("topic", ""),
            content=data.get("content", ""),
            domain=data.get("domain", "general"),
            quality=data.get("quality", 0.5),
            source_session=data.get("source_session", ""),
        )
        kp.packet_id = data.get("id", kp.packet_id)
        kp.created_at = data.get("created_at", time.time())
        kp.access_count = data.get("access_count", 0)
        kp.last_accessed = data.get("last_accessed", 0.0)
        return kp


class KnowledgeIndex:
    """Indice de busqueda de knowledge packets por keywords."""

    def __init__(self):
        self.topic_index = defaultdict(list)   # topic -> [packet_id, ...]
        self.keyword_index = defaultdict(set)  # keyword -> {packet_id, ...}

    def add(self, packet: KnowledgePacket):
        """Indexa un packet."""
        self.topic_index[packet.topic].append(packet.packet_id)

        for kw in packet.get_keywords():
            self.keyword_index[kw].add(packet.packet_id)

    def remove(self, packet: KnowledgePacket):
        """Elimina un packet del indice."""
        if packet.topic in self.topic_index:
            self.topic_index[packet.topic] = [
                pid for pid in self.topic_index[packet.topic]
                if pid != packet.packet_id
            ]
            if not self.topic_index[packet.topic]:
                del self.topic_index[packet.topic]

        for kw in packet.get_keywords():
            self.keyword_index[kw].discard(packet.packet_id)
            if not self.keyword_index[kw]:
                del self.keyword_index[kw]

    def search(self, query: str, top_k: int = 5) -> list:
        """Busca packets por overlap de keywords. Retorna [(packet_id, score)]."""
        query_words = set(
            w.lower() for w in re.findall(r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}\b', query.lower())
        )

        if not query_words:
            return []

        scores = defaultdict(float)
        for word in query_words:
            for packet_id in self.keyword_index.get(word, set()):
                scores[packet_id] += 1.0

        # Normalizar por cantidad de query words
        for pid in scores:
            scores[pid] /= len(query_words)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def rebuild(self, packets: dict):
        """Reconstruye el indice desde un dict de packets."""
        self.topic_index = defaultdict(list)
        self.keyword_index = defaultdict(set)
        for packet in packets.values():
            self.add(packet)


class MergeStrategy:
    """Deduplicacion por containment similarity: |A inter B| / min(|A|, |B|)."""

    MERGE_THRESHOLD = 0.7

    @staticmethod
    def containment_similarity(packet_a: KnowledgePacket,
                                packet_b: KnowledgePacket) -> float:
        """Calcula containment similarity entre dos packets."""
        words_a = packet_a.get_content_words()
        words_b = packet_b.get_content_words()

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        min_size = min(len(words_a), len(words_b))

        return len(intersection) / min_size if min_size > 0 else 0.0

    @classmethod
    def should_merge(cls, packet_a: KnowledgePacket,
                     packet_b: KnowledgePacket) -> bool:
        """Determina si dos packets deben mergearse (son duplicados)."""
        # Mismo topic = merge seguro si contenido similar
        if packet_a.topic == packet_b.topic:
            sim = cls.containment_similarity(packet_a, packet_b)
            return sim > 0.5  # Umbral mas bajo para mismo topic

        sim = cls.containment_similarity(packet_a, packet_b)
        return sim >= cls.MERGE_THRESHOLD

    @classmethod
    def merge(cls, existing: KnowledgePacket,
              incoming: KnowledgePacket) -> KnowledgePacket:
        """Mergea dos packets, conservando el de mayor calidad y
        extendiendo contenido si el incoming agrega algo nuevo."""
        # Conservar el de mayor calidad como base
        if incoming.quality > existing.quality:
            base = incoming
            extra = existing
        else:
            base = existing
            extra = incoming

        # Agregar contenido unico del extra
        base_words = base.get_content_words()
        extra_words = extra.get_content_words()
        new_words = extra_words - base_words

        if new_words and len(new_words) > 5:
            # Hay contenido nuevo significativo, extender
            extra_sentences = [s.strip() for s in extra.content.split(".")
                               if s.strip()]
            for sentence in extra_sentences:
                sentence_words = set(re.findall(r'\b\w{3,}\b', sentence.lower()))
                if sentence_words & new_words and len(base.content) < 1800:
                    base.content += f" {sentence}."

        # Actualizar quality al maximo
        base.quality = max(base.quality, extra.quality)
        # Sumar access counts
        base.access_count += extra.access_count

        return base


class KnowledgeSharing:
    """Coordinador de knowledge sharing con persistencia."""

    def __init__(self, base_dir: str = "data/knowledge_sharing"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.packets = {}          # packet_id -> KnowledgePacket
        self.index = KnowledgeIndex()
        self.total_shared = 0
        self.total_imported = 0
        self.total_exported = 0
        self.max_packets = 500
        self.enabled = True

        self._load()

    def share(self, topic: str, content: str, domain: str = "general",
              quality: float = 0.5) -> dict:
        """Agrega un paquete de conocimiento."""
        if not self.enabled or not content.strip():
            return {"error": "Sharing deshabilitado o contenido vacio"}

        packet = KnowledgePacket(
            topic=topic,
            content=content,
            domain=domain,
            quality=quality,
            source_session=str(int(time.time())),
        )

        # Verificar duplicados
        for existing in self.packets.values():
            if MergeStrategy.should_merge(existing, packet):
                merged = MergeStrategy.merge(existing, packet)
                # Reindexar el merged
                self.index.remove(existing)
                self.index.add(merged)
                self.packets[merged.packet_id] = merged
                self.total_shared += 1
                return {
                    "status": "merged",
                    "packet_id": merged.packet_id,
                    "topic": merged.topic,
                    "quality": merged.quality,
                }

        # Nuevo packet
        self.packets[packet.packet_id] = packet
        self.index.add(packet)
        self.total_shared += 1

        # Eviccion
        if len(self.packets) > self.max_packets:
            self._evict()

        return {
            "status": "created",
            "packet_id": packet.packet_id,
            "topic": packet.topic,
            "quality": packet.quality,
        }

    def search(self, query: str, top_k: int = 5) -> list:
        """Busca conocimiento por keywords. Retorna lista de packets."""
        if not query.strip():
            return []

        results = self.index.search(query, top_k=top_k)
        found = []

        for packet_id, score in results:
            packet = self.packets.get(packet_id)
            if packet:
                packet.touch()
                found.append({
                    "packet_id": packet.packet_id,
                    "topic": packet.topic,
                    "content": packet.content[:300],
                    "domain": packet.domain,
                    "quality": packet.quality,
                    "relevance": round(score, 3),
                })

        return found

    def export_knowledge(self, topics: list = None) -> dict:
        """Exporta paquetes de conocimiento (todos o filtrados por topics)."""
        packets_to_export = []

        for packet in self.packets.values():
            if topics is None or packet.topic in [t.lower().strip() for t in topics]:
                packets_to_export.append(packet.to_dict())

        self.total_exported += len(packets_to_export)

        return {
            "version": "3.4",
            "exported_at": time.time(),
            "count": len(packets_to_export),
            "packets": packets_to_export,
        }

    def import_knowledge(self, data: dict) -> dict:
        """Importa paquetes con deduplicacion via MergeStrategy."""
        if not isinstance(data, dict) or "packets" not in data:
            return {"error": "Formato de importacion invalido"}

        imported = 0
        merged = 0
        skipped = 0

        for pd in data.get("packets", []):
            try:
                incoming = KnowledgePacket.from_dict(pd)
            except Exception:
                skipped += 1
                continue

            # Buscar duplicados
            found_dup = False
            for existing in list(self.packets.values()):
                if MergeStrategy.should_merge(existing, incoming):
                    result = MergeStrategy.merge(existing, incoming)
                    self.index.remove(existing)
                    self.index.add(result)
                    self.packets[result.packet_id] = result
                    merged += 1
                    found_dup = True
                    break

            if not found_dup:
                self.packets[incoming.packet_id] = incoming
                self.index.add(incoming)
                imported += 1

        self.total_imported += imported + merged

        # Eviccion
        while len(self.packets) > self.max_packets:
            self._evict()

        return {
            "imported": imported,
            "merged": merged,
            "skipped": skipped,
            "total_packets": len(self.packets),
        }

    def get_context_for_prompt(self, user_input: str, max_chars: int = 400) -> str:
        """Si hay conocimiento relevante al input, lo inyecta en el prompt."""
        if not self.enabled or not self.packets:
            return ""

        results = self.search(user_input, top_k=3)

        if not results:
            return ""

        # Solo incluir resultados con relevancia minima
        relevant = [r for r in results if r["relevance"] >= 0.3]
        if not relevant:
            return ""

        parts = ["[CONOCIMIENTO COMPARTIDO RELEVANTE]"]
        total = 0

        for r in relevant:
            entry = f"  [{r['domain']}] {r['topic']}: {r['content'][:150]}"
            if total + len(entry) > max_chars - 50:
                break
            parts.append(entry)
            total += len(entry)

        return "\n".join(parts) if len(parts) > 1 else ""

    def get_stats(self) -> dict:
        domains = defaultdict(int)
        for p in self.packets.values():
            domains[p.domain] += 1

        avg_quality = 0.0
        if self.packets:
            avg_quality = sum(p.quality for p in self.packets.values()) / len(self.packets)

        return {
            "total_shared": self.total_shared,
            "total_imported": self.total_imported,
            "total_exported": self.total_exported,
            "stored_packets": len(self.packets),
            "domains": dict(domains),
            "avg_quality": round(avg_quality, 3),
            "most_accessed": self._most_accessed()[:3],
        }

    def _most_accessed(self) -> list:
        """Retorna los packets mas accedidos."""
        sorted_packets = sorted(
            self.packets.values(),
            key=lambda p: p.access_count,
            reverse=True,
        )
        return [{"topic": p.topic, "accesses": p.access_count}
                for p in sorted_packets[:5] if p.access_count > 0]

    def status(self) -> str:
        domains = len(set(p.domain for p in self.packets.values()))
        return (f"  Packets: {len(self.packets)} ({domains} dominios) | "
                f"Compartidos: {self.total_shared} | "
                f"Importados: {self.total_imported} | "
                f"Exportados: {self.total_exported}")

    def generate_report(self) -> str:
        lines = [
            "=== KNOWLEDGE SHARING ===",
            f"Total compartidos: {self.total_shared}",
            f"Total importados: {self.total_imported}",
            f"Total exportados: {self.total_exported}",
            f"Packets almacenados: {len(self.packets)}",
        ]

        # Por dominio
        domains = defaultdict(list)
        for p in self.packets.values():
            domains[p.domain].append(p)

        if domains:
            lines.append(f"\nPor dominio:")
            for dom, packets in sorted(domains.items()):
                topics = [p.topic for p in packets[:5]]
                avg_q = sum(p.quality for p in packets) / len(packets)
                lines.append(f"  {dom} ({len(packets)}): calidad prom {avg_q:.0%}")
                lines.append(f"    Topics: {', '.join(topics)}")

        # Mas accedidos
        accessed = self._most_accessed()
        if accessed:
            lines.append(f"\nMas accedidos:")
            for item in accessed[:5]:
                lines.append(f"  {item['topic']}: {item['accesses']} accesos")

        # Calidad
        if self.packets:
            qualities = [p.quality for p in self.packets.values()]
            lines.append(f"\nCalidad: min={min(qualities):.0%}, "
                         f"max={max(qualities):.0%}, "
                         f"prom={sum(qualities)/len(qualities):.0%}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_shared": self.total_shared,
            "total_imported": self.total_imported,
            "total_exported": self.total_exported,
            "packets": [p.to_dict() for p in self.packets.values()],
        }
        path = self.base_dir / "knowledge_sharing.json"
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "knowledge_sharing.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_shared = data.get("total_shared", 0)
            self.total_imported = data.get("total_imported", 0)
            self.total_exported = data.get("total_exported", 0)

            for pd in data.get("packets", []):
                packet = KnowledgePacket.from_dict(pd)
                self.packets[packet.packet_id] = packet

            # Reconstruir indice
            self.index.rebuild(self.packets)
        except Exception:
            pass

    def clear(self):
        self.packets = {}
        self.index = KnowledgeIndex()
        self.total_shared = 0
        self.total_imported = 0
        self.total_exported = 0
        self.save()

    def _evict(self):
        """Elimina packets de menor calidad y acceso."""
        if len(self.packets) <= self.max_packets:
            return

        # Score de eviccion: menor quality + menor acceso = primero en irse
        sorted_packets = sorted(
            self.packets.values(),
            key=lambda p: p.quality * 0.6 + min(p.access_count, 10) / 10.0 * 0.4,
        )

        to_remove = len(self.packets) - self.max_packets
        for packet in sorted_packets[:to_remove]:
            self.index.remove(packet)
            del self.packets[packet.packet_id]
