"""전투 노드 커맨드 핸들러 및 페널티 계산 모듈.

_run_combat_node()의 커맨드 분기 로직을 개별 함수로 분리한다.
각 핸들러는 (action, trace_level, backtrack_used, difficulty) 형태의
CommandResult 튜플을 반환한다.

    action:
        "continue"  — 루프 계속
        "cleared"   — 노드 클리어, difficulty 포함
        "death"     — 사망 처리
"""

import random
import time
from typing import Any

from diver_class import DiverClass, get_class_profile, get_cracker_penalty_reduction, use_active_skill
from route_map import NodeType
from constants import (
    CRACKER_SPEED_BONUS_AMOUNT,
    CRACKER_SPEED_BONUS_THRESHOLD,
    CRACKER_SPEED_BONUS_TIME,
    ELITE_PENALTY_MULT,
    TRACE_MAX,
)
from ui_renderer import console

# (action, trace_level, backtrack_used, difficulty)
CommandResult = tuple[str, int, bool, str | None]

_CONTINUE: str = "continue"
_CLEARED: str = "cleared"
_DEATH: str = "death"


# ── 페널티 계산 ────────────────────────────────────────────────────────────────

def calculate_analyze_penalty(
    base_penalty: int,
    runtime: dict[str, Any],
    node_type: NodeType,
    diver_class: "DiverClass | None",
    run_state: dict[str, Any],
    scenario_theme: str,
    scenario_difficulty: str = "",
) -> tuple[int, int, bool, bool]:
    """
    오답 시 적용할 추적도 페널티를 계산한다.

    Returns:
        (applied_penalty, raw_penalty, memory_echo_applied, boss_cap_applied)
    """
    ascension_flat = int(runtime.get("ascension_penalty_flat", 0))
    safe_base = max(1, int(base_penalty) + ascension_flat)
    penalty_mult = float(runtime.get("penalty_multiplier", 1.0))

    elite_mult = 1.0
    if node_type == NodeType.ELITE:
        elite_mult = min(
            ELITE_PENALTY_MULT,
            runtime.get("elite_penalty_cap", ELITE_PENALTY_MULT),
        )

    cracker_mult = (
        get_cracker_penalty_reduction(run_state)
        if diver_class == DiverClass.CRACKER
        else 1.0
    )

    analyst_mult = 1.0
    if run_state.get("analyst_hard_penalty_reduction"):
        if scenario_difficulty.strip().upper() in ("HARD", "NIGHTMARE"):
            analyst_mult = 0.9

    memory_echo_applied = False
    memory_echo_mult = 1.0
    if run_state.get("memory_echo_active"):
        theme = scenario_theme.strip()
        cleared_themes = run_state.get("cleared_themes")
        if isinstance(cleared_themes, set) and theme and theme in cleared_themes:
            # echo_amplifier 아티팩트: 감쇠율 강화 (기본 0.8 → override 가능)
            memory_echo_mult = float(runtime.get("memory_echo_mult_override", 0.8))
            memory_echo_applied = True

    # trace_shield 아티팩트: 현재 추적도 70% 이상 구간에서 패널티 20% 감소
    trace_shield_mult = 1.0
    if run_state.get("trace_shield_active"):
        current_trace = int(run_state.get("current_trace", 0))
        if current_trace >= 70:
            trace_shield_mult = 0.8

    # adaptive_shield 퍼크: 추적도 50% 이상 구간에서 패널티 10% 추가 감소
    adaptive_shield_mult = 1.0
    if runtime.get("adaptive_shield_active"):
        current_trace = int(run_state.get("current_trace", 0))
        if current_trace >= 50:
            adaptive_shield_mult = 0.9

    raw_penalty = max(
        1,
        int(
            safe_base
            * penalty_mult
            * elite_mult
            * cracker_mult
            * analyst_mult
            * memory_echo_mult
            * trace_shield_mult
            * adaptive_shield_mult
        ),
    )

    if node_type == NodeType.BOSS:
        boss_mult = max(1.0, float(runtime.get("ascension_boss_penalty_mult", 1.0)))
        raw_penalty = max(1, int(raw_penalty * boss_mult))

    applied_penalty = raw_penalty
    boss_cap_applied = False
    if node_type == NodeType.BOSS and runtime.get("boss_penalty_cap") is not None:
        cap = max(1, int(runtime["boss_penalty_cap"]))
        if applied_penalty > cap:
            applied_penalty = cap
            boss_cap_applied = True

    return applied_penalty, raw_penalty, memory_echo_applied, boss_cap_applied


