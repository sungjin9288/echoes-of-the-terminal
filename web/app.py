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
import pathlib
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Cookie, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
            if removed:
                print(f"[session] cleaned up {removed} expired sessions")

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
    echoes_sid: str | None = Cookie(default=None),
):
    """게임 스레드를 시작하고 /game 페이지로 리다이렉트한다."""
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


@app.get("/api/game/{sid}/poll")
async def game_poll(sid: str):
    """게임 출력 청크를 반환한다. htmx 폴링 엔드포인트."""
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
    return {"status": "ok", "sessions": store.stats()}
