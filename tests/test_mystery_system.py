"""MYSTERY 노드 시스템 단위 테스트."""

from __future__ import annotations

import pytest

from mystery_system import (
    MYSTERY_INDEX,
    MYSTERY_POOL,
    MysteryEvent,
    apply_mystery_outcome,
    get_mystery_snapshot,
    pick_mystery,
    resolve_mystery_outcome,
)


# ── 구조 검증 ─────────────────────────────────────────────────────────────────

def test_mystery_pool_has_eighteen_events() -> None:
    assert len(MYSTERY_POOL) == 18


def test_mystery_index_matches_pool() -> None:
    """MYSTERY_INDEX는 MYSTERY_POOL과 완전히 일치해야 한다."""
    assert set(MYSTERY_INDEX.keys()) == {m.event_id for m in MYSTERY_POOL}


def test_mystery_event_ids_are_unique() -> None:
    ids = [m.event_id for m in MYSTERY_POOL]
    assert len(ids) == len(set(ids))


def test_mystery_event_fields_non_empty() -> None:
    """모든 이벤트의 문자열 필드가 비어 있지 않아야 한다."""
    for event in MYSTERY_POOL:
        assert event.event_id.strip()
        assert event.title.strip()
        assert event.description.strip()
        assert event.engage_prompt.strip()
        assert event.good_desc.strip()
        assert event.bad_desc.strip()


def test_mystery_event_bad_trace_delta_positive() -> None:
    """나쁜 결과의 trace_delta는 0 이상이어야 한다 (추적도 증가)."""
    for event in MYSTERY_POOL:
        assert event.bad_trace_delta >= 0, (
            f"{event.event_id}: bad_trace_delta={event.bad_trace_delta}"
        )


def test_mystery_event_good_trace_delta_non_positive() -> None:
    """좋은 결과의 trace_delta는 0 이하여야 한다 (추적도 감소 또는 유지)."""
    for event in MYSTERY_POOL:
        assert event.good_trace_delta <= 0, (
            f"{event.event_id}: good_trace_delta={event.good_trace_delta}"
        )


def test_mystery_event_is_dataclass_frozen() -> None:
    """MysteryEvent는 frozen dataclass로 불변이어야 한다."""
    event = MYSTERY_POOL[0]
    with pytest.raises((AttributeError, TypeError)):
        event.title = "modified"  # type: ignore[misc]


# ── pick_mystery ──────────────────────────────────────────────────────────────

def test_pick_mystery_deterministic() -> None:
    """같은 시드와 포지션은 항상 같은 이벤트를 반환한다."""
    e1 = pick_mystery(12345, 3)
    e2 = pick_mystery(12345, 3)
    assert e1.event_id == e2.event_id


def test_pick_mystery_different_seeds_vary() -> None:
    """다른 시드는 (같은 포지션이더라도) 다른 이벤트를 선택할 수 있다."""
    results = {pick_mystery(seed, 0).event_id for seed in range(1, 50)}
    # 18종 중 최소 2종 이상 선택되어야 결정론적 분포가 작동함
    assert len(results) >= 2


def test_pick_mystery_different_positions_vary() -> None:
    """같은 시드지만 다른 포지션은 다른 이벤트를 선택할 수 있다."""
    results = {pick_mystery(99999, pos).event_id for pos in range(8)}
    assert len(results) >= 2


def test_pick_mystery_returns_mystery_event() -> None:
    event = pick_mystery(1, 0)
    assert isinstance(event, MysteryEvent)


def test_pick_mystery_result_in_pool() -> None:
    """반환된 이벤트는 MYSTERY_POOL에 포함되어야 한다."""
    event = pick_mystery(7777, 5)
    assert event in MYSTERY_POOL


# ── resolve_mystery_outcome ───────────────────────────────────────────────────

def test_resolve_mystery_outcome_deterministic() -> None:
    """같은 시드+포지션은 항상 같은 결과를 반환한다."""
    r1 = resolve_mystery_outcome(42, 2)
    r2 = resolve_mystery_outcome(42, 2)
    assert r1 == r2


def test_resolve_mystery_outcome_returns_bool() -> None:
    result = resolve_mystery_outcome(1000, 0)
    assert isinstance(result, bool)


def test_resolve_mystery_outcome_varies_across_seeds() -> None:
    """충분히 많은 시드에서 True/False 모두 나와야 한다."""
    results = {resolve_mystery_outcome(seed, 0) for seed in range(1, 100)}
    assert True in results
    assert False in results


def test_resolve_mystery_outcome_varies_across_positions() -> None:
    """같은 시드라도 포지션에 따라 결과가 달라질 수 있다."""
    results = {resolve_mystery_outcome(12345, pos) for pos in range(8)}
    assert len(results) >= 2  # True와 False 모두 포함


# ── apply_mystery_outcome ─────────────────────────────────────────────────────

def _make_event(
    good_trace: int = -20,
    bad_trace: int = 30,
    good_frags: int = 200,
    bad_frags: int = 0,
) -> MysteryEvent:
    return MysteryEvent(
        event_id="test_event",
        title="테스트 이벤트",
        description="테스트용",
        engage_prompt="테스트 개입",
        good_desc="성공",
        bad_desc="실패",
        good_trace_delta=good_trace,
        bad_trace_delta=bad_trace,
        good_fragments_delta=good_frags,
        bad_fragments_delta=bad_frags,
    )


