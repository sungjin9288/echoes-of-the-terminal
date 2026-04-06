"""Achievement definitions and evaluation helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ACHIEVEMENTS: tuple[dict[str, str], ...] = (
    # ── 탐험 (Exploration) ────────────────────────────────────────────────────
    {
        "id": "first_shutdown",
        "title": "첫 번째 추락",
        "desc": "처음으로 SYSTEM SHUTDOWN을 경험했다.",
    },
    {
        "id": "first_breach",
        "title": "첫 번째 돌파",
        "desc": "처음으로 CORE BREACHED에 성공했다.",
    },
    {
        "id": "runs_10",
        "title": "단골 해커",
        "desc": "총 10회 런을 완료했다 (승패 무관).",
    },
    {
        "id": "runs_50",
        "title": "숙련된 침입자",
        "desc": "총 50회 런을 완료했다.",
    },
    {
        "id": "victories_5",
        "title": "연속 타격",
        "desc": "5회 이상 승리했다.",
    },
    {
        "id": "victories_25",
        "title": "중견 해커",
        "desc": "누적 25회 승리를 달성했다.",
    },
    # ── 완벽 수행 (Perfection) ────────────────────────────────────────────────
    {
        "id": "perfect_infiltration",
        "title": "완전 침묵",
        "desc": "오답과 타임아웃 없이 런을 클리어했다.",
    },
    {
        "id": "zero_trace_win",
        "title": "무결의 침투",
        "desc": "런 종료 시 추적도 0%로 승리했다.",
    },
    {
        "id": "perfect_analyst",
        "title": "순수 분석",
        "desc": "ANALYST로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_perk_win",
        "title": "맨손 돌파",
        "desc": "영구 특성 없이 런을 클리어했다.",
    },
    # ── 클래스 (Class) ────────────────────────────────────────────────────────
    {
        "id": "analyst_victory",
        "title": "분석의 끝",
        "desc": "ANALYST로 첫 승리를 달성했다.",
    },
    {
        "id": "ghost_victory",
        "title": "그림자 질주",
        "desc": "GHOST로 첫 승리를 달성했다.",
    },
    {
        "id": "cracker_victory",
        "title": "파열 지점",
        "desc": "CRACKER로 첫 승리를 달성했다.",
    },
    {
        "id": "class_trinity",
        "title": "삼중 잠입",
        "desc": "세 클래스 모두로 최소 1회 승리했다.",
    },
    {
        "id": "analyst_master",
        "title": "알고리즘의 주인",
        "desc": "ANALYST로 5회 이상 승리했다.",
    },
    {
        "id": "ghost_master",
        "title": "그림자 귀신",
        "desc": "GHOST로 5회 이상 승리했다.",
    },
    {
        "id": "cracker_master",
        "title": "균열 전문가",
        "desc": "CRACKER로 5회 이상 승리했다.",
    },
    {
        "id": "triple_master",
        "title": "전천후 침입자",
        "desc": "세 클래스 모두 5회 이상 승리했다.",
    },
    # ── 도전 (Challenge) ──────────────────────────────────────────────────────
    {
        "id": "ascension_5",
        "title": "첫 번째 도전",
        "desc": "Ascension 5 이상에서 승리했다.",
    },
    {
        "id": "ascension_10",
        "title": "고도 상승",
        "desc": "Ascension 10 이상에서 승리했다.",
    },
    {
        "id": "ascension_15",
        "title": "극한의 영역",
        "desc": "Ascension 15 이상에서 승리했다.",
    },
    {
        "id": "ascension_20",
        "title": "심연 돌파",
        "desc": "Ascension 20을 클리어했다.",
    },
    {
        "id": "nightmare_clear",
        "title": "악몽의 생존자",
        "desc": "NIGHTMARE 난이도 노드가 포함된 런을 클리어했다.",
    },
    # ── 수집 (Collection) ─────────────────────────────────────────────────────
    {
        "id": "perk_collector",
        "title": "완비된 장비실",
        "desc": "모든 영구 특성을 해금했다.",
    },
    {
        "id": "endings_3",
        "title": "분기의 목격자",
        "desc": "3종 이상의 엔딩을 해금했다.",
    },
    {
        "id": "all_endings",
        "title": "모든 결말",
        "desc": "5종 엔딩을 모두 해금했다.",
    },
    # ── 캠페인 (Campaign) ─────────────────────────────────────────────────────
    {
        "id": "campaign_clear",
        "title": "터미널의 침묵",
        "desc": "100시간 캠페인을 완전히 클리어했다.",
    },
    {
        "id": "campaign_points_10000",
        "title": "누적된 데이터",
        "desc": "캠페인 포인트 10,000점을 돌파했다.",
    },
    {
        "id": "campaign_points_30000",
        "title": "데이터 수집가",
        "desc": "캠페인 포인트 30,000점을 달성했다.",
    },
    # ── 극한 (Extreme) ────────────────────────────────────────────────────────
    {
        "id": "all_nodes_correct",
        "title": "완벽한 런",
        "desc": "8노드 모두 첫 번째 시도에 정답을 입력해 클리어했다.",
    },
    {
        "id": "ascension_20_perfect",
        "title": "전설적 침투",
        "desc": "Ascension 20에서 오답 없이 클리어했다.",
    },
)

ACHIEVEMENT_INDEX: dict[str, dict[str, str]] = {
    item["id"]: item for item in ACHIEVEMENTS
}

DEFAULT_ACHIEVEMENT_STATE: dict[str, list[str]] = {
    "unlocked": [],
}


def normalize_achievement_state(raw_state: Any) -> dict[str, list[str]]:
    """Normalize stored achievement state to the current schema."""
    state = deepcopy(DEFAULT_ACHIEVEMENT_STATE)
    if not isinstance(raw_state, dict):
        return state

    raw_unlocked = raw_state.get("unlocked", [])
    if not isinstance(raw_unlocked, list):
        return state

    unlocked: list[str] = []
    seen: set[str] = set()
    for item in raw_unlocked:
        if not isinstance(item, str):
            continue
        if item not in ACHIEVEMENT_INDEX or item in seen:
            continue
        unlocked.append(item)
        seen.add(item)
    state["unlocked"] = unlocked
    return state


def get_achievement_snapshot(achievement_state: dict[str, Any]) -> dict[str, Any]:
    """Build a UI-friendly snapshot of achievement progress."""
    normalized = normalize_achievement_state(achievement_state)
    unlocked_ids = normalized["unlocked"]
    unlocked_entries = [
        ACHIEVEMENT_INDEX[achievement_id]
        for achievement_id in unlocked_ids
        if achievement_id in ACHIEVEMENT_INDEX
    ]
    return {
        "unlocked_count": len(unlocked_entries),
        "total_count": len(ACHIEVEMENTS),
        "unlocked_ids": unlocked_ids,
        "unlocked_entries": unlocked_entries,
    }


def evaluate_achievements(
    save_data: dict[str, Any],
    run_summary: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """
    Evaluate achievement unlocks against current save state and optional run summary.

    Returns newly unlocked achievement entries.
    """
    achievement_state = normalize_achievement_state(save_data.get("achievements", {}))
    unlocked = set(achievement_state["unlocked"])
    newly_unlocked: list[dict[str, str]] = []

    def _unlock(achievement_id: str) -> None:
        if achievement_id in unlocked:
            return
        entry = ACHIEVEMENT_INDEX.get(achievement_id)
        if entry is None:
            return
        unlocked.add(achievement_id)
        achievement_state["unlocked"].append(achievement_id)
        newly_unlocked.append(entry)

    campaign = save_data.get("campaign", {})
    if not isinstance(campaign, dict):
        campaign = {}
    class_victories = campaign.get("class_victories", {})
    if not isinstance(class_victories, dict):
        class_victories = {}
    perks = save_data.get("perks", {})
    if not isinstance(perks, dict):
        perks = {}

    if run_summary:
        result = str(run_summary.get("result", ""))
        is_victory = bool(run_summary.get("is_victory", False))
        class_key = str(run_summary.get("class_key", "")).upper()
        ascension_level = max(0, int(run_summary.get("ascension_level", 0)))
        wrong_analyzes = max(0, int(run_summary.get("wrong_analyzes", 0)))
        timeout_events = max(0, int(run_summary.get("timeout_events", 0)))
        trace_final = max(0, int(run_summary.get("trace_final", 100)))
        correct_answers = max(0, int(run_summary.get("correct_answers", 0)))
        cleared_difficulties: list[str] = list(run_summary.get("cleared_difficulties", []))

        if result == "shutdown":
            _unlock("first_shutdown")

        if is_victory:
            _unlock("first_breach")

            # 클래스별 첫 승리
            if class_key == "ANALYST":
                _unlock("analyst_victory")
            if class_key == "GHOST":
                _unlock("ghost_victory")
            if class_key == "CRACKER":
                _unlock("cracker_victory")

            # ASC 단계별 승리
            if ascension_level >= 5:
                _unlock("ascension_5")
            if ascension_level >= 10:
                _unlock("ascension_10")
            if ascension_level >= 15:
                _unlock("ascension_15")
            if ascension_level >= 20:
                _unlock("ascension_20")

            # 완벽 수행
            if wrong_analyzes == 0 and timeout_events == 0:
                _unlock("perfect_infiltration")
                if class_key == "ANALYST":
                    _unlock("perfect_analyst")
                if ascension_level >= 20:
                    _unlock("ascension_20_perfect")
            if trace_final == 0:
                _unlock("zero_trace_win")

            # 전체 노드 정답 (8노드 클리어, 오답 0)
            if correct_answers >= 8 and wrong_analyzes == 0:
                _unlock("all_nodes_correct")

            # 퍼크 없이 승리
            if not any(perks.values()):
                _unlock("no_perk_win")

            # NIGHTMARE 노드 포함 런 클리어
            if any(d.strip().upper() == "NIGHTMARE" for d in cleared_difficulties):
                _unlock("nightmare_clear")

    # 캠페인 누적 지표 (run_summary 없이도 평가)
    campaign_runs = int(campaign.get("runs", 0))
    campaign_victories = int(campaign.get("victories", 0))
    campaign_points = int(campaign.get("points", 0))

    if campaign_runs >= 10:
        _unlock("runs_10")
    if campaign_runs >= 50:
        _unlock("runs_50")
    if campaign_victories >= 5:
        _unlock("victories_5")
    if campaign_victories >= 25:
        _unlock("victories_25")
    if campaign_points >= 10000:
        _unlock("campaign_points_10000")
    if campaign_points >= 30000:
        _unlock("campaign_points_30000")

    # 클래스 마스터 (class_victories 기반)
    if all(int(class_victories.get(ck, 0)) >= 1 for ck in ("ANALYST", "GHOST", "CRACKER")):
        _unlock("class_trinity")
    if int(class_victories.get("ANALYST", 0)) >= 5:
        _unlock("analyst_master")
    if int(class_victories.get("GHOST", 0)) >= 5:
        _unlock("ghost_master")
    if int(class_victories.get("CRACKER", 0)) >= 5:
        _unlock("cracker_master")
    if all(int(class_victories.get(ck, 0)) >= 5 for ck in ("ANALYST", "GHOST", "CRACKER")):
        _unlock("triple_master")

    # 퍼크 수집
    if perks and all(bool(perks.get(perk_key, False)) for perk_key in perks):
        _unlock("perk_collector")

    # 엔딩 수집
    endings_data = save_data.get("endings", {})
    if isinstance(endings_data, dict):
        endings_unlocked = endings_data.get("unlocked", [])
        if isinstance(endings_unlocked, list):
            endings_count = len([e for e in endings_unlocked if isinstance(e, str)])
            if endings_count >= 3:
                _unlock("endings_3")
            if endings_count >= 5:
                _unlock("all_endings")

    # 캠페인 클리어
    if bool(campaign.get("cleared", False)):
        _unlock("campaign_clear")

    save_data["achievements"] = achievement_state
    return newly_unlocked
