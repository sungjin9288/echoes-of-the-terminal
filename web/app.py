"""web/app.py — FastAPI 앱 진입점.

모듈 임포트 순서 (critical):
    1. web.adapters  → ConsoleBridge 정의
    2. ui_renderer   → console 패치 (ConsoleBridge 교체)
    3. install_patches() → builtins.input + PromptBase.ask 패치
    4. 게임 모듈      → 이미 패치된 console 을 임포트하게 됨
    (게임 모듈은 엔드포인트 내부에서 lazy 임포트)
"""

from __future__ import annotations

# ── 1. 패치를 게임 모듈 임포트 이전에 설치 ────────────────────────────────────
import ui_renderer as _ui_mod
from web.adapters import ConsoleBridge, install_patches

_bridge = ConsoleBridge(_ui_mod.console)
_ui_mod.console = _bridge   # run_loops 등이 아직 임포트되지 않았으므로 안전
install_patches()            # builtins.input + PromptBase.ask 패치

# ── 2. 이후 일반 임포트 ───────────────────────────────────────────────────────
import asyncio
import json as _json
import pathlib
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Cookie, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.rate_limit import (
    COMMAND_PER_MINUTE,
    GAME_START_PER_MINUTE,
    MAX_CONCURRENT_GAMES,
    STREAM_PER_MINUTE,
    check_rate,
    cleanup,
)
from web.session import SESSION_TTL, store

# ── 앱 설정 ────────────────────────────────────────────────────────────────────

BASE_DIR = str(pathlib.Path(__file__).parent)  # web/ 디렉터리 (Windows 호환)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """주기적 세션 만료 정리 태스크."""
    async def _cleanup():
        while True:
            await asyncio.sleep(300)  # 5분마다
            removed = store.cleanup_expired()
            rl_removed = cleanup()
            if removed or rl_removed:
                print(f"[session] cleaned up {removed} sessions, {rl_removed} rate-limit keys")

    task = asyncio.create_task(_cleanup())
    yield
    task.cancel()


app = FastAPI(title="Echoes of the Terminal — Web", version="2.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/static"), name="static")
templates = Jinja2Templates(directory=f"{BASE_DIR}/templates")

# ── 세션 쿠키 헬퍼 ────────────────────────────────────────────────────────────

COOKIE_NAME = "echoes_sid"


def _resolve_session(sid: str | None) -> tuple[Any, bool]:
    """세션 조회 또는 생성. (session, is_new) 반환."""
    session = store.get(sid) if sid else None
    if session is None:
        return store.create(), True
    return session, False


def _attach_cookie(resp: Any, session_id: str) -> None:
    """응답 객체에 세션 쿠키를 첨부한다."""
    resp.set_cookie(COOKIE_NAME, session_id, max_age=SESSION_TTL, httponly=True)


# ── 페이지 라우트 ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def lobby_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    session, is_new = _resolve_session(echoes_sid)

    # 세이브 데이터 로드 (lazy)
    from progression_system import _normalize_save_data, load_save

    save_data = load_save()
    _normalize_save_data(save_data)

    run_count = len(save_data.get("run_history", []))
    leaderboard = save_data.get("leaderboard", [])
    top_score = leaderboard[0]["score"] if leaderboard else 0

    resp = templates.TemplateResponse(
        request,
        "lobby.html",
        {
            "session_id": session.session_id,
            "run_count": run_count,
            "top_score": top_score,
            "diver_classes": ["ANALYST", "GHOST", "CRACKER"],
            "selected_class": session.selected_class_name,
            "ascension": session.ascension_level,
        },
    )
    if is_new:
        _attach_cookie(resp, session.session_id)
    return resp


@app.get("/game", response_class=HTMLResponse)
async def game_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    if not echoes_sid:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/">')
    session = store.get(echoes_sid)
    if session is None:
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/">')
    return templates.TemplateResponse(
        request,
        "game.html",
        {"session_id": session.session_id, "status": session.status},
    )


# ── API 라우트 ────────────────────────────────────────────────────────────────

@app.post("/api/lobby/select")
async def lobby_select(
    diver_class: str = Form(...),
    ascension: int = Form(0),
    echoes_sid: str | None = Cookie(default=None),
):
    """로비에서 클래스·어센션 선택을 저장한다."""
    if not echoes_sid:
        raise HTTPException(400, "No session")
    session = store.get(echoes_sid)
    if session is None:
        raise HTTPException(404, "Session not found")

    valid_classes = {"ANALYST", "GHOST", "CRACKER"}
    if diver_class not in valid_classes:
        raise HTTPException(400, f"Invalid class: {diver_class}")
    if not 0 <= ascension <= 20:
        raise HTTPException(400, "Ascension must be 0-20")

    session.selected_class_name = diver_class
    session.ascension_level = ascension
    return {"ok": True, "class": diver_class, "ascension": ascension}


