"""Artifact effect regression tests."""

from artifact_system import Artifact, apply_artifact_effect, get_artifact


def _artifact(artifact_id: str) -> Artifact:
    artifact = get_artifact(artifact_id)
    assert artifact is not None
    return artifact


def test_null_protocol_applies_boss_penalty_cap() -> None:
    runtime = {"boss_penalty_cap": 999}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("null_protocol"), runtime, run_state)

    assert runtime["boss_penalty_cap"] == 40


def test_noise_filter_increments_nightmare_noise_reduce() -> None:
    runtime: dict[str, int] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("noise_filter"), runtime, run_state)
    apply_artifact_effect(_artifact("noise_filter"), runtime, run_state)

    assert runtime["nightmare_noise_reduce"] == 2


def test_memory_echo_sets_runtime_state_flag() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("memory_echo"), runtime, run_state)

    assert run_state.get("memory_echo_active") is True


def test_echo_cache_sets_runtime_state_flag() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("echo_cache"), runtime, run_state)

    assert run_state.get("echo_cache_active") is True


def test_ghost_signal_uses_skip_next_penalty_slot_once() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {"skip_next_penalty": False}

    apply_artifact_effect(_artifact("ghost_signal"), runtime, run_state)
    assert run_state.get("ghost_signal_active") is True
    assert run_state.get("skip_next_penalty") is True

    # 이미 슬롯이 점유되었다면 ghost_signal_active를 추가로 설정하지 않는다.
    run_state_occupied: dict[str, object] = {"skip_next_penalty": True}
    apply_artifact_effect(_artifact("ghost_signal"), runtime, run_state_occupied)
    assert run_state_occupied.get("ghost_signal_active") is None
    assert run_state_occupied.get("skip_next_penalty") is True


def test_relay_booster_applies_floor() -> None:
    runtime = {"timeout_penalty": 1}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("relay_booster"), runtime, run_state)

    assert runtime["timeout_penalty"] == 1


def test_overclock_extends_time_limit_by_five() -> None:
    runtime = {"time_limit_seconds": 30}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("overclock"), runtime, run_state)

    assert runtime["time_limit_seconds"] == 35


def test_signal_buffer_sets_on_timeout_skip_once() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("signal_buffer"), runtime, run_state)

    assert run_state.get("on_timeout_skip_once") is True


def test_frag_scanner_applies_shop_discount() -> None:
    runtime: dict[str, float] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("frag_scanner"), runtime, run_state)

    assert abs(runtime["shop_discount"] - 0.9) < 1e-9

    # 중복 적용 시 복리로 곱해진다
    apply_artifact_effect(_artifact("frag_scanner"), runtime, run_state)
    assert abs(runtime["shop_discount"] - 0.81) < 1e-9


def test_chrono_anchor_restores_time_on_wrong() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, int] = {}

    apply_artifact_effect(_artifact("chrono_anchor"), runtime, run_state)

    assert run_state["on_wrong_time_restore"] == 3

    # 중복 적용 시 누적
    apply_artifact_effect(_artifact("chrono_anchor"), runtime, run_state)
    assert run_state["on_wrong_time_restore"] == 6


def test_entropy_sink_caps_elite_flat_penalty() -> None:
    runtime: dict[str, int] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("entropy_sink"), runtime, run_state)

    assert runtime["elite_flat_penalty_cap"] == 30

    # 이미 낮은 값이면 더 낮은 쪽을 유지
    runtime2: dict[str, int] = {"elite_flat_penalty_cap": 20}
    apply_artifact_effect(_artifact("entropy_sink"), runtime2, run_state)
    assert runtime2["elite_flat_penalty_cap"] == 20


def test_system_purge_sets_clear_trace_to_zero() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("system_purge"), runtime, run_state)

    assert run_state.get("clear_trace_to_zero") is True


# ── v8.8 신규 아티팩트 4종 ────────────────────────────────────────────────────

def test_mystery_lens_sets_fail_penalty_mult() -> None:
    runtime: dict[str, float] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("mystery_lens"), runtime, run_state)

    assert abs(runtime["mystery_fail_penalty_mult"] - 0.5) < 1e-9

    # 이미 더 낮은 값이 있으면 그 값을 유지
    runtime2: dict[str, float] = {"mystery_fail_penalty_mult": 0.3}
    apply_artifact_effect(_artifact("mystery_lens"), runtime2, run_state)
    assert abs(runtime2["mystery_fail_penalty_mult"] - 0.3) < 1e-9


