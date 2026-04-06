"""멀티 엔딩 시스템 — 런 결과 조건에 따른 5종 엔딩 판정."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from progression_system import is_campaign_cleared


@dataclass(frozen=True)
class Ending:
    """단일 엔딩 메타데이터."""

    ending_id: str
    title: str           # 엔딩 제목
    subtitle: str        # 부제
    flavor_text: str     # 플레이버 텍스트 (여러 줄 가능)
    color: str           # Rich 색상 코드
    border_style: str    # Rich 패널 테두리 스타일
    priority: int        # 낮을수록 먼저 표시 (복수 조건 충족 시)


# ── 엔딩 정의 (5종) ──────────────────────────────────────────────────────────

ENDINGS: dict[str, Ending] = {
    "TRUE_END": Ending(
        ending_id="TRUE_END",
        title="TERMINAL SILENCE",
        subtitle="아르고스 코어 완전 침묵",
        flavor_text=(
            "100번의 침투, 수백 번의 실패와 재기.\n"
            "마침내 ARGOS의 마지막 신호가 꺼졌다.\n\n"
            "터미널에는 오직 정적만이 남아 있다.\n"
            "당신은 그림자 속에서 전설이 되었다."
        ),
        color="bold #FFD700",
        border_style="#FFD700",
        priority=1,
    ),
    "ASCENSION_END": Ending(
        ending_id="ASCENSION_END",
        title="APEX PROTOCOL",
        subtitle="최고 난이도 격파",
        flavor_text=(
            "ARGOS는 당신을 위해 모든 방어를 올렸다.\n"
            "그리고 당신은 그 모든 것을 부쉈다.\n\n"
            "ASC-20. 이 등급에서 살아남은 자는\n"
            "아직 당신 이전에 없었다."
        ),
        color="bold #FF4500",
        border_style="#FF4500",
        priority=2,
    ),
    "GHOST_END": Ending(
        ending_id="GHOST_END",
        title="PHANTOM BREACH",
        subtitle="완전 은신 침투",
        flavor_text=(
            "추적도 10%. 아르고스는 당신을 감지하지 못했다.\n"
            "당신은 시스템에 존재하지 않는 유령이었다.\n\n"
            "코어가 열렸다. 경보는 울리지 않았다.\n"
            "완벽한 침투란 존재가 지워지는 것이다."
        ),
        color="bold #00FF7F",
        border_style="#00FF7F",
        priority=3,
    ),
    "ANALYST_END": Ending(
        ending_id="ANALYST_END",
        title="ZERO ERROR",
        subtitle="완전 무결 분석",
        flavor_text=(
            "단 한 번의 오답도, 단 한 번의 타임아웃도 없었다.\n"
            "모든 로그의 모순이 당신 앞에 투명하게 열렸다.\n\n"
            "당신은 분석가가 아니다.\n"
            "당신은 진실 그 자체다."
        ),
        color="bold #00BFFF",
        border_style="#00BFFF",
        priority=4,
    ),
    "SURVIVOR_END": Ending(
        ending_id="SURVIVOR_END",
        title="LAST SIGNAL",
        subtitle="벼랑 끝 생존",
        flavor_text=(
            "추적도 90%. 경보가 울리고 있었다.\n"
            "아르고스는 당신을 잡을 수 있다고 믿었다.\n\n"
            "하지만 당신은 코어를 열었다.\n"
            "살아남는 것도 실력이다."
        ),
        color="bold #FF6347",
        border_style="#FF6347",
        priority=5,
    ),
}

# 잠금 해제 기록용 세이브 키
ENDINGS_SAVE_KEY = "endings"


def evaluate_ending(
    run_result: dict[str, Any],
    save_data: dict[str, Any],
) -> Ending | None:
    """
    런 결과와 세이브 상태로 활성화할 엔딩을 결정한다.

    Args:
        run_result: {
            "is_victory": bool,
            "trace_final": int,          # 런 종료 시 추적도 (%)
            "wrong_analyzes": int,        # 오답 횟수
            "timeout_events": int,        # 타임아웃 횟수
            "ascension_level": int,       # 플레이한 각성 레벨
            "correct_answers": int,       # 클리어한 노드 수
        }
        save_data: 전체 세이브 데이터

    Returns:
        활성화된 Ending 객체, 없으면 None (일반 승리/패배로 처리)
    """
    if not run_result.get("is_victory", False):
        return None

    campaign = save_data.get("campaign", {})
    trace = int(run_result.get("trace_final", 100))
    wrong = int(run_result.get("wrong_analyzes", 0))
    timeouts = int(run_result.get("timeout_events", 0))
    asc = int(run_result.get("ascension_level", 0))
    correct = int(run_result.get("correct_answers", 0))

    candidates: list[Ending] = []

    # TRUE_END: 캠페인 클리어 달성 시
    if is_campaign_cleared(campaign):
        candidates.append(ENDINGS["TRUE_END"])

    # ASCENSION_END: ASC 20 승리
    if asc >= 20:
        candidates.append(ENDINGS["ASCENSION_END"])

    # GHOST_END: 최종 추적도 10% 이하로 승리
    if trace <= 10:
        candidates.append(ENDINGS["GHOST_END"])

    # ANALYST_END: 오답 0 + 타임아웃 0 + 최소 6노드 클리어
    if wrong == 0 and timeouts == 0 and correct >= 6:
        candidates.append(ENDINGS["ANALYST_END"])

    # SURVIVOR_END: 최종 추적도 90% 이상으로 승리
    if trace >= 90:
        candidates.append(ENDINGS["SURVIVOR_END"])

    if not candidates:
        return None

    # 우선순위가 가장 높은 엔딩 반환
    return min(candidates, key=lambda e: e.priority)


def record_ending_unlock(
    save_data: dict[str, Any],
    ending_id: str,
) -> bool:
    """
    엔딩 해금을 세이브 데이터에 기록한다.

    Returns:
        True if this is a newly unlocked ending, False if already unlocked.
    """
    if ENDINGS_SAVE_KEY not in save_data or not isinstance(save_data[ENDINGS_SAVE_KEY], dict):
        save_data[ENDINGS_SAVE_KEY] = {"unlocked": []}

    unlocked: list[str] = save_data[ENDINGS_SAVE_KEY].get("unlocked", [])
    if not isinstance(unlocked, list):
        unlocked = []
        save_data[ENDINGS_SAVE_KEY]["unlocked"] = unlocked

    if ending_id in unlocked:
        return False

    unlocked.append(ending_id)
    return True


def get_endings_snapshot(save_data: dict[str, Any]) -> dict[str, Any]:
    """세이브 데이터에서 엔딩 해금 스냅샷을 반환한다."""
    raw = save_data.get(ENDINGS_SAVE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    unlocked = raw.get("unlocked", [])
    if not isinstance(unlocked, list):
        unlocked = []

    valid_ids = set(ENDINGS.keys())
    unlocked_clean = [eid for eid in unlocked if eid in valid_ids]

    return {
        "unlocked_ids": unlocked_clean,
        "unlocked_count": len(unlocked_clean),
        "total_count": len(ENDINGS),
        "unlocked_entries": [ENDINGS[eid] for eid in unlocked_clean],
    }
