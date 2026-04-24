"""tests/test_web_session.py — FastAPI 웹 세션 E2E 테스트.

httpx AsyncClient 로 FastAPI TestClient 를 사용한다.
실제 게임 스레드는 시작하지 않고 세션/라우트 동작만 검증한다.
"""

from __future__ import annotations

import pytest

# ── web 패키지 임포트 (게임 모듈보다 먼저) ────────────────────────────────────
from web.app import app  # noqa: E402 — 패치 설치 포함
from web.session import store

# ── httpx 동기 TestClient ─────────────────────────────────────────────────────
try:
    from httpx import ASGITransport, AsyncClient
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

pytestmark = pytest.mark.skipif(not _HAS_HTTPX, reason="httpx not installed")


@pytest.fixture(autouse=True)
def _clear_sessions():
    """각 테스트 전 세션 저장소 초기화."""
    store._sessions.clear()
    yield
    store._sessions.clear()


@pytest.fixture
def client():
    """httpx AsyncClient fixture (sync wrapper via pytest-asyncio 불필요)."""
    import asyncio
    from httpx import ASGITransport, Client

    # 동기 테스트를 위해 AsyncClient 대신 동기 사용 불가 → asyncio.run 래핑 패턴
    # 여기서는 httpx 의 동기 테스트 클라이언트를 흉내낸다.
    transport = ASGITransport(app=app)

    class _SyncWrapper:
        def __init__(self):
            self._ac = AsyncClient(transport=transport, base_url="http://test")
            self._loop = asyncio.new_event_loop()

        def get(self, url, **kw):
            return self._loop.run_until_complete(self._ac.get(url, **kw))

        def post(self, url, **kw):
            return self._loop.run_until_complete(self._ac.post(url, **kw))

        def close(self):
            self._loop.run_until_complete(self._ac.aclose())
            self._loop.close()

    c = _SyncWrapper()
    yield c
    c.close()


# ── 기본 라우트 ────────────────────────────────────────────────────────────────

class TestLobbyPage:
    def test_lobby_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_lobby_sets_session_cookie(self, client):
        r = client.get("/")
        assert "echoes_sid" in r.cookies

    def test_lobby_contains_logo(self, client):
        r = client.get("/")
        assert "TERMINAL" in r.text

    def test_lobby_shows_class_options(self, client):
        r = client.get("/")
        for cls in ("ANALYST", "GHOST", "CRACKER"):
            assert cls in r.text

    def test_lobby_reuses_existing_cookie(self, client):
        r1 = client.get("/")
        sid1 = r1.cookies["echoes_sid"]

        r2 = client.get("/", cookies={"echoes_sid": sid1})
        # 세션이 이미 존재하면 새 쿠키를 발급하지 않거나 동일 sid 반환
        assert r2.status_code == 200


