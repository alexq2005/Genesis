"""
GENESIS — Session Manager
Gestiona multiples conversaciones/sesiones independientes.

Cada sesion tiene:
- ID unico y nombre descriptivo
- Historial de conversacion propio
- Metadata (fecha de creacion, ultimo acceso, tema)
- Puede pausarse y reanudarse

Permite trabajar en multiples contextos sin mezclar conversaciones.

Uso:
    sm = SessionManager(base_dir)
    sm.create("proyecto_web", "Desarrollo del frontend")
    sm.switch("proyecto_web")
    messages = sm.get_messages()
    sm.add_message("user", "Hola")
    sm.add_message("assistant", "Hola!")
    sessions = sm.list_sessions()
"""
import json
import time
import os
from pathlib import Path
from typing import Optional, List


class Session:
    """Una sesion de conversacion individual."""

    def __init__(self, session_id: str, name: str = "", topic: str = ""):
        self.session_id = session_id
        self.name = name or session_id
        self.topic = topic
        self.messages = []
        self.created_at = time.time()
        self.last_access = time.time()
        self.metadata = {}

    def add_message(self, role: str, content: str):
        """Agrega un mensaje a la sesion."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        self.last_access = time.time()

    def get_messages(self, limit: int = 0) -> list:
        """Obtiene mensajes de la sesion."""
        if limit > 0:
            return self.messages[-limit:]
        return self.messages

    def clear_messages(self):
        """Limpia mensajes pero mantiene la sesion."""
        self.messages = []

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "topic": self.topic,
            "messages": self.messages,
            "created_at": self.created_at,
            "last_access": self.last_access,
            "message_count": len(self.messages),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        s = cls(
            session_id=data.get("session_id", ""),
            name=data.get("name", ""),
            topic=data.get("topic", ""),
        )
        s.messages = data.get("messages", [])
        s.created_at = data.get("created_at", time.time())
        s.last_access = data.get("last_access", time.time())
        s.metadata = data.get("metadata", {})
        return s


class SessionManager:
    """Gestiona multiples sesiones de conversacion."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "memory_data" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.sessions = {}     # id -> Session
        self.active_id = None  # sesion activa

        # Cargar sesiones existentes
        self._load_sessions()

        # Crear sesion default si no existe ninguna
        if not self.sessions:
            self.create("default", "Sesion principal")

        # Activar la mas reciente
        if not self.active_id:
            most_recent = max(self.sessions.values(), key=lambda s: s.last_access)
            self.active_id = most_recent.session_id

    def create(self, session_id: str, topic: str = "") -> str:
        """
        Crea una nueva sesion.

        Args:
            session_id: identificador unico (sin espacios)
            topic: tema de la sesion

        Returns:
            Mensaje de confirmacion
        """
        # Sanitizar ID
        clean_id = session_id.strip().lower().replace(" ", "_")
        clean_id = "".join(c for c in clean_id if c.isalnum() or c == "_")

        if not clean_id:
            return "ID de sesion invalido."

        if clean_id in self.sessions:
            return f"Sesion '{clean_id}' ya existe. Usa /session switch {clean_id}"

        session = Session(
            session_id=clean_id,
            name=clean_id,
            topic=topic,
        )
        self.sessions[clean_id] = session
        self.active_id = clean_id
        self._save_session(session)

        return f"Sesion '{clean_id}' creada y activada."

    def switch(self, session_id: str) -> str:
        """Cambia a otra sesion."""
        if session_id not in self.sessions:
            # Buscar por match parcial
            matches = [sid for sid in self.sessions if session_id.lower() in sid.lower()]
            if len(matches) == 1:
                session_id = matches[0]
            elif len(matches) > 1:
                return f"Multiples sesiones matchean: {', '.join(matches)}"
            else:
                return f"Sesion '{session_id}' no encontrada."

        # Guardar sesion actual antes de cambiar
        if self.active_id and self.active_id in self.sessions:
            self._save_session(self.sessions[self.active_id])

        self.active_id = session_id
        session = self.sessions[session_id]
        session.last_access = time.time()

        return (f"Sesion activa: {session.name} "
                f"({len(session.messages)} mensajes, tema: {session.topic or 'general'})")

    def delete(self, session_id: str) -> str:
        """Elimina una sesion."""
        if session_id not in self.sessions:
            return f"Sesion '{session_id}' no encontrada."
        if session_id == self.active_id:
            return "No se puede eliminar la sesion activa. Cambia a otra primero."
        if len(self.sessions) <= 1:
            return "No se puede eliminar la unica sesion."

        # Eliminar archivo
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        del self.sessions[session_id]
        return f"Sesion '{session_id}' eliminada."

    def rename(self, session_id: str, new_name: str) -> str:
        """Renombra una sesion."""
        if session_id not in self.sessions:
            return f"Sesion '{session_id}' no encontrada."
        self.sessions[session_id].name = new_name
        self._save_session(self.sessions[session_id])
        return f"Sesion renombrada a '{new_name}'."

    def get_active(self) -> Optional[Session]:
        """Retorna la sesion activa."""
        if self.active_id and self.active_id in self.sessions:
            return self.sessions[self.active_id]
        return None

    def add_message(self, role: str, content: str):
        """Agrega mensaje a la sesion activa."""
        session = self.get_active()
        if session:
            session.add_message(role, content)
            # Auto-save cada 5 mensajes
            if len(session.messages) % 5 == 0:
                self._save_session(session)

    def get_messages(self, limit: int = 0) -> list:
        """Obtiene mensajes de la sesion activa."""
        session = self.get_active()
        if session:
            return session.get_messages(limit)
        return []

    def list_sessions(self) -> str:
        """Lista todas las sesiones."""
        if not self.sessions:
            return "No hay sesiones."

        lines = ["=== Sesiones ==="]
        for sid, session in sorted(self.sessions.items(), key=lambda x: -x[1].last_access):
            active = " [ACTIVA]" if sid == self.active_id else ""
            msgs = len(session.messages)
            topic = session.topic or "general"
            lines.append(f"  {session.name}{active} — {topic} ({msgs} msgs)")

        lines.append(f"\n  Total: {len(self.sessions)} sesiones")
        return "\n".join(lines)

    def save_all(self):
        """Guarda todas las sesiones a disco."""
        for session in self.sessions.values():
            self._save_session(session)

    def status(self) -> str:
        """Estado resumido."""
        total = len(self.sessions)
        active_name = self.sessions.get(self.active_id, Session("?")).name
        total_msgs = sum(len(s.messages) for s in self.sessions.values())
        return (f"Sessions: {total} sesiones | "
                f"Activa: {active_name} | "
                f"Mensajes totales: {total_msgs}")

    # --- Persistencia ---

    def _save_session(self, session: Session):
        """Guarda una sesion a disco."""
        try:
            session_file = self.sessions_dir / f"{session.session_id}.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_sessions(self):
        """Carga todas las sesiones desde disco."""
        try:
            for f in self.sessions_dir.glob("*.json"):
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                session = Session.from_dict(data)
                if session.session_id:
                    self.sessions[session.session_id] = session
        except Exception:
            pass
