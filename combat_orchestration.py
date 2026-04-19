"""전투·MYSTERY·런 중간 상점 노드 실행 모듈.

_run_combat_node, _run_mystery_node, _run_mid_run_shop 및 관련 헬퍼를 캡슐화한다.
main.py의 run_game_session / run_daily_challenge에서 임포트해 사용한다.
"""

import math
import re
import random
import threading
import time
from typing import Any

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from artifact_system import Artifact, apply_artifact_effect, draw_artifacts
from combat_commands import (
    handle_analyze,
    handle_cat_log,
    handle_help,
    handle_ls,
    handle_skill,
)
from combat_timer import CombatTimer
from constants import (
    MAX_NODES_PER_RUN,
    MID_SHOP_BUFFER_COST,
    MID_SHOP_TRACE_COST,
    MID_SHOP_TRACE_HEAL,
    REST_HEAL_AMOUNT,
    TIMEOUT_PENALTY,
    TRACE_MAX,
)
from diver_class import DiverClass, get_class_profile, on_node_clear
from mutator_system import apply_glitch_masking
from mystery_system import apply_mystery_outcome, pick_mystery, resolve_mystery_outcome
from route_map import NodeType
from ui_renderer import (
    console,
    print_argos_message,
    render_alert,
    render_artifact_hud,
    render_artifact_selection,
    render_info_panel,
    render_logo,
    render_route_choice,
    type_text,
    wait_for_enter,
)


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _get_mid_shop_costs(runtime: dict[str, Any]) -> tuple[int, int, float]:
    """런 중간 상점 아이템 비용을 ascension 배율 포함해 계산한다."""
    cost_mult = max(1.0, float(runtime.get("ascension_shop_cost_mult", 1.0)))
    trace_cost = max(1, math.ceil(MID_SHOP_TRACE_COST * cost_mult))
    buffer_cost = max(1, math.ceil(MID_SHOP_BUFFER_COST * cost_mult))
    return trace_cost, buffer_cost, cost_mult


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
    """추적도 페널티를 적용한 뒤 사망 처리를 수행한다."""
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


