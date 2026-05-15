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


class TestRateLimit:
    """레이트 리밋 동작 테스트."""

    @pytest.fixture(autouse=True)
    def _reset_rl(self):
        from web.rate_limit import reset
        reset()
        yield
        reset()

    def test_check_rate_allows_within_limit(self):
        from web.rate_limit import check_rate
        for _ in range(5):
            assert check_rate("test_key", limit=5) is True

    def test_check_rate_blocks_over_limit(self):
        from web.rate_limit import check_rate
        for _ in range(3):
            check_rate("test_key", limit=3)
        # 4번째는 차단
        assert check_rate("test_key", limit=3) is False

    def test_check_rate_different_keys_independent(self):
        from web.rate_limit import check_rate
        for _ in range(3):
            check_rate("key_a", limit=3)
        # key_b는 별도 카운터
        assert check_rate("key_b", limit=3) is True

    def test_cleanup_removes_stale_keys(self):
        import time
        from web.rate_limit import _counters, cleanup, _lock

        with _lock:
            _counters["stale_key"] = [time.time() - 400]
        removed = cleanup()
        assert removed >= 1
        with _lock:
            assert "stale_key" not in _counters

    def test_game_start_rate_limited_429(self, client):
        """게임 시작 레이트 리밋 초과 시 429."""
        from web.rate_limit import GAME_START_PER_MINUTE, check_rate

        # X-Forwarded-For 헤더로 IP 고정 → check_rate 와 같은 키 사용 가능
        test_ip = "203.0.113.1"  # TEST-NET-3 (RFC 5737) — 충돌 없음
        for _ in range(GAME_START_PER_MINUTE):
            check_rate(f"start:{test_ip}", limit=GAME_START_PER_MINUTE)

        r = client.post("/api/game/start", headers={"X-Forwarded-For": test_ip})
        assert r.status_code == 429

    def test_command_rate_limited_429(self, client):
        """커맨드 레이트 리밋 초과 시 429."""
        from web.rate_limit import COMMAND_PER_MINUTE, check_rate
        from web.session import store

        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        session = store.get(sid)
        assert session is not None
        session.status = "playing"

        # 한도까지 소비
        for _ in range(COMMAND_PER_MINUTE):
            check_rate(f"cmd:{sid}", limit=COMMAND_PER_MINUTE)

        r2 = client.post(f"/api/game/{sid}/command", data={"cmd": "ls"})
        assert r2.status_code == 429

    def test_health_includes_rate_limit_info(self, client):
        r = client.get("/api/health")
        data = r.json()
        assert "active_games" in data
        assert "max_games" in data
        assert "rate_limit_keys" in data


class TestSSEStream:
    """SSE /stream 엔드포인트 테스트."""

    def test_stream_unknown_session_404(self, client):
        r = client.get("/api/game/nonexistent/stream")
        assert r.status_code == 404

    def test_stream_returns_event_stream_content_type(self, client):
        import asyncio
        import httpx
        from web.session import store

        session = store.create()
        session.status = "ended"  # 즉시 종료 상태로 설정

        async def _read_first_event():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                async with ac.stream("GET", f"/api/game/{session.session_id}/stream") as resp:
                    assert resp.status_code == 200
                    assert "text/event-stream" in resp.headers.get("content-type", "")
                    # 첫 이벤트 라인만 읽고 반환
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            return line

        loop = asyncio.new_event_loop()
        try:
            line = loop.run_until_complete(_read_first_event())
            assert line is not None
            assert "data:" in line
        finally:
            loop.close()

    def test_stream_delivers_pushed_chunks(self, client):
        import asyncio
        import json
        import httpx
        from web.session import store

        session = store.create()
        session.push_output("<pre>SSE TEST</pre>", waiting=False)
        session.status = "ended"

        received = []

        async def _read_events():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                async with ac.stream("GET", f"/api/game/{session.session_id}/stream") as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            received.append(data)
                            if data.get("done"):
                                break

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_read_events())
        finally:
            loop.close()

        html_chunks = [d for d in received if d.get("html")]
        assert any("SSE TEST" in d["html"] for d in html_chunks)

    def test_stream_sends_done_on_session_end(self, client):
        import asyncio
        import json
        import httpx
        from web.session import store

        session = store.create()
        session.status = "ended"

        done_events = []

        async def _read_until_done():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test", timeout=10.0
            ) as ac:
                async with ac.stream("GET", f"/api/game/{session.session_id}/stream") as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            if data.get("done"):
                                done_events.append(data)
                                break

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_read_until_done())
        finally:
            loop.close()

        assert len(done_events) == 1
        assert done_events[0]["status"] == "ended"


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


