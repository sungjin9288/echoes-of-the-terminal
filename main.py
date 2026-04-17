"""Echoes of the Terminal 메인 실행 파일 (루트 맵 + 아티팩트 시스템 통합판)."""

import math
import random
import re
import threading
import time
from typing import Any

from rich.prompt import Prompt
from rich.table import Table

from achievement_system import evaluate_achievements
from artifact_system import Artifact, apply_artifact_effect, draw_artifacts
from diver_class import (
    DiverClass,
    apply_class_modifiers,
    get_cracker_penalty_reduction,
    on_node_clear,
    use_active_skill,
)
from constants import (
    ELITE_PENALTY_MULT,
    MAX_NODES_PER_RUN,
    MID_SHOP_BUFFER_COST,
    MID_SHOP_TRACE_COST,
    MID_SHOP_TRACE_HEAL,
    REST_HEAL_AMOUNT,
    TIME_LIMIT_DEFAULT,
    TIME_LIMIT_EXTENDED,
    TIMEOUT_PENALTY,
    TRACE_MAX,
)
from daily_challenge import (
    calculate_daily_score,
    get_daily_seed,
    get_daily_state,
    get_today_str,
    has_played_today,
    record_daily_result,
    select_daily_scenarios,
)
from combat_commands import (
    CommandResult,
    calculate_analyze_penalty as _calculate_analyze_penalty_impl,
)
from combat_orchestration import (
    _apply_asc20_boss_phase_override,
    _handle_death_check,
    _offer_artifact,
    run_combat_node as _run_combat_node,
    run_mid_run_shop as _run_mid_run_shop,
    run_mystery_node as _run_mystery_node,
)
from data_loader import load_boss_phase_pack, load_scenarios
from mutator_system import apply_glitch_masking
from mystery_system import (
    apply_mystery_outcome,
    pick_mystery,
    resolve_mystery_outcome,
)
from lobby import (
    run_lobby_loop as _run_lobby_loop_impl,
    select_diver_class as _select_diver_class,
)
from progression_system import (
    ASCENSION_MAX_LEVEL,
    apply_ascension_reward_multiplier as _apply_ascension_reward_multiplier,
    get_ascension_profile,
    load_save,
    save_game,
)
from route_map import (
    NodeType,
    build_route_choices,
    get_desc,
    get_label,
    get_style,
)
from ui_renderer import (
    console,
    print_argos_message,
    render_achievement_unlocks,
    render_artifact_hud,
    render_artifact_selection,
    render_daily_challenge_intro,
    render_daily_history,
    render_daily_result,
    render_info_panel,
    render_logo,
    render_route_choice,
    type_text,
    wait_for_enter as _wait_for_enter_ui,
)


def _wait_for_enter(message: str = "계속하려면 Enter를 누르세요") -> None:
    """화면 전환 전 사용자의 확인 입력을 받는다."""
    _wait_for_enter_ui(message)


def _build_runtime_modifiers(perks: dict[str, bool]) -> dict[str, Any]:
    """
    보유 특성(perks)을 게임 루프용 런타임 설정으로 변환한다.

    Returns:
        penalty_multiplier: 오답 페널티 계수 (기본 1.0, 특성 보유 시 0.85)
        time_limit_seconds: 제한 시간 (기본 30, 특성 보유 시 40)
        glitch_word_count: Hard 글리치 치환 개수 (기본 None=2~3 랜덤, 특성 보유 시 1)
        timeout_penalty: 타임아웃 추적도 패널티 (기본 TIMEOUT_PENALTY)
        elite_penalty_cap: ELITE 노드 페널티 배율 상한 (기본 1.5, dual_core 보유 시 1.2)
    """
    base_timeout = TIMEOUT_PENALTY
    if perks.get("trace_dampener", False):
        base_timeout = max(1, int(base_timeout * 0.9))

    return {
        "penalty_multiplier": 0.85 if perks.get("penalty_reduction", False) else 1.0,
        "time_limit_seconds": TIME_LIMIT_EXTENDED if perks.get("time_extension", False) else TIME_LIMIT_DEFAULT,
        "glitch_word_count": 1 if perks.get("glitch_filter", False) else None,
        "timeout_penalty": base_timeout,
        "elite_penalty_cap": 1.35 if perks.get("elite_shield", False) else ELITE_PENALTY_MULT,
        "node_scanner_active": bool(perks.get("node_scanner", False)),
        "frag_reward_multiplier": 1.2 if perks.get("fragment_amplifier", False) else 1.0,
        "on_correct_time_bonus": 3 if perks.get("keyword_echo", False) else 0,
        # v9.0 신규 퍼크
        "adaptive_shield_active": bool(perks.get("adaptive_shield", False)),
        "start_frag_bonus": 50 if perks.get("data_recovery", False) else 0,
        "swift_analysis_active": bool(perks.get("swift_analysis", False)),
    }


