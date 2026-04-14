"""Echoes of the Terminal 메인 실행 파일 (루트 맵 + 아티팩트 시스템 통합판)."""

import math
import random
import re
import threading
import time
from typing import Any

from rich.prompt import Prompt
from rich.table import Table

from achievement_system import evaluate_achievements, get_achievement_snapshot
from artifact_system import Artifact, apply_artifact_effect, draw_artifacts
from diver_class import (
    CLASS_MENU_MAP,
    CLASS_PROFILES,
    DiverClass,
    apply_class_modifiers,
    get_class_profile,
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
from ending_system import evaluate_ending, get_endings_snapshot, record_ending_unlock
from daily_challenge import (
    calculate_daily_score,
    get_daily_seed,
    get_daily_state,
    get_today_str,
    has_played_today,
    record_daily_result,
    select_daily_scenarios,
)
from combat_timer import CombatTimer
from combat_commands import (
    CommandResult,
    calculate_analyze_penalty as _calculate_analyze_penalty_impl,
    handle_analyze,
    handle_cat_log,
    handle_help,
    handle_ls,
    handle_skill,
)
from data_loader import load_argos_taunts, load_boss_phase_pack, load_scenarios
from mutator_system import apply_glitch_masking
from mystery_system import (
    apply_mystery_outcome,
    pick_mystery,
    resolve_mystery_outcome,
)
from progression_system import (
    ASCENSION_MAX_LEVEL,
    CAMPAIGN_CLEAR_CLASS_VICTORIES,
    CAMPAIGN_CLEAR_POINTS,
    CAMPAIGN_CLEAR_TOTAL_VICTORIES,
    calculate_campaign_gain,
    PERK_DESC_MAP,
    PERK_LABEL_MAP,
    PERK_MENU_MAP,
    PERK_PRICES,
    calculate_base_reward,
    calculate_reward,
    get_ascension_profile,
    get_campaign_progress_snapshot,
    load_save,
    save_game,
    update_campaign_progress,
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
    render_alert,
    render_achievement_unlocks,
    render_artifact_hud,
    render_artifact_selection,
    render_class_selection,
    render_daily_challenge_intro,
    render_daily_history,
    render_daily_result,
    render_ending,
    render_endings_gallery,
    render_info_panel,
    render_lobby,
    render_logo,
    render_records_screen,
    render_route_choice,
    render_settlement_log,
    render_shop,
    set_argos_taunts,
    type_text,
)


def _wait_for_enter(message: str = "계속하려면 Enter를 누르세요") -> None:
    """화면 전환 전 사용자의 확인 입력을 받는다."""
    Prompt.ask(f"[bold white]{message}[/bold white]", default="")


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


def _apply_ascension_reward_multiplier(
    reward: int,
    ascension_level: int,
) -> tuple[int, float]:
    """Ascension 레벨에 따른 런 보상 배율을 적용한다."""
    safe_reward = max(0, int(reward))
    profile = get_ascension_profile(ascension_level)
    multiplier = max(0.0, float(profile.get("reward_mult", 1.0)))
    return max(0, int(safe_reward * multiplier)), multiplier


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


def _build_boss_fake_keywords(
    text_log: str,
    target_keyword: str,
    count: int,
) -> list[str]:
    """보스 페이즈에서 표시할 가짜 키워드 후보를 생성한다."""
    target_norm = target_keyword.strip().lower()
    candidates = sorted(
        {
            m.group(0)
            for m in re.finditer(r"\b[\w가-힣]{2,8}\b", text_log, re.UNICODE)
            if m.group(0).strip().lower() != target_norm and not m.group(0).isdigit()
        }
    )
    if not candidates:
        return []
    safe_count = max(0, min(len(candidates), int(count)))
    if safe_count <= 0:
        return []
    return random.sample(candidates, safe_count)


def _apply_trace_penalty_and_check_death(
    trace_level: int,
    penalty: int,
    perks: dict[str, bool],
    backtrack_used: bool,
    run_state: dict[str, Any],
    timer: threading.Timer | None,
) -> tuple[int, bool, bool]:
    """
    추적도 페널티를 적용한 뒤 사망 처리를 수행한다.

    Returns:
        trace_level, backtrack_used, survived
    """
    safe_penalty = max(0, int(penalty))
    if safe_penalty <= 0:
        return trace_level, backtrack_used, True

    trace_level += safe_penalty
    console.print(f"[bold white]TRACE +{safe_penalty}% -> {trace_level}%[/bold white]")
    if trace_level >= TRACE_MAX:
        trace_level, backtrack_used, survived = _handle_death_check(
            trace_level, perks, backtrack_used, run_state, timer
        )
        return trace_level, backtrack_used, survived
    return trace_level, backtrack_used, True


def _check_boss_command_block(
    command_name: str,
    node_type: "NodeType",
    boss_phase_index: int,
    block_from_phase: int,
    trace_level: int,
    violation_penalty: int,
    perks: dict[str, bool],
    backtrack_used: bool,
    run_state: dict[str, Any],
    timer: "threading.Timer | None",
) -> tuple[int, bool, bool, bool]:
    """
    ASC20 보스 명령 차단 여부를 확인하고 패널티를 적용한다.

    Returns:
        (trace_level, backtrack_used, survived, was_blocked)
        was_blocked=True이면 호출부에서 continue 처리가 필요하다.
    """
    if node_type != NodeType.BOSS or boss_phase_index < block_from_phase:
        return trace_level, backtrack_used, True, False

    console.print(
        f"[bold red][ASCENSION LOCK] 해당 페이즈에서는 '{command_name}' 명령이 차단됩니다.[/bold red]"
    )
    if timer is not None:
        trace_level, backtrack_used, survived = _apply_trace_penalty_and_check_death(
            trace_level=trace_level,
            penalty=violation_penalty,
            perks=perks,
            backtrack_used=backtrack_used,
            run_state=run_state,
            timer=timer,
        )
        return trace_level, backtrack_used, survived, True
    return trace_level, backtrack_used, True, True


def _apply_asc20_boss_phase_override(
    scenario: dict[str, Any],
    runtime: dict[str, Any],
    boss_phase_pack: dict[int, list[dict[str, str]]],
) -> dict[str, Any]:
    """
    ASC20 보스 페이즈 데이터팩 오버라이드를 현재 시나리오에 적용한다.

    오버라이드 대상 필드:
    - text_log
    - target_keyword
    - logical_flaw_explanation (선택)
    """
    if int(runtime.get("ascension_level", 0)) < 20:
        return scenario
    if not scenario.get("is_boss", False):
        return scenario
    if not boss_phase_pack:
        return scenario

    try:
        node_id = int(scenario.get("node_id", -1))
    except (TypeError, ValueError):
        return scenario

    phase_index = max(1, int(runtime.get("boss_phase_index", 1)))
    phases = boss_phase_pack.get(node_id, [])
    if not phases:
        return scenario
    if phase_index > len(phases):
        return scenario

    phase_override = phases[phase_index - 1]
    merged = dict(scenario)
    merged["text_log"] = phase_override["text_log"]
    merged["target_keyword"] = phase_override["target_keyword"]
    logical_flaw = phase_override.get("logical_flaw_explanation")
    if logical_flaw:
        merged["logical_flaw_explanation"] = logical_flaw
    return merged


def _initialize_argos_taunts() -> None:
    """아르고스 대사 데이터를 로드해 UI 모듈에 주입한다."""
    try:
        taunts = load_argos_taunts("argos_taunts.json")
        set_argos_taunts(taunts)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold yellow]아르고스 대사 로드 실패: {exc}[/bold yellow]")
        set_argos_taunts({})


