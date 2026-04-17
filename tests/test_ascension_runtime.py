"""Ascension runtime modifier tests."""

from main import (
    _apply_ascension_modifiers,
    _apply_ascension_reward_multiplier,
    _calculate_analyze_penalty,
    _get_boss_phase_runtime,
    _mutate_route_choices_for_ascension,
)
from combat_orchestration import (
    _apply_asc20_boss_phase_override,
    _build_boss_fake_keywords,
    _get_mid_shop_costs,
)
from progression_system import get_ascension_profile
from route_map import NodeType


def _runtime() -> dict[str, float | int | None]:
    return {
        "penalty_multiplier": 1.0,
        "time_limit_seconds": 30,
        "timeout_penalty": 10,
        "elite_penalty_cap": 1.5,
        "glitch_word_count": None,
    }


def test_apply_ascension_level_zero_keeps_defaults() -> None:
    runtime = _runtime()
    start_trace = _apply_ascension_modifiers(0, runtime)
    assert start_trace == 0
    assert runtime["time_limit_seconds"] == 30
    assert runtime["timeout_penalty"] == 10
    assert runtime["ascension_penalty_flat"] == 0
    assert runtime["ascension_shop_cost_mult"] == 1.0
    assert runtime["ascension_reward_mult"] == 1.0
    assert runtime["ascension_boss_penalty_mult"] == 1.0
    assert runtime["ascension_boss_phases"] == 1
    assert runtime["ascension_boss_block_cat_log_from_phase"] == 99
    assert runtime["ascension_boss_block_skill_from_phase"] == 99
    assert runtime["ascension_boss_command_violation_penalty"] == 0
    assert runtime["ascension_boss_fake_keyword_count"] == 0


def test_apply_ascension_level_three_shortens_time() -> None:
    runtime = _runtime()
    start_trace = _apply_ascension_modifiers(3, runtime)
    assert start_trace == 0
    assert runtime["time_limit_seconds"] == 10
    assert runtime["ascension_penalty_flat"] == 5
    assert runtime["ascension_force_easy_glitch"] is True


def test_apply_ascension_level_five_starts_with_trace_twenty() -> None:
    runtime = _runtime()
    start_trace = _apply_ascension_modifiers(5, runtime)
    assert start_trace == 20
    assert runtime["timeout_penalty"] == 14


def test_calculate_penalty_includes_ascension_flat_bonus() -> None:
    runtime = _runtime()
    runtime["ascension_penalty_flat"] = 5
    applied, raw, memory_applied, boss_cap_applied = _calculate_analyze_penalty(
        base_penalty=20,
        runtime=runtime,
        node_type=NodeType.NORMAL,
        diver_class=None,
        run_state={},
        scenario_theme="General",
    )
    assert applied == 25
    assert raw == 25
    assert memory_applied is False
    assert boss_cap_applied is False


def test_get_ascension_profile_clamps_out_of_range_level() -> None:
    low = get_ascension_profile(-5)
    high = get_ascension_profile(999)
    assert low["level"] == 0
    assert high["level"] == 20


def test_get_ascension_profile_high_tier_modifiers() -> None:
    lvl10 = get_ascension_profile(10)
    lvl15 = get_ascension_profile(15)
    lvl20 = get_ascension_profile(20)

    assert lvl10["shop_cost_mult"] == 1.15
    assert lvl10["reward_mult"] == 0.95
    assert lvl10["boss_penalty_mult"] == 1.10
    assert lvl10["boss_phases"] == 1
    assert lvl10["route_min_elite_choices"] == 0

    assert lvl15["shop_cost_mult"] == 1.30
    assert lvl15["reward_mult"] == 0.90
    assert lvl15["boss_penalty_mult"] == 1.20
    assert lvl15["boss_phases"] == 1
    assert lvl15["route_min_elite_choices"] == 2

    assert lvl20["shop_cost_mult"] == 1.50
    assert lvl20["reward_mult"] == 0.85
    assert lvl20["boss_penalty_mult"] == 1.35
    assert lvl20["boss_phases"] == 3
    assert lvl20["boss_phase_time_delta"] == -2
    assert lvl20["boss_phase_penalty_step"] == 0.12
    assert lvl20["boss_block_cat_log_from_phase"] == 2
    assert lvl20["boss_block_skill_from_phase"] == 3
    assert lvl20["boss_command_violation_penalty"] == 4
    assert lvl20["boss_fake_keyword_count"] == 4
    assert lvl20["route_min_elite_choices"] == 3


def test_calculate_penalty_applies_ascension_boss_multiplier() -> None:
    runtime = _runtime()
    runtime["ascension_boss_penalty_mult"] = 1.35
    applied, raw, _, _ = _calculate_analyze_penalty(
        base_penalty=20,
        runtime=runtime,
        node_type=NodeType.BOSS,
        diver_class=None,
        run_state={},
        scenario_theme="Boss",
    )
    assert raw == 27
    assert applied == 27