def _apply_ascension_modifiers(
    ascension_level: int,
    runtime: dict[str, Any],
) -> int:
    """
    각성 레벨에 따른 런타임 난이도 보정을 적용하고 시작 추적도를 반환한다.

    상세 값은 progression_system.ASCENSION_TABLE을 단일 기준으로 사용한다.
    """
    profile = get_ascension_profile(ascension_level)
    runtime["ascension_level"] = profile["level"]
    runtime["ascension_penalty_flat"] = profile["penalty_flat"]
    runtime["ascension_force_easy_glitch"] = profile["force_easy_glitch"]
    runtime["ascension_shop_cost_mult"] = profile["shop_cost_mult"]
    runtime["ascension_reward_mult"] = profile["reward_mult"]
    runtime["ascension_boss_penalty_mult"] = profile["boss_penalty_mult"]
    runtime["ascension_boss_phases"] = profile["boss_phases"]
    runtime["ascension_boss_phase_time_delta"] = profile["boss_phase_time_delta"]
    runtime["ascension_boss_phase_penalty_step"] = profile["boss_phase_penalty_step"]
    runtime["ascension_boss_block_cat_log_from_phase"] = profile["boss_block_cat_log_from_phase"]
    runtime["ascension_boss_block_skill_from_phase"] = profile["boss_block_skill_from_phase"]
    runtime["ascension_boss_command_violation_penalty"] = profile["boss_command_violation_penalty"]
    runtime["ascension_boss_fake_keyword_count"] = profile["boss_fake_keyword_count"]
    runtime["ascension_route_elite_chance"] = profile["route_elite_chance"]
    runtime["ascension_route_relief_decay_chance"] = profile["route_relief_decay_chance"]
    runtime["ascension_route_min_elite_choices"] = profile["route_min_elite_choices"]
    runtime["time_limit_seconds"] = max(
        8,
        runtime.get("time_limit_seconds", TIME_LIMIT_DEFAULT)
        + int(profile["time_limit_delta"]),
    )
    runtime["timeout_penalty"] = max(
        1,
        runtime.get("timeout_penalty", TIMEOUT_PENALTY)
        + int(profile["timeout_penalty_delta"]),
    )
    return int(profile["start_trace"])


def _get_mid_shop_costs(runtime: dict[str, Any]) -> tuple[int, int, float]:
    """현재 런타임(Ascension 포함)에 맞춘 중간 상점 비용을 계산한다."""
    mult = max(1.0, float(runtime.get("ascension_shop_cost_mult", 1.0)))
    trace_cost = max(1, math.ceil(MID_SHOP_TRACE_COST * mult))
    buffer_cost = max(1, math.ceil(MID_SHOP_BUFFER_COST * mult))
    return trace_cost, buffer_cost, mult


def _mutate_route_choices_for_ascension(
    route_choices: list[tuple[NodeType, NodeType]],
    runtime: dict[str, Any],
) -> tuple[list[tuple[NodeType, NodeType]], dict[str, int]]:
    """
    Ascension 고레벨에서 경로 선택지를 변이해 전투 밀도를 높인다.

    Returns:
        mutated_choices, stats
        stats:
            elite_choices: 전체 분기 선택지 중 ELITE 개수
            forced_elite: 최소 ELITE 보장을 위해 강제 치환된 횟수
            mutated_to_elite: 확률 변이로 NORMAL -> ELITE 치환된 횟수
            relief_decay: REST/SHOP -> NORMAL 치환된 횟수
    """
    elite_chance = max(0.0, float(runtime.get("ascension_route_elite_chance", 0.0)))
    relief_decay_chance = max(
        0.0,
        float(runtime.get("ascension_route_relief_decay_chance", 0.0)),
    )
    min_elite = max(0, int(runtime.get("ascension_route_min_elite_choices", 0)))

    def _mutate_one(node_type: NodeType) -> tuple[NodeType, int, int]:
        # return: (node_type, mutated_to_elite, relief_decay)
        if node_type == NodeType.NORMAL and elite_chance > 0 and random.random() < elite_chance:
            return NodeType.ELITE, 1, 0
        if (
            node_type in (NodeType.SHOP, NodeType.REST)
            and relief_decay_chance > 0
            and random.random() < relief_decay_chance
        ):
            return NodeType.NORMAL, 0, 1
        return node_type, 0, 0

    mutated: list[tuple[NodeType, NodeType]] = []
    mutated_to_elite = 0
    relief_decay = 0
    for left, right in route_choices:
        new_left, left_to_elite, left_decay = _mutate_one(left)
        new_right, right_to_elite, right_decay = _mutate_one(right)
        mutated_to_elite += left_to_elite + right_to_elite
        relief_decay += left_decay + right_decay
        mutated.append((new_left, new_right))

    # 최소 ELITE 선택지 개수 보장
    elite_choices = sum(
        1
        for left, right in mutated
        for node in (left, right)
        if node == NodeType.ELITE
    )
    forced_elite = 0
    if elite_choices < min_elite:
        need = min_elite - elite_choices
        for idx, (left, right) in enumerate(mutated):
            if need <= 0:
                break
            new_left, new_right = left, right
            if new_left == NodeType.NORMAL:
                new_left = NodeType.ELITE
                need -= 1
                forced_elite += 1
            if need > 0 and new_right == NodeType.NORMAL:
                new_right = NodeType.ELITE
                need -= 1
                forced_elite += 1
            mutated[idx] = (new_left, new_right)

    elite_choices = sum(
        1
        for left, right in mutated
        for node in (left, right)
        if node == NodeType.ELITE
    )
    return mutated, {
        "elite_choices": elite_choices,
        "forced_elite": forced_elite,
        "mutated_to_elite": mutated_to_elite,
        "relief_decay": relief_decay,
    }


