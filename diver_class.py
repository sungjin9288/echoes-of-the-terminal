"""다이버 클래스 시스템 — ANALYST / GHOST / CRACKER 3종 클래스 정의 및 효과 적용."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DiverClass(str, Enum):
    """플레이어가 선택 가능한 다이버 클래스."""

    ANALYST = "ANALYST"
    GHOST = "GHOST"
    CRACKER = "CRACKER"


@dataclass(frozen=True)
class ClassProfile:
    """다이버 클래스의 메타데이터 및 설명."""

    diver_class: DiverClass
    name: str
    tagline: str  # 한 줄 설명
    passives: list[str]  # 수동 효과 목록 (표시용)
    active_name: str  # 액티브 스킬 이름
    active_desc: str  # 액티브 스킬 설명
    active_cooldown: int  # 스킬 사용 가능 노드 수 (0 = 런당 1회)


# ── 클래스 프로필 정의 ─────────────────────────────────────────────────────────

CLASS_PROFILES: dict[DiverClass, ClassProfile] = {
    DiverClass.ANALYST: ClassProfile(
        diver_class=DiverClass.ANALYST,
        name="애널리스트",
        tagline="로그 분석의 달인. 정보를 먼저 읽는 자가 살아남는다.",
        passives=[
            "노드 진입 시 target_keyword 글자 수 힌트 자동 공개",
            "오답 시 '틀린 이유' 카테고리 힌트 제공 (날짜/이름/사건 중 하나)",
            "HARD 이상 노드에서 penalty_rate 10% 감소",
        ],
        active_name="딥 스캔",
        active_desc="현재 로그에서 target_keyword의 첫 두 글자를 공개한다.",
        active_cooldown=0,  # 런당 1회
    ),
    DiverClass.GHOST: ClassProfile(
        diver_class=DiverClass.GHOST,
        name="고스트",
        tagline="흔적을 남기지 않는 침투자. 추적도는 적의 무기다.",
        passives=[
            "오답 1회당 추적도 상승량 20% 감소 (penalty_multiplier × 0.8)",
            "타임아웃 추적도 패널티 10% → 6%",
            "REST 노드 추적도 회복량 +15% 추가",
        ],
        active_name="페이드아웃",
        active_desc="현재 추적도를 즉시 15% 감소시킨다.",
        active_cooldown=0,  # 런당 1회
    ),
    DiverClass.CRACKER: ClassProfile(
        diver_class=DiverClass.CRACKER,
        name="크래커",
        tagline="한방에 부수는 해커. 위험할수록 강해진다.",
        passives=[
            "정답 시 다음 노드의 penalty_rate 5% 감소 (연속 클리어 스택)",
            "ELITE 노드 클리어 시 아티팩트 선택지 +1 추가 (4개)",
            "추적도 50% 이상일 때 analyze 정답 판정 1초 내 입력 보너스: 추적도 -3%",
        ],
        active_name="브루트 포스",
        active_desc="다음 analyze 명령어를 틀려도 추적도가 오르지 않는다 (1회).",
        active_cooldown=0,  # 런당 1회
    ),
}

# 메뉴 번호 → DiverClass 매핑
CLASS_MENU_MAP: dict[str, DiverClass] = {
    "1": DiverClass.ANALYST,
    "2": DiverClass.GHOST,
    "3": DiverClass.CRACKER,
}


def get_class_profile(diver_class: DiverClass) -> ClassProfile:
    """다이버 클래스의 프로필을 반환한다."""
    return CLASS_PROFILES[diver_class]


def apply_class_modifiers(
    diver_class: DiverClass,
    runtime: dict[str, Any],
    run_state: dict[str, Any],
) -> None:
    """
    클래스 패시브 효과를 런타임 설정과 런 상태에 적용한다.

    run_game_session 초기화 직후 한 번 호출한다.

    runtime 수정:
        - penalty_multiplier: GHOST는 × 0.8
        - timeout_penalty: GHOST는 6으로 고정
        - analyst_hint_active: 글자 수 힌트 여부
        - elite_artifact_bonus: CRACKER의 ELITE 아티팩트 +1

    run_state 수정:
        - analyst_hint_active: 노드별 글자 수 힌트
        - cracker_streak: 연속 클리어 스택 (페널티 감소 계수)
        - active_skill_available: 액티브 스킬 사용 가능 여부
    """
    if diver_class == DiverClass.GHOST:
        runtime["penalty_multiplier"] = runtime.get("penalty_multiplier", 1.0) * 0.8
        runtime["timeout_penalty"] = 6
        runtime["rest_heal_bonus_class"] = 15

    elif diver_class == DiverClass.ANALYST:
        run_state["analyst_hint_active"] = True  # 글자 수 힌트 활성화
        run_state["analyst_wrong_hint_active"] = True  # 오답 카테고리 힌트
        run_state["analyst_hard_penalty_reduction"] = True  # HARD+ 페널티 10% 감소

    elif diver_class == DiverClass.CRACKER:
        run_state["cracker_streak"] = 0  # 연속 클리어 스택
        runtime["elite_artifact_bonus"] = 1  # ELITE 아티팩트 선택지 +1

    # 모든 클래스 공통: 액티브 스킬 준비
    run_state["active_skill_available"] = True
    run_state["active_skill_used"] = False


def use_active_skill(
    diver_class: DiverClass,
    trace_level: int,
    runtime: dict[str, Any],
    run_state: dict[str, Any],
    scenario: dict[str, Any] | None = None,
) -> tuple[int, str | None]:
    """
    액티브 스킬을 발동한다.

    Returns:
        (updated_trace_level, hint_text)
        hint_text는 스킬 발동 후 표시할 추가 정보 (없으면 None)
    """
    if not run_state.get("active_skill_available") or run_state.get("active_skill_used"):
        return trace_level, None

    run_state["active_skill_used"] = True
    run_state["active_skill_available"] = False

    if diver_class == DiverClass.ANALYST:
        # 딥 스캔: 첫 두 글자 공개
        if scenario:
            kw = str(scenario.get("target_keyword", ""))
            hint = kw[:2] if len(kw) >= 2 else kw
            return trace_level, f"[DEEP SCAN] 키워드 첫 두 글자: '{hint}__'"
        return trace_level, None

    elif diver_class == DiverClass.GHOST:
        # 페이드아웃: 추적도 -15%
        fade_amount = min(15, trace_level)
        trace_level -= fade_amount
        return trace_level, f"[FADE OUT] 추적도 -{fade_amount}%  현재: {trace_level}%"

    elif diver_class == DiverClass.CRACKER:
        # 브루트 포스: 다음 오답 면역
        run_state["skip_next_penalty"] = True
        return trace_level, "[BRUTE FORCE] 다음 오답 페널티 면제 준비 완료."

    return trace_level, None


def on_node_clear(
    diver_class: DiverClass,
    trace_level: int,
    scenario: dict[str, Any],
    run_state: dict[str, Any],
) -> int:
    """
    노드 클리어 시 클래스 추가 효과를 적용하고 업데이트된 trace_level을 반환한다.
    """
    if diver_class == DiverClass.CRACKER:
        # 연속 클리어 스택 증가 (최대 5스택, 스택당 penalty_rate -5%)
        streak = run_state.get("cracker_streak", 0)
        run_state["cracker_streak"] = min(streak + 1, 5)

    return trace_level


def get_cracker_penalty_reduction(run_state: dict[str, Any]) -> float:
    """
    크래커의 연속 클리어 스택에 따른 페널티 감소 배율을 반환한다.

    스택 1당 5% 감소, 최대 5스택(25% 감소).
    배율은 1.0 기준 감소값 (예: 스택 2 → 0.9).
    """
    streak = run_state.get("cracker_streak", 0)
    reduction = streak * 0.05
    return max(0.75, 1.0 - reduction)