class TestShop:
    """상점 페이지 + 구매 API."""

    def test_shop_page_returns_200(self, client):
        r = client.get("/shop")
        assert r.status_code == 200

    def test_shop_renders_all_13_perks(self, client):
        """13종 퍼크 카드가 모두 렌더된다."""
        from progression_system import PERK_PRICES
        r = client.get("/shop")
        for perk_id in PERK_PRICES.keys():
            assert f'data-perk="{perk_id}"' in r.text

    def test_shop_shows_balance(self, client, monkeypatch):
        import progression_system as ps
        monkeypatch.setattr(ps, "load_save", lambda: {"data_fragments": 999})
        r = client.get("/shop")
        assert "999" in r.text

    def test_header_nav_has_shop_link(self, client):
        r = client.get("/")
        assert 'href="/shop"' in r.text

    def test_buy_perk_success(self, client, monkeypatch, tmp_path):
        """충분한 잔액으로 구매 성공."""
        import progression_system as ps
        # 메모리 상태로 저장 시뮬레이트
        state = {"data_fragments": 500, "perks": {}}
        monkeypatch.setattr(ps, "load_save", lambda: state)
        monkeypatch.setattr(ps, "save_game", lambda data: None)

        r = client.post("/api/shop/buy_perk", data={"perk_id": "glitch_filter"})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["perk_id"] == "glitch_filter"
        # glitch_filter price = 20, 500 - 20 = 480
        assert body["fragments_after"] == 480
        assert body["perks_owned"] == 1

    def test_buy_perk_insufficient_funds_402(self, client, monkeypatch):
        import progression_system as ps
        state = {"data_fragments": 5, "perks": {}}
        monkeypatch.setattr(ps, "load_save", lambda: state)
        monkeypatch.setattr(ps, "save_game", lambda data: None)

        r = client.post("/api/shop/buy_perk", data={"perk_id": "glitch_filter"})
        assert r.status_code == 402
        body = r.json()
        assert body["ok"] is False
        assert body["reason"] == "insufficient_funds"

    def test_buy_perk_already_owned_409(self, client, monkeypatch):
        import progression_system as ps
        state = {"data_fragments": 500, "perks": {"glitch_filter": True}}
        monkeypatch.setattr(ps, "load_save", lambda: state)
        monkeypatch.setattr(ps, "save_game", lambda data: None)

        r = client.post("/api/shop/buy_perk", data={"perk_id": "glitch_filter"})
        assert r.status_code == 409
        body = r.json()
        assert body["reason"] == "already_owned"

    def test_buy_perk_unknown_404(self, client, monkeypatch):
        import progression_system as ps
        state = {"data_fragments": 500, "perks": {}}
        monkeypatch.setattr(ps, "load_save", lambda: state)
        monkeypatch.setattr(ps, "save_game", lambda data: None)

        r = client.post("/api/shop/buy_perk", data={"perk_id": "nonexistent_perk"})
        assert r.status_code == 404
        body = r.json()
        assert body["reason"] == "unknown_perk"

    def test_purchase_perk_pure_function_unknown(self):
        from progression_system import purchase_perk
        result = purchase_perk({"data_fragments": 100, "perks": {}}, "bogus_id")
        assert result["ok"] is False
        assert result["reason"] == "unknown_perk"

    def test_purchase_perk_pure_function_success(self):
        from progression_system import purchase_perk
        save = {"data_fragments": 100, "perks": {}}
        result = purchase_perk(save, "glitch_filter")
        assert result["ok"] is True
        # glitch_filter price = 20
        assert save["data_fragments"] == 80
        assert save["perks"]["glitch_filter"] is True

    def test_purchase_perk_idempotent_on_failure(self):
        """실패 시 save_data 가 변경되지 않아야 한다."""
        from progression_system import purchase_perk
        save = {"data_fragments": 5, "perks": {}}
        before = dict(save)
        purchase_perk(save, "backtrack_protocol")  # price=80, 부족
        assert save["data_fragments"] == before["data_fragments"]
        assert save["perks"] == {}


