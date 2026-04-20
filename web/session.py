"""web/session.py — 세션 저장소 및 생명 주기 관리."""

from __future__ import annotations

import secrets
import time
from typing import Any

from web.adapters import WebGameSession

# 세션 만료 기준 (초)
SESSION_TTL: int = 3600  # 1시간


class SessionStore:
    """인메모리 세션 저장소.

    스레드 안전성: 세션 딕셔너리 자체는 CPython GIL로 보호.
    세션 내부 상태는 WebGameSession 이 자체적으로 Lock 관리.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, WebGameSession] = {}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self) -> WebGameSession:
        session_id = secrets.token_urlsafe(16)
        session = WebGameSession(session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> WebGameSession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    # ── 만료 정리 ──────────────────────────────────────────────────────────────

    def cleanup_expired(self) -> int:
        """TTL 초과 세션 삭제 후 삭제 수 반환."""
        now = time.time()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_active > SESSION_TTL
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    # ── 통계 ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        statuses: dict[str, int] = {}
        for s in self._sessions.values():
            statuses[s.status] = statuses.get(s.status, 0) + 1
        return {"total": len(self._sessions), "by_status": statuses}


# 앱 전역 단일 저장소
store = SessionStore()
