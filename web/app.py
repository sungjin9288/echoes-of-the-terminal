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
from constants import VERSION as _GAME_VERSION

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


VALID_THEMES = frozenset({"default", "colorblind", "high_contrast"})
VALID_LANGS = frozenset({"ko", "en"})


def _get_theme(sid: str | None) -> str:
    """세션에서 선택된 테마를 반환한다 (없으면 default)."""
    if not sid:
        return "default"
    session = store.get(sid)
    if session is None:
        return "default"
    theme = getattr(session, "theme", "default")
    return theme if theme in VALID_THEMES else "default"


def _get_lang(sid: str | None) -> str:
    """세션에서 선택된 언어를 반환한다 (없으면 ko)."""
    if not sid:
        return "ko"
    session = store.get(sid)
    if session is None:
        return "ko"
    lang = getattr(session, "lang", "ko")
    return lang if lang in VALID_LANGS else "ko"


# Jinja2 환경에 i18n 헬퍼 등록 — 모든 템플릿에서 t('key', lang=...) 호출 가능
from i18n import translate as _translate  # noqa: E402

templates.env.globals["translate"] = _translate


# ── 업적 카테고리 분류 ────────────────────────────────────────────────────────

ACH_CATEGORIES: tuple[str, ...] = (
    "exploration", "class", "collection", "campaign", "mystery", "extreme",
)


def _categorize_achievement(ach_id: str) -> str:
    """업적 ID로부터 6개 카테고리 중 하나로 분류한다.

    분류 우선순위는 명시적으로 가장 구체적인 것부터.
    """
    aid = ach_id.lower()
    # daily / mystery 는 collection 으로 묶음
    if aid.startswith(("mystery_", "argos_lure", "phantom_node", "deepscan_streak")):
        return "mystery"
    if aid.startswith(("artifact_", "perk_", "daily_", "fragments_")) or "endings" in aid:
        return "collection"
    if aid.startswith("campaign_"):
        return "campaign"
    # 극한: ascension 20 / 핸디캡 / nightmare 다회
    if "asc20" in aid or "handicap" in aid or "extreme" in aid or "nightmare_only" in aid:
        return "extreme"
    if aid.startswith(("analyst_", "ghost_", "cracker_", "class_", "all_classes", "trinity")):
        return "class"
    # 기본: exploration (runs, victories, first, perfect, no_perk 등)
    return "exploration"


# ── 페이지 라우트 ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def lobby_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    session, is_new = _resolve_session(echoes_sid)

    # 세이브 데이터 로드 (lazy)
    from daily_challenge import get_daily_state, get_today_str, has_played_today
    from progression_system import _normalize_save_data, load_save

    save_data = load_save()
    _normalize_save_data(save_data)

    run_count = len(save_data.get("run_history", []))
    leaderboard = save_data.get("leaderboard", [])
    top_score = leaderboard[0]["score"] if leaderboard else 0

    today_str = get_today_str()
    daily_played = has_played_today(get_daily_state(save_data), today_str)

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
            "active_page": "lobby",
            "version": _GAME_VERSION,
            "today_str": today_str,
            "daily_played": daily_played,
            "theme": session.theme,
            "lang": session.lang,
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
        {
            "session_id": session.session_id,
            "status": session.status,
            "active_page": "game",
            "version": _GAME_VERSION,
            "theme": session.theme,
            "lang": session.lang,
        },
    )


@app.get("/records", response_class=HTMLResponse)
async def records_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """런 기록 화면 — 리더보드 · 런 히스토리 · 개인 최고 기록."""
    from progression_system import (
        _normalize_save_data,
        get_leaderboard,
        get_personal_records,
        get_run_history,
        load_save,
    )

    save_data = load_save()
    _normalize_save_data(save_data)

    leaderboard = get_leaderboard(save_data)
    run_history = list(reversed(get_run_history(save_data)))[:20]  # 최근 20개, 최신순
    personal_records = get_personal_records(save_data)

    # 요약 통계 계산
    all_runs = get_run_history(save_data)
    total_runs = len(all_runs)
    wins = sum(1 for r in all_runs if r.get("result") == "victory")
    win_rate = round(wins * 100 / total_runs) if total_runs else 0
    best_score = leaderboard[0]["score"] if leaderboard else 0
    total_fragments = sum(r.get("reward", 0) for r in all_runs)

    return templates.TemplateResponse(
        request,
        "records.html",
        {
            "leaderboard": leaderboard,
            "run_history": run_history,
            "personal_records": personal_records,
            "total_runs": total_runs,
            "win_rate": win_rate,
            "best_score": best_score,
            "total_fragments": total_fragments,
            "active_page": "records",
            "version": _GAME_VERSION,
            "theme": _get_theme(echoes_sid),
            "lang": _get_lang(echoes_sid),
        },
    )


