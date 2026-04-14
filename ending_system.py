"""멀티 엔딩 시스템 — 런 결과 조건에 따른 8종 엔딩 판정."""

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


# ── 엔딩 정의 (8종) ──────────────────────────────────────────────────────────

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
    "SPEEDRUN_END": Ending(
        ending_id="SPEEDRUN_END",
        title="ZERO LATENCY",
        subtitle="완벽 속도 침투",
        flavor_text=(
            "오답 없음. 타임아웃 없음. ASC 10 이상.\n"
            "당신은 시스템을 분해하듯 통과했다.\n\n"
            "ARGOS는 당신을 추적조차 할 수 없었다.\n"
            "빛보다 빠른 침투자."
        ),
        color="bold #E0E0FF",
        border_style="#A0A0FF",
        priority=6,
    ),
    "CRACKER_END": Ending(
        ending_id="CRACKER_END",
        title="CHAIN REACTION",
        subtitle="연쇄 균열 돌파",
        flavor_text=(
            "CRACKER. 오답 없이 악몽을 통과했다.\n"
            "연속 클리어 스트릭이 극에 달했을 때,\n\n"
            "ARGOS의 방어선은 도미노처럼 무너졌다.\n"
            "한 번의 균열이 전체를 삼켰다."
        ),
        color="bold #FFA500",
        border_style="#FF8C00",
        priority=7,
    ),
    "VETERAN_END": Ending(
        ending_id="VETERAN_END",
        title="IRON WILL",
        subtitle="역경 속 철의 의지",
        flavor_text=(
            "세 번 틀렸다. 그래도 ASC 15 이상.\n"
            "당신은 완벽하지 않았다. 하지만 포기하지 않았다.\n\n"
            "ARGOS는 당신을 다 잡았다고 생각했다.\n"
            "그러나 베테랑은 실수로부터 배운다."
        ),
        color="bold #CD853F",
        border_style="#8B6914",
        priority=8,
    ),
    "MYSTERY_END": Ending(
        ending_id="MYSTERY_END",
        title="CHAOS PROTOCOL",
        subtitle="미지의 신호를 타고",
        flavor_text=(
            "당신은 ARGOS의 함정을 함정으로 되돌렸다.\n"
            "미스터리는 위험이 아닌 무기였다.\n\n"
            "ARGOS는 예측 불가능한 것을 두려워한다.\n"
            "그리고 당신은 그 예측 불가능함 그 자체였다."
        ),
        color="bold #FF8C00",
        border_style="#FF6600",
        priority=9,
    ),
    "COLLECTOR_END": Ending(
        ending_id="COLLECTOR_END",
        title="FULL LOADOUT",
        subtitle="완전 무장 침투",
        flavor_text=(
            "4개의 유물. 런 내내 당신의 손은 가득 찼다.\n"
            "각각의 유물이 ARGOS의 방벽에 균열을 냈다.\n\n"
            "수집가는 강하다. 당신은 그것을 증명했다."
        ),
        color="bold #9370DB",
        border_style="#7B68EE",
        priority=10,
    ),
    "COMEBACK_END": Ending(
        ending_id="COMEBACK_END",
        title="LAST SIGNAL",
        subtitle="벼랑 끝 역전",
        flavor_text=(
            "추적도 95%. 한 발짝만 더 틀렸어도 끝이었다.\n"
            "그러나 당신은 그 상황에서 역전했다.\n\n"
            "ARGOS는 승리를 확신했다.\n"
            "그것이 ARGOS의 마지막 오류였다."
        ),
        color="bold #DC143C",
        border_style="#B22222",
        priority=11,
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
            "trace_final": int,              # 런 종료 시 추적도 (%)
            "wrong_analyzes": int,            # 오답 횟수
            "timeout_events": int,            # 타임아웃 횟수
            "ascension_level": int,           # 플레이한 각성 레벨
            "correct_answers": int,           # 클리어한 노드 수
            "class_key": str,                 # 다이버 클래스 (ANALYST/GHOST/CRACKER)
            "cleared_difficulties": list[str], # 클리어한 노드 난이도 목록
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
    class_key = str(run_result.get("class_key", "")).upper()
    cleared_difficulties: list[str] = list(run_result.get("cleared_difficulties", []))
    mystery_engaged = int(run_result.get("mystery_engaged", 0))
    mystery_good = int(run_result.get("mystery_good", 0))
    artifacts_held = int(run_result.get("artifacts_held", 0))
    max_trace_reached = int(run_result.get("max_trace_reached", 0))

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

    # SPEEDRUN_END: 오답 0 + 타임아웃 0 + ASC 10 이상
    if wrong == 0 and timeouts == 0 and asc >= 10:
        candidates.append(ENDINGS["SPEEDRUN_END"])

    # CRACKER_END: CRACKER 클래스 + 오답 0 + NIGHTMARE 노드 포함 클리어
    _has_nightmare = any(d.strip().upper() == "NIGHTMARE" for d in cleared_difficulties)
    if class_key == "CRACKER" and wrong == 0 and _has_nightmare:
        candidates.append(ENDINGS["CRACKER_END"])

    # VETERAN_END: ASC 15 이상 + 오답 3회 이상으로 승리
    if asc >= 15 and wrong >= 3:
        candidates.append(ENDINGS["VETERAN_END"])

    # MYSTERY_END: MYSTERY 노드 개입 3회 이상 + 모든 개입이 성공
    if mystery_engaged >= 3 and mystery_engaged == mystery_good:
        candidates.append(ENDINGS["MYSTERY_END"])

    # COLLECTOR_END: 런 중 아티팩트 4종 이상 보유하고 승리
    if artifacts_held >= 4:
        candidates.append(ENDINGS["COLLECTOR_END"])

    # COMEBACK_END: 런 중 최대 추적도 95% 이상 + 최종 추적도 60% 이하로 역전 승리
    if max_trace_reached >= 95 and trace <= 60:
        candidates.append(ENDINGS["COMEBACK_END"])

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
