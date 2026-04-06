"""Combat penalty calculation regression tests."""

from diver_class import DiverClass
from main import _calculate_analyze_penalty
from route_map import NodeType


def _runtime(**overrides: float | int) -> dict[str, float | int]:
    runtime: dict[str, float | int] = {
        "penalty_multiplier": 1.0,
        "elite_penalty_cap": 1.5,
    }
    runtime.update(overrides)
    return runtime


def test_penalty_base_case_without_modifiers() -> None:
    applied, raw, memory_applied, boss_cap_applied = _calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state={},
        scenario_theme="General",
    )
    assert applied == 20
    assert raw == 20
    assert memory_applied is False
    assert boss_cap_applied is False


def test_penalty_applies_elite_multiplier_cap() -> None:
    applied, raw, memory_applied, boss_cap_applied = _calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(elite_penalty_cap=1.2),
        node_type=NodeType.ELITE,
        diver_class=None,
        run_state={},
        scenario_theme="General",
    )
    assert applied == 24
    assert raw == 24
    assert memory_applied is False
    assert boss_cap_applied is False


def test_penalty_stacks_cracker_and_memory_echo() -> None:
    run_state = {
        "cracker_streak": 2,  # 10% reduction -> x0.9
        "memory_echo_active": True,
        "cleared_themes": {"Vault"},
    }
    applied, raw, memory_applied, boss_cap_applied = _calculate_analyze_penalty(
        base_penalty=20,
        runtime=_runtime(),
        node_type=NodeType.NORMAL,
        diver_class=DiverClass.CRACKER,
        run_state=run_state,
        scenario_theme="Vault",
    )
    # 20 * 0.9 * 0.8 = 14.4 -> int 14
    assert applied == 14
    assert raw == 14
    assert memory_applied is True
    assert boss_cap_applied is False


def test_penalty_applies_boss_cap() -> None:
    applied, raw, memory_applied, boss_cap_applied = _calculate_analyze_penalty(
        base_penalty=80,
        runtime=_runtime(boss_penalty_cap=40),
        node_type=NodeType.BOSS,
        diver_class=None,
        run_state={},
        scenario_theme="Core",
    )
    assert applied == 40
    assert raw == 80
    assert memory_applied is False
    assert boss_cap_applied is True


def test_penalty_has_minimum_floor_of_one() -> None:
    applied, raw, memory_applied, boss_cap_applied = _calculate_analyze_penalty(
        base_penalty=1,
        runtime=_runtime(penalty_multiplier=0.05),
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state={},
        scenario_theme="General",
    )
    assert applied == 1
    assert raw == 1
    assert memory_applied is False
    assert boss_cap_applied is False