def test_apply_good_outcome_reduces_trace() -> None:
    event = _make_event(good_trace=-20)
    new_trace, _, _ = apply_mystery_outcome(event, True, 50, {})
    assert new_trace == 30  # 50 - 20


def test_apply_bad_outcome_increases_trace() -> None:
    event = _make_event(bad_trace=30)
    new_trace, _, _ = apply_mystery_outcome(event, False, 50, {})
    assert new_trace == 80  # 50 + 30


def test_apply_trace_clamped_at_zero() -> None:
    """trace는 0 미만으로 내려가지 않는다."""
    event = _make_event(good_trace=-50)
    new_trace, _, _ = apply_mystery_outcome(event, True, 10, {})
    assert new_trace == 0


def test_apply_trace_clamped_at_100() -> None:
    """trace는 100 초과로 올라가지 않는다."""
    event = _make_event(bad_trace=40)
    new_trace, _, _ = apply_mystery_outcome(event, False, 80, {})
    assert new_trace == 100


def test_apply_good_outcome_adds_fragments() -> None:
    event = _make_event(good_frags=250)
    save_data = {"data_fragments": 100}
    _, new_save, _ = apply_mystery_outcome(event, True, 50, save_data)
    assert new_save["data_fragments"] == 350


def test_apply_bad_outcome_loses_fragments() -> None:
    event = _make_event(bad_frags=-150)
    save_data = {"data_fragments": 200}
    _, new_save, _ = apply_mystery_outcome(event, False, 50, save_data)
    assert new_save["data_fragments"] == 50


def test_apply_fragments_clamped_at_zero() -> None:
    """데이터 조각은 0 미만으로 내려가지 않는다."""
    event = _make_event(bad_frags=-500)
    save_data = {"data_fragments": 100}
    _, new_save, _ = apply_mystery_outcome(event, False, 50, save_data)
    assert new_save["data_fragments"] == 0


def test_apply_outcome_does_not_mutate_save_data() -> None:
    """원본 save_data는 수정되지 않아야 한다 (불변 패턴)."""
    event = _make_event(good_frags=300)
    original = {"data_fragments": 100, "other_key": "value"}
    original_copy = dict(original)
    apply_mystery_outcome(event, True, 50, original)
    assert original == original_copy


def test_apply_outcome_returns_result_message() -> None:
    event = _make_event()
    _, _, good_msg = apply_mystery_outcome(event, True, 50, {})
    _, _, bad_msg = apply_mystery_outcome(event, False, 50, {})
    assert good_msg == "성공"
    assert bad_msg == "실패"


def test_apply_outcome_missing_fragments_key() -> None:
    """save_data에 data_fragments가 없을 때 0으로 처리한다."""
    event = _make_event(good_frags=100)
    _, new_save, _ = apply_mystery_outcome(event, True, 50, {})
    assert new_save["data_fragments"] == 100


def test_apply_outcome_no_fragment_change() -> None:
    """fragment delta가 0이면 data_fragments 값이 유지된다."""
    event = _make_event(good_frags=0)
    save_data = {"data_fragments": 500}
    _, new_save, _ = apply_mystery_outcome(event, True, 50, save_data)
    assert new_save["data_fragments"] == 500


# ── get_mystery_snapshot ──────────────────────────────────────────────────────

def test_get_mystery_snapshot_total() -> None:
    snap = get_mystery_snapshot()
    assert snap["total_events"] == 18


def test_get_mystery_snapshot_event_ids() -> None:
    snap = get_mystery_snapshot()
    assert len(snap["event_ids"]) == 18
    assert len(set(snap["event_ids"])) == 18  # 모두 고유


# ── 통합: pick + resolve + apply 파이프라인 ──────────────────────────────────

def test_full_pipeline_produces_valid_trace() -> None:
    """pick → resolve → apply 전체 파이프라인이 유효한 trace를 반환한다."""
    run_seed = 98765
    position = 4
    trace = 60
    save_data: dict = {"data_fragments": 500}

    event = pick_mystery(run_seed, position)
    is_good = resolve_mystery_outcome(run_seed, position)
    new_trace, new_save, msg = apply_mystery_outcome(event, is_good, trace, save_data)

    assert 0 <= new_trace <= 100
    assert new_save["data_fragments"] >= 0
    assert isinstance(msg, str) and len(msg) > 0


def test_full_pipeline_deterministic_across_calls() -> None:
    """같은 시드라면 파이프라인 결과가 항상 동일하다."""
    run_seed = 11111
    position = 2
    trace = 45
    save_data: dict = {"data_fragments": 300}

    def _run() -> tuple[int, int, str]:
        event = pick_mystery(run_seed, position)
        is_good = resolve_mystery_outcome(run_seed, position)
        new_trace, new_save, msg = apply_mystery_outcome(event, is_good, trace, save_data)
        return new_trace, new_save["data_fragments"], msg

    result1 = _run()
    result2 = _run()
    assert result1 == result2