def test_mid_shop_costs_scale_with_ascension_multiplier() -> None:
    runtime = _runtime()
    runtime["ascension_shop_cost_mult"] = 1.30
    trace_cost, buffer_cost, mult = _get_mid_shop_costs(runtime)
    assert mult == 1.30
    assert trace_cost == 20
    assert buffer_cost == 33


def test_apply_ascension_reward_multiplier_reduces_reward() -> None:
    adjusted, mult = _apply_ascension_reward_multiplier(100, 20)
    assert mult == 0.85
    assert adjusted == 85


def test_get_boss_phase_runtime_scales_penalty_and_time() -> None:
    runtime = _runtime()
    runtime["ascension_boss_penalty_mult"] = 1.2
    runtime["ascension_boss_phases"] = 3
    runtime["ascension_boss_phase_time_delta"] = -2
    runtime["ascension_boss_phase_penalty_step"] = 0.1

    phase1 = _get_boss_phase_runtime(runtime, 1)
    phase3 = _get_boss_phase_runtime(runtime, 3)

    assert phase1["boss_phase_index"] == 1
    assert phase1["boss_phase_total"] == 3
    assert phase1["ascension_boss_penalty_mult"] == 1.2
    assert phase1["time_limit_seconds"] == 30

    assert phase3["boss_phase_index"] == 3
    assert phase3["boss_phase_total"] == 3
    assert abs(float(phase3["ascension_boss_penalty_mult"]) - 1.44) < 1e-9
    assert phase3["time_limit_seconds"] == 26


def test_build_boss_fake_keywords_excludes_target(monkeypatch) -> None:
    monkeypatch.setattr("main.random.sample", lambda seq, k: list(seq)[:k])
    text_log = "argos protocol vector breach signal terminal core memory"
    fake = _build_boss_fake_keywords(text_log, "core", 3)
    assert fake == ["argos", "breach", "memory"]
    assert "core" not in fake


def test_apply_asc20_boss_phase_override_replaces_text_and_keyword() -> None:
    scenario = {
        "node_id": 999,
        "is_boss": True,
        "text_log": "base-log",
        "target_keyword": "base-kw",
        "logical_flaw_explanation": "base-explain",
    }
    runtime = {"ascension_level": 20, "boss_phase_index": 2}
    pack = {
        999: [
            {"text_log": "p1-log", "target_keyword": "p1-kw"},
            {"text_log": "p2-log", "target_keyword": "p2-kw", "logical_flaw_explanation": "p2-exp"},
            {"text_log": "p3-log", "target_keyword": "p3-kw"},
        ]
    }
    overridden = _apply_asc20_boss_phase_override(scenario, runtime, pack)
    assert overridden["text_log"] == "p2-log"
    assert overridden["target_keyword"] == "p2-kw"
    assert overridden["logical_flaw_explanation"] == "p2-exp"


def test_apply_asc20_boss_phase_override_keeps_base_when_unmatched() -> None:
    scenario = {
        "node_id": 999,
        "is_boss": True,
        "text_log": "base-log",
        "target_keyword": "base-kw",
    }
    runtime = {"ascension_level": 19, "boss_phase_index": 1}
    pack = {999: [{"text_log": "p1-log", "target_keyword": "p1-kw"}]}
    overridden = _apply_asc20_boss_phase_override(scenario, runtime, pack)
    assert overridden["text_log"] == "base-log"
    assert overridden["target_keyword"] == "base-kw"


def test_mutate_route_choices_enforces_min_elite_choices() -> None:
    route_choices = [(NodeType.NORMAL, NodeType.NORMAL)] * 6
    runtime = {
        "ascension_route_elite_chance": 0.0,
        "ascension_route_relief_decay_chance": 0.0,
        "ascension_route_min_elite_choices": 3,
    }
    mutated, stats = _mutate_route_choices_for_ascension(route_choices, runtime)
    assert stats["forced_elite"] >= 3
    elite_count = sum(1 for left, right in mutated for n in (left, right) if n == NodeType.ELITE)
    assert elite_count >= 3


def test_mutate_route_choices_applies_relief_decay(monkeypatch) -> None:
    # random.random()=0.0이면 모든 확률 변이가 발동한다.
    monkeypatch.setattr("main.random.random", lambda: 0.0)
    route_choices = [
        (NodeType.REST, NodeType.SHOP),
        (NodeType.NORMAL, NodeType.NORMAL),
    ]
    runtime = {
        "ascension_route_elite_chance": 0.5,
        "ascension_route_relief_decay_chance": 0.5,
        "ascension_route_min_elite_choices": 1,
    }
    mutated, stats = _mutate_route_choices_for_ascension(route_choices, runtime)
    assert mutated[0][0] == NodeType.NORMAL
    assert mutated[0][1] == NodeType.NORMAL
    assert mutated[1][0] == NodeType.ELITE
    assert mutated[1][1] == NodeType.ELITE
    assert stats["relief_decay"] == 2
