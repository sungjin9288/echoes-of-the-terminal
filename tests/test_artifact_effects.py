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