@app.get("/shop", response_class=HTMLResponse)
async def shop_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """상점 페이지 — 13종 퍼크 카드, 데이터 조각으로 구매."""
    from progression_system import (
        PERK_DESC_MAP,
        PERK_LABEL_MAP,
        PERK_PRICES,
        _normalize_save_data,
        load_save,
    )

    save_data = load_save()
    _normalize_save_data(save_data)

    perks_owned = save_data.get("perks", {}) if isinstance(save_data.get("perks"), dict) else {}
    fragments = int(save_data.get("data_fragments", 0))

    items: list[dict[str, Any]] = []
    for perk_id, price in PERK_PRICES.items():
        owned = bool(perks_owned.get(perk_id, False))
        items.append({
            "id": perk_id,
            "label": PERK_LABEL_MAP.get(perk_id, perk_id),
            "desc": PERK_DESC_MAP.get(perk_id, ""),
            "price": price,
            "owned": owned,
            "affordable": (not owned) and fragments >= price,
        })

    total = len(items)
    owned_count = sum(1 for it in items if it["owned"])

    return templates.TemplateResponse(
        request,
        "shop.html",
        {
            "perks": items,
            "fragments": fragments,
            "owned_count": owned_count,
            "total": total,
            "completion": round(owned_count * 100 / total) if total else 0,
            "active_page": "shop",
            "version": _GAME_VERSION,
            "theme": _get_theme(echoes_sid),
            "lang": _get_lang(echoes_sid),
        },
    )


@app.post("/api/shop/buy_perk")
async def buy_perk(
    perk_id: str = Form(...),
    echoes_sid: str | None = Cookie(default=None),
):
    """퍼크 1개를 구매한다.

    결과 코드:
      - ok=True            구매 성공
      - unknown_perk       404 — 알 수 없는 퍼크 ID
      - already_owned      409
      - insufficient_funds 402 (Payment Required)
    """
    from progression_system import (
        _normalize_save_data,
        load_save,
        purchase_perk,
        save_game,
    )

    save_data = load_save()
    _normalize_save_data(save_data)

    result = purchase_perk(save_data, perk_id)

    if not result["ok"]:
        reason = result["reason"]
        status_code = {
            "unknown_perk": 404,
            "already_owned": 409,
            "insufficient_funds": 402,
        }.get(reason, 400)
        return JSONResponse(
            {"ok": False, "reason": reason, "fragments_after": result["fragments_after"],
             "perks_owned": result["perks_owned"]},
            status_code=status_code,
        )

    # 영속화
    try:
        save_game(save_data)
    except OSError as exc:
        return JSONResponse(
            {"ok": False, "reason": "save_failed", "error": str(exc)},
            status_code=500,
        )

    return JSONResponse({
        "ok": True,
        "perk_id": perk_id,
        "label": result["label"],
        "fragments_after": result["fragments_after"],
        "perks_owned": result["perks_owned"],
    })


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """다이버 프로필 + 캠페인 진행도 페이지."""
    from progression_system import (
        _normalize_save_data,
        get_campaign_progress_snapshot,
        get_diver_profile,
        load_save,
    )

    save_data = load_save()
    _normalize_save_data(save_data)

    profile = get_diver_profile(save_data)
    campaign_raw = save_data.get("campaign", {})
    campaign = get_campaign_progress_snapshot(campaign_raw if isinstance(campaign_raw, dict) else {})

    # 데이터 조각 잔액
    data_fragments = int(save_data.get("data_fragments", 0))

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "profile": profile,
            "campaign": campaign,
            "data_fragments": data_fragments,
            "campaign_points_pct": round(campaign["points_ratio"] * 100),
            "campaign_victories_pct": round(campaign["victories_ratio"] * 100),
            "class_keys": ("ANALYST", "GHOST", "CRACKER"),
            "active_page": "profile",
            "version": _GAME_VERSION,
            "theme": _get_theme(echoes_sid),
            "lang": _get_lang(echoes_sid),
        },
    )


@app.get("/endings", response_class=HTMLResponse)
async def endings_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """엔딩 갤러리 — 13종 엔딩 카드. 잠금된 엔딩은 힌트만 표시."""
    from ending_system import ENDINGS, get_endings_snapshot
    from progression_system import _normalize_save_data, load_save

    save_data = load_save()
    _normalize_save_data(save_data)

    snapshot = get_endings_snapshot(save_data)
    unlocked: set[str] = set(snapshot["unlocked_ids"])

    # priority 순으로 정렬해서 노출 (낮을수록 우선)
    sorted_endings = sorted(ENDINGS.values(), key=lambda e: e.priority)
    items: list[dict[str, Any]] = []
    for ending in sorted_endings:
        is_unlocked = ending.ending_id in unlocked
        items.append({
            "id": ending.ending_id,
            "title": ending.title,
            "subtitle": ending.subtitle,
            "flavor_text": ending.flavor_text,
            "color": ending.color,
            "priority": ending.priority,
            "unlocked": is_unlocked,
        })

    return templates.TemplateResponse(
        request,
        "endings.html",
        {
            "endings": items,
            "unlocked_count": snapshot["unlocked_count"],
            "total": snapshot["total_count"],
            "completion": round(snapshot["unlocked_count"] * 100 / snapshot["total_count"])
                          if snapshot["total_count"] else 0,
            "active_page": "endings",
            "version": _GAME_VERSION,
            "theme": _get_theme(echoes_sid),
            "lang": _get_lang(echoes_sid),
        },
    )