def _print_help(active_skill_name: str = "") -> None:
    """CLI help 텍스트를 출력한다."""
    console.print("[bold green]사용 가능 명령어[/bold green]")
    console.print("[bold white]- help[/bold white] : 명령어 목록 출력")
    console.print("[bold white]- ls[/bold white] : 현재 노드의 테마/난이도 출력")
    console.print("[bold white]- cat log[/bold white] : 현재 시나리오 로그 출력")
    console.print("[bold white]- analyze [키워드][/bold white] : 키워드 분석 공격 시도")
    console.print("[bold white]- clear[/bold white] : 터미널 화면 정리")
    if active_skill_name:
        console.print(
            f"[bold #00FFFF]- skill[/bold #00FFFF] : 액티브 스킬 발동 ({active_skill_name})"
        )


def _render_combat_screen(
    scenario: dict[str, Any],
    position: int,
    total_positions: int,
    trace_level: int,
    time_limit_seconds: int,
    node_type: NodeType,
    acquired_artifacts: list[Artifact],
) -> None:
    """전투 노드 진입 시 기본 UI를 렌더링한다."""
    is_boss = bool(scenario.get("is_boss", False))
    is_elite = node_type == NodeType.ELITE
    console.clear()
    render_logo()
    render_info_panel(
        current_node=position + 1,
        total_nodes=total_positions,
        trace_level=trace_level,
        time_limit_seconds=time_limit_seconds,
        is_boss=is_boss,
    )
    if is_boss:
        node_style = "bold red"
    elif is_elite:
        node_style = "bold magenta"
    else:
        node_style = "bold green"

    elite_tag = " [ELITE ×1.5]" if is_elite else ""
    type_text(
        f"[ NODE {scenario['node_id']} ] THEME {scenario['theme']} | {scenario['difficulty']}{elite_tag}",
        style=node_style,
        delay=0.02,
    )
    type_text(
        "터미널 접속 완료. 명령어가 기억나지 않으면 'help'를 입력하라.",
        style="bold white",
        delay=0.02,
    )
    render_artifact_hud(acquired_artifacts)
    print_argos_message("encounter_node")


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


def _offer_artifact(
    acquired_artifacts: list[Artifact],
    runtime: dict[str, Any],
    run_state: dict[str, Any],
    source: str = "ELITE",
    num_choices: int = 3,
) -> None:
    """
    아티팩트 선택 UI를 표시하고, 선택된 아티팩트를 acquired_artifacts에 추가한다.

    아티팩트 효과는 즉시 runtime과 run_state에 반영된다.
    """
    exclude_ids = [a.artifact_id for a in acquired_artifacts]
    candidates = draw_artifacts(num_choices, exclude_ids=exclude_ids)

    if not candidates:
        console.print("[bold yellow]획득 가능한 아티팩트가 없습니다.[/bold yellow]")
        _wait_for_enter()
        return

    render_artifact_selection(candidates, source=source)

    valid_choices = [str(i) for i in range(1, len(candidates) + 1)] + ["0"]
    choice_str = Prompt.ask(
        "[bold magenta]획득할 아티팩트 번호 (0: 건너뜀)[/bold magenta]",
        choices=valid_choices,
        default="1",
    )

    if choice_str == "0":
        return

    chosen = candidates[int(choice_str) - 1]
    acquired_artifacts.append(chosen)
    apply_artifact_effect(chosen, runtime, run_state)
    console.print(
        f"[bold magenta][ARTIFACT] 획득: {chosen.name} — {chosen.desc}[/bold magenta]"
    )
    _wait_for_enter()


