"""
GENESIS — Network Manager (v4.4)

Gestión de red de nodos: Genesis descubre, conecta y comunica
con nodos de una red distribuida, con detección de nodos inactivos
y broadcast de mensajes.

Componentes:
- NetworkNode: nodo de red con dirección, estado y heartbeat
- DiscoveryProtocol: descubrimiento y mantenimiento de nodos activos
- NetworkManager: coordinador con conexiones y persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict, deque


class NetworkNode:
    """Un nodo de la red."""

    VALID_STATUSES = ("discovered", "connected", "disconnected")

    def __init__(self, address: str, port: int = 8000,
                 node_id: str = None, name: str = ""):
        self.node_id = node_id or hashlib.md5(
            f"{address}:{port}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.address = address
        self.port = port
        self.name = name or f"node-{self.node_id[:6]}"
        self.status = "discovered"
        self.last_seen = time.time()
        self.created_at = time.time()
        self.messages_sent = 0
        self.messages_received = 0
        self.ping_latency_ms = 0.0
        self.metadata = {}          # arbitrary node metadata

    @property
    def endpoint(self) -> str:
        """Endpoint completo del nodo."""
        return f"{self.address}:{self.port}"

    @property
    def is_stale(self) -> bool:
        """Nodo inactivo (no visto en 5 minutos)."""
        return (time.time() - self.last_seen) > 300

    @property
    def uptime_seconds(self) -> float:
        """Tiempo desde descubrimiento."""
        return time.time() - self.created_at

    def ping(self, latency_ms: float = 0.0):
        """Simula un ping al nodo."""
        self.last_seen = time.time()
        self.ping_latency_ms = latency_ms
        if self.status == "disconnected":
            self.status = "discovered"

    def connect(self):
        """Marca el nodo como conectado."""
        self.status = "connected"
        self.last_seen = time.time()

    def disconnect(self):
        """Marca el nodo como desconectado."""
        self.status = "disconnected"

    def to_dict(self) -> dict:
        return {
            "id": self.node_id,
            "address": self.address,
            "port": self.port,
            "name": self.name,
            "status": self.status,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "ping_latency_ms": round(self.ping_latency_ms, 2),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NetworkNode":
        node = cls(
            address=data.get("address", "127.0.0.1"),
            port=data.get("port", 8000),
            node_id=data.get("id"),
            name=data.get("name", ""),
        )
        node.status = data.get("status", "discovered")
        node.last_seen = data.get("last_seen", time.time())
        node.created_at = data.get("created_at", time.time())
        node.messages_sent = data.get("messages_sent", 0)
        node.messages_received = data.get("messages_received", 0)
        node.ping_latency_ms = data.get("ping_latency_ms", 0.0)
        node.metadata = data.get("metadata", {})
        return node


class DiscoveryProtocol:
    """Protocolo de descubrimiento y mantenimiento de nodos."""

    STALE_TIMEOUT = 300      # 5 minutos

    def __init__(self):
        self.discovered_log = deque(maxlen=200)  # log de descubrimientos

    def discover(self, address: str, port: int,
                 known_nodes: dict) -> NetworkNode:
        """
        Descubre un nodo. Si ya existe, actualiza last_seen.
        Retorna el nodo (existente o nuevo).
        """
        # Buscar si ya existe por endpoint
        for node in known_nodes.values():
            if node.address == address and node.port == port:
                node.ping()
                self.discovered_log.append({
                    "action": "rediscovered",
                    "node_id": node.node_id,
                    "endpoint": node.endpoint,
                    "timestamp": time.time(),
                })
                return node

        # Nuevo nodo
        node = NetworkNode(address=address, port=port)
        self.discovered_log.append({
            "action": "discovered",
            "node_id": node.node_id,
            "endpoint": node.endpoint,
            "timestamp": time.time(),
        })
        return node

    def ping_all(self, nodes: dict) -> list:
        """
        Simula ping a todos los nodos.
        Retorna lista de nodos que respondieron.
        """
        alive = []
        for node in nodes.values():
            if node.status != "disconnected":
                # Simulate ping with deterministic latency based on node_id
                hash_val = int(hashlib.md5(
                    node.node_id.encode()
                ).hexdigest()[:4], 16)
                latency = 1.0 + (hash_val % 100)
                node.ping(latency)
                alive.append(node)
        return alive

    def cleanup_stale(self, nodes: dict) -> list:
        """
        Elimina nodos inactivos (no vistos en 5 minutos).
        Retorna lista de node_ids eliminados.
        """
        stale_ids = []
        now = time.time()
        for nid, node in list(nodes.items()):
            if (now - node.last_seen) > self.STALE_TIMEOUT:
                stale_ids.append(nid)
                self.discovered_log.append({
                    "action": "stale_removed",
                    "node_id": nid,
                    "endpoint": node.endpoint,
                    "timestamp": now,
                })

        for nid in stale_ids:
            del nodes[nid]

        return stale_ids

    def get_discovery_log(self, limit: int = 20) -> list:
        """Obtiene los últimos eventos de descubrimiento."""
        return list(self.discovered_log)[-limit:]


class NetworkManager:
    """
    Coordinador de la red de nodos.
    Gestiona descubrimiento, conexiones, y mensajes broadcast.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/network_manager")
        self.data_file = self.base_dir / "network_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.nodes = {}             # node_id -> NetworkNode
        self.discovery = DiscoveryProtocol()
        self.message_log = deque(maxlen=500)
        self.max_nodes = 200
        self.total_nodes_seen = 0
        self.total_messages = 0
        self.enabled = True

        self._load()

    @property
    def connected_count(self) -> int:
        """Número de nodos conectados."""
        return sum(1 for n in self.nodes.values() if n.status == "connected")

    def discover_nodes(self, address: str, port: int = 8000) -> str:
        """
        Descubre un nodo en la red.
        Retorna node_id del nodo descubierto.
        """
        if not self.enabled:
            return ""

        node = self.discovery.discover(address, port, self.nodes)
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node
            self.total_nodes_seen += 1

            # Trim si excede máximo
            if len(self.nodes) > self.max_nodes:
                self._evict()

        return node.node_id

    def connect(self, node_id: str) -> bool:
        """Conecta a un nodo descubierto."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        if node.is_stale:
            return False
        node.connect()
        return True

    def disconnect(self, node_id: str) -> bool:
        """Desconecta de un nodo."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        node.disconnect()
        return True

    def broadcast(self, message: str, sender_id: str = "local") -> dict:
        """
        Envía un mensaje a todos los nodos conectados.
        Retorna dict con resultados del broadcast.
        """
        if not self.enabled:
            return {"sent": 0, "failed": 0}

        connected = self.get_connected()
        sent = 0
        failed = 0

        for node in connected:
            if not node.is_stale:
                node.messages_received += 1
                sent += 1
                self.message_log.append({
                    "type": "broadcast",
                    "sender": sender_id,
                    "target": node.node_id,
                    "message": message[:200],
                    "timestamp": time.time(),
                })
            else:
                node.disconnect()
                failed += 1

        self.total_messages += sent

        return {
            "sent": sent,
            "failed": failed,
            "total_connected": len(connected),
        }

    def send_message(self, node_id: str, message: str,
                     sender_id: str = "local") -> bool:
        """Envía un mensaje a un nodo específico."""
        node = self.nodes.get(node_id)
        if not node or node.status != "connected" or node.is_stale:
            return False

        node.messages_received += 1
        self.total_messages += 1
        self.message_log.append({
            "type": "direct",
            "sender": sender_id,
            "target": node_id,
            "message": message[:200],
            "timestamp": time.time(),
        })
        return True

    def get_connected(self) -> list:
        """Obtiene todos los nodos conectados."""
        return [n for n in self.nodes.values() if n.status == "connected"]

    def get_node(self, node_id: str) -> NetworkNode:
        """Obtiene un nodo por ID."""
        return self.nodes.get(node_id)

    def ping_network(self) -> dict:
        """Ping a toda la red y cleanup de nodos inactivos."""
        alive = self.discovery.ping_all(self.nodes)
        stale_removed = self.discovery.cleanup_stale(self.nodes)
        return {
            "alive": len(alive),
            "stale_removed": len(stale_removed),
            "total": len(self.nodes),
        }

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de red para el prompt."""
        if not self.enabled or not self.nodes:
            return ""

        connected = self.connected_count
        total = len(self.nodes)
        if total == 0:
            return ""

        lines = ["[ESTADO DE RED]"]
        lines.append(
            f"Nodos: {connected}/{total} conectados"
        )

        # Nodos inactivos warning
        stale = sum(1 for n in self.nodes.values() if n.is_stale)
        if stale > 0:
            lines.append(f"Nodos inactivos: {stale}")

        # Latencia promedio
        latencies = [
            n.ping_latency_ms for n in self.nodes.values()
            if n.ping_latency_ms > 0
        ]
        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            lines.append(f"Latencia promedio: {avg_lat:.0f}ms")

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_nodes": len(self.nodes),
            "connected_count": self.connected_count,
            "total_nodes_seen": self.total_nodes_seen,
            "total_messages": self.total_messages,
            "stale_nodes": sum(1 for n in self.nodes.values() if n.is_stale),
        }

    def status(self) -> str:
        return (f"Nodos: {self.connected_count}/{len(self.nodes)} | "
                f"Mensajes: {self.total_messages} | "
                f"Total vistos: {self.total_nodes_seen}")

    def generate_report(self) -> str:
        lines = ["=== NETWORK MANAGER REPORT ==="]
        lines.append(f"Nodos totales: {len(self.nodes)}")
        lines.append(f"Conectados: {self.connected_count}")
        lines.append(f"Total nodos vistos: {self.total_nodes_seen}")
        lines.append(f"Total mensajes: {self.total_messages}")

        if self.nodes:
            lines.append(f"\nNodos:")
            for node in sorted(self.nodes.values(),
                                key=lambda n: n.last_seen, reverse=True):
                stale_tag = " [STALE]" if node.is_stale else ""
                lines.append(
                    f"  {node.name} ({node.endpoint}) [{node.status}]{stale_tag} "
                    f"latencia={node.ping_latency_ms:.0f}ms "
                    f"msgs={node.messages_received}"
                )

        # Mensajes recientes
        recent_msgs = list(self.message_log)[-5:]
        if recent_msgs:
            lines.append(f"\nMensajes recientes:")
            for msg in recent_msgs:
                lines.append(
                    f"  [{msg['type']}] {msg['sender']} -> {msg['target']}: "
                    f"{msg['message'][:50]}"
                )

        # Discovery log
        disc_log = self.discovery.get_discovery_log(5)
        if disc_log:
            lines.append(f"\nDescubrimientos recientes:")
            for entry in disc_log:
                lines.append(
                    f"  {entry['action']}: {entry.get('endpoint', '?')}"
                )

        return "\n".join(lines)

    def save(self):
        data = {
            "total_nodes_seen": self.total_nodes_seen,
            "total_messages": self.total_messages,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "message_log": list(self.message_log)[-100:],
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
            self.total_nodes_seen = data.get("total_nodes_seen", 0)
            self.total_messages = data.get("total_messages", 0)
            for nid, ndata in data.get("nodes", {}).items():
                self.nodes[nid] = NetworkNode.from_dict(ndata)
            for msg in data.get("message_log", []):
                self.message_log.append(msg)
        except Exception:
            pass

    def clear(self):
        self.nodes = {}
        self.message_log = deque(maxlen=500)
        self.total_nodes_seen = 0
        self.total_messages = 0

    def _evict(self):
        """Elimina nodos más antiguos y desconectados."""
        if len(self.nodes) <= self.max_nodes:
            return
        # Primero eliminar stale, luego disconnected, luego los más antiguos
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: (
                0 if x[1].is_stale else 1,
                0 if x[1].status == "disconnected" else 1,
                x[1].last_seen,
            ),
        )
        to_remove = len(self.nodes) - self.max_nodes
        for nid, _ in sorted_nodes[:to_remove]:
            del self.nodes[nid]