class TestProfilePage:
    """다이버 프로필 + 캠페인 진행도 페이지 (GET /profile)."""

    def test_returns_200(self, client):
        r = client.get("/profile")
        assert r.status_code == 200

    def test_renders_diver_title(self, client):
        """다이버 프로필 헤더가 렌더된다."""
        r = client.get("/profile")
        # i18n 키 — 한국어 기본 "다이버 프로필" 또는 영문
        assert "다이버 프로필" in r.text or "DIVER PROFILE" in r.text

    def test_renders_campaign_section(self, client):
        r = client.get("/profile")
        assert "캠페인 진행도" in r.text or "CAMPAIGN PROGRESS" in r.text

    def test_renders_class_grid(self, client):
        """3개 클래스 그리드가 모두 렌더된다."""
        r = client.get("/profile")
        for cls in ("ANALYST", "GHOST", "CRACKER"):
            assert cls in r.text

    def test_renders_fragment_count(self, client, monkeypatch):
        import progression_system as ps
        fake = {"data_fragments": 1234}
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/profile")
        assert "1234" in r.text

    def test_renders_campaign_points(self, client, monkeypatch):
        """캠페인 포인트가 진행 바와 함께 렌더된다."""
        import progression_system as ps
        fake = {
            "campaign": {"points": 12000, "victories": 30, "class_victories": {}},
        }
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/profile")
        # 포인트 표시 (12000 / 60000)
        assert "12000" in r.text
        assert "60000" in r.text  # CAMPAIGN_CLEAR_POINTS

    def test_campaign_cleared_renders_status(self, client, monkeypatch):
        import progression_system as ps
        fake = {
            "campaign": {
                "cleared": True,
                "ascension_unlocked": 10,
                "points": 60000,
                "victories": 500,
                "class_victories": {"ANALYST": 150, "GHOST": 150, "CRACKER": 150},
            }
        }
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/profile")
        # cleared status 라벨 한/영 모두 허용
        assert "CLEARED" in r.text or "클리어 완료" in r.text or "✓" in r.text

    def test_header_nav_has_profile_link(self, client):
        r = client.get("/")
        assert 'href="/profile"' in r.text

    def test_active_page_highlighted(self, client):
        r = client.get("/profile")
        assert 'class="active"' in r.text