def _handle_death_check(
    trace_level: int,
    perks: dict[str, bool],
    backtrack_used: bool,
    run_state: dict[str, Any],
    timer: threading.Timer | None,
) -> tuple[int, bool, bool]:
    """
    추적도 >= 100 시 사망 처리를 순서대로 시도한다.

    처리 우선순위:
    1. backtrack_protocol (퍼크, 재사용 1회)
    2. phantom_core (아티팩트, 재사용 1회)
    3. 사망 확정

    Returns:
        (trace_level, backtrack_used, survived)
    """
    if perks.get("backtrack_protocol") and not backtrack_used:
        backtrack_used = True
        trace_level = TRACE_MAX // 2
        console.print(
            "[bold #00FFFF][BACKTRACK PROTOCOL] 추적도 50%로 회복됨.[/bold #00FFFF]"
        )
        return trace_level, backtrack_used, True

    if run_state.get("phantom_core_active"):
        run_state["phantom_core_active"] = False
        trace_level = int(TRACE_MAX * 0.75)
        console.print(
            "[bold magenta][PHANTOM CORE] 부활. 추적도 75%로 회복됨.[/bold magenta]"
        )
        return trace_level, backtrack_used, True

    if timer is not None:
        timer.cancel()
    render_alert("SYSTEM SHUTDOWN - 사망")
    print_argos_message("game_over")
    return trace_level, backtrack_used, False


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