# ── 커맨드 핸들러 ──────────────────────────────────────────────────────────────

def handle_help(active_skill_name: str) -> None:
    """help 명령어: 사용 가능한 명령 목록 출력."""
    from ui_renderer import render_help_panel
    render_help_panel(active_skill_name=active_skill_name)


def handle_ls(scenario: dict[str, Any], node_type: NodeType) -> None:
    """ls 명령어: 현재 노드 정보 출력."""
    boss_tag = " [BOSS]" if scenario.get("is_boss") else ""
    elite_tag = " [ELITE]" if node_type == NodeType.ELITE else ""
    console.print(
        f"[bold green]node_{scenario['node_id']}[/bold green] "
        f"theme={scenario['theme']} difficulty={scenario['difficulty']}"
        f"{boss_tag}{elite_tag}"
    )


def handle_cat_log(
    scenario: dict[str, Any],
    run_state: dict[str, Any],
    echo_cache_used: bool,
    timer_has_fired: bool,
    extend_timeout_fn: "Any",
) -> bool:
    """
    cat log 명령어: 원본 로그 재출력 및 echo_cache 처리.

    Returns:
        업데이트된 echo_cache_used 값
    """
    from ui_renderer import type_text
    type_text(scenario["text_log"], style="white", delay=0.02)
    if run_state.get("echo_cache_active") and not echo_cache_used and not timer_has_fired:
        extend_timeout_fn(2)
        echo_cache_used = True
        console.print(
            "[bold magenta][ECHO CACHE] 타이머 2초 정지 효과가 적용되었습니다.[/bold magenta]"
        )
    return echo_cache_used


def handle_skill(
    diver_class: "DiverClass | None",
    trace_level: int,
    runtime: dict[str, Any],
    run_state: dict[str, Any],
    scenario: dict[str, Any],
) -> int:
    """
    skill 명령어: 클래스 액티브 스킬 실행.

    Returns:
        업데이트된 trace_level
    """
    if diver_class is None:
        console.print("[bold yellow]클래스가 없습니다. 액티브 스킬을 사용할 수 없습니다.[/bold yellow]")
        return trace_level
    if not run_state.get("active_skill_available") or run_state.get("active_skill_used"):
        console.print("[bold yellow]액티브 스킬은 이미 사용했습니다 (런당 1회).[/bold yellow]")
        return trace_level
    trace_level, hint = use_active_skill(diver_class, trace_level, runtime, run_state, scenario)
    if hint:
        console.print(f"[bold #00FFFF]{hint}[/bold #00FFFF]")
    return trace_level


