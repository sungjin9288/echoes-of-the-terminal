"""diver_class.py 단위 테스트."""

from typing import Any

import pytest

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


def _runtime() -> dict[str, Any]:
    return {"penalty_multiplier": 1.0, "timeout_penalty": 10}


def _run_state() -> dict[str, Any]:
    return {}


# ── get_class_profile ─────────────────────────────────────────────────────────

def test_get_class_profile_returns_analyst_profile() -> None:
    profile = get_class_profile(DiverClass.ANALYST)
    assert profile.diver_class == DiverClass.ANALYST
    assert profile.name == "애널리스트"
    assert profile.active_cooldown == 0


def test_get_class_profile_all_classes_registered() -> None:
    for cls in DiverClass:
        profile = get_class_profile(cls)
        assert profile.diver_class == cls
        assert profile.active_name
        assert profile.active_desc


def test_class_profiles_covers_all_classes() -> None:
    assert set(CLASS_PROFILES.keys()) == set(DiverClass)


def test_class_menu_map_has_three_entries() -> None:
    assert set(CLASS_MENU_MAP.values()) == set(DiverClass)


# ── apply_class_modifiers — GHOST ─────────────────────────────────────────────

def test_ghost_reduces_penalty_multiplier() -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(DiverClass.GHOST, runtime, run_state)
    assert abs(runtime["penalty_multiplier"] - 0.8) < 1e-9


def test_ghost_sets_timeout_penalty_to_six() -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(DiverClass.GHOST, runtime, run_state)
    assert runtime["timeout_penalty"] == 6


def test_ghost_sets_rest_heal_bonus() -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(DiverClass.GHOST, runtime, run_state)
    assert runtime["rest_heal_bonus_class"] == 15


# ── apply_class_modifiers — ANALYST ──────────────────────────────────────────

def test_analyst_sets_hint_flags_in_run_state() -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(DiverClass.ANALYST, runtime, run_state)
    assert run_state["analyst_hint_active"] is True
    assert run_state["analyst_wrong_hint_active"] is True
    assert run_state["analyst_hard_penalty_reduction"] is True


def test_analyst_does_not_modify_penalty_multiplier() -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(DiverClass.ANALYST, runtime, run_state)
    assert runtime["penalty_multiplier"] == 1.0


# ── apply_class_modifiers — CRACKER ──────────────────────────────────────────

def test_cracker_initialises_streak_and_elite_bonus() -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(DiverClass.CRACKER, runtime, run_state)
    assert run_state["cracker_streak"] == 0
    assert runtime["elite_artifact_bonus"] == 1


# ── apply_class_modifiers — all classes ──────────────────────────────────────

@pytest.mark.parametrize("cls", list(DiverClass))
def test_all_classes_enable_active_skill(cls: DiverClass) -> None:
    runtime = _runtime()
    run_state = _run_state()
    apply_class_modifiers(cls, runtime, run_state)
    assert run_state["active_skill_available"] is True
    assert run_state["active_skill_used"] is False


# ── use_active_skill ──────────────────────────────────────────────────────────

def test_ghost_skill_reduces_trace_level() -> None:
    run_state = {"active_skill_available": True, "active_skill_used": False}
    new_trace, hint = use_active_skill(DiverClass.GHOST, 40, _runtime(), run_state)
    assert new_trace == 25
    assert "추적도 -15%" in (hint or "")


def test_ghost_skill_clamps_at_zero() -> None:
    run_state = {"active_skill_available": True, "active_skill_used": False}
    new_trace, _ = use_active_skill(DiverClass.GHOST, 5, _runtime(), run_state)
    assert new_trace == 0


def test_analyst_skill_returns_keyword_hint() -> None:
    run_state = {"active_skill_available": True, "active_skill_used": False}
    scenario = {"target_keyword": "GPS"}
    new_trace, hint = use_active_skill(DiverClass.ANALYST, 30, _runtime(), run_state, scenario)
    assert new_trace == 30
    assert "GP" in (hint or "")


def test_analyst_skill_without_scenario_returns_none_hint() -> None:
    run_state = {"active_skill_available": True, "active_skill_used": False}
    _, hint = use_active_skill(DiverClass.ANALYST, 30, _runtime(), run_state, None)
    assert hint is None


def test_cracker_skill_sets_skip_next_penalty() -> None:
    run_state = {"active_skill_available": True, "active_skill_used": False}
    new_trace, hint = use_active_skill(DiverClass.CRACKER, 50, _runtime(), run_state)
    assert new_trace == 50
    assert run_state.get("skip_next_penalty") is True
    assert hint is not None


def test_skill_not_fired_when_already_used() -> None:
    run_state = {"active_skill_available": False, "active_skill_used": True}
    new_trace, hint = use_active_skill(DiverClass.GHOST, 40, _runtime(), run_state)
    assert new_trace == 40
    assert hint is None


def test_skill_marks_used_flag_after_activation() -> None:
    run_state = {"active_skill_available": True, "active_skill_used": False}
    use_active_skill(DiverClass.GHOST, 30, _runtime(), run_state)
    assert run_state["active_skill_used"] is True
    assert run_state["active_skill_available"] is False


# ── on_node_clear ─────────────────────────────────────────────────────────────

def test_cracker_on_node_clear_increments_streak() -> None:
    run_state = {"cracker_streak": 2}
    on_node_clear(DiverClass.CRACKER, 30, {"difficulty": "Easy"}, run_state)
    assert run_state["cracker_streak"] == 3


def test_cracker_streak_caps_at_five() -> None:
    run_state = {"cracker_streak": 5}
    on_node_clear(DiverClass.CRACKER, 30, {"difficulty": "Easy"}, run_state)
    assert run_state["cracker_streak"] == 5


def test_analyst_on_node_clear_does_not_change_trace() -> None:
    run_state: dict[str, Any] = {}
    result = on_node_clear(DiverClass.ANALYST, 25, {"difficulty": "Hard"}, run_state)
    assert result == 25


# ── get_cracker_penalty_reduction ─────────────────────────────────────────────

def test_cracker_penalty_reduction_at_streak_zero() -> None:
    assert get_cracker_penalty_reduction({"cracker_streak": 0}) == 1.0


def test_cracker_penalty_reduction_at_streak_two() -> None:
    # 2스택 → 1.0 - 0.10 = 0.90
    result = get_cracker_penalty_reduction({"cracker_streak": 2})
    assert abs(result - 0.90) < 1e-9


def test_cracker_penalty_reduction_capped_at_0_75() -> None:
    # 5스택이면 1.0 - 0.25 = 0.75
    result = get_cracker_penalty_reduction({"cracker_streak": 5})
    assert result == 0.75


def test_cracker_penalty_reduction_minimum_floor() -> None:
    # 스택이 999여도 최솟값은 0.75
    result = get_cracker_penalty_reduction({"cracker_streak": 999})
    assert result == 0.75