def _run_combat_node(
    scenario: dict[str, Any],
    position: int,
    total_positions: int,
    trace_level: int,
    node_type: NodeType,
    perks: dict[str, bool],
    runtime: dict[str, Any],
    backtrack_used: bool,
    run_state: dict[str, Any],
    acquired_artifacts: list[Artifact],
    diver_class: "DiverClass | None" = None,
) -> tuple[int, bool, str, str | None]:
    """
    전투 노드(NORMAL/ELITE/BOSS) 한 판을 실행한다.

    Returns:
        tuple:
            - trace_level: 업데이트된 추적도
            - backtrack_used: 백트랙 프로토콜 사용 여부
            - result: "cleared" | "death"
            - difficulty: 클리어 시 노드 난이도, 사망 시 None
    """
    scenario_difficulty = str(scenario.get("difficulty", ""))
    boss_phase_index = max(1, int(runtime.get("boss_phase_index", 1)))
    boss_phase_total = max(1, int(runtime.get("boss_phase_total", 1)))
    boss_block_cat_log_from_phase = max(
        1,
        int(runtime.get("ascension_boss_block_cat_log_from_phase", 99)),
    )
    boss_block_skill_from_phase = max(
        1,
        int(runtime.get("ascension_boss_block_skill_from_phase", 99)),
    )
    boss_command_violation_penalty = max(
        0,
        int(runtime.get("ascension_boss_command_violation_penalty", 0)),
    )
    boss_fake_keyword_count = max(
        0,
        int(runtime.get("ascension_boss_fake_keyword_count", 0)),
    )
    masking_difficulty = scenario_difficulty
    if runtime.get("ascension_force_easy_glitch") and scenario_difficulty.strip().upper() == "EASY":
        masking_difficulty = "HARD"

    glitched_log = apply_glitch_masking(
        text_log=scenario["text_log"],
        difficulty=masking_difficulty,
        target_keyword=scenario["target_keyword"],
        glitch_word_count=runtime["glitch_word_count"],
        nightmare_noise_reduce=runtime.get("nightmare_noise_reduce", 0),
    )

    _render_combat_screen(
        scenario=scenario,
        position=position,
        total_positions=total_positions,
        trace_level=trace_level,
        time_limit_seconds=runtime["time_limit_seconds"],
        node_type=node_type,
        acquired_artifacts=acquired_artifacts,
    )
    if node_type == NodeType.BOSS and boss_phase_total > 1:
        console.print(
            f"[bold red][BOSS PHASE] {boss_phase_index}/{boss_phase_total}[/bold red]"
        )
        blocked_commands: list[str] = []
        if boss_phase_index >= boss_block_cat_log_from_phase:
            blocked_commands.append("cat log")
        if boss_phase_index >= boss_block_skill_from_phase:
            blocked_commands.append("skill")
        if blocked_commands:
            console.print(
                "[bold red][ASCENSION LOCK] 사용 불가 명령: "
                f"{', '.join(blocked_commands)}[/bold red]"
            )
    if node_type == NodeType.BOSS and boss_fake_keyword_count > 0:
        fake_keywords = _build_boss_fake_keywords(
            text_log=str(scenario.get("text_log", "")),
            target_keyword=str(scenario.get("target_keyword", "")),
            count=boss_fake_keyword_count,
        )
        if fake_keywords:
            fake_line = " / ".join(f"'{word}'" for word in fake_keywords)
            console.print(
                f"[bold red][ARGOS SPOOF] 의심 키워드: {fake_line}[/bold red]"
            )

    # lexical_assist: NIGHTMARE 노드에서 target_keyword 첫 글자 힌트 공개
    if scenario["difficulty"].upper() == "NIGHTMARE" and perks.get("lexical_assist"):
        target_str = str(scenario.get("target_keyword", ""))
        hint_char = target_str[0] if target_str else "?"
        console.print(
            f"[bold #00FFFF][LEXICAL ASSIST] 키워드 첫 글자: '{hint_char}'[/bold #00FFFF]"
        )

    # ANALYST 패시브: 글자 수 힌트 자동 공개
    if run_state.get("analyst_hint_active"):
        kw = str(scenario.get("target_keyword", ""))
        console.print(
            f"[bold cyan][ANALYST] 키워드 글자 수: {len(kw)}자[/bold cyan]"
        )

    type_text(glitched_log, style="white", delay=0.02)

    active_skill_name = (
        get_class_profile(diver_class).active_name if diver_class is not None else ""
    )

    # ── 타임아웃 타이머 설정 ─────────────────────────────────────────────────────
    def _on_timeout() -> None:
        console.print("\n[bold #00FFFF]>>> ARGOS 개입: 입력 제한 시간 초과 <<<[/bold #00FFFF]")
        print_argos_message("timeout")

    timer = CombatTimer(
        timeout_seconds=runtime["time_limit_seconds"],
        on_timeout=_on_timeout,
    )
    timer.start()

    effective_timeout_penalty = runtime.get("timeout_penalty", TIMEOUT_PENALTY)
    timeout_penalty_applied = False
    echo_cache_used = False
    last_prompt_time = time.monotonic()

    def _cancel_timer() -> None:
        timer.cancel()

    def _handle_death(t: int, bu: bool) -> tuple[int, bool, bool]:
        return _handle_death_check(t, perks, bu, run_state, timer.raw_timer)

    while True:
        last_prompt_time = time.monotonic()
        command_raw = Prompt.ask("[bold green]root@argos:~#[/bold green]").strip()

        # 타임아웃 패널티 한 번만 적용
        if timer.has_fired and not timeout_penalty_applied:
            timeout_penalty_applied = True
            run_state["timeout_events"] = int(run_state.get("timeout_events", 0)) + 1
            trace_level += effective_timeout_penalty
            console.print(
                f"[bold white]TRACE +{effective_timeout_penalty}% -> {trace_level}%[/bold white]"
            )
            if trace_level >= TRACE_MAX:
                trace_level, backtrack_used, survived = _handle_death(trace_level, backtrack_used)
                if not survived:
                    return trace_level, backtrack_used, "death", None

        if not command_raw:
            continue

        command_lower = command_raw.lower()

        if command_lower == "help":
            handle_help(active_skill_name=active_skill_name)
            continue

        if command_lower == "ls":
            handle_ls(scenario=scenario, node_type=node_type)
            continue

        if command_lower == "cat log":
            trace_level, backtrack_used, survived, was_blocked = _check_boss_command_block(
                command_name="cat log",
                node_type=node_type,
                boss_phase_index=boss_phase_index,
                block_from_phase=boss_block_cat_log_from_phase,
                trace_level=trace_level,
                violation_penalty=boss_command_violation_penalty,
                perks=perks,
                backtrack_used=backtrack_used,
                run_state=run_state,
                timer=timer.raw_timer,
            )
            if was_blocked:
                if not survived:
                    return trace_level, backtrack_used, "death", None
                continue
            echo_cache_used = handle_cat_log(
                scenario=scenario,
                run_state=run_state,
                echo_cache_used=echo_cache_used,
                timer_has_fired=timer.has_fired,
                extend_timeout_fn=timer.extend,
            )
            continue

        if command_lower == "clear":
            _render_combat_screen(
                scenario=scenario,
                position=position,
                total_positions=total_positions,
                trace_level=trace_level,
                time_limit_seconds=runtime["time_limit_seconds"],
                node_type=node_type,
                acquired_artifacts=acquired_artifacts,
            )
            continue

        if command_lower == "skill":
            trace_level, backtrack_used, survived, was_blocked = _check_boss_command_block(
                command_name="skill",
                node_type=node_type,
                boss_phase_index=boss_phase_index,
                block_from_phase=boss_block_skill_from_phase,
                trace_level=trace_level,
                violation_penalty=boss_command_violation_penalty,
                perks=perks,
                backtrack_used=backtrack_used,
                run_state=run_state,
                timer=timer.raw_timer,
            )
            if was_blocked:
                if not survived:
                    return trace_level, backtrack_used, "death", None
                continue
            trace_level = handle_skill(
                diver_class=diver_class,
                trace_level=trace_level,
                runtime=runtime,
                run_state=run_state,
                scenario=scenario,
            )
            continue

        if command_lower.startswith("analyze"):
            action, trace_level, backtrack_used, difficulty = handle_analyze(
                command_raw=command_raw,
                scenario=scenario,
                trace_level=trace_level,
                backtrack_used=backtrack_used,
                node_type=node_type,
                diver_class=diver_class,
                runtime=runtime,
                run_state=run_state,
                perks=perks,
                last_prompt_time=last_prompt_time,
                cancel_timer_fn=_cancel_timer,
                handle_death_fn=_handle_death,
            )
            if action == "death":
                return trace_level, backtrack_used, "death", None
            if action == "cleared":
                return trace_level, backtrack_used, "cleared", difficulty
            continue

        console.print("[bold yellow]명령어를 찾을 수 없습니다. 'help'를 입력하세요.[/bold yellow]")

    # 도달 불가 — 타입 체커 만족용
    timer.cancel()
    return trace_level, backtrack_used, "death", None