def handle_analyze(
    command_raw: str,
    scenario: dict[str, Any],
    trace_level: int,
    backtrack_used: bool,
    node_type: NodeType,
    diver_class: "DiverClass | None",
    runtime: dict[str, Any],
    run_state: dict[str, Any],
    perks: dict[str, bool],
    last_prompt_time: float,
    cancel_timer_fn: "Any",
    handle_death_fn: "Any",
    extend_timeout_fn: "Any | None" = None,
) -> CommandResult:
    """
    analyze [키워드] 명령어: 정답/오답 판정 및 페널티 처리.

    Returns:
        CommandResult (action, trace_level, backtrack_used, difficulty)
    """
    from main import print_argos_message
    parts = command_raw.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        console.print("[bold yellow]사용법: analyze [키워드][/bold yellow]")
        return _CONTINUE, trace_level, backtrack_used, None

    s_user = parts[1].strip().lower()
    s_target = str(scenario["target_keyword"]).strip().lower()

    is_correct = s_user == s_target
    quantum_activated = False
    if not is_correct and run_state.get("quantum_key_active"):
        is_correct = True
        quantum_activated = True
        run_state["quantum_key_active"] = False

    if is_correct:
        cancel_timer_fn()
        if quantum_activated:
            console.print("[bold magenta][QUANTUM KEY] 양자 해킹 성공. 추적도 유지.[/bold magenta]")

        # cascade_core: 정답 스트릭 카운트 증가, 3연속 시 다음 오답 면제 활성
        if run_state.get("cascade_core_active"):
            streak = int(run_state.get("cascade_streak", 0)) + 1
            run_state["cascade_streak"] = streak
            if streak >= 3 and not run_state.get("cascade_used"):
                run_state["skip_next_penalty"] = True
                run_state["cascade_used"] = True
                run_state["cascade_streak"] = 0
                console.print(
                    "[bold #00FFFF][CASCADE CORE] 3연속 정답 달성! 다음 오답 페널티 면제.[/bold #00FFFF]"
                )

        if (
            diver_class == DiverClass.CRACKER
            and trace_level >= CRACKER_SPEED_BONUS_THRESHOLD
            and (time.monotonic() - last_prompt_time) <= CRACKER_SPEED_BONUS_TIME
        ):
            bonus = min(CRACKER_SPEED_BONUS_AMOUNT, trace_level)
            trace_level -= bonus
            console.print(
                f"[bold magenta][CRACKER] 속공 보너스! 추적도 -{bonus}%  "
                f"현재: {trace_level}%[/bold magenta]"
            )

        console.print("[bold green]해킹 성공. 다음 노드로 이동합니다.[/bold green]")
        print_argos_message("node_clear")
        return _CLEARED, trace_level, backtrack_used, scenario["difficulty"]

    # 오답 처리
    run_state["wrong_analyzes"] = int(run_state.get("wrong_analyzes", 0)) + 1

    # cascade_core: 3연속 정답 스트릭 초기화
    if run_state.get("cascade_core_active"):
        run_state["cascade_streak"] = 0

    # pulse_barrier: 오답 직후 다음 노드 +5초 대기
    if run_state.get("pulse_barrier_active"):
        run_state["pending_time_bonus"] = (
            run_state.get("pending_time_bonus", 0) + 5
        )

    if run_state.get("skip_next_penalty"):
        run_state["skip_next_penalty"] = False
        console.print("[bold #00FFFF][MISS SHIELD] 오답 면역 발동. 추적도 유지.[/bold #00FFFF]")
        return _CONTINUE, trace_level, backtrack_used, None

    if diver_class == DiverClass.ANALYST and run_state.get("analyst_wrong_hint_active"):
        hint_category = random.choice(["날짜", "이름", "사건/행동"])
        console.print(f"[bold cyan][ANALYST] 키워드 카테고리 힌트: '{hint_category}'[/bold cyan]")

    # swift_analysis 퍼크: 런당 첫 오답에 한해 패널티 50% 감소
    swift_half = False
    if run_state.get("swift_analysis_ready"):
        run_state["swift_analysis_ready"] = False
        swift_half = True

    scenario_difficulty = str(scenario.get("difficulty", ""))
    base_penalty = int(scenario["penalty_rate"])
    display_base = base_penalty + int(runtime.get("ascension_penalty_flat", 0))

    applied_penalty, raw_penalty, memory_echo_applied, boss_cap_applied = calculate_analyze_penalty(
        base_penalty=base_penalty,
        runtime=runtime,
        node_type=node_type,
        diver_class=diver_class,
        run_state=run_state,
        scenario_theme=str(scenario.get("theme", "")),
        scenario_difficulty=scenario_difficulty,
    )

    if swift_half:
        applied_penalty = max(1, applied_penalty // 2)
        console.print("[bold #00FFFF][SWIFT ANALYSIS] 첫 오답 패널티 50% 감소.[/bold #00FFFF]")
    if memory_echo_applied:
        console.print("[bold magenta][MEMORY ECHO] 반복 테마 감쇠: 페널티 20% 감소.[/bold magenta]")
    if boss_cap_applied:
        console.print(
            f"[bold magenta][NULL PROTOCOL] 보스 페널티 상한 적용: "
            f"{raw_penalty}% -> {applied_penalty}%[/bold magenta]"
        )

    trace_level += applied_penalty
    console.print("[bold white on red]접근 거부. 추적도 상승.[/bold white on red]")
    if applied_penalty != display_base:
        console.print(
            f"[bold white]TRACE +{applied_penalty}% (기본 {display_base}%) -> {trace_level}%[/bold white]"
        )
    else:
        console.print(f"[bold white]TRACE +{applied_penalty}% -> {trace_level}%[/bold white]")

    print_argos_message("wrong_analyze")

    if trace_level >= TRACE_MAX:
        trace_level, backtrack_used, survived = handle_death_fn(trace_level, backtrack_used)
        if not survived:
            return _DEATH, trace_level, backtrack_used, None

    # chrono_anchor: 오답 후 생존 시 제한시간 즉시 복구
    restore_secs = int(run_state.get("on_wrong_time_restore", 0))
    if restore_secs > 0 and extend_timeout_fn is not None:
        extend_timeout_fn(restore_secs)
        console.print(
            f"[bold #00FFFF][CHRONO ANCHOR] 제한시간 +{restore_secs}초 복구[/bold #00FFFF]"
        )

    return _CONTINUE, trace_level, backtrack_used, None