def _get_boss_phase_runtime(
    runtime: dict[str, Any],
    phase_index: int,
) -> dict[str, Any]:
    """
    보스 멀티 페이즈 전투용 런타임 설정을 생성한다.

    - 페이즈가 올라갈수록 보스 페널티 배율을 추가 증폭한다.
    - 페이즈가 올라갈수록 제한 시간을 단계적으로 줄인다.
    """
    total_phases = max(1, int(runtime.get("ascension_boss_phases", 1)))
    safe_phase_index = max(1, min(total_phases, int(phase_index)))

    phase_runtime = dict(runtime)
    phase_runtime["boss_phase_index"] = safe_phase_index
    phase_runtime["boss_phase_total"] = total_phases

    if total_phases <= 1:
        return phase_runtime

    base_boss_mult = max(1.0, float(runtime.get("ascension_boss_penalty_mult", 1.0)))
    phase_penalty_step = max(0.0, float(runtime.get("ascension_boss_phase_penalty_step", 0.0)))
    phase_bonus_mult = 1.0 + (safe_phase_index - 1) * phase_penalty_step
    phase_runtime["ascension_boss_penalty_mult"] = base_boss_mult * phase_bonus_mult

    base_time_limit = int(runtime.get("time_limit_seconds", TIME_LIMIT_DEFAULT))
    phase_time_delta = int(runtime.get("ascension_boss_phase_time_delta", 0))
    phase_runtime["time_limit_seconds"] = max(
        8,
        base_time_limit + (safe_phase_index - 1) * phase_time_delta,
    )
    return phase_runtime
















def _select_combat_scenarios(
    scenarios: list[dict[str, Any]], count: int
) -> list[dict[str, Any]]:
    """NORMAL/ELITE 노드에 사용할 시나리오를 샘플링한다."""
    normal_pool = [s for s in scenarios if not s.get("is_boss", False)]
    random.shuffle(normal_pool)
    return normal_pool[:count]


