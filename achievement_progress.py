"""업적 진행률 계산 모듈.

`achievement_system.py`의 unlock 로직은 이벤트/상태 판정에 집중하고,
본 모듈은 "누적 카운터" 계열 업적에 한해 (current, target) 쌍을 계산한다.

공개 API:
- compute_achievement_progress(achievement_id, save_data) -> (current, target) | None
- get_locked_progress_entries(save_data, top_n) -> list[ProgressEntry]
- format_progress_bar(current, target, width) -> str
"""

from __future__ import annotations

from typing import Any, Callable

from achievement_data import ACHIEVEMENT_INDEX
from achievement_system import normalize_achievement_state


# ── 세이브 데이터에서 값을 꺼내는 헬퍼 ────────────────────────────────────────

def _campaign_field(save_data: dict[str, Any], key: str) -> int:
    campaign = save_data.get("campaign", {})
    if not isinstance(campaign, dict):
        return 0
    value = campaign.get(key, 0)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _class_victories(save_data: dict[str, Any], class_key: str) -> int:
    campaign = save_data.get("campaign", {})
    if not isinstance(campaign, dict):
        return 0
    cv = campaign.get("class_victories", {})
    if not isinstance(cv, dict):
        return 0
    try:
        return max(0, int(cv.get(class_key, 0)))
    except (TypeError, ValueError):
        return 0


def _all_classes_min(save_data: dict[str, Any]) -> int:
    """세 클래스 승리 중 최솟값 — triple_master/triple_10 계열."""
    return min(
        _class_victories(save_data, "ANALYST"),
        _class_victories(save_data, "GHOST"),
        _class_victories(save_data, "CRACKER"),
    )


def _endings_count(save_data: dict[str, Any]) -> int:
    endings = save_data.get("endings", {})
    if not isinstance(endings, dict):
        return 0
    unlocked = endings.get("unlocked", [])
    if not isinstance(unlocked, list):
        return 0
    return sum(1 for e in unlocked if isinstance(e, str))


def _data_fragments(save_data: dict[str, Any]) -> int:
    try:
        return max(0, int(save_data.get("data_fragments", 0)))
    except (TypeError, ValueError):
        return 0


def _owned_perks(save_data: dict[str, Any]) -> int:
    perks = save_data.get("perks", {})
    if not isinstance(perks, dict):
        return 0
    return sum(1 for v in perks.values() if bool(v))


def _mystery_field(save_data: dict[str, Any], key: str) -> int:
    stats = save_data.get("mystery_stats", {})
    if not isinstance(stats, dict):
        return 0
    try:
        return max(0, int(stats.get(key, 0)))
    except (TypeError, ValueError):
        return 0


# ── 업적 ID → (metric getter, target) 명세 ─────────────────────────────────