class TestEndingsPage:
    """엔딩 갤러리 페이지 (GET /endings)."""

    def test_returns_200(self, client):
        r = client.get("/endings")
        assert r.status_code == 200

    def test_shows_total_count(self, client):
        """13개 엔딩 카드가 모두 렌더된다."""
        r = client.get("/endings")
        # ID 또는 잠금 상태가 13번 등장
        from ending_system import ENDINGS
        # 각 엔딩 ID가 텍스트에 포함됨 (잠금이면 "??? — ID" 형식)
        for eid in ENDINGS.keys():
            assert eid in r.text, f"엔딩 {eid}가 렌더에 없음"

    def test_locked_endings_show_question_marks(self, client, monkeypatch):
        """기본 상태에서 모든 엔딩이 잠금 표시."""
        import progression_system as ps
        monkeypatch.setattr(ps, "load_save", lambda: {})
        r = client.get("/endings")
        # 모든 엔딩 = locked → ??? 마스킹
        assert r.text.count("???") >= 13

    def test_unlocked_ending_shows_title(self, client, monkeypatch):
        """해금된 엔딩은 실제 타이틀로 표시."""
        import progression_system as ps
        fake = {"endings": {"unlocked": ["GHOST_END"]}}
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/endings")
        # GHOST_END 의 title = "PHANTOM BREACH"
        assert "PHANTOM BREACH" in r.text

    def test_header_nav_has_endings_link(self, client):
        r = client.get("/")
        assert 'href="/endings"' in r.text

    def test_shows_completion_summary(self, client, monkeypatch):
        import progression_system as ps
        fake = {"endings": {"unlocked": ["GHOST_END", "ANALYST_END"]}}
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/endings")
        # 2 / 13 (15%) 형식으로 렌더됨
        assert "2" in r.text and "13" in r.text

    def test_hint_keys_present_for_locked(self, client, monkeypatch):
        """잠금된 엔딩은 i18n 힌트가 노출된다."""
        import progression_system as ps
        monkeypatch.setattr(ps, "load_save", lambda: {})
        r = client.get("/endings")
        # 한국어 기본 — TRUE_END 힌트 일부
        assert "정점" in r.text or "Apex" in r.text


class TestAchievementsPage:
    """업적 갤러리 페이지 (GET /achievements)."""

    def test_returns_200(self, client):
        r = client.get("/achievements")
        assert r.status_code == 200

    def test_contains_summary_completion(self, client):
        """전체/해금 카운트가 렌더된다."""
        r = client.get("/achievements")
        # 형식: 0 / 118 (0%) 또는 0/118
        assert "118" in r.text or "115" in r.text  # 현재 총 업적 수 (118)

    def test_contains_category_tabs(self, client):
        """6개 카테고리 + ALL 탭이 모두 렌더된다."""
        r = client.get("/achievements")
        for cat in ("exploration", "class", "collection", "campaign", "mystery", "extreme"):
            assert f'data-cat="{cat}"' in r.text
        assert 'data-cat="all"' in r.text

    def test_locked_achievements_show_masked_title(self, client, monkeypatch):
        """모든 업적이 잠금 상태인 경우 ??? 마스킹 표시."""
        import progression_system as ps
        # 깨끗한 세이브 (해금 없음)
        monkeypatch.setattr(ps, "load_save", lambda: {})
        r = client.get("/achievements")
        assert "???" in r.text

    def test_unlocked_achievement_shows_real_title(self, client, monkeypatch):
        """해금된 업적은 실제 제목으로 표시된다."""
        import progression_system as ps
        fake = {"achievements": {"unlocked": ["first_breach"]}}
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/achievements")
        # first_breach 업적 제목 "첫 번째 돌파" (KO) — 기본 ko
        assert "첫 번째 돌파" in r.text or "First Breach" in r.text

    def test_progress_bar_for_trackable_achievement(self, client, monkeypatch):
        """진행률 추적 가능한 업적은 current/target 표시."""
        import progression_system as ps
        fake = {
            "run_history": [{"result": "victory"}] * 3,
            "achievements": {"unlocked": []},
        }
        monkeypatch.setattr(ps, "load_save", lambda: fake)
        r = client.get("/achievements")
        # runs_10 진행률: 3 / 10
        assert "/ 10" in r.text or "/10" in r.text

    def test_categorize_helper(self):
        """카테고리 분류 헬퍼 — 6개 카테고리 정확히 매핑."""
        from web.app import _categorize_achievement
        assert _categorize_achievement("runs_10") == "exploration"
        assert _categorize_achievement("analyst_victory") == "class"
        assert _categorize_achievement("mystery_master") == "mystery"
        assert _categorize_achievement("artifact_collector") == "collection"
        assert _categorize_achievement("campaign_complete") == "campaign"
        assert _categorize_achievement("asc20_clear") == "extreme"

    def test_header_nav_has_achievements_link(self, client):
        r = client.get("/")
        assert 'href="/achievements"' in r.text

    def test_active_page_highlighted(self, client):
        r = client.get("/achievements")
        # active 클래스가 있어야 함
        assert 'class="active"' in r.text