def _run_mid_run_shop(
    save_data: dict[str, Any],
    trace_level: int,
    run_state: dict[str, Any],
    runtime: dict[str, Any],
) -> int:
    """
    런 중간 상점을 실행하고 업데이트된 trace_level을 반환한다.

    데이터 조각을 소비해 즉시 효과 아이템을 구매할 수 있다.
    구매 내역은 save_data를 직접 수정하므로 호출부에서 별도 저장이 필요 없다.
    """
    while True:
        trace_cost, buffer_cost, cost_mult = _get_mid_shop_costs(runtime)
        console.clear()
        render_logo()
        console.print("[bold yellow]>>> MID-RUN SHOP — ARGOS 데이터 마켓[/bold yellow]")
        console.print(f"[bold white]보유 데이터 조각: {save_data['data_fragments']}[/bold white]")
        if cost_mult > 1.0:
            console.print(
                f"[bold yellow][ASCENSION] 상점가 보정 ×{cost_mult:.2f} 적용[/bold yellow]"
            )
        console.print()

        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("번호", style="bold white", width=6)
        table.add_column("아이템", style="bold white")
        table.add_column("효과", style="white")
        table.add_column("비용", style="bold white", width=8)
        table.add_column("상태", style="bold white", width=10)

        has_buffer = run_state.get("skip_next_penalty", False)

        table.add_row(
            "1",
            "추적도 제거제",
            f"추적도 -{MID_SHOP_TRACE_HEAL}% 즉시 회복",
            str(trace_cost),
            "구매 가능" if trace_level > 0 else "[dim]추적도 0%[/dim]",
        )
        table.add_row(
            "2",
            "오답 면역 쉴드",
            "다음 오답 1회 페널티 무시",
            str(buffer_cost),
            "[bold cyan]활성화됨[/bold cyan]" if has_buffer else "구매 가능",
        )
        table.add_row("0", "상점 나가기", "계속 진행", "-", "-")
        console.print(table)

        choice = Prompt.ask(
            "[bold yellow]구매할 아이템 번호[/bold yellow]",
            choices=["0", "1", "2"],
            default="0",
        )

        if choice == "0":
            return trace_level

        if choice == "1":
            if trace_level <= 0:
                console.print("[bold yellow]추적도가 이미 0%입니다.[/bold yellow]")
                _wait_for_enter()
                continue
            if save_data["data_fragments"] < trace_cost:
                console.print(
                    f"[bold red]데이터 조각이 부족합니다. (필요: {trace_cost})[/bold red]"
                )
                _wait_for_enter()
                continue
            heal_amount = min(MID_SHOP_TRACE_HEAL, trace_level)
            trace_level -= heal_amount
            save_data["data_fragments"] -= trace_cost
            console.print(
                f"[bold cyan]추적도 -{heal_amount}% 회복. 현재 추적도: {trace_level}%[/bold cyan]"
            )
            _wait_for_enter()

        elif choice == "2":
            if has_buffer:
                console.print("[bold yellow]이미 오답 면역 쉴드가 활성화되어 있습니다.[/bold yellow]")
                _wait_for_enter()
                continue
            if save_data["data_fragments"] < buffer_cost:
                console.print(
                    f"[bold red]데이터 조각이 부족합니다. (필요: {buffer_cost})[/bold red]"
                )
                _wait_for_enter()
                continue
            run_state["skip_next_penalty"] = True
            save_data["data_fragments"] -= buffer_cost
            console.print("[bold cyan]오답 면역 쉴드 활성화. 다음 오답 1회 페널티 면제.[/bold cyan]")
            _wait_for_enter()


def _select_diver_class() -> DiverClass:
    """
    게임 시작 전 다이버 클래스를 선택하는 UI를 표시하고 선택된 클래스를 반환한다.
    """
    console.clear()
    render_logo()
    profiles = list(CLASS_PROFILES.values())
    render_class_selection(profiles)

    choice = Prompt.ask(
        "[bold white]클래스 번호를 선택하세요[/bold white]",
        choices=list(CLASS_MENU_MAP.keys()),
        default="1",
    )
    selected = CLASS_MENU_MAP[choice]
    profile = get_class_profile(selected)
    console.print(
        f"\n[bold white]클래스 선택: [{profile.diver_class.value}] {profile.name}[/bold white]"
    )
    _wait_for_enter()
    return selected


def _select_ascension_level(save_data: dict[str, Any]) -> int:
    """
    시작 전 사용할 각성 레벨(Ascension)을 선택한다.

    해금된 최대 레벨까지만 선택 가능하다.
    """
    campaign = save_data.get("campaign", {})
    if not isinstance(campaign, dict):
        campaign = {}
    unlocked = int(campaign.get("ascension_unlocked", 0))
    unlocked = max(0, min(ASCENSION_MAX_LEVEL, unlocked))

    console.clear()
    render_logo()
    console.print("[bold white]━━━ ASCENSION SELECTION ━━━[/bold white]")
    console.print(
        f"[bold white]현재 해금: 0 ~ {unlocked}[/bold white] "
        "[dim](승리 시 현재 레벨 이상 클리어하면 다음 레벨 해금)[/dim]"
    )
    console.print(
        "[bold white]주요 규칙: ASC 1(+5 페널티), ASC 3(제한시간 단축), ASC 5(시작 TRACE 20), "
        "ASC 10+(상점가↑/보상↓/보스 강화), ASC 18+(보스 멀티 페이즈), "
        "ASC 20(보스 페이즈 명령 잠금/시나리오 변조)[/bold white]\n"
    )

    choices = [str(i) for i in range(unlocked + 1)]
    selected = int(
        Prompt.ask(
            "[bold white]각성 레벨을 선택하세요[/bold white]",
            choices=choices,
            default=str(unlocked),
        )
    )
    console.print(f"[bold cyan]ASCENSION {selected} 선택[/bold cyan]")
    _wait_for_enter()
    return selected


