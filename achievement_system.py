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
        "id": "endings_8",
        "title": "결말의 수집가",
        "desc": "8종 이상의 엔딩을 해금했다.",
    },
    {
        "id": "all_endings",
        "title": "모든 결말",
        "desc": "11종 엔딩을 모두 해금했다.",
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
    # ── 탐험 확장 (Exploration+) ──────────────────────────────────────────────
    {
        "id": "runs_25",
        "title": "단골 침입자",
        "desc": "총 25회 런을 완료했다.",
    },
    {
        "id": "runs_100",
        "title": "베테랑 해커",
        "desc": "총 100회 런을 완료했다.",
    },
    {
        "id": "runs_200",
        "title": "살아있는 전설",
        "desc": "총 200회 런을 완료했다.",
    },
    {
        "id": "victories_50",
        "title": "엘리트 침투자",
        "desc": "누적 50회 승리를 달성했다.",
    },
    {
        "id": "victories_100",
        "title": "시스템의 적",
        "desc": "누적 100회 승리를 달성했다.",
    },
    # ── 완벽 수행 확장 (Perfection+) ─────────────────────────────────────────
    {
        "id": "perfect_ghost",
        "title": "유령의 완전함",
        "desc": "GHOST로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_cracker",
        "title": "오류 없는 균열",
        "desc": "CRACKER로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_skill_win",
        "title": "맨 머리로 돌파",
        "desc": "액티브 스킬을 한 번도 사용하지 않고 런을 클리어했다.",
    },
    # ── 클래스 마스터 확장 (Class+) ───────────────────────────────────────────
    {
        "id": "analyst_10",
        "title": "알고리즘의 신",
        "desc": "ANALYST로 10회 이상 승리했다.",
    },
    {
        "id": "ghost_10",
        "title": "그림자의 전설",
        "desc": "GHOST로 10회 이상 승리했다.",
    },
    {
        "id": "cracker_10",
        "title": "파열의 달인",
        "desc": "CRACKER로 10회 이상 승리했다.",
    },
    {
        "id": "triple_10",
        "title": "완전한 침입자",
        "desc": "세 클래스 모두 10회 이상 승리했다.",
    },
    # ── 도전 확장 (Challenge+) ────────────────────────────────────────────────
    {
        "id": "ascension_3",
        "title": "첫 번째 각성",
        "desc": "Ascension 3 이상에서 승리했다.",
    },
    {
        "id": "ascension_7",
        "title": "시스템 압박",
        "desc": "Ascension 7 이상에서 승리했다.",
    },
    {
        "id": "ascension_12",
        "title": "심화 침투",
        "desc": "Ascension 12 이상에서 승리했다.",
    },
    {
        "id": "ascension_17",
        "title": "극한의 문턱",
        "desc": "Ascension 17 이상에서 승리했다.",
    },
    # ── 수집 확장 (Collection+) ───────────────────────────────────────────────
    {
        "id": "campaign_points_50000",
        "title": "데이터 폭풍",
        "desc": "캠페인 포인트 50,000점을 달성했다.",
    },
    {
        "id": "campaign_points_100000",
        "title": "무한 데이터",
        "desc": "캠페인 포인트 100,000점을 달성했다.",
    },
    # ── 극한 확장 (Extreme+) ──────────────────────────────────────────────────
    {
        "id": "ascension_20_analyst",
        "title": "알고리즘의 끝자락",
        "desc": "ANALYST로 Ascension 20을 클리어했다.",
    },
    {
        "id": "ascension_20_ghost",
        "title": "그림자의 정점",
        "desc": "GHOST로 Ascension 20을 클리어했다.",
    },
    {
        "id": "ascension_20_cracker",
        "title": "균열의 완성",
        "desc": "CRACKER로 Ascension 20을 클리어했다.",
    },
    {
        "id": "asc20_no_perk",
        "title": "맨손의 신",
        "desc": "영구 특성 없이 Ascension 20을 클리어했다.",
    },
    {
        "id": "asc20_trinity",
        "title": "터미널의 지배자",
        "desc": "세 클래스 모두로 Ascension 20을 클리어했다.",
    },
    {
        "id": "analyst_zero_trace",
        "title": "완벽한 분석",
        "desc": "ANALYST로 런 종료 시 추적도 0%로 승리했다.",
    },
    # ── 탐험 추가 (Exploration++) ──────────────────────────────────────────────
    {
        "id": "victories_10",
        "title": "검증된 해커",
        "desc": "누적 10회 승리를 달성했다.",
    },
    # ── 완벽 심화 (Perfection++) ──────────────────────────────────────────────
    {
        "id": "perfect_asc5",
        "title": "각성 속 완벽함",
        "desc": "Ascension 5 이상에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_asc10",
        "title": "심화 각성의 완벽함",
        "desc": "Ascension 10 이상에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_skill_asc10",
        "title": "맨주먹의 각성자",
        "desc": "액티브 스킬 미사용으로 Ascension 10 이상에서 승리했다.",
    },
    # ── 클래스 심화 (Class++) ─────────────────────────────────────────────────
    {
        "id": "ghost_no_timeout",
        "title": "소리 없는 유령",
        "desc": "GHOST로 타임아웃 없이 런을 클리어했다.",
    },
    {
        "id": "cracker_nightmare",
        "title": "균열의 악몽",
        "desc": "CRACKER로 NIGHTMARE 노드가 포함된 런을 클리어했다.",
    },
    {
        "id": "analyst_asc15",
        "title": "분석의 극한",
        "desc": "ANALYST로 Ascension 15 이상에서 승리했다.",
    },
    {
        "id": "ghost_asc15",
        "title": "유령의 극한",
        "desc": "GHOST로 Ascension 15 이상에서 승리했다.",
    },
    {
        "id": "cracker_asc15",
        "title": "균열의 극한",
        "desc": "CRACKER로 Ascension 15 이상에서 승리했다.",
    },
    # ── 수집/해금 (Collection++) ──────────────────────────────────────────────
    {
        "id": "endings_1",
        "title": "첫 번째 결말",
        "desc": "첫 번째 엔딩을 해금했다.",
    },
    {
        "id": "perk_first",
        "title": "첫 번째 강화",
        "desc": "첫 번째 영구 특성을 해금했다.",
    },
    {
        "id": "ascension_unlocked_5",
        "title": "각성의 문턱",
        "desc": "Ascension 5까지 해금했다.",
    },
    {
        "id": "ascension_unlocked_10",
        "title": "각성의 중반",
        "desc": "Ascension 10까지 해금했다.",
    },
    {
        "id": "ascension_unlocked_15",
        "title": "각성의 심연",
        "desc": "Ascension 15까지 해금했다.",
    },
    {
        "id": "ascension_unlocked_20",
        "title": "각성의 정점",
        "desc": "Ascension 20까지 완전히 해금했다.",
    },
    # ── 데이터 파편 (Data Fragments) ─────────────────────────────────────────
    {
        "id": "data_fragments_500",
        "title": "데이터 수집가",
        "desc": "데이터 파편을 500개 이상 보유했다.",
    },
    {
        "id": "data_fragments_2000",
        "title": "데이터 군주",
        "desc": "데이터 파편을 2,000개 이상 보유했다.",
    },
    # ── 극한 심화 (Extreme++) ─────────────────────────────────────────────────
    {
        "id": "perfect_analyst_asc10",
        "title": "알고리즘의 완성",
        "desc": "ANALYST로 Ascension 10 이상에서 오답 없이 승리했다.",
    },
    {
        "id": "perfect_ghost_asc10",
        "title": "그림자의 완성",
        "desc": "GHOST로 Ascension 10 이상에서 오답 없이 승리했다.",
    },
    {
        "id": "perfect_cracker_asc10",
        "title": "균열의 완성",
        "desc": "CRACKER로 Ascension 10 이상에서 오답 없이 승리했다.",
    },
    # ── 탐험 최종 (Exploration Final) ────────────────────────────────────────
    {
        "id": "runs_300",
        "title": "침입의 역사",
        "desc": "총 300회 런을 완료했다.",
    },
    {
        "id": "runs_500",
        "title": "불멸의 해커",
        "desc": "총 500회 런을 완료했다.",
    },
    {
        "id": "victories_200",
        "title": "무적의 침투자",
        "desc": "누적 200회 승리를 달성했다.",
    },
    {
        "id": "victories_500",
        "title": "전설의 시작",
        "desc": "누적 500회 승리를 달성했다.",
    },
    # ── 완벽 최종 (Perfection Final) ─────────────────────────────────────────
    {
        "id": "perfect_asc15",
        "title": "각성의 완벽함",
        "desc": "Ascension 15 이상에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "no_skill_perfect",
        "title": "본능적 침투",
        "desc": "액티브 스킬 미사용으로 오답 없이 런을 클리어했다.",
    },
    {
        "id": "ghost_trace_zero",
        "title": "유령의 궤적",
        "desc": "GHOST로 런 종료 시 추적도 0%로 승리했다.",
    },
    {
        "id": "cracker_trace_zero",
        "title": "균열 없는 균열",
        "desc": "CRACKER로 런 종료 시 추적도 0%로 승리했다.",
    },
    {
        "id": "no_timeout_asc15",
        "title": "시간을 지배하는 자",
        "desc": "Ascension 15 이상에서 타임아웃 없이 승리했다.",
    },
    {
        "id": "survivor",
        "title": "포기를 모르는 자",
        "desc": "3회 이상 오답 입력 후에도 런을 클리어했다.",
    },
    # ── 클래스 최종 (Class Final) ─────────────────────────────────────────────
    {
        "id": "analyst_nightmare",
        "title": "분석의 악몽",
        "desc": "ANALYST로 NIGHTMARE 노드가 포함된 런을 클리어했다.",
    },
    {
        "id": "ghost_nightmare",
        "title": "유령의 악몽",
        "desc": "GHOST로 NIGHTMARE 노드가 포함된 런을 클리어했다.",
    },
    {
        "id": "perfect_analyst_asc20",
        "title": "분석의 신",
        "desc": "ANALYST로 Ascension 20에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_ghost_asc20",
        "title": "유령의 신",
        "desc": "GHOST로 Ascension 20에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "perfect_cracker_asc20",
        "title": "균열의 신",
        "desc": "CRACKER로 Ascension 20에서 오답 없이 런을 클리어했다.",
    },
    {
        "id": "ghost_asc20_no_timeout",
        "title": "유령의 침묵",
        "desc": "GHOST로 Ascension 20에서 타임아웃 없이 승리했다.",
    },
    {
        "id": "no_skill_asc20",
        "title": "각성 속 맨주먹",
        "desc": "Ascension 20에서 액티브 스킬을 사용하지 않고 승리했다.",
    },
    # ── 핸디캡 (Handicap) ────────────────────────────────────────────────────
    {
        "id": "no_skill_no_perk",
        "title": "순수한 침투",
        "desc": "영구 특성과 액티브 스킬 없이 런을 클리어했다.",
    },
    {
        "id": "analyst_no_perk",
        "title": "무장해제된 분석가",
        "desc": "ANALYST로 영구 특성 없이 승리했다.",
    },
    {
        "id": "ghost_no_perk",
        "title": "무장해제된 유령",
        "desc": "GHOST로 영구 특성 없이 승리했다.",
    },
    {
        "id": "cracker_no_perk",
        "title": "무장해제된 균열",
        "desc": "CRACKER로 영구 특성 없이 승리했다.",
    },
    # ── 수집 최종 (Collection Final) ─────────────────────────────────────────
    {
        "id": "data_fragments_5000",
        "title": "데이터 황제",
        "desc": "데이터 파편을 5,000개 이상 보유했다.",
    },
    {
        "id": "data_fragments_10000",
        "title": "데이터 신",
        "desc": "데이터 파편을 10,000개 이상 보유했다.",
    },
    {
        "id": "campaign_points_200000",
        "title": "무한 데이터 군주",
        "desc": "캠페인 포인트 200,000점을 달성했다.",
    },
    {
        "id": "campaign_points_500000",
        "title": "시스템의 붕괴",
        "desc": "캠페인 포인트 500,000점을 달성했다.",
    },
    # ── MYSTERY (미스터리 노드) ───────────────────────────────────────────────
    {
        "id": "mystery_first_engage",
        "title": "첫 번째 도박",
        "desc": "처음으로 MYSTERY 노드에서 이벤트에 개입했다.",
    },
    {
        "id": "mystery_good_5",
        "title": "행운의 다이버",
        "desc": "MYSTERY 노드 개입에서 좋은 결과를 누적 5회 얻었다.",
    },
    {
        "id": "mystery_engaged_20",
        "title": "위험 중독자",
        "desc": "MYSTERY 노드에서 총 20회 이상 개입했다.",
    },
    {
        "id": "mystery_all_good_run",
        "title": "완벽한 직관",
        "desc": "한 런에서 모든 MYSTERY 개입에서 좋은 결과를 얻었다 (최소 2회 이상 개입).",
    },
    {
        "id": "mystery_all_skip_run",
        "title": "신중한 해커",
        "desc": "한 런에서 모든 MYSTERY 노드를 무시했다 (최소 2회 이상 등장).",
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
    mystery_total = mystery_engaged + mystery_skipped  # 런에서 등장한 MYSTERY 노드 수

    # 첫 번째 개입
    if mystery_engaged >= 1:
        _unlock("mystery_first_engage")

    # 누적 카운터는 save_data에 기록
    if "mystery_stats" not in save_data or not isinstance(save_data["mystery_stats"], dict):
        save_data["mystery_stats"] = {"total_engaged": 0, "total_good": 0}
    m_stats = save_data["mystery_stats"]
    m_stats["total_engaged"] = int(m_stats.get("total_engaged", 0)) + mystery_engaged
    m_stats["total_good"] = int(m_stats.get("total_good", 0)) + mystery_good

    if m_stats["total_good"] >= 5:
        _unlock("mystery_good_5")
    if m_stats["total_engaged"] >= 20:
        _unlock("mystery_engaged_20")

    # 런 단위 업적
    if mystery_engaged >= 2 and mystery_engaged == mystery_good:
        _unlock("mystery_all_good_run")
    if mystery_total >= 2 and mystery_skipped == mystery_total:
        _unlock("mystery_all_skip_run")

    save_data["achievements"] = achievement_state
    return newly_unlocked