def _select_boss_scenario(
    scenarios: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """BOSS 노드에 사용할 시나리오를 샘플링한다."""
    boss_pool = [s for s in scenarios if s.get("is_boss", False)]
    return random.choice(boss_pool) if boss_pool else None






def _calculate_analyze_penalty(
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

    combat_commands.calculate_analyze_penalty의 re-export 래퍼.
    기존 테스트에서 main._calculate_analyze_penalty를 직접 참조하므로 유지.
    """
    return _calculate_analyze_penalty_impl(
        base_penalty=base_penalty,
        runtime=runtime,
        node_type=node_type,
        diver_class=diver_class,
        run_state=run_state,
        scenario_theme=scenario_theme,
        scenario_difficulty=scenario_difficulty,
    )







def _initialize_run_state(
    perks: dict[str, bool],
    diver_class: "DiverClass | None",
    ascension_level: int,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """
    런 시작에 필요한 runtime, run_state, 초기 trace_level을 생성한다.

    Returns:
        (runtime, run_state, trace_level)
    """
    run_state: dict[str, Any] = {
        "skip_next_penalty": False,
        "cleared_themes": set(),
        "wrong_analyzes": 0,
        "timeout_events": 0,
        "mystery_frags_gained": 0,
    }
    runtime = _build_runtime_modifiers(perks)
    trace_level = _apply_ascension_modifiers(ascension_level, runtime)

    # swift_analysis: 런 시작 시 첫 오답 패널티 감소 슬롯 초기화
    if runtime.get("swift_analysis_active"):
        run_state["swift_analysis_ready"] = True

    if ascension_level > 0:
        console.print(
            f"[bold yellow][ASCENSION {ascension_level}] 난이도 보정 적용 "
            f"(시작 TRACE: {trace_level}%)[/bold yellow]"
        )
    boss_phases = max(1, int(runtime.get("ascension_boss_phases", 1)))
    if boss_phases > 1:
        console.print(
            f"[bold yellow][ASCENSION BOSS] 보스 멀티 페이즈 활성: {boss_phases}단계[/bold yellow]"
        )

    if diver_class is not None:
        apply_class_modifiers(diver_class, runtime, run_state)

    return runtime, run_state, trace_level


def _load_combat_pools(
    ascension_level: int,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[int, list[dict[str, str]]]] | None:
    """
    시나리오 파일에서 전투 풀, 보스, 보스 페이즈팩을 로드한다.

    Returns:
        (combat_pool, boss_scenario, boss_phase_pack) 또는 실패 시 None
    """
    try:
        scenarios = load_scenarios("scenarios.json")
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]시나리오 로드 실패: {exc}[/bold red]")
        return None

    combat_pool = _select_combat_scenarios(scenarios, MAX_NODES_PER_RUN)
    boss_scenario = _select_boss_scenario(scenarios)

    if not combat_pool:
        console.print("[bold red]시나리오가 비어 있어 런을 시작할 수 없습니다.[/bold red]")
        return None

    boss_phase_pack: dict[int, list[dict[str, str]]] = {}
    if ascension_level >= 20:
        try:
            boss_phase_pack = load_boss_phase_pack("boss_phase_pack.json")
            console.print(
                f"[bold yellow][ASCENSION DATA] 보스 페이즈 데이터팩 로드: "
                f"{len(boss_phase_pack)}개 보스[/bold yellow]"
            )
        except (FileNotFoundError, ValueError) as exc:
            console.print(
                f"[bold yellow][ASCENSION DATA] 보스 페이즈 데이터팩 로드 실패: {exc}[/bold yellow]"
            )

    return combat_pool, boss_scenario, boss_phase_pack


def _build_run_stats(
    run_state: dict[str, Any],
    trace_level: int,
    max_trace_reached: int,
    acquired_artifacts: list[Artifact],
    is_victory: bool = False,
) -> dict[str, Any]:
    """런 종료 시점의 통계 딕셔너리를 생성한다. (shutdown·victory 공통)"""
    # system_purge: 승리 시 최종 추적도를 0으로 기록 (엔딩 판정 반영)
    trace_final = trace_level
    if is_victory and run_state.get("clear_trace_to_zero"):
        trace_final = 0

    return {
        "wrong_analyzes": run_state.get("wrong_analyzes", 0),
        "timeout_events": run_state.get("timeout_events", 0),
        "trace_final": trace_final,
        "skill_used": bool(run_state.get("active_skill_used", False)),
        "mystery_engaged": run_state.get("mystery_engaged", 0),
        "mystery_good": run_state.get("mystery_good", 0),
        "mystery_skipped": run_state.get("mystery_skipped", 0),
        "artifacts_held": len(acquired_artifacts),
        "max_trace_reached": max_trace_reached,
        "cascade_triggered": bool(run_state.get("cascade_used", False)),
        "void_scanner_used": bool(run_state.get("void_scanner_used", False)),
        "mystery_frags_gained": int(run_state.get("mystery_frags_gained", 0)),
    }


def run_game_session(
    perks: dict[str, bool],
    save_data: dict[str, Any],
    diver_class: DiverClass | None = None,
    ascension_level: int = 0,
) -> tuple[int, bool, str, list[str], dict[str, int]]:
    """
    단일 런 (8 포지션: 7 regular + 1 boss)을 실행한다.

    Route Map 구조:
    - Position 0: 항상 NORMAL
    - Position 1-6: 이전 노드 클리어 후 플레이어가 A/B 경로를 선택
    - Position 7: 항상 BOSS

    Artifact 획득:
    - ELITE 노드 클리어 시: 3개 후보 중 1개 선택 (CRACKER는 4개)
    - BOSS 노드 클리어 시: 2개 후보 중 1개 선택

    Args:
        perks: 플레이어 보유 특성
        save_data: 세이브 데이터 (중간 상점 구매 시 직접 수정됨)
        diver_class: 선택된 다이버 클래스 (None이면 클래스 없이 진행)
        ascension_level: 적용할 각성 레벨 (0~20)

    Returns:
        tuple[int, bool, str, list[str], dict[str, int]]:
            - correct_answers: 전투 클리어 횟수
            - is_victory: 승리 여부
            - result: "victory" | "shutdown" | "aborted"
            - node_difficulties_cleared: 클리어된 전투 노드 난이도 목록
            - run_stats: {"wrong_analyzes": int, "timeout_events": int}
    """
    runtime, run_state, trace_level = _initialize_run_state(
        perks=perks,
        diver_class=diver_class,
        ascension_level=ascension_level,
    )
    acquired_artifacts: list[Artifact] = []
    run_seed = random.randint(1, 2**31 - 1)

    result = _load_combat_pools(ascension_level=ascension_level)
    if result is None:
        return 0, False, "aborted", [], {"wrong_analyzes": 0, "timeout_events": 0}
    combat_pool, boss_scenario, boss_phase_pack = result

    route_choices = build_route_choices(MAX_NODES_PER_RUN - 1)
    route_choices, route_mutation_stats = _mutate_route_choices_for_ascension(
        route_choices,
        runtime,
    )
    if ascension_level >= 12:
        console.print(
            "[bold yellow][ASCENSION ROUTE] "
            f"ELITE 선택지 {route_mutation_stats['elite_choices']}개 "
            f"(확률 변이 {route_mutation_stats['mutated_to_elite']}, "
            f"강제 보정 {route_mutation_stats['forced_elite']}, "
            f"휴식/상점 약화 {route_mutation_stats['relief_decay']})[/bold yellow]"
        )
    # data_recovery: 런 시작 시 데이터 조각 +50 즉시 지급
    start_frag = int(runtime.get("start_frag_bonus", 0))
    if start_frag > 0:
        save_data["data_fragments"] += start_frag
        console.print(
            f"[bold green][DATA RECOVERY] 런 시작 보너스: 데이터 조각 +{start_frag} 획득[/bold green]"
        )

    total_positions = MAX_NODES_PER_RUN + 1  # 8 (regular 7 + boss 1)
    correct_answers = 0
    node_difficulties_cleared: list[str] = []
    backtrack_used = False
    max_trace_reached = trace_level  # 런 중 최대 추적도 기록

    current_node_type = NodeType.NORMAL
    combat_pool_idx = 0

    for position in range(total_positions):
        ntype = NodeType.BOSS if position == MAX_NODES_PER_RUN else current_node_type
        if trace_level > max_trace_reached:
            max_trace_reached = trace_level
        # trace_shield 아티팩트용 현재 추적도 동기화
        run_state["current_trace"] = trace_level

        # ── 포지션 시작: pulse_barrier 오답 후 타임 보너스 적용 ──────────────
        pending_bonus = int(run_state.get("pending_time_bonus", 0))
        if pending_bonus > 0:
            run_state["pending_time_bonus"] = 0
            runtime["time_limit_seconds"] = (
                int(runtime.get("time_limit_seconds", 30)) + pending_bonus
            )
            console.print(
                f"[bold #00FFFF][PULSE BARRIER] 이번 노드 제한시간 +{pending_bonus}초 보정[/bold #00FFFF]"
            )

        # ── 포지션 시작: argos_fragment 자동 추적도 감소 ─────────────────────
        per_node_reduce = run_state.get("per_node_trace_reduction", 0)
        if per_node_reduce > 0 and trace_level > 0:
            reduced = min(per_node_reduce, trace_level)
            trace_level -= reduced
            console.print(
                f"[bold magenta][ARGOS FRAGMENT] 추적도 자동 -{reduced}%  "
                f"현재: {trace_level}%[/bold magenta]"
            )

        # ── REST NODE ────────────────────────────────────────────────────────
        if ntype == NodeType.REST:
            console.clear()
            render_logo()
            rest_bonus = run_state.get("rest_heal_bonus", 0)
            class_rest_bonus = runtime.get("rest_heal_bonus_class", 0)
            total_heal = REST_HEAL_AMOUNT + rest_bonus + class_rest_bonus
            heal_amount = min(total_heal, trace_level)
            trace_level -= heal_amount
            total_bonus = rest_bonus + class_rest_bonus
            bonus_str = f" (+{total_bonus} 보너스)" if total_bonus > 0 else ""
            type_text(
                f"[REST NODE] 시스템 재조정 완료.\n"
                f"추적도 -{heal_amount}%{bonus_str}  현재: {trace_level}%",
                style="bold cyan",
                delay=0.03,
            )
            _wait_for_enter()

        # ── SHOP NODE ────────────────────────────────────────────────────────
        elif ntype == NodeType.SHOP:
            trace_level = _run_mid_run_shop(save_data, trace_level, run_state, runtime)

        # ── MYSTERY NODE ─────────────────────────────────────────────────────
        elif ntype == NodeType.MYSTERY:
            trace_level, save_data = _run_mystery_node(
                save_data, trace_level, run_seed, position, run_state, runtime
            )

        # ── COMBAT NODE (NORMAL / ELITE / BOSS) ─────────────────────────────
        else:
            if ntype == NodeType.BOSS:
                if boss_scenario is None:
                    console.print("[bold yellow]보스 시나리오 없음. 런 완료 처리.[/bold yellow]")
                    break
                scenario = boss_scenario
            else:
                if combat_pool_idx >= len(combat_pool):
                    console.print("[bold yellow]시나리오 풀 소진. 런 완료 처리.[/bold yellow]")
                    break
                scenario = combat_pool[combat_pool_idx]
                combat_pool_idx += 1

            difficulty: str | None = None
            if ntype == NodeType.BOSS:
                combat_result = "cleared"
                total_boss_phases = max(1, int(runtime.get("ascension_boss_phases", 1)))
                for phase_index in range(1, total_boss_phases + 1):
                    phase_runtime = _get_boss_phase_runtime(runtime, phase_index)
                    phase_scenario = _apply_asc20_boss_phase_override(
                        scenario,
                        phase_runtime,
                        boss_phase_pack,
                    )
                    if total_boss_phases > 1:
                        phase_mult = float(phase_runtime.get("ascension_boss_penalty_mult", 1.0))
                        phase_time = int(phase_runtime.get("time_limit_seconds", runtime["time_limit_seconds"]))
                        console.print(
                            f"[bold red][ASCENSION BOSS] 페이즈 {phase_index}/{total_boss_phases} "
                            f"(보스 페널티 x{phase_mult:.2f}, 제한시간 {phase_time}초)[/bold red]"
                        )
                    trace_level, backtrack_used, combat_result, difficulty = _run_combat_node(
                        scenario=phase_scenario,
                        position=position,
                        total_positions=total_positions,
                        trace_level=trace_level,
                        node_type=ntype,
                        perks=perks,
                        runtime=phase_runtime,
                        backtrack_used=backtrack_used,
                        run_state=run_state,
                        acquired_artifacts=acquired_artifacts,
                        diver_class=diver_class,
                    )

                    if combat_result == "death":
                        return correct_answers, False, "shutdown", node_difficulties_cleared, _build_run_stats(run_state, trace_level, max_trace_reached, acquired_artifacts)

                    if phase_index < total_boss_phases:
                        console.print(
                            "[bold red][ASCENSION BOSS] 코어 외피 붕괴. 다음 페이즈 진입.[/bold red]"
                        )
            else:
                trace_level, backtrack_used, combat_result, difficulty = _run_combat_node(
                    scenario=scenario,
                    position=position,
                    total_positions=total_positions,
                    trace_level=trace_level,
                    node_type=ntype,
                    perks=perks,
                    runtime=runtime,
                    backtrack_used=backtrack_used,
                    run_state=run_state,
                    acquired_artifacts=acquired_artifacts,
                    diver_class=diver_class,
                )

            if combat_result == "death":
                return correct_answers, False, "shutdown", node_difficulties_cleared, _build_run_stats(run_state, trace_level, max_trace_reached, acquired_artifacts)

            # 전투 클리어 후 처리
            correct_answers += 1
            if difficulty:
                node_difficulties_cleared.append(difficulty)
            cleared_themes = run_state.get("cleared_themes")
            if isinstance(cleared_themes, set):
                theme = str(scenario.get("theme", "")).strip()
                if theme:
                    cleared_themes.add(theme)

            # 클래스 클리어 효과 (CRACKER 스택 등)
            if diver_class is not None:
                trace_level = on_node_clear(diver_class, trace_level, scenario, run_state)

            # trace_siphon: 클리어 시 추적도 자동 감소
            on_clear_reduce = run_state.get("on_clear_trace_reduction", 0)
            if on_clear_reduce > 0 and trace_level > 0:
                reduced = min(on_clear_reduce, trace_level)
                trace_level -= reduced
                console.print(
                    f"[bold cyan][TRACE SIPHON] 추적도 -{reduced}%  현재: {trace_level}%[/bold cyan]"
                )

            # data_shard_x: 클리어 시 즉시 데이터 조각 획득
            frag_bonus = run_state.get("on_clear_frag_bonus", 0)
            if frag_bonus > 0:
                save_data["data_fragments"] += frag_bonus
                console.print(
                    f"[bold green][DATA SHARD X] 데이터 조각 +{frag_bonus} 즉시 획득[/bold green]"
                )

            # void_scanner: 첫 NIGHTMARE 클리어 시 +20 파편
            if (
                run_state.get("void_scanner_active")
                and str(scenario.get("difficulty", "")).upper() == "NIGHTMARE"
                and not run_state.get("void_scanner_used")
            ):
                run_state["void_scanner_used"] = True
                save_data["data_fragments"] += 20
                console.print(
                    "[bold green][VOID SCANNER] 첫 NIGHTMARE 클리어 보너스: 데이터 조각 +20[/bold green]"
                )

            # ELITE 클리어 시 아티팩트 선택 제공 (CRACKER는 +1 추가)
            if ntype == NodeType.ELITE:
                elite_art_count = 3 + runtime.get("elite_artifact_bonus", 0)
                _offer_artifact(acquired_artifacts, runtime, run_state, source="ELITE", num_choices=elite_art_count)

            # BOSS 클리어 = 런 완료 + 아티팩트 선택
            if ntype == NodeType.BOSS:
                _offer_artifact(acquired_artifacts, runtime, run_state, source="BOSS", num_choices=2)
                break

        # ── ROUTE CHOICE (position 0-5 이후에만 표시) ──────────────────────
        if position < MAX_NODES_PER_RUN - 1:
            left, right = route_choices[position]
            render_route_choice(
                current_depth=position,
                total_depth=MAX_NODES_PER_RUN,
                left_type_name=left.value,
                right_type_name=right.value,
                left_label=get_label(left),
                right_label=get_label(right),
                left_desc=get_desc(left),
                right_desc=get_desc(right),
                left_style=get_style(left),
                right_style=get_style(right),
            )
            path_choice = Prompt.ask(
                "[bold white]경로를 선택하세요[/bold white]",
                choices=["A", "B"],
                default="A",
            )
            current_node_type = left if path_choice.upper() == "A" else right

    console.print("[bold green]CORE BREACHED - 승리[/bold green]")
    return correct_answers, True, "victory", node_difficulties_cleared, _build_run_stats(run_state, trace_level, max_trace_reached, acquired_artifacts, is_victory=True)




def run_daily_challenge(save_data: dict[str, Any]) -> None:
    """
    데일리 챌린지 런을 실행한다.

    - 날짜 고정 시드로 시나리오와 루트를 결정해 모든 플레이어에게 동일한 맵을 제공한다.
    - 하루 1회만 플레이 가능 (재도전 차단).
    - REST/SHOP/ELITE 노드 모두 일반 런과 동일하게 처리한다.
    - 보상 배율 ×1.5 적용.
    """
    today = get_today_str()
    daily_state = get_daily_state(save_data)

    render_daily_challenge_intro(today, already_played=has_played_today(daily_state, today))

    if has_played_today(daily_state, today):
        render_daily_history(daily_state.get("history", []))
        _wait_for_enter("로비로 복귀하려면 Enter를 누르세요")
        return

    # 클래스 선택 (데일리에서도 클래스 효과 적용)
    selected_class = _select_diver_class()

    # 날짜 시드로 시나리오 풀 결정
    try:
        scenarios = load_scenarios("scenarios.json")
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]시나리오 로드 실패: {exc}[/bold red]")
        return

    daily_combat_pool, daily_boss = select_daily_scenarios(scenarios, today, MAX_NODES_PER_RUN)

    if not daily_combat_pool:
        console.print("[bold red]데일리 챌린지 시나리오를 구성할 수 없습니다.[/bold red]")
        return

    console.print(
        f"[bold cyan][DAILY SEED] 오늘의 시드가 로드되었습니다 — {today}[/bold cyan]"
    )

    # 데일리는 ascension 0 고정 (공정성), 보유 perks는 적용
    runtime, run_state, trace_level = _initialize_run_state(
        perks=save_data["perks"],
        diver_class=selected_class,
        ascension_level=0,
    )
    acquired_artifacts: list[Artifact] = []

    backtrack_used = False
    correct_answers = 0
    node_difficulties_cleared: list[str] = []
    combat_pool_idx = 0
    combat_result = "cleared"
    total_positions = MAX_NODES_PER_RUN + 1
    max_trace_reached = trace_level  # 데일리 런 중 최대 추적도 기록

    # 날짜 시드로 루트 선택지 결정 (재현성 보장)
    _rng_state = random.getstate()
    random.seed(get_daily_seed(today) ^ 0xABCDEF)
    route_choices = build_route_choices(MAX_NODES_PER_RUN - 1)
    random.setstate(_rng_state)  # 전역 random 상태 복원

    current_node_type = NodeType.NORMAL

    # ── 데일리 런 루프 ──────────────────────────────────────────────────────
    for position in range(total_positions):
        ntype = NodeType.BOSS if position == MAX_NODES_PER_RUN else current_node_type
        if trace_level > max_trace_reached:
            max_trace_reached = trace_level
        # trace_shield 아티팩트용 현재 추적도 동기화
        run_state["current_trace"] = trace_level

        # argos_fragment 자동 추적도 감소
        per_node_reduce = run_state.get("per_node_trace_reduction", 0)
        if per_node_reduce > 0 and trace_level > 0:
            reduced = min(per_node_reduce, trace_level)
            trace_level -= reduced
            console.print(
                f"[bold magenta][ARGOS FRAGMENT] 추적도 자동 -{reduced}%  "
                f"현재: {trace_level}%[/bold magenta]"
            )

        # ── REST NODE ─────────────────────────────────────────────────────
        if ntype == NodeType.REST:
            console.clear()
            render_logo()
            rest_bonus = run_state.get("rest_heal_bonus", 0)
            class_rest_bonus = runtime.get("rest_heal_bonus_class", 0)
            total_heal = REST_HEAL_AMOUNT + rest_bonus + class_rest_bonus
            heal_amount = min(total_heal, trace_level)
            trace_level -= heal_amount
            bonus_str = f" (+{rest_bonus + class_rest_bonus} 보너스)" if (rest_bonus + class_rest_bonus) > 0 else ""
            type_text(
                f"[REST NODE] 시스템 재조정 완료.\n"
                f"추적도 -{heal_amount}%{bonus_str}  현재: {trace_level}%",
                style="bold cyan",
                delay=0.03,
            )
            _wait_for_enter()

        # ── SHOP NODE ─────────────────────────────────────────────────────
        elif ntype == NodeType.SHOP:
            trace_level = _run_mid_run_shop(save_data, trace_level, run_state, runtime)

        # ── MYSTERY NODE ──────────────────────────────────────────────────
        elif ntype == NodeType.MYSTERY:
            daily_run_seed = get_daily_seed(today)
            trace_level, save_data = _run_mystery_node(
                save_data, trace_level, daily_run_seed, position, run_state, runtime
            )

        # ── COMBAT NODE (NORMAL / ELITE / BOSS) ───────────────────────────
        else:
            if ntype == NodeType.BOSS:
                if daily_boss is None:
                    console.print("[bold yellow]보스 시나리오 없음. 런 완료 처리.[/bold yellow]")
                    break
                scenario = daily_boss
            else:
                if combat_pool_idx >= len(daily_combat_pool):
                    console.print("[bold yellow]시나리오 풀 소진. 런 완료 처리.[/bold yellow]")
                    break
                scenario = daily_combat_pool[combat_pool_idx]
                combat_pool_idx += 1

            trace_level, backtrack_used, combat_result, difficulty = _run_combat_node(
                scenario=scenario,
                position=position,
                total_positions=total_positions,
                trace_level=trace_level,
                node_type=ntype,
                perks=save_data["perks"],
                runtime=runtime,
                backtrack_used=backtrack_used,
                run_state=run_state,
                acquired_artifacts=acquired_artifacts,
                diver_class=selected_class,
            )

            if combat_result == "death":
                break

            correct_answers += 1
            if difficulty:
                node_difficulties_cleared.append(difficulty)
            if selected_class is not None:
                trace_level = on_node_clear(selected_class, trace_level, scenario, run_state)

            # 클리어 후 처리
            on_clear_reduce = run_state.get("on_clear_trace_reduction", 0)
            if on_clear_reduce > 0 and trace_level > 0:
                reduced = min(on_clear_reduce, trace_level)
                trace_level -= reduced
                console.print(f"[bold cyan][TRACE SIPHON] 추적도 -{reduced}%  현재: {trace_level}%[/bold cyan]")

            frag_bonus = run_state.get("on_clear_frag_bonus", 0)
            if frag_bonus > 0:
                save_data["data_fragments"] += frag_bonus
                console.print(f"[bold green][DATA SHARD X] 데이터 조각 +{frag_bonus} 즉시 획득[/bold green]")

            if ntype == NodeType.ELITE:
                elite_art_count = 3 + runtime.get("elite_artifact_bonus", 0)
                _offer_artifact(acquired_artifacts, runtime, run_state, source="ELITE", num_choices=elite_art_count)

            if ntype == NodeType.BOSS:
                _offer_artifact(acquired_artifacts, runtime, run_state, source="BOSS", num_choices=2)
                break

        # ── ROUTE CHOICE ──────────────────────────────────────────────────
        if position < MAX_NODES_PER_RUN - 1:
            left, right = route_choices[position]
            render_route_choice(
                current_depth=position,
                total_depth=MAX_NODES_PER_RUN,
                left_type_name=left.value,
                right_type_name=right.value,
                left_label=get_label(left),
                right_label=get_label(right),
                left_desc=get_desc(left),
                right_desc=get_desc(right),
                left_style=get_style(left),
                right_style=get_style(right),
            )
            path_choice = Prompt.ask(
                "[bold white]경로를 선택하세요[/bold white]",
                choices=["A", "B"],
                default="A",
            )
            current_node_type = left if path_choice.upper() == "A" else right

    # ── 승리 판정 ────────────────────────────────────────────────────────────
    is_victory = (combat_result != "death" and position == total_positions - 1)
    if is_victory:
        console.print("[bold green]CORE BREACHED - 데일리 챌린지 승리![/bold green]")

    # ── 점수 계산 및 보상 ──────────────────────────────────────────────────
    base_reward = calculate_base_reward(node_difficulties_cleared)
    final_reward = calculate_reward(correct_answers, is_victory, node_difficulties_cleared)
    # 데일리 배율 적용
    daily_reward = int(final_reward * 1.5)
    save_data["data_fragments"] += daily_reward

    wrong_analyzes = run_state.get("wrong_analyzes", 0)
    timeout_events = run_state.get("timeout_events", 0)

    score = calculate_daily_score(
        correct_answers=correct_answers,
        is_victory=is_victory,
        trace_final=trace_level,
        wrong_analyzes=wrong_analyzes,
        timeout_events=timeout_events,
        base_reward=base_reward,
    )

    class_key = selected_class.value if selected_class else ""
    updated_daily = record_daily_result(
        save_data=save_data,
        date_str=today,
        score=score,
        is_victory=is_victory,
        correct_answers=correct_answers,
        trace_final=trace_level,
        class_key=class_key,
        wrong_analyzes=wrong_analyzes,
    )

    console.print(
        f"[bold #00FFFF][DAILY REWARD] 보상 배율 ×1.5 적용: "
        f"{final_reward} → {daily_reward} 데이터 조각[/bold #00FFFF]"
    )

    render_daily_result(
        date_str=today,
        score=score,
        is_victory=is_victory,
        correct_answers=correct_answers,
        trace_final=trace_level,
        class_key=class_key,
        streak=updated_daily.get("streak", 1),
        best_score=updated_daily.get("best_score", score),
    )

    # 업적 평가
    run_summary = {
        "result": "victory" if is_victory else "shutdown",
        "is_victory": is_victory,
        "class_key": class_key,
        "ascension_level": 0,
        "wrong_analyzes": wrong_analyzes,
        "timeout_events": timeout_events,
    }
    newly_unlocked = evaluate_achievements(save_data, run_summary)
    if newly_unlocked:
        render_achievement_unlocks(newly_unlocked)

    try:
        save_game(save_data)
    except OSError as exc:
        console.print(f"[bold red]{exc}[/bold red]")

    _wait_for_enter("로비로 복귀하려면 Enter를 누르세요")


def run_lobby_loop() -> None:
    """게임 전체 상태 머신 (로비 → 런/상점 → 로비)을 실행한다.

    lobby 모듈의 구현에 run_game_session / run_daily_challenge를 주입한다.
    """
    _run_lobby_loop_impl(run_game_session, run_daily_challenge)


if __name__ == "__main__":
    run_lobby_loop()