PROGRESS_SPECS: dict[str, tuple[Callable[[dict[str, Any]], int], int]] = {
    # 런/승리 누적
    "runs_10": (lambda s: _campaign_field(s, "runs"), 10),
    "runs_25": (lambda s: _campaign_field(s, "runs"), 25),
    "runs_50": (lambda s: _campaign_field(s, "runs"), 50),
    "runs_100": (lambda s: _campaign_field(s, "runs"), 100),
    "runs_200": (lambda s: _campaign_field(s, "runs"), 200),
    "runs_300": (lambda s: _campaign_field(s, "runs"), 300),
    "runs_500": (lambda s: _campaign_field(s, "runs"), 500),
    "victories_5": (lambda s: _campaign_field(s, "victories"), 5),
    "victories_10": (lambda s: _campaign_field(s, "victories"), 10),
    "victories_25": (lambda s: _campaign_field(s, "victories"), 25),
    "victories_50": (lambda s: _campaign_field(s, "victories"), 50),
    "victories_100": (lambda s: _campaign_field(s, "victories"), 100),
    "victories_200": (lambda s: _campaign_field(s, "victories"), 200),
    "victories_500": (lambda s: _campaign_field(s, "victories"), 500),
    # 캠페인 포인트
    "campaign_points_10000": (lambda s: _campaign_field(s, "points"), 10000),
    "campaign_points_30000": (lambda s: _campaign_field(s, "points"), 30000),
    "campaign_points_50000": (lambda s: _campaign_field(s, "points"), 50000),
    "campaign_points_100000": (lambda s: _campaign_field(s, "points"), 100000),
    "campaign_points_200000": (lambda s: _campaign_field(s, "points"), 200000),
    "campaign_points_500000": (lambda s: _campaign_field(s, "points"), 500000),
    # 클래스별 누적 승리
    "analyst_master": (lambda s: _class_victories(s, "ANALYST"), 5),
    "ghost_master": (lambda s: _class_victories(s, "GHOST"), 5),
    "cracker_master": (lambda s: _class_victories(s, "CRACKER"), 5),
    "analyst_10": (lambda s: _class_victories(s, "ANALYST"), 10),
    "ghost_10": (lambda s: _class_victories(s, "GHOST"), 10),
    "cracker_10": (lambda s: _class_victories(s, "CRACKER"), 10),
    # 삼중 클래스 (최솟값 기준)
    "class_trinity": (_all_classes_min, 1),
    "triple_master": (_all_classes_min, 5),
    "triple_10": (_all_classes_min, 10),
    # ASC 해금 마일스톤
    "ascension_unlocked_5": (lambda s: _campaign_field(s, "ascension_unlocked"), 5),
    "ascension_unlocked_10": (lambda s: _campaign_field(s, "ascension_unlocked"), 10),
    "ascension_unlocked_15": (lambda s: _campaign_field(s, "ascension_unlocked"), 15),
    "ascension_unlocked_20": (lambda s: _campaign_field(s, "ascension_unlocked"), 20),
    # 엔딩 수집
    "endings_1": (_endings_count, 1),
    "endings_3": (_endings_count, 3),
    "endings_8": (_endings_count, 8),
    "all_endings": (_endings_count, 11),
    # 데이터 파편 보유
    "data_fragments_500": (_data_fragments, 500),
    "data_fragments_2000": (_data_fragments, 2000),
    "data_fragments_5000": (_data_fragments, 5000),
    "data_fragments_10000": (_data_fragments, 10000),
    # 퍼크 수집
    "perk_hoarder_5": (_owned_perks, 5),
    "perk_hoarder_10": (_owned_perks, 10),
    # MYSTERY 누적
    "mystery_good_5": (lambda s: _mystery_field(s, "total_good"), 5),
    "mystery_engaged_20": (lambda s: _mystery_field(s, "total_engaged"), 20),
}


# ── 공개 API ──────────────────────────────────────────────────────────────

def compute_achievement_progress(
    achievement_id: str,
    save_data: dict[str, Any],
) -> tuple[int, int] | None:
    """주어진 업적 ID의 (current, target)을 반환. 진행률 추적 대상이 아니면 None."""
    spec = PROGRESS_SPECS.get(achievement_id)
    if spec is None:
        return None
    getter, target = spec
    try:
        current = max(0, int(getter(save_data)))
    except Exception:
        current = 0
    # target 초과 시 target으로 cap
    return (min(current, target), target)


def get_locked_progress_entries(
    save_data: dict[str, Any],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """미해금 업적 중 진행률이 있는 항목을 진행 비율 내림차순으로 반환.

    각 엔트리 형태:
        {"id": str, "title": str, "desc": str, "current": int, "target": int, "ratio": float}
    """
    state = normalize_achievement_state(save_data.get("achievements", {}))
    unlocked = set(state["unlocked"])

    entries: list[dict[str, Any]] = []
    for ach_id, (getter, target) in PROGRESS_SPECS.items():
        if ach_id in unlocked:
            continue
        ach_entry = ACHIEVEMENT_INDEX.get(ach_id)
        if ach_entry is None:
            continue
        if target <= 0:
            continue
        try:
            current = max(0, int(getter(save_data)))
        except Exception:
            current = 0
        current_capped = min(current, target)
        ratio = current_capped / target
        entries.append({
            "id": ach_id,
            "title": str(ach_entry.get("title", "")),
            "desc": str(ach_entry.get("desc", "")),
            "current": current_capped,
            "target": target,
            "ratio": ratio,
        })

    # 진행 비율 내림차순, 동률은 target 작은 순(해금 임박)
    entries.sort(key=lambda e: (-e["ratio"], e["target"]))
    if top_n > 0:
        return entries[:top_n]
    return entries


def format_progress_bar(current: int, target: int, width: int = 10) -> str:
    """유니코드 블록 문자로 진행바 문자열 생성. 예: '[▓▓▓░░░░░░░]'."""
    if width <= 0:
        return ""
    if target <= 0:
        filled = 0
    else:
        ratio = max(0.0, min(1.0, current / target))
        filled = int(round(ratio * width))
        filled = max(0, min(width, filled))
    return "[" + "▓" * filled + "░" * (width - filled) + "]"