@app.post("/api/game/start")
async def game_start(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """게임 스레드를 시작하고 /game 페이지로 리다이렉트한다."""
    # 동시 실행 게임 수 상한 체크
    active = sum(1 for s in store._sessions.values() if s.status == "playing")
    if active >= MAX_CONCURRENT_GAMES:
        raise HTTPException(503, "서버가 가득 찼습니다. 잠시 후 다시 시도해주세요.")

    # IP당 게임 시작 레이트 리밋
    ip = _client_ip(request)
    if not check_rate(f"start:{ip}", limit=GAME_START_PER_MINUTE):
        raise HTTPException(429, "게임 시작 요청이 너무 많습니다. 1분 후 다시 시도해주세요.")

    session, is_new = _resolve_session(echoes_sid)
    if session.status == "playing":
        return JSONResponse({"ok": False, "reason": "already_playing"}, status_code=409)

    from progression_system import _normalize_save_data, load_save

    save_data = load_save()
    _normalize_save_data(save_data)

    session.start_game(save_data)
    resp = JSONResponse({"ok": True, "redirect": "/game"})
    if is_new:
        _attach_cookie(resp, session.session_id)
    return resp


def _client_ip(request: Request) -> str:
    """클라이언트 IP 추출 (fly.io Fly-Client-IP 헤더 우선)."""
    return (
        request.headers.get("Fly-Client-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )


@app.get("/api/game/{sid}/stream")
async def game_stream(sid: str, request: Request):
    """SSE 스트리밍 — 게임 출력을 실시간으로 브라우저에 push한다.

    각 이벤트 형식: ``data: {"html": "...", "status": "playing"}\n\n``
    게임 종료 시 ``data: {"done": true, "status": "ended"}\n\n`` 를 전송하고 스트림을 닫는다.
    """
    # SSE 연결 레이트 리밋 (IP당 분당 STREAM_PER_MINUTE)
    ip = _client_ip(request)
    if not check_rate(f"stream:{ip}", limit=STREAM_PER_MINUTE):
        raise HTTPException(429, "연결 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.")

    session = store.get(sid)
    if session is None:
        return JSONResponse({"error": "session_not_found"}, status_code=404)

    async def _event_gen():
        drained_ticks = 0
        while True:
            if await request.is_disconnected():
                break

            session.last_active = time.time()
            chunks = session.pop_output_chunks()

            for chunk in chunks:
                yield f"data: {_json.dumps(chunk)}\n\n"

            if chunks:
                drained_ticks = 0
            else:
                drained_ticks += 1

            # 세션 종료 + 큐 비워진 것 확인 후 done 이벤트로 스트림 종료
            if session.status in ("ended", "error") and drained_ticks >= 2:
                yield f"data: {_json.dumps({'html': '', 'status': session.status, 'done': True})}\n\n"
                break

            await asyncio.sleep(0.05)  # 50ms 폴링 — CPU 20 fps

    return StreamingResponse(
        _event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # nginx proxy 버퍼링 비활성화
            "Connection": "keep-alive",
        },
    )


@app.get("/api/game/{sid}/poll")
async def game_poll(sid: str):
    """게임 출력 청크를 반환한다 (하위 호환 폴링 엔드포인트)."""
    session = store.get(sid)
    if session is None:
        return JSONResponse({"error": "session_not_found"}, status_code=404)

    session.last_active = time.time()
    chunks = session.pop_output_chunks()
    return JSONResponse(
        {
            "chunks": chunks,
            "status": session.status,
            "waiting": session.status == "playing",
        }
    )


@app.post("/api/game/{sid}/command")
async def game_command(sid: str, cmd: str = Form("")):
    """브라우저에서 게임 커맨드를 수신해 게임 스레드로 전달한다."""
    session = store.get(sid)
    if session is None:
        raise HTTPException(404, "Session not found")
    if session.status != "playing":
        raise HTTPException(409, "Game not running")

    # 세션당 커맨드 레이트 리밋
    if not check_rate(f"cmd:{sid}", limit=COMMAND_PER_MINUTE):
        raise HTTPException(429, "명령어 입력이 너무 빠릅니다. 잠시 후 다시 시도해주세요.")

    session.send_command(cmd)
    return JSONResponse({"ok": True})


@app.post("/api/game/{sid}/quit")
async def game_quit(sid: str):
    """게임 세션을 종료한다."""
    session = store.get(sid)
    if session:
        session.send_command("quit")
        session.status = "ended"
    return JSONResponse({"ok": True, "redirect": "/"})


@app.get("/api/health")
async def health():
    from web.rate_limit import _counters

    active_games = sum(1 for s in store._sessions.values() if s.status == "playing")
    return {
        "status": "ok",
        "sessions": store.stats(),
        "active_games": active_games,
        "max_games": MAX_CONCURRENT_GAMES,
        "rate_limit_keys": len(_counters),
    }
