"""combat_commands.py 단위 테스트."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from combat_commands import calculate_analyze_penalty, handle_analyze, handle_cat_log, handle_skill
from diver_class import DiverClass
from route_map import NodeType


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _runtime(
    penalty_mult: float = 1.0,
    ascension_flat: int = 0,
    elite_cap: float = 1.5,
    boss_penalty_mult: float = 1.0,
    boss_penalty_cap: int | None = None,
) -> dict[str, Any]:
    return {
        "penalty_multiplier": penalty_mult,
        "ascension_penalty_flat": ascension_flat,
        "elite_penalty_cap": elite_cap,
        "ascension_boss_penalty_mult": boss_penalty_mult,
        "boss_penalty_cap": boss_penalty_cap,
    }


def _run_state(
    trace: int = 30,
    cracker_streak: int = 0,
    memory_echo: bool = False,
    cleared_themes: set[str] | None = None,
    trace_shield: bool = False,
    adaptive_shield: bool = False,
    analyst_hard_reduction: bool = False,
    skip_next: bool = False,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "current_trace": trace,
        "cracker_streak": cracker_streak,
        "wrong_analyzes": 0,
    }
    if memory_echo:
        state["memory_echo_active"] = True
        state["cleared_themes"] = cleared_themes or set()
    if trace_shield:
        state["trace_shield_active"] = True
    if adaptive_shield:
        state["adaptive_shield_active"] = True
    if analyst_hard_reduction:
        state["analyst_hard_penalty_reduction"] = True
    if skip_next:
        state["skip_next_penalty"] = True
    return state


def _scenario(penalty_rate: int = 20, difficulty: str = "Easy", theme: str = "A") -> dict[str, Any]:
    return {
        "node_id": 1,
        "theme": theme,
        "difficulty": difficulty,
        "text_log": "수사 조서 내용",
        "target_keyword": "GPS",
        "penalty_rate": penalty_rate,
        "is_boss": False,
    }


# ── calculate_analyze_penalty — 기본 ─────────────────────────────────────────

def test_penalty_returns_base_when_no_modifiers() -> None:
    applied, raw, mem_echo, boss_cap = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert applied == 20
    assert raw == 20
    assert mem_echo is False
    assert boss_cap is False


def test_penalty_adds_ascension_flat() -> None:
    applied, raw, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(ascension_flat=5),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert applied == 25
    assert raw == 25


def test_penalty_applies_elite_multiplier() -> None:
    applied, raw, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.ELITE,
        diver_class=None,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert applied == 30   # 20 × 1.5
    assert raw == 30


def test_penalty_applies_boss_multiplier() -> None:
    applied, raw, _, boss_cap = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(boss_penalty_mult=1.35),
        node_type=NodeType.BOSS,
        diver_class=None,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert raw == 27   # 20 × 1.35
    assert applied == 27
    assert boss_cap is False


def test_penalty_applies_boss_cap() -> None:
    applied, raw, _, boss_cap = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(boss_penalty_mult=1.5, boss_penalty_cap=25),
        node_type=NodeType.BOSS,
        diver_class=None,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert raw == 30
    assert applied == 25
    assert boss_cap is True


def test_ghost_reduces_penalty_via_penalty_multiplier() -> None:
    runtime = _runtime(penalty_mult=0.8)
    applied, raw, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=runtime,
        node_type=NodeType.NORMAL,
        diver_class=DiverClass.GHOST,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert applied == 16   # 20 × 0.8


def test_cracker_streak_reduces_penalty() -> None:
    # streak 4 → multiplier 0.80
    applied, raw, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=DiverClass.CRACKER,
        run_state=_run_state(cracker_streak=4),
        scenario_theme="A",
    )
    assert applied == 16   # 20 × 0.80


def test_analyst_reduces_penalty_on_hard() -> None:
    applied, raw, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=DiverClass.ANALYST,
        run_state=_run_state(analyst_hard_reduction=True),
        scenario_theme="A",
        scenario_difficulty="Hard",
    )
    assert applied == 18   # 20 × 0.9


def test_memory_echo_reduces_penalty_on_cleared_theme() -> None:
    applied, raw, mem_echo, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(memory_echo=True, cleared_themes={"A"}),
        scenario_theme="A",
    )
    assert applied == 16   # 20 × 0.8
    assert mem_echo is True


def test_memory_echo_not_applied_for_uncleared_theme() -> None:
    applied, raw, mem_echo, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(memory_echo=True, cleared_themes={"B"}),
        scenario_theme="A",
    )
    assert applied == 20
    assert mem_echo is False


def test_trace_shield_reduces_penalty_above_70() -> None:
    applied, raw, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(trace=75, trace_shield=True),
        scenario_theme="A",
    )
    assert applied == 16   # 20 × 0.8


def test_trace_shield_not_applied_below_70() -> None:
    applied, _, _, _ = calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(trace=50, trace_shield=True),
        scenario_theme="A",
    )
    assert applied == 20


def test_penalty_minimum_is_one() -> None:
    # 매우 낮은 base penalty라도 최솟값은 1
    applied, _, _, _ = calculate_analyze_penalty(
        base_penalty=0,
        runtime=_runtime(penalty_mult=0.1),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state=_run_state(),
        scenario_theme="A",
    )
    assert applied >= 1


# ── handle_cat_log ────────────────────────────────────────────────────────────

def test_cat_log_extends_timer_when_echo_cache_active_and_not_used(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())

    extended_by: list[int] = []
    run_state = {"echo_cache_active": True}
    type_text_mock = MagicMock()
    monkeypatch.setattr("combat_commands.type_text", type_text_mock, raising=False)

    result = handle_cat_log(
        scenario=_scenario(),
        run_state=run_state,
        echo_cache_used=False,
        timer_has_fired=False,
        extend_timeout_fn=lambda secs: extended_by.append(secs),
    )
    assert result is True          # echo_cache_used 플래그가 True로 바뀜
    assert 2 in extended_by        # 2초 연장


def test_cat_log_does_not_extend_timer_when_already_used(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.type_text", MagicMock(), raising=False)

    extended_by: list[int] = []
    run_state = {"echo_cache_active": True}
    result = handle_cat_log(
        scenario=_scenario(),
        run_state=run_state,
        echo_cache_used=True,
        timer_has_fired=False,
        extend_timeout_fn=lambda secs: extended_by.append(secs),
    )
    assert result is True          # 이미 사용됐으므로 플래그 유지
    assert not extended_by         # 연장 없음


def test_cat_log_does_not_extend_timer_when_fired(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.type_text", MagicMock(), raising=False)

    extended_by: list[int] = []
    run_state = {"echo_cache_active": True}
    result = handle_cat_log(
        scenario=_scenario(),
        run_state=run_state,
        echo_cache_used=False,
        timer_has_fired=True,
        extend_timeout_fn=lambda secs: extended_by.append(secs),
    )
    assert result is False         # timer가 이미 발동 → 연장 안 됨
    assert not extended_by


# ── handle_skill ─────────────────────────────────────────────────────────────

def test_handle_skill_with_no_diver_class_returns_unchanged_trace(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    run_state = {"active_skill_available": True, "active_skill_used": False}
    new_trace = handle_skill(
        diver_class=None,
        trace_level=40,
        runtime=_runtime(),
        run_state=run_state,
        scenario=_scenario(),
    )
    assert new_trace == 40


def test_handle_skill_when_already_used_returns_unchanged_trace(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    run_state = {"active_skill_available": False, "active_skill_used": True}
    new_trace = handle_skill(
        diver_class=DiverClass.GHOST,
        trace_level=40,
        runtime=_runtime(),
        run_state=run_state,
        scenario=_scenario(),
    )
    assert new_trace == 40


def test_handle_skill_ghost_reduces_trace(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    run_state = {"active_skill_available": True, "active_skill_used": False}
    new_trace = handle_skill(
        diver_class=DiverClass.GHOST,
        trace_level=40,
        runtime=_runtime(),
        run_state=run_state,
        scenario=_scenario(),
    )
    assert new_trace == 25   # 40 - 15


# ── handle_analyze — 정답 경로 ───────────────────────────────────────────────

def test_handle_analyze_correct_answer_returns_cleared(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    scenario = _scenario()
    run_state = _run_state()
    action, trace, _, difficulty = handle_analyze(
        command_raw="analyze GPS",
        scenario=scenario,
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert action == "cleared"
    assert difficulty == "Easy"


def test_handle_analyze_correct_answer_case_insensitive(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    scenario = _scenario()  # target_keyword = "GPS"
    action, *_ = handle_analyze(
        command_raw="analyze gps",
        scenario=scenario,
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=_run_state(),
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert action == "cleared"


# ── handle_analyze — 오답 경로 ───────────────────────────────────────────────

def test_handle_analyze_wrong_answer_increases_trace(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    scenario = _scenario(penalty_rate=20)
    run_state = _run_state(trace=30)
    action, trace, _, _ = handle_analyze(
        command_raw="analyze WRONG",
        scenario=scenario,
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert action == "continue"
    assert trace == 50   # 30 + 20


def test_handle_analyze_wrong_answer_increments_wrong_count(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    run_state = _run_state(trace=30)
    handle_analyze(
        command_raw="analyze WRONG",
        scenario=_scenario(),
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert run_state["wrong_analyzes"] == 1


def test_handle_analyze_skip_next_penalty_skips_trace_increase(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    run_state = _run_state(trace=30, skip_next=True)
    action, trace, _, _ = handle_analyze(
        command_raw="analyze WRONG",
        scenario=_scenario(penalty_rate=30),
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert action == "continue"
    assert trace == 30   # 페널티 면제


def test_handle_analyze_death_when_trace_reaches_100(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    run_state = _run_state(trace=90)

    def _death(tl: int, bu: bool) -> tuple[int, bool, bool]:
        return tl, bu, False  # 사망 처리, survived=False

    action, trace, _, _ = handle_analyze(
        command_raw="analyze WRONG",
        scenario=_scenario(penalty_rate=20),
        trace_level=90,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=_death,
    )
    assert action == "death"


def test_handle_analyze_no_keyword_returns_continue(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())

    action, trace, _, _ = handle_analyze(
        command_raw="analyze",
        scenario=_scenario(),
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=_run_state(),
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert action == "continue"
    assert trace == 30   # 변화 없음


def test_handle_analyze_cascade_core_streak_increments_on_correct(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    run_state = _run_state()
    run_state["cascade_core_active"] = True
    run_state["cascade_streak"] = 0

    handle_analyze(
        command_raw="analyze GPS",
        scenario=_scenario(),
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
    )
    assert run_state["cascade_streak"] == 1


def test_handle_analyze_chrono_anchor_extends_timer_on_survival(monkeypatch) -> None:
    monkeypatch.setattr("combat_commands.console", MagicMock())
    monkeypatch.setattr("combat_commands.print_argos_message", MagicMock(), raising=False)

    extended_by: list[int] = []
    run_state = _run_state(trace=30)
    run_state["on_wrong_time_restore"] = 5

    handle_analyze(
        command_raw="analyze WRONG",
        scenario=_scenario(penalty_rate=10),
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=_runtime(),
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=lambda: None,
        handle_death_fn=lambda tl, bu: (tl, bu, True),
        extend_timeout_fn=lambda secs: extended_by.append(secs),
    )
    assert 5 in extended_by