def _run_mystery_node(
    save_data: dict[str, Any],
    trace_level: int,
    run_seed: int,
    node_position: int,
    run_state: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """
    미스터리 노드를 실행하고 업데이트된 (trace_level, save_data)를 반환한다.

    플레이어는 [A] 개입 또는 [B] 무시를 선택한다.
    개입 선택 시 런 시드와 포지션으로 결정된 결과가 적용된다.
    run_state가 제공되면 mystery_engaged, mystery_good, mystery_skipped 카운터를 기록한다.

    Args:
        save_data: 현재 세이브 데이터 (data_fragments 포함)
        trace_level: 현재 추적도
        run_seed: 런 고유 시드
        node_position: 현재 노드 포지션
        run_state: 런 상태 dict (통계 추적용, 선택)

    Returns:
        (new_trace_level, new_save_data)
    """
    from rich.panel import Panel
    from rich.text import Text

    event = pick_mystery(run_seed, node_position)

    console.clear()
    render_logo()

    header = Text("[ MYSTERY NODE ]", style="bold #FF8C00", justify="center")
    console.print(header)
    console.print()

    event_panel = Panel(
        f"[bold #FFD700]{event.title}[/bold #FFD700]\n\n"
        f"{event.description}\n\n"
        f"[dim]──────────────────────────────────────────────[/dim]\n"
        f"[bold white][A][/bold white] {event.engage_prompt}\n"
        f"[bold white][B][/bold white] 무시하고 다음 노드로 진행한다. (안전)",
        border_style="#FF8C00",
        title="[bold #FF8C00]정체불명 시스템 이벤트[/bold #FF8C00]",
    )
    console.print(event_panel)
    console.print()

    choice = ""
    while choice not in ("a", "b"):
        choice = Prompt.ask(
            "[bold #FF8C00]선택[/bold #FF8C00]",
            choices=["A", "B", "a", "b"],
            show_choices=False,
        ).strip().lower()

    if choice == "b":
        type_text(
            "[MYSTERY] 이벤트를 무시했다. 아무 일도 일어나지 않았다.",
            style="dim",
            delay=0.02,
        )
        if run_state is not None:
            run_state["mystery_skipped"] = run_state.get("mystery_skipped", 0) + 1
        _wait_for_enter()
        return trace_level, save_data

    # 개입 선택
    if run_state is not None:
        run_state["mystery_engaged"] = run_state.get("mystery_engaged", 0) + 1
    is_good = resolve_mystery_outcome(run_seed, node_position)
    if is_good and run_state is not None:
        run_state["mystery_good"] = run_state.get("mystery_good", 0) + 1
    new_trace, new_save_data, message = apply_mystery_outcome(
        event, is_good, trace_level, save_data
    )

    result_style = "bold green" if is_good else "bold red"
    type_text(message, style=result_style, delay=0.03)
    console.print(
        f"[{result_style}]추적도: {trace_level}% → {new_trace}%[/{result_style}]"
    )

    frag_before = int(save_data.get("data_fragments", 0))
    frag_after = int(new_save_data.get("data_fragments", 0))
    if frag_after != frag_before:
        delta = frag_after - frag_before
        sign = "+" if delta > 0 else ""
        console.print(
            f"[bold yellow]데이터 조각: {frag_before} → {frag_after} "
            f"({sign}{delta})[/bold yellow]"
        )

    _wait_for_enter()
    return new_trace, new_save_data


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
    }
    runtime = _build_runtime_modifiers(perks)
    trace_level = _apply_ascension_modifiers(ascension_level, runtime)

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
    total_positions = MAX_NODES_PER_RUN + 1  # 8 (regular 7 + boss 1)
    correct_answers = 0
    node_difficulties_cleared: list[str] = []
    backtrack_used = False

    current_node_type = NodeType.NORMAL
    combat_pool_idx = 0

    for position in range(total_positions):
        ntype = NodeType.BOSS if position == MAX_NODES_PER_RUN else current_node_type

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
                save_data, trace_level, run_seed, position, run_state
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
                        return correct_answers, False, "shutdown", node_difficulties_cleared, {"wrong_analyzes": run_state.get("wrong_analyzes", 0), "timeout_events": run_state.get("timeout_events", 0), "trace_final": trace_level, "skill_used": bool(run_state.get("active_skill_used", False)), "mystery_engaged": run_state.get("mystery_engaged", 0), "mystery_good": run_state.get("mystery_good", 0), "mystery_skipped": run_state.get("mystery_skipped", 0)}

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
                return correct_answers, False, "shutdown", node_difficulties_cleared, {"wrong_analyzes": run_state.get("wrong_analyzes", 0), "timeout_events": run_state.get("timeout_events", 0), "trace_final": trace_level, "skill_used": bool(run_state.get("active_skill_used", False)), "mystery_engaged": run_state.get("mystery_engaged", 0), "mystery_good": run_state.get("mystery_good", 0), "mystery_skipped": run_state.get("mystery_skipped", 0)}

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
    return correct_answers, True, "victory", node_difficulties_cleared, {"wrong_analyzes": run_state.get("wrong_analyzes", 0), "timeout_events": run_state.get("timeout_events", 0), "trace_final": trace_level, "skill_used": bool(run_state.get("active_skill_used", False)), "mystery_engaged": run_state.get("mystery_engaged", 0), "mystery_good": run_state.get("mystery_good", 0), "mystery_skipped": run_state.get("mystery_skipped", 0)}