class TestLobbySelect:
    def test_select_class_ok(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]

        r2 = client.post(
            "/api/lobby/select",
            data={"diver_class": "GHOST", "ascension": "5"},
            cookies={"echoes_sid": sid},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["ok"] is True
        assert body["class"] == "GHOST"
        assert body["ascension"] == 5

        session = store.get(sid)
        assert session is not None
        assert session.selected_class_name == "GHOST"
        assert session.ascension_level == 5

    def test_select_invalid_class_400(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post(
            "/api/lobby/select",
            data={"diver_class": "HACKER", "ascension": "0"},
            cookies={"echoes_sid": sid},
        )
        assert r2.status_code == 400

    def test_select_invalid_ascension_400(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post(
            "/api/lobby/select",
            data={"diver_class": "ANALYST", "ascension": "99"},
            cookies={"echoes_sid": sid},
        )
        assert r2.status_code == 400

    def test_select_no_session_400(self, client):
        r = client.post(
            "/api/lobby/select",
            data={"diver_class": "ANALYST", "ascension": "0"},
        )
        assert r.status_code == 400


class TestGamePage:
    def test_game_page_without_session_redirects(self, client):
        r = client.get("/game")
        # 세션 없으면 리다이렉트 HTML 반환
        assert r.status_code == 200
        assert "refresh" in r.text.lower()

    def test_game_page_with_session_ok(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.get("/game", cookies={"echoes_sid": sid})
        assert r2.status_code == 200
        assert "term-screen" in r2.text


class TestPollEndpoint:
    def test_poll_unknown_session_404(self, client):
        r = client.get("/api/game/nonexistent/poll")
        assert r.status_code == 404

    def test_poll_new_session_empty_chunks(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        session = store.get(sid)
        assert session is not None

        r2 = client.get(f"/api/game/{sid}/poll")
        assert r2.status_code == 200
        data = r2.json()
        assert "chunks" in data
        assert isinstance(data["chunks"], list)
        assert data["status"] == "lobby"

    def test_poll_returns_pushed_chunks(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        session = store.get(sid)
        assert session is not None

        session.push_output("<pre>TEST OUTPUT</pre>", waiting=True)
        r2 = client.get(f"/api/game/{sid}/poll")
        data = r2.json()
        assert len(data["chunks"]) == 1
        assert "TEST OUTPUT" in data["chunks"][0]["html"]

    def test_poll_clears_chunks_after_read(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        session = store.get(sid)
        assert session is not None

        session.push_output("<pre>ONCE</pre>")
        client.get(f"/api/game/{sid}/poll")  # 첫 번째 폴링 → chunks 소비

        r2 = client.get(f"/api/game/{sid}/poll")
        data = r2.json()
        assert len(data["chunks"]) == 0


class TestCommandEndpoint:
    def test_command_not_playing_409(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post(
            f"/api/game/{sid}/command",
            data={"cmd": "analyze GPS"},
        )
        assert r2.status_code == 409

    def test_command_unknown_session_404(self, client):
        r = client.post(
            "/api/game/badid/command",
            data={"cmd": "ls"},
        )
        assert r.status_code == 404

    def test_command_queued_to_session(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        session = store.get(sid)
        assert session is not None
        session.status = "playing"

        r2 = client.post(
            f"/api/game/{sid}/command",
            data={"cmd": "cat log"},
        )
        assert r2.status_code == 200
        assert r2.json()["ok"] is True

        # 큐에 명령어가 들어갔는지 확인
        cmd = session._input_q.get_nowait()
        assert cmd == "cat log"


class TestQuitEndpoint:
    def test_quit_ok(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post(f"/api/game/{sid}/quit")
        assert r2.status_code == 200
        data = r2.json()
        assert data["ok"] is True

    def test_quit_unknown_session_still_ok(self, client):
        r = client.post("/api/game/badid/quit")
        assert r.status_code == 200


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "sessions" in data


class TestSessionStore:
    def test_create_and_get(self):
        session = store.create()
        assert store.get(session.session_id) is session

    def test_delete(self):
        session = store.create()
        store.delete(session.session_id)
        assert store.get(session.session_id) is None

    def test_cleanup_expired(self):
        import time

        session = store.create()
        session.last_active = time.time() - 9999  # 만료
        removed = store.cleanup_expired()
        assert removed >= 1
        assert store.get(session.session_id) is None

    def test_cleanup_active_not_removed(self):
        session = store.create()
        removed = store.cleanup_expired()
        assert removed == 0
        assert store.get(session.session_id) is session


class TestWebGameSession:
    def test_initial_status_lobby(self):
        from web.adapters import WebGameSession

        s = WebGameSession("test-id")
        assert s.status == "lobby"

    def test_push_and_pop_chunks(self):
        from web.adapters import WebGameSession

        s = WebGameSession("test-id")
        s.push_output("<pre>A</pre>", waiting=True)
        s.push_output("<pre>B</pre>", waiting=False)
        chunks = s.pop_output_chunks()
        assert len(chunks) == 2
        assert chunks[0]["html"] == "<pre>A</pre>"
        assert chunks[0]["waiting"] is True

        # 두 번째 pop 은 비어 있어야 함
        assert s.pop_output_chunks() == []

    def test_flush_console_html_empty(self):
        from web.adapters import WebGameSession

        s = WebGameSession("test-id")
        # 아무것도 출력하지 않으면 None 반환
        result = s.flush_console_html()
        assert result is None

    def test_flush_console_html_with_output(self):
        from web.adapters import WebGameSession

        s = WebGameSession("test-id")
        s.console.print("[bold green]HELLO[/bold green]")
        result = s.flush_console_html()
        assert result is not None
        assert "HELLO" in result

    def test_flush_clears_buffer(self):
        from web.adapters import WebGameSession

        s = WebGameSession("test-id")
        s.console.print("FIRST")
        s.flush_console_html()
        # 두 번째 플러시는 None
        assert s.flush_console_html() is None