class TestI18nToggle:
    """언어 토글 엔드포인트 테스트 (POST /api/settings/lang)."""

    def test_default_lang_is_ko(self, client):
        """초기 로비는 한국어로 렌더된다."""
        r = client.get("/")
        assert 'lang="ko"' in r.text

    def test_set_lang_to_en(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post(
            "/api/settings/lang",
            data={"lang": "en"},
            cookies={"echoes_sid": sid},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["ok"] is True
        assert body["lang"] == "en"

    def test_lang_persists_on_lobby(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        client.post("/api/settings/lang", data={"lang": "en"}, cookies={"echoes_sid": sid})
        r2 = client.get("/", cookies={"echoes_sid": sid})
        assert 'lang="en"' in r2.text
        # 영문 라벨이 렌더돼야 함
        assert "SELECT CLASS" in r2.text
        assert "ASCENSION LEVEL" in r2.text

    def test_lang_persists_on_records(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        client.post("/api/settings/lang", data={"lang": "en"}, cookies={"echoes_sid": sid})
        r2 = client.get("/records", cookies={"echoes_sid": sid})
        assert 'lang="en"' in r2.text
        assert "LEADERBOARD" in r2.text

    def test_ko_renders_korean_labels(self, client):
        """기본 한국어 모드에서 한국어 라벨이 렌더된다."""
        r = client.get("/")
        # ko.json의 web.lobby.select_class 값
        assert "클래스 선택" in r.text or "SELECT CLASS" in r.text  # 둘 다 허용 (개발 단계)

    def test_en_overrides_ko_class_desc(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        client.post("/api/settings/lang", data={"lang": "en"}, cookies={"echoes_sid": sid})
        r2 = client.get("/", cookies={"echoes_sid": sid})
        # 영문 클래스 설명
        assert "Keyword hints" in r2.text

    def test_invalid_lang_400(self, client):
        r = client.post("/api/settings/lang", data={"lang": "jp"})
        assert r.status_code == 400

    def test_lang_toggle_buttons_in_header(self, client):
        """헤더에 KO/EN 토글 버튼이 렌더된다."""
        r = client.get("/")
        assert 'data-lang-value="ko"' in r.text
        assert 'data-lang-value="en"' in r.text

    def test_session_lang_default_ko(self):
        """WebGameSession.lang 기본값 검증."""
        from web.adapters import WebGameSession
        s = WebGameSession("lang-test")
        assert s.lang == "ko"

    def test_translate_helper_stateless(self):
        """i18n.translate가 글로벌 상태와 무관하게 작동해야 함."""
        from i18n import translate, get_language
        ko_val = translate("ko", "web.header.lobby")
        en_val = translate("en", "web.header.lobby")
        # 동시에 호출 가능, 다른 결과
        assert ko_val == "로비"
        assert en_val == "LOBBY"
        # 글로벌 set_language는 영향 받지 않음
        original = get_language()
        assert translate("ko", "web.header.records") == "기록"
        # 글로벌 상태 변경 없음 검증
        assert get_language() == original

    def test_translate_falls_back_to_ko_for_missing_key(self):
        from i18n import translate
        result = translate("en", "nonexistent.key.xyz")
        # 없으면 키 자체 반환
        assert result == "nonexistent.key.xyz"


class TestThemeToggle:
    """테마 토글 엔드포인트 테스트 (POST /api/settings/theme)."""

    def test_default_theme_on_lobby(self, client):
        """초기 로비는 default 테마로 렌더된다."""
        r = client.get("/")
        assert 'data-theme="default"' in r.text

    def test_set_valid_theme_ok(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post(
            "/api/settings/theme",
            data={"theme": "colorblind"},
            cookies={"echoes_sid": sid},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["ok"] is True
        assert body["theme"] == "colorblind"

    def test_theme_persists_on_lobby_after_set(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        client.post(
            "/api/settings/theme",
            data={"theme": "high_contrast"},
            cookies={"echoes_sid": sid},
        )
        r2 = client.get("/", cookies={"echoes_sid": sid})
        assert 'data-theme="high_contrast"' in r2.text

    def test_theme_persists_on_records_page(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        client.post(
            "/api/settings/theme",
            data={"theme": "colorblind"},
            cookies={"echoes_sid": sid},
        )
        r2 = client.get("/records", cookies={"echoes_sid": sid})
        assert 'data-theme="colorblind"' in r2.text

    def test_invalid_theme_400(self, client):
        r = client.post(
            "/api/settings/theme",
            data={"theme": "neon_disco"},
        )
        assert r.status_code == 400

    def test_set_theme_creates_session_if_missing(self, client):
        """쿠키 없이 요청 시 새 세션 생성."""
        r = client.post(
            "/api/settings/theme",
            data={"theme": "default"},
        )
        assert r.status_code == 200
        assert "echoes_sid" in r.cookies

    def test_theme_toggle_buttons_in_base_html(self, client):
        """헤더에 3개 테마 토글 버튼이 렌더된다."""
        r = client.get("/")
        for name in ("default", "colorblind", "high_contrast"):
            assert f'data-theme-value="{name}"' in r.text

    def test_web_game_session_has_theme_field(self):
        """WebGameSession.theme 기본값 검증."""
        from web.adapters import WebGameSession
        s = WebGameSession("theme-test")
        assert s.theme == "default"

    def test_css_contains_theme_variants(self):
        """style.css에 세 가지 테마 분기가 모두 정의됨."""
        from pathlib import Path
        css = (Path(__file__).parent.parent / "web" / "static" / "style.css").read_text(encoding="utf-8")
        assert ':root[data-theme="default"]' in css
        assert ':root[data-theme="colorblind"]' in css
        assert ':root[data-theme="high_contrast"]' in css


class TestDailyChallenge:
    """데일리 챌린지 엔드포인트 테스트."""

    def test_daily_start_redirects_to_game(self, client):
        """POST /api/daily/start → 200 + redirect to /game."""
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        r2 = client.post("/api/daily/start", cookies={"echoes_sid": sid})
        assert r2.status_code == 200
        data = r2.json()
        assert data["ok"] is True
        assert data["redirect"] == "/game"

    def test_daily_start_sets_session_to_playing(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        client.post("/api/daily/start", cookies={"echoes_sid": sid})
        session = store.get(sid)
        assert session is not None
        assert session.status == "playing"

    def test_daily_start_already_playing_409(self, client):
        r = client.get("/")
        sid = r.cookies["echoes_sid"]
        session = store.get(sid)
        assert session is not None
        session.status = "playing"
        r2 = client.post("/api/daily/start", cookies={"echoes_sid": sid})
        assert r2.status_code == 409

    def test_daily_start_creates_session_if_missing(self, client):
        """세션 쿠키 없이 요청하면 새 세션을 생성한다."""
        r = client.post("/api/daily/start")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert "echoes_sid" in r.cookies

    def test_lobby_shows_daily_button(self, client):
        """로비 페이지에 데일리 챌린지 버튼이 있다 (한/영)."""
        r = client.get("/")
        assert "데일리 챌린지" in r.text or "DAILY CHALLENGE" in r.text

    def test_lobby_shows_today_date(self, client):
        """로비 페이지에 오늘 날짜가 표시된다."""
        from daily_challenge import get_today_str
        today = get_today_str()
        r = client.get("/")
        assert today in r.text

    def test_lobby_shows_completed_when_played(self, client, monkeypatch):
        """이미 플레이한 경우 완료 상태로 표시된다 (한/영)."""
        import daily_challenge as dc
        monkeypatch.setattr(dc, "has_played_today", lambda *a, **kw: True)
        r = client.get("/")
        assert "완료" in r.text or "COMPLETED" in r.text

    def test_daily_rate_limited_429(self, client):
        """데일리 챌린지도 IP당 레이트 리밋을 공유한다."""
        from web.rate_limit import GAME_START_PER_MINUTE, check_rate
        test_ip = "203.0.113.2"
        for _ in range(GAME_START_PER_MINUTE):
            check_rate(f"start:{test_ip}", limit=GAME_START_PER_MINUTE)
        r = client.post("/api/daily/start", headers={"X-Forwarded-For": test_ip})
        assert r.status_code == 429

    def test_web_game_session_has_start_daily_method(self):
        """WebGameSession에 start_daily_challenge 메서드가 존재한다."""
        from web.adapters import WebGameSession
        s = WebGameSession("test-daily-id")
        assert hasattr(s, "start_daily_challenge")
        assert callable(s.start_daily_challenge)


class TestRecordsPage:
    """GET /records 엔드포인트 테스트."""

    def test_records_returns_200(self, client):
        r = client.get("/records")
        assert r.status_code == 200

    def test_records_contains_leaderboard_section(self, client):
        r = client.get("/records")
        assert "리더보드" in r.text or "LEADERBOARD" in r.text

    def test_records_contains_recent_runs_section(self, client):
        r = client.get("/records")
        assert "최근 런" in r.text or "RECENT RUNS" in r.text

    def test_records_contains_personal_bests_section(self, client):
        r = client.get("/records")
        assert "개인 최고 기록" in r.text or "PERSONAL BESTS" in r.text

    def test_records_shows_empty_state_when_no_data(self, client, monkeypatch):
        """세이브 데이터가 없을 때 빈 상태 메시지를 표시한다."""
        import progression_system as ps

        monkeypatch.setattr(ps, "load_save", lambda: {})
        r = client.get("/records")
        assert r.status_code == 200
        assert "기록 없음" in r.text or "NO ENTRIES" in r.text

    def test_records_shows_nav_links(self, client):
        r = client.get("/records")
        assert 'href="/"' in r.text
        assert 'href="/records"' in r.text

    def test_records_active_page_highlighted(self, client):
        """records 페이지에서 RECORDS 네비 링크가 active 처리된다."""
        r = client.get("/records")
        # active 클래스가 records 링크에 붙어야 함
        assert 'class="active"' in r.text

    def test_records_shows_stat_blocks(self, client):
        """요약 통계 4개 블록이 모두 존재한다 (한국어 또는 영문)."""
        r = client.get("/records")
        ko_en_pairs = [
            ("전체 런 수", "TOTAL RUNS"),
            ("승률", "WIN RATE"),
            ("최고 점수", "BEST SCORE"),
            ("총 획득 조각", "TOTAL FRAGMENTS"),
        ]
        for ko, en in ko_en_pairs:
            assert ko in r.text or en in r.text, f"{ko}/{en} 라벨 없음"

    def test_records_shows_version(self, client):
        """버전 정보가 헤더에 표시된다."""
        from constants import VERSION
        r = client.get("/records")
        assert VERSION in r.text

    def test_records_with_populated_leaderboard(self, client, monkeypatch):
        """리더보드 데이터가 있을 때 점수와 클래스가 렌더된다."""
        import progression_system as ps

        fake_save = {
            "leaderboard": [
                {
                    "rank": 1, "score": 9999, "date": "2026-05-07",
                    "class_key": "GHOST", "ascension": 10,
                    "result": "victory", "trace_final": 42,
                    "reward": 300, "correct_answers": 7,
                }
            ],
            "run_history": [],
            "personal_records": {},
        }
        monkeypatch.setattr(ps, "load_save", lambda: dict(fake_save))
        r = client.get("/records")
        assert "9999" in r.text
        assert "GHOST" in r.text