def test_fragment_cache_adds_to_clear_frag_bonus() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, int] = {}

    apply_artifact_effect(_artifact("fragment_cache"), runtime, run_state)
    assert run_state["on_clear_frag_bonus"] == 8

    # data_shard_x와 함께 사용하면 누적
    apply_artifact_effect(_artifact("data_shard_x"), runtime, run_state)
    assert run_state["on_clear_frag_bonus"] == 11  # 8 + 3


def test_trace_shield_sets_active_flag() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("trace_shield"), runtime, run_state)

    assert run_state.get("trace_shield_active") is True

    # 중복 적용해도 True 유지
    apply_artifact_effect(_artifact("trace_shield"), runtime, run_state)
    assert run_state.get("trace_shield_active") is True


def test_neural_override_sets_active_flag() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("neural_override"), runtime, run_state)

    assert run_state.get("neural_override_active") is True


# ── v9.3 신규 아티팩트 4종 ────────────────────────────────────────────────────

def test_pulse_barrier_sets_active_flag() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("pulse_barrier"), runtime, run_state)

    assert run_state.get("pulse_barrier_active") is True


def test_void_scanner_sets_active_flag() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("void_scanner"), runtime, run_state)

    assert run_state.get("void_scanner_active") is True


def test_echo_amplifier_sets_memory_echo_mult_override() -> None:
    runtime: dict[str, float] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("echo_amplifier"), runtime, run_state)

    assert abs(runtime["memory_echo_mult_override"] - 0.65) < 1e-9

    # 이미 더 낮은 값이 있으면 그 값을 유지
    runtime2: dict[str, float] = {"memory_echo_mult_override": 0.5}
    apply_artifact_effect(_artifact("echo_amplifier"), runtime2, run_state)
    assert abs(runtime2["memory_echo_mult_override"] - 0.5) < 1e-9


def test_cascade_core_sets_active_flag_and_streak() -> None:
    runtime: dict[str, object] = {}
    run_state: dict[str, object] = {}

    apply_artifact_effect(_artifact("cascade_core"), runtime, run_state)

    assert run_state.get("cascade_core_active") is True
    assert run_state.get("cascade_streak") == 0


# ── 아티팩트 런타임 소비 통합 테스트 ──────────────────────────────────────────

def test_chrono_anchor_extend_called_on_wrong_answer() -> None:
    """chrono_anchor: 오답 후 생존 시 extend_timeout_fn이 on_wrong_time_restore 초로 호출된다."""
    from combat_commands import handle_analyze
    from route_map import NodeType

    scenario = {
        "target_keyword": "GPS",
        "penalty_rate": 20,
        "difficulty": "Easy",
        "theme": "A",
        "text_log": "테스트 로그",
    }
    run_state: dict[str, object] = {
        "on_wrong_time_restore": 3,
        "wrong_analyzes": 0,
    }
    runtime: dict[str, object] = {"ascension_penalty_flat": 0, "penalty_multiplier": 1.0}
    extended: list[int] = []

    def _extend(secs: int) -> None:
        extended.append(secs)

    def _cancel() -> None:
        pass

    def _death(t: int, bu: bool) -> tuple[int, bool, bool]:
        return t, bu, True  # 항상 생존

    action, trace_level, _, _ = handle_analyze(
        command_raw="analyze WRONG",
        scenario=scenario,
        trace_level=30,
        backtrack_used=False,
        node_type=NodeType.NORMAL,
        diver_class=None,
        runtime=runtime,
        run_state=run_state,
        perks={},
        last_prompt_time=0.0,
        cancel_timer_fn=_cancel,
        handle_death_fn=_death,
        extend_timeout_fn=_extend,
    )

    assert action == "continue"
    assert extended == [3], "extend_timeout_fn이 3초로 호출되어야 함"


def test_system_purge_zeroes_trace_final_on_victory() -> None:
    """system_purge: 승리 시 _build_run_stats의 trace_final이 0이 된다."""
    from main import _build_run_stats

    run_state: dict[str, object] = {"clear_trace_to_zero": True}

    stats_victory = _build_run_stats(
        run_state=run_state,
        trace_level=75,
        max_trace_reached=80,
        acquired_artifacts=[],
        is_victory=True,
    )
    assert stats_victory["trace_final"] == 0, "승리+system_purge 시 trace_final=0"

    stats_defeat = _build_run_stats(
        run_state=run_state,
        trace_level=100,
        max_trace_reached=100,
        acquired_artifacts=[],
        is_victory=False,
    )
    assert stats_defeat["trace_final"] == 100, "패배 시 system_purge 미적용"