def _check_boss_command_block(
    command_name: str,
    node_type: NodeType,
    boss_phase_index: int,
    block_from_phase: int,
    trace_level: int,
    violation_penalty: int,
    perks: dict[str, bool],
    backtrack_used: bool,
    run_state: dict[str, Any],
    timer: threading.Timer | None,
) -> tuple[int, bool, bool, bool]:
    """
    ASC20 보스 명령 차단 여부를 확인하고 패널티를 적용한다.

    Returns:
        (trace_level, backtrack_used, survived, was_blocked)
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
    """ASC20 보스 페이즈 데이터팩 오버라이드를 현재 시나리오에 적용한다."""
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
        console.print("[bold red]>>> BOSS NODE — 최종 방어 계층 접근 중 <<<[/bold red]")
    elif is_elite:
        console.print("[bold yellow]>>> ELITE NODE — 고위험 구역 진입 <<<[/bold yellow]")

    if acquired_artifacts:
        render_artifact_hud(acquired_artifacts)


def _offer_artifact(
    acquired_artifacts: list[Artifact],
    runtime: dict[str, Any],
    run_state: dict[str, Any],
    source: str = "ELITE",
    num_choices: int = 3,
) -> None:
    """아티팩트 선택 UI를 표시하고, 선택된 아티팩트를 acquired_artifacts에 추가한다."""
    exclude_ids = [a.artifact_id for a in acquired_artifacts]
    candidates = draw_artifacts(num_choices, exclude_ids=exclude_ids)

    if not candidates:
        console.print("[bold yellow]획득 가능한 아티팩트가 없습니다.[/bold yellow]")
        wait_for_enter()
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
    run_state.setdefault("timeline", []).append({
        "event": "artifact",
        "node": int(run_state.get("current_node", 0)),
        "detail": chosen.name,
    })
    wait_for_enter()


# ── 메인 노드 실행 함수들 ──────────────────────────────────────────────────────

def run_combat_node(
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
        1, int(runtime.get("ascension_boss_block_cat_log_from_phase", 99))
    )
    boss_block_skill_from_phase = max(
        1, int(runtime.get("ascension_boss_block_skill_from_phase", 99))
    )
    boss_command_violation_penalty = max(
        0, int(runtime.get("ascension_boss_command_violation_penalty", 0))
    )
    boss_fake_keyword_count = max(
        0, int(runtime.get("ascension_boss_fake_keyword_count", 0))
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

    if scenario["difficulty"].upper() == "NIGHTMARE" and perks.get("lexical_assist"):
        target_str = str(scenario.get("target_keyword", ""))
        hint_char = target_str[0] if target_str else "?"
        console.print(
            f"[bold #00FFFF][LEXICAL ASSIST] 키워드 첫 글자: '{hint_char}'[/bold #00FFFF]"
        )

    if run_state.get("analyst_hint_active"):
        kw = str(scenario.get("target_keyword", ""))
        console.print(
            f"[bold cyan][ANALYST] 키워드 글자 수: {len(kw)}자[/bold cyan]"
        )

    type_text(glitched_log, style="white", delay=0.02)

    active_skill_name = (
        get_class_profile(diver_class).active_name if diver_class is not None else ""
    )

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

        if timer.has_fired and not timeout_penalty_applied:
            timeout_penalty_applied = True
            run_state["timeout_events"] = int(run_state.get("timeout_events", 0)) + 1
            trace_level += effective_timeout_penalty
            console.print(
                f"[bold white]TRACE +{effective_timeout_penalty}% -> {trace_level}%[/bold white]"
            )
            run_state.setdefault("timeline", []).append({
                "event": "timeout",
                "node": position + 1,
                "detail": f"+{effective_timeout_penalty}%",
            })
            if trace_level >= TRACE_MAX:
                trace_level, backtrack_used, survived = _handle_death(trace_level, backtrack_used)
                if not survived:
                    return trace_level, backtrack_used, "death", None

        if not command_raw:
            continue

        command_lower = command_raw.lower()

        if command_lower == "help":
            _print_help(active_skill_name=active_skill_name)
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
                extend_timeout_fn=timer.extend,
            )
            if action == "death":
                return trace_level, backtrack_used, "death", None
            if action == "cleared":
                return trace_level, backtrack_used, "cleared", difficulty
            continue

        console.print("[bold yellow]명령어를 찾을 수 없습니다. 'help'를 입력하세요.[/bold yellow]")

    timer.cancel()
    return trace_level, backtrack_used, "death", None


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


def run_mystery_node(
    save_data: dict[str, Any],
    trace_level: int,
    run_seed: int,
    node_position: int,
    run_state: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """
    미스터리 노드를 실행하고 업데이트된 (trace_level, save_data)를 반환한다.

    플레이어는 [A] 개입 또는 [B] 무시를 선택한다.
    """
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
            run_state.setdefault("timeline", []).append({
                "event": "mystery_skip",
                "node": node_position + 1,
                "detail": event.title,
            })
        wait_for_enter()
        return trace_level, save_data

    if run_state is not None:
        run_state["mystery_engaged"] = run_state.get("mystery_engaged", 0) + 1
    is_good = resolve_mystery_outcome(run_seed, node_position)
    if is_good and run_state is not None:
        run_state["mystery_good"] = run_state.get("mystery_good", 0) + 1
    new_trace, new_save_data, message = apply_mystery_outcome(
        event, is_good, trace_level, save_data
    )

    if not is_good and runtime is not None:
        fail_mult = runtime.get("mystery_fail_penalty_mult", 1.0)
        if fail_mult < 1.0:
            raw_delta = event.bad_trace_delta
            reduced_delta = max(0, int(raw_delta * fail_mult))
            new_trace = min(100, max(0, trace_level + reduced_delta))

    if run_state is not None and run_state.get("neural_override_active") and new_trace >= 90:
        new_trace = max(0, new_trace - 10)
        run_state["neural_override_active"] = False

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
        if run_state is not None and delta > 0:
            run_state["mystery_frags_gained"] = (
                int(run_state.get("mystery_frags_gained", 0)) + delta
            )

    if run_state is not None:
        outcome_str = "좋은 결과" if is_good else "나쁜 결과"
        run_state.setdefault("timeline", []).append({
            "event": "mystery_engage",
            "node": node_position + 1,
            "detail": f"{event.title} ({outcome_str})",
        })

    wait_for_enter()
    return new_trace, new_save_data


def run_mid_run_shop(
    save_data: dict[str, Any],
    trace_level: int,
    run_state: dict[str, Any],
    runtime: dict[str, Any],
) -> int:
    """런 중간 상점을 실행하고 업데이트된 trace_level을 반환한다."""
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
                wait_for_enter()
                continue
            if save_data["data_fragments"] < trace_cost:
                console.print(
                    f"[bold red]데이터 조각이 부족합니다. (필요: {trace_cost})[/bold red]"
                )
                wait_for_enter()
                continue
            heal_amount = min(MID_SHOP_TRACE_HEAL, trace_level)
            trace_level -= heal_amount
            save_data["data_fragments"] -= trace_cost
            console.print(
                f"[bold cyan]추적도 -{heal_amount}% 회복. 현재 추적도: {trace_level}%[/bold cyan]"
            )
            wait_for_enter()

        elif choice == "2":
            if has_buffer:
                console.print("[bold yellow]이미 오답 면역 쉴드가 활성화되어 있습니다.[/bold yellow]")
                wait_for_enter()
                continue
            if save_data["data_fragments"] < buffer_cost:
                console.print(
                    f"[bold red]데이터 조각이 부족합니다. (필요: {buffer_cost})[/bold red]"
                )
                wait_for_enter()
                continue
            run_state["skip_next_penalty"] = True
            save_data["data_fragments"] -= buffer_cost
            console.print("[bold cyan]오답 면역 쉴드 활성화. 다음 오답 1회 페널티 면제.[/bold cyan]")
            wait_for_enter()