@app.get("/achievements", response_class=HTMLResponse)
async def achievements_page(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """업적 갤러리 — 115+ 업적을 카테고리별 카드 그리드로 표시."""
    from achievement_data import ACHIEVEMENTS
    from achievement_progress import compute_achievement_progress
    from achievement_system import normalize_achievement_state
    from progression_system import _normalize_save_data, load_save

    save_data = load_save()
    _normalize_save_data(save_data)

    state = normalize_achievement_state(save_data.get("achievements", {}))
    unlocked: set[str] = set(state["unlocked"])

    # 카테고리별로 그룹화
    by_category: dict[str, list[dict[str, Any]]] = {c: [] for c in ACH_CATEGORIES}
    for ach in ACHIEVEMENTS:
        ach_id = str(ach["id"])
        cat = _categorize_achievement(ach_id)
        is_unlocked = ach_id in unlocked
        progress = compute_achievement_progress(ach_id, save_data)

        item: dict[str, Any] = {
            "id": ach_id,
            "title": str(ach.get("title", "")),
            "desc": str(ach.get("desc", "")),
            "unlocked": is_unlocked,
        }
        if progress is not None and progress[1] > 0:
            item["current"] = progress[0]
            item["target"] = progress[1]
            item["ratio"] = round(progress[0] * 100 / progress[1])
        else:
            item["current"] = None
            item["target"] = None
            item["ratio"] = None

        by_category.setdefault(cat, []).append(item)

    total = len(ACHIEVEMENTS)
    unlocked_count = sum(1 for a in ACHIEVEMENTS if str(a["id"]) in unlocked)
    completion = round(unlocked_count * 100 / total) if total else 0

    return templates.TemplateResponse(
        request,
        "achievements.html",
        {
            "by_category": by_category,
            "categories": list(ACH_CATEGORIES),
            "total": total,
            "unlocked_count": unlocked_count,
            "completion": completion,
            "active_page": "achievements",
            "version": _GAME_VERSION,
            "theme": _get_theme(echoes_sid),
            "lang": _get_lang(echoes_sid),
        },
    )


# ── API 라우트 ────────────────────────────────────────────────────────────────

@app.post("/api/settings/theme")
async def set_theme(
    theme: str = Form(...),
    echoes_sid: str | None = Cookie(default=None),
):
    """세션의 테마를 변경한다 (default | colorblind | high_contrast)."""
    if theme not in VALID_THEMES:
        raise HTTPException(400, f"Invalid theme: {theme}")

    session, is_new = _resolve_session(echoes_sid)
    session.theme = theme

    resp = JSONResponse({"ok": True, "theme": theme})
    if is_new:
        _attach_cookie(resp, session.session_id)
    return resp


@app.post("/api/settings/lang")
async def set_lang(
    lang: str = Form(...),
    echoes_sid: str | None = Cookie(default=None),
):
    """세션의 언어를 변경한다 (ko | en)."""
    if lang not in VALID_LANGS:
        raise HTTPException(400, f"Invalid lang: {lang}")

    session, is_new = _resolve_session(echoes_sid)
    session.lang = lang

    resp = JSONResponse({"ok": True, "lang": lang})
    if is_new:
        _attach_cookie(resp, session.session_id)
    return resp


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


@app.post("/api/daily/start")
async def daily_start(
    request: Request,
    echoes_sid: str | None = Cookie(default=None),
):
    """데일리 챌린지 스레드를 시작하고 /game 페이지로 리다이렉트한다."""
    active = sum(1 for s in store._sessions.values() if s.status == "playing")
    if active >= MAX_CONCURRENT_GAMES:
        raise HTTPException(503, "서버가 가득 찼습니다. 잠시 후 다시 시도해주세요.")

    ip = _client_ip(request)
    if not check_rate(f"start:{ip}", limit=GAME_START_PER_MINUTE):
        raise HTTPException(429, "게임 시작 요청이 너무 많습니다. 1분 후 다시 시도해주세요.")

    session, is_new = _resolve_session(echoes_sid)
    if session.status == "playing":
        return JSONResponse({"ok": False, "reason": "already_playing"}, status_code=409)

    from progression_system import _normalize_save_data, load_save

    save_data = load_save()
    _normalize_save_data(save_data)

    session.start_daily_challenge(save_data)
    resp = JSONResponse({"ok": True, "redirect": "/game"})
    if is_new:
        _attach_cookie(resp, session.session_id)
    return resp


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