def run_shop(save_data: dict[str, Any]) -> None:
    """로비 상점 루프를 실행한다."""
    valid_choices = list(PERK_MENU_MAP.keys()) + ["0"]

    while True:
        console.clear()
        render_shop(
            data_fragments=save_data["data_fragments"],
            perks=save_data["perks"],
            perk_prices=PERK_PRICES,
            perk_menu_map=PERK_MENU_MAP,
            perk_label_map=PERK_LABEL_MAP,
            perk_desc_map=PERK_DESC_MAP,
        )
        choice = Prompt.ask(
            "[bold green]구매할 특성 번호를 선택하세요 (0: 로비 복귀)[/bold green]",
            choices=valid_choices,
            default="0",
        )

        if choice == "0":
            return

        perk_key = PERK_MENU_MAP[choice]
        perk_label = PERK_LABEL_MAP.get(perk_key, perk_key)
        perk_price = PERK_PRICES.get(perk_key, 999999)

        if save_data["perks"].get(perk_key, False):
            console.print("[bold yellow]이미 구매한 특성입니다.[/bold yellow]")
            _wait_for_enter()
            continue

        if save_data["data_fragments"] < perk_price:
            console.print(
                f"[bold red]데이터 조각이 부족합니다. (필요: {perk_price})[/bold red]"
            )
            _wait_for_enter()
            continue

        prev_fragments = save_data["data_fragments"]
        prev_owned = save_data["perks"].get(perk_key, False)

        save_data["data_fragments"] -= perk_price
        save_data["perks"][perk_key] = True

        try:
            save_game(save_data)
            console.print(f"[bold green]특성 구매 완료: {perk_label}[/bold green]")
        except OSError as exc:
            save_data["data_fragments"] = prev_fragments
            save_data["perks"][perk_key] = prev_owned
            console.print(f"[bold red]{exc}[/bold red]")

        _wait_for_enter()


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
    run_state: dict[str, Any] = {
        "skip_next_penalty": False,
        "cleared_themes": set(),
        "wrong_analyzes": 0,
        "timeout_events": 0,
    }
    runtime = _build_runtime_modifiers(save_data["perks"])
    trace_level = _apply_ascension_modifiers(0, runtime)

    acquired_artifacts: list[Artifact] = []
    if selected_class is not None:
        apply_class_modifiers(selected_class, runtime, run_state)

    backtrack_used = False
    correct_answers = 0
    node_difficulties_cleared: list[str] = []
    combat_pool_idx = 0
    combat_result = "cleared"
    total_positions = MAX_NODES_PER_RUN + 1

    # 날짜 시드로 루트 선택지 결정 (재현성 보장)
    _rng_state = random.getstate()
    random.seed(get_daily_seed(today) ^ 0xABCDEF)
    route_choices = build_route_choices(MAX_NODES_PER_RUN - 1)
    random.setstate(_rng_state)  # 전역 random 상태 복원

    current_node_type = NodeType.NORMAL

    # ── 데일리 런 루프 ──────────────────────────────────────────────────────
    for position in range(total_positions):
        ntype = NodeType.BOSS if position == MAX_NODES_PER_RUN else current_node_type

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
                save_data, trace_level, daily_run_seed, position, run_state
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
                _offer_artifact(acquired_artifacts, runtime, run_state, source="ELITE", num_choices=3)

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
    """게임 전체 상태 머신 (로비 → 런/상점 → 로비)을 실행한다."""
    _initialize_argos_taunts()

    while True:
        save_data = load_save()

        console.clear()
        daily_state = get_daily_state(save_data)
        today_played = has_played_today(daily_state, get_today_str())
        ach_snap = get_achievement_snapshot(save_data.get("achievements", {}))
        render_lobby(
            data_fragments=save_data["data_fragments"],
            perks=save_data["perks"],
            campaign=save_data.get("campaign"),
            achievement_snapshot=ach_snap,
            daily_available=not today_played,
        )

        menu_choice = Prompt.ask(
            "[bold green]메뉴를 선택하세요[/bold green]",
            choices=["1", "2", "3", "4", "5"],
            default="1",
        )

        if menu_choice == "1":
            selected_class = _select_diver_class()
            selected_ascension = _select_ascension_level(save_data)
            correct_answers, is_victory, result, node_difficulties_cleared, run_stats = run_game_session(
                save_data["perks"],
                save_data,
                diver_class=selected_class,
                ascension_level=selected_ascension,
            )

            base_reward = calculate_base_reward(node_difficulties_cleared)
            reward = calculate_reward(
                correct_answers=correct_answers,
                is_victory=is_victory,
                node_difficulties=node_difficulties_cleared,
            )
            reward_before_asc = reward
            reward, reward_mult = _apply_ascension_reward_multiplier(
                reward,
                selected_ascension,
            )
            save_data["data_fragments"] += reward

            campaign_gain = 0
            campaign_update = {"just_cleared": False, "campaign": save_data.get("campaign", {})}
            if result != "aborted":
                campaign_gain = calculate_campaign_gain(reward, is_victory)
                campaign_update = update_campaign_progress(
                    save_data=save_data,
                    gain=campaign_gain,
                    is_victory=is_victory,
                    class_key=selected_class.value,
                    ascension_level=selected_ascension,
                )

            try:
                save_game(save_data)
            except OSError as exc:
                console.print(f"[bold red]{exc}[/bold red]")

            if result == "shutdown":
                console.print("[bold red]세션 종료: SYSTEM SHUTDOWN[/bold red]")
            elif result == "victory":
                console.print("[bold green]세션 종료: CORE BREACHED[/bold green]")
            else:
                console.print("[bold yellow]세션이 비정상적으로 중단되었습니다.[/bold yellow]")

            render_settlement_log(
                correct_answers=correct_answers,
                base_reward=base_reward,
                final_reward=reward,
                is_victory=is_victory,
                trace_final=run_stats.get("trace_final", -1),
            )
            if reward_mult < 1.0 and reward_before_asc != reward:
                console.print(
                    f"[bold yellow][ASCENSION TAX] 보상 배율 ×{reward_mult:.2f} 적용: "
                    f"{reward_before_asc} -> {reward}[/bold yellow]"
                )

            campaign_snapshot = get_campaign_progress_snapshot(campaign_update["campaign"])
            class_victories = campaign_snapshot["class_victories"]
            console.print(
                f"[bold #00FFFF][SYSTEM LOG] 캠페인 점수 +{campaign_gain} "
                f"→ {campaign_snapshot['points']}/{CAMPAIGN_CLEAR_POINTS}[/bold #00FFFF]"
            )
            console.print(
                f"[bold #00FFFF][SYSTEM LOG] 캠페인 승리: "
                f"{campaign_snapshot['victories']}/{CAMPAIGN_CLEAR_TOTAL_VICTORIES}[/bold #00FFFF]"
            )
            console.print(
                "[bold #00FFFF][SYSTEM LOG] 클래스 숙련: "
                f"ANALYST {class_victories.get('ANALYST', 0)}/{CAMPAIGN_CLEAR_CLASS_VICTORIES} | "
                f"GHOST {class_victories.get('GHOST', 0)}/{CAMPAIGN_CLEAR_CLASS_VICTORIES} | "
                f"CRACKER {class_victories.get('CRACKER', 0)}/{CAMPAIGN_CLEAR_CLASS_VICTORIES}"
                "[/bold #00FFFF]"
            )
            if campaign_update["just_cleared"]:
                render_alert(
                    "TRUE ENDING UNLOCKED - 100H CAMPAIGN CLEAR\n"
                    "ARGOS CORE 완전 침묵. 장기 침투 작전 종료."
                )

            # ── 엔딩 / 업적 평가 및 표시 ───────────────────────────────────────
            if result != "aborted":
                run_summary = {
                    "result": result,
                    "is_victory": is_victory,
                    "class_key": selected_class.value,
                    "ascension_level": selected_ascension,
                    "wrong_analyzes": run_stats.get("wrong_analyzes", 0),
                    "timeout_events": run_stats.get("timeout_events", 0),
                    "trace_final": run_stats.get("trace_final", 100),
                    "correct_answers": correct_answers,
                    "cleared_difficulties": node_difficulties_cleared,
                    "skill_used": bool(run_stats.get("skill_used", False)),
                    "mystery_engaged": run_stats.get("mystery_engaged", 0),
                    "mystery_good": run_stats.get("mystery_good", 0),
                    "mystery_skipped": run_stats.get("mystery_skipped", 0),
                }
                # 엔딩 판정
                triggered_ending = evaluate_ending(run_summary, save_data)
                if triggered_ending:
                    is_new_ending = record_ending_unlock(save_data, triggered_ending.ending_id)
                    render_ending(triggered_ending, is_new=is_new_ending)
                    try:
                        save_game(save_data)
                    except OSError as exc:
                        console.print(f"[bold red]{exc}[/bold red]")

                newly_unlocked = evaluate_achievements(save_data, run_summary)
                if newly_unlocked:
                    render_achievement_unlocks(newly_unlocked)
                    try:
                        save_game(save_data)
                    except OSError as exc:
                        console.print(f"[bold red]{exc}[/bold red]")

            _wait_for_enter("로비로 복귀하려면 Enter를 누르세요")
            continue

        if menu_choice == "2":
            run_shop(save_data)
            continue

        if menu_choice == "3":
            console.print("[bold white]세션을 종료합니다.[/bold white]")
            break

        if menu_choice == "4":
            run_daily_challenge(save_data)
            continue

        if menu_choice == "5":
            ach_snap = get_achievement_snapshot(save_data.get("achievements", {}))
            end_snap = get_endings_snapshot(save_data)
            camp_snap = get_campaign_progress_snapshot(save_data.get("campaign", {}))
            daily_snap = get_daily_state(save_data)
            render_records_screen(ach_snap, end_snap, camp_snap, daily_snap)
            _wait_for_enter("로비로 복귀하려면 Enter를 누르세요")
            continue


if __name__ == "__main__":
    run_lobby_loop()
