"""업적 평가 로직 및 상태 관리.

업적 정의 데이터(115종)는 achievement_data.py에 분리되어 있다.
외부 공개 API: evaluate_achievements, get_achievement_snapshot, normalize_achievement_state
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from achievement_data import (
    ACHIEVEMENT_INDEX,
    ACHIEVEMENTS,
    DEFAULT_ACHIEVEMENT_STATE,
)


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
    """Evaluate achievement unlocks against current save state and optional run summary.

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
        skill_used = bool(run_summary.get("skill_used", False))

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
            if ascension_level >= 3:
                _unlock("ascension_3")
            if ascension_level >= 5:
                _unlock("ascension_5")
            if ascension_level >= 7:
                _unlock("ascension_7")
            if ascension_level >= 10:
                _unlock("ascension_10")
            if ascension_level >= 12:
                _unlock("ascension_12")
            if ascension_level >= 15:
                _unlock("ascension_15")
            if ascension_level >= 17:
                _unlock("ascension_17")
            if ascension_level >= 20:
                _unlock("ascension_20")

            # 완벽 수행
            if wrong_analyzes == 0 and timeout_events == 0:
                _unlock("perfect_infiltration")
                if class_key == "ANALYST":
                    _unlock("perfect_analyst")
                if class_key == "GHOST":
                    _unlock("perfect_ghost")
                if class_key == "CRACKER":
                    _unlock("perfect_cracker")
                if ascension_level >= 20:
                    _unlock("ascension_20_perfect")
            if trace_final == 0:
                _unlock("zero_trace_win")
                if class_key == "ANALYST":
                    _unlock("analyst_zero_trace")

            # 전체 노드 정답 (8노드 클리어, 오답 0)
            if correct_answers >= 8 and wrong_analyzes == 0:
                _unlock("all_nodes_correct")

            # 퍼크 없이 승리
            if not any(perks.values()):
                _unlock("no_perk_win")
                if ascension_level >= 20:
                    _unlock("asc20_no_perk")

            # 스킬 미사용 승리
            if not skill_used:
                _unlock("no_skill_win")

            # NIGHTMARE 노드 포함 런 클리어
            if any(d.strip().upper() == "NIGHTMARE" for d in cleared_difficulties):
                _unlock("nightmare_clear")

            # ASC 20 클래스별 승리
            if ascension_level >= 20:
                if class_key == "ANALYST":
                    _unlock("ascension_20_analyst")
                if class_key == "GHOST":
                    _unlock("ascension_20_ghost")
                if class_key == "CRACKER":
                    _unlock("ascension_20_cracker")

            # 완벽 심화
            if wrong_analyzes == 0 and timeout_events == 0:
                if ascension_level >= 5:
                    _unlock("perfect_asc5")
                if ascension_level >= 10:
                    _unlock("perfect_asc10")
                    if class_key == "ANALYST":
                        _unlock("perfect_analyst_asc10")
                    if class_key == "GHOST":
                        _unlock("perfect_ghost_asc10")
                    if class_key == "CRACKER":
                        _unlock("perfect_cracker_asc10")

            # 스킬 미사용 + 고각성 승리
            if not skill_used and ascension_level >= 10:
                _unlock("no_skill_asc10")

            # 클래스 심화
            if class_key == "GHOST" and timeout_events == 0:
                _unlock("ghost_no_timeout")
                if ascension_level >= 20:
                    _unlock("ghost_asc20_no_timeout")
            if class_key == "CRACKER" and any(
                d.strip().upper() == "NIGHTMARE" for d in cleared_difficulties
            ):
                _unlock("cracker_nightmare")
            if class_key == "ANALYST" and ascension_level >= 15:
                _unlock("analyst_asc15")
            if class_key == "GHOST" and ascension_level >= 15:
                _unlock("ghost_asc15")
            if class_key == "CRACKER" and ascension_level >= 15:
                _unlock("cracker_asc15")

            # NIGHTMARE 노드 포함 런 클래스별
            _has_nightmare = any(d.strip().upper() == "NIGHTMARE" for d in cleared_difficulties)
            if _has_nightmare:
                if class_key == "ANALYST":
                    _unlock("analyst_nightmare")
                if class_key == "GHOST":
                    _unlock("ghost_nightmare")

            # 완벽 최종
            if wrong_analyzes == 0 and timeout_events == 0:
                if ascension_level >= 15:
                    _unlock("perfect_asc15")
                if ascension_level >= 20:
                    if class_key == "ANALYST":
                        _unlock("perfect_analyst_asc20")
                    if class_key == "GHOST":
                        _unlock("perfect_ghost_asc20")
                    if class_key == "CRACKER":
                        _unlock("perfect_cracker_asc20")

            # 타임아웃 없이 고각성
            if timeout_events == 0 and ascension_level >= 15:
                _unlock("no_timeout_asc15")

            # 스킬 미사용 + 완벽
            if not skill_used and wrong_analyzes == 0:
                _unlock("no_skill_perfect")
            if not skill_used and ascension_level >= 20:
                _unlock("no_skill_asc20")

            # trace 0% 클래스별
            if trace_final == 0:
                if class_key == "GHOST":
                    _unlock("ghost_trace_zero")
                if class_key == "CRACKER":
                    _unlock("cracker_trace_zero")

            # 핸디캡
            _no_perks = not any(perks.values())
            if _no_perks and not skill_used:
                _unlock("no_skill_no_perk")
            if _no_perks:
                if class_key == "ANALYST":
                    _unlock("analyst_no_perk")
                if class_key == "GHOST":
                    _unlock("ghost_no_perk")
                if class_key == "CRACKER":
                    _unlock("cracker_no_perk")

            # 역경 극복 (오답 3+ 후 승리)
            if wrong_analyzes >= 3:
                _unlock("survivor")

    # 캠페인 누적 지표 (run_summary 없이도 평가)
    campaign_runs = int(campaign.get("runs", 0))
    campaign_victories = int(campaign.get("victories", 0))
    campaign_points = int(campaign.get("points", 0))

    if campaign_runs >= 10:
        _unlock("runs_10")
    if campaign_runs >= 25:
        _unlock("runs_25")
    if campaign_runs >= 50:
        _unlock("runs_50")
    if campaign_runs >= 100:
        _unlock("runs_100")
    if campaign_runs >= 200:
        _unlock("runs_200")
    if campaign_runs >= 300:
        _unlock("runs_300")
    if campaign_runs >= 500:
        _unlock("runs_500")
    if campaign_victories >= 5:
        _unlock("victories_5")
    if campaign_victories >= 10:
        _unlock("victories_10")
    if campaign_victories >= 25:
        _unlock("victories_25")
    if campaign_victories >= 50:
        _unlock("victories_50")
    if campaign_victories >= 100:
        _unlock("victories_100")
    if campaign_victories >= 200:
        _unlock("victories_200")
    if campaign_victories >= 500:
        _unlock("victories_500")
    if campaign_points >= 10000:
        _unlock("campaign_points_10000")
    if campaign_points >= 30000:
        _unlock("campaign_points_30000")
    if campaign_points >= 50000:
        _unlock("campaign_points_50000")
    if campaign_points >= 100000:
        _unlock("campaign_points_100000")
    if campaign_points >= 200000:
        _unlock("campaign_points_200000")
    if campaign_points >= 500000:
        _unlock("campaign_points_500000")

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
    if int(class_victories.get("ANALYST", 0)) >= 10:
        _unlock("analyst_10")
    if int(class_victories.get("GHOST", 0)) >= 10:
        _unlock("ghost_10")
    if int(class_victories.get("CRACKER", 0)) >= 10:
        _unlock("cracker_10")
    if all(int(class_victories.get(ck, 0)) >= 10 for ck in ("ANALYST", "GHOST", "CRACKER")):
        _unlock("triple_10")

    # 퍼크 수집
    if perks and any(bool(v) for v in perks.values()):
        _unlock("perk_first")
    if perks and all(bool(perks.get(perk_key, False)) for perk_key in perks):
        _unlock("perk_collector")

    # 엔딩 수집
    endings_data = save_data.get("endings", {})
    if isinstance(endings_data, dict):
        endings_unlocked = endings_data.get("unlocked", [])
        if isinstance(endings_unlocked, list):
            endings_count = len([e for e in endings_unlocked if isinstance(e, str)])
            if endings_count >= 1:
                _unlock("endings_1")
            if endings_count >= 3:
                _unlock("endings_3")
            if endings_count >= 8:
                _unlock("endings_8")
            if endings_count >= 11:
                _unlock("all_endings")

    # ASC 해금 마일스톤
    ascension_unlocked = int(campaign.get("ascension_unlocked", 0))
    if ascension_unlocked >= 5:
        _unlock("ascension_unlocked_5")
    if ascension_unlocked >= 10:
        _unlock("ascension_unlocked_10")
    if ascension_unlocked >= 15:
        _unlock("ascension_unlocked_15")
    if ascension_unlocked >= 20:
        _unlock("ascension_unlocked_20")

    # 데이터 파편
    data_fragments = int(save_data.get("data_fragments", 0))
    if data_fragments >= 500:
        _unlock("data_fragments_500")
    if data_fragments >= 2000:
        _unlock("data_fragments_2000")
    if data_fragments >= 5000:
        _unlock("data_fragments_5000")
    if data_fragments >= 10000:
        _unlock("data_fragments_10000")

    # ASC 20 삼중 클리어 (세 클래스 모두 asc20 승리 업적 보유 시)
    asc20_classes = {"ascension_20_analyst", "ascension_20_ghost", "ascension_20_cracker"}
    if asc20_classes.issubset(unlocked):
        _unlock("asc20_trinity")

    # 캠페인 클리어
    if bool(campaign.get("cleared", False)):
        _unlock("campaign_clear")

    # ── MYSTERY 노드 업적 ─────────────────────────────────────────────────────
    mystery_engaged = int(run_summary.get("mystery_engaged", 0)) if run_summary else 0
    mystery_good = int(run_summary.get("mystery_good", 0)) if run_summary else 0
    mystery_skipped = int(run_summary.get("mystery_skipped", 0)) if run_summary else 0
    mystery_total = mystery_engaged + mystery_skipped

    if mystery_engaged >= 1:
        _unlock("mystery_first_engage")

    if "mystery_stats" not in save_data or not isinstance(save_data["mystery_stats"], dict):
        save_data["mystery_stats"] = {"total_engaged": 0, "total_good": 0}
    m_stats = save_data["mystery_stats"]
    m_stats["total_engaged"] = int(m_stats.get("total_engaged", 0)) + mystery_engaged
    m_stats["total_good"] = int(m_stats.get("total_good", 0)) + mystery_good

    if m_stats["total_good"] >= 5:
        _unlock("mystery_good_5")
    if m_stats["total_engaged"] >= 20:
        _unlock("mystery_engaged_20")

    if mystery_engaged >= 2 and mystery_engaged == mystery_good:
        _unlock("mystery_all_good_run")
    if mystery_total >= 2 and mystery_skipped == mystery_total:
        _unlock("mystery_all_skip_run")

    # ── 아티팩트 업적 ─────────────────────────────────────────────────────────
    if run_summary:
        artifacts_held = int(run_summary.get("artifacts_held", 0))
        is_vic = bool(run_summary.get("is_victory", False))
        if is_vic and artifacts_held >= 1:
            _unlock("artifact_first_win")
        if is_vic and artifacts_held >= 3:
            _unlock("artifact_hoarder")
        if is_vic and artifacts_held >= 5:
            _unlock("artifact_zealot")

    # ── 퍼크 업적 ────────────────────────────────────────────────────────────
    owned_perks = sum(1 for v in perks.values() if bool(v))
    if owned_perks >= 5:
        _unlock("perk_hoarder_5")
    if owned_perks >= 10:
        _unlock("perk_hoarder_10")

    if run_summary:
        is_vic = bool(run_summary.get("is_victory", False))
        if is_vic and bool(perks.get("swift_analysis", False)):
            _unlock("swift_first_win")

    # ── 특수 아티팩트 업적 ───────────────────────────────────────────────────
    if run_summary:
        is_vic = bool(run_summary.get("is_victory", False))
        if is_vic and bool(run_summary.get("cascade_triggered", False)):
            _unlock("cascade_master")
        if is_vic and bool(run_summary.get("void_scanner_used", False)):
            _unlock("void_hunter")
        mystery_frags = int(run_summary.get("mystery_frags_gained", 0))
        if is_vic and mystery_frags >= 300:
            _unlock("mystery_rich")

    save_data["achievements"] = achievement_state
    return newly_unlocked
