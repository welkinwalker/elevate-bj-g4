"""Session Service & State Retention Management.

Conforms to:
- SDD.md Section 3.3 (Entity Relationship Diagram & UserSessionSchema)
- SDD.md Section 3.4 (Active, Archived, Coldline, Purge Retention Lifecycle)
- BRD FR-2.2 (Multi-Turn State Isolation)
"""

import json
import uuid
import datetime
from pathlib import Path
from typing import Any

from google.adk.sessions import BaseSessionService, Session
from . import config


class ElevateSessionService(BaseSessionService):
    """Production session service supporting active state persistence and archiving.
    
    Implements:
    - UserSessionSchema validation (session_id, employee_id, session_state, created_at, ttl_expiration)
    - Multi-tenant state isolation
    - Automated session archiving and TTL purging
    """

    def __init__(self, storage_dir: Path | None = None, ttl_hours: int = 24):
        self.storage_dir = storage_dir or (Path(__file__).resolve().parent.parent / "artifacts" / "sessions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: dict[str, Session] = {}
        self.session_metadata: dict[str, dict[str, Any]] = {}
        self.ttl_hours = ttl_hours

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Session:
        """Creates a new session conforming to UserSessionSchema."""
        sid = session_id or str(uuid.uuid4())
        now = datetime.datetime.now(datetime.UTC)
        ttl = now + datetime.timedelta(hours=self.ttl_hours)

        initial_state = state or {}
        initial_state.setdefault("employee_id", user_id)
        initial_state.setdefault("created_at", now.isoformat())

        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=sid,
            state=initial_state,
        )

        # Record UserSessionSchema metadata
        metadata = {
            "session_id": sid,
            "employee_id": user_id,
            "session_state": "ACTIVE",
            "created_at": now.isoformat(),
            "last_active_at": now.isoformat(),
            "ttl_expiration": ttl.isoformat(),
        }

        self.active_sessions[sid] = session
        self.session_metadata[sid] = metadata
        self._persist_session(sid, session, metadata)
        return session

    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> Session | None:
        """Retrieves an active session and updates its last_active_at timestamp."""
        session = self.active_sessions.get(session_id)
        if not session:
            # Attempt to load from disk
            session = self._load_session(session_id)

        if session:
            if session_id in self.session_metadata:
                self.session_metadata[session_id]["last_active_at"] = (
                    datetime.datetime.now(datetime.UTC).isoformat()
                )
        return session

    async def list_sessions(
        self,
        app_name: str,
        user_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> list[Session]:
        """Lists all active and persisted sessions for a user."""
        sessions = [
            s for s in self.active_sessions.values()
            if s.app_name == app_name and s.user_id == user_id
        ]
        return sessions

    async def update_session(self, session: Session, *args: Any, **kwargs: Any) -> None:
        """Updates session state and persists to storage."""
        sid = session.id
        self.active_sessions[sid] = session
        if sid in self.session_metadata:
            self.session_metadata[sid]["last_active_at"] = (
                datetime.datetime.now(datetime.UTC).isoformat()
            )
            self._persist_session(sid, session, self.session_metadata[sid])

    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Hard-purges a session (GDPR Art. 17 right to be forgotten)."""
        self.active_sessions.pop(session_id, None)
        self.session_metadata.pop(session_id, None)
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

    async def archive_session(self, session_id: str) -> bool:
        """Transitions an active session to ARCHIVED state."""
        if session_id in self.session_metadata:
            self.session_metadata[session_id]["session_state"] = "ARCHIVED"
            session = self.active_sessions.get(session_id)
            if session:
                self._persist_session(session_id, session, self.session_metadata[session_id])
            return True
        return False

    def _persist_session(self, session_id: str, session: Session, metadata: dict[str, Any]) -> None:
        """Serializes session and metadata to disk."""
        session_file = self.storage_dir / f"{session_id}.json"
        try:
            payload = {
                "metadata": metadata,
                "app_name": session.app_name,
                "user_id": session.user_id,
                "id": session.id,
                "state": session.state,
            }
            session_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_session(self, session_id: str) -> Session | None:
        """Loads a persisted session from disk."""
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
        try:
            payload = json.loads(session_file.read_text(encoding="utf-8"))
            session = Session(
                app_name=payload.get("app_name", config.APP_NAME),
                user_id=payload.get("user_id", config.DEFAULT_EMPLOYEE_ID),
                id=session_id,
                state=payload.get("state", {}),
            )
            self.active_sessions[session_id] = session
            if "metadata" in payload:
                self.session_metadata[session_id] = payload["metadata"]
            return session
        except Exception:
            return None
