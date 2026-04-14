"""Ending system unit tests — 8종 엔딩 조건 및 기록 검증."""

from ending_system import (
    ENDINGS,
    evaluate_ending,
    get_endings_snapshot,
    record_ending_unlock,
)
from progression_system import (
    CAMPAIGN_CLEAR_CLASS_VICTORIES,
    CAMPAIGN_CLEAR_POINTS,
    CAMPAIGN_CLEAR_TOTAL_VICTORIES,
    CAMPAIGN_CLASS_KEYS,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _run(
    *,
    is_victory: bool = True,
    trace_final: int = 50,
    wrong_analyzes: int = 0,
    timeout_events: int = 0,
    ascension_level: int = 0,
    correct_answers: int = 7,
    class_key: str = "ANALYST",
    cleared_difficulties: list | None = None,
    mystery_engaged: int = 0,
    mystery_good: int = 0,
    artifacts_held: int = 0,
    max_trace_reached: int = 50,
) -> dict:
    return {
        "is_victory": is_victory,
        "trace_final": trace_final,
        "wrong_analyzes": wrong_analyzes,
        "timeout_events": timeout_events,
        "ascension_level": ascension_level,
        "correct_answers": correct_answers,
        "class_key": class_key,
        "cleared_difficulties": cleared_difficulties or ["Easy", "Hard"],
        "mystery_engaged": mystery_engaged,
        "mystery_good": mystery_good,
        "artifacts_held": artifacts_held,
        "max_trace_reached": max_trace_reached,
    }


def _save_cleared() -> dict:
    """캠페인 클리어 조건을 실제로 충족하는 세이브 데이터."""
    return {
        "campaign": {
            "points": CAMPAIGN_CLEAR_POINTS,
            "runs": CAMPAIGN_CLEAR_TOTAL_VICTORIES,
            "victories": CAMPAIGN_CLEAR_TOTAL_VICTORIES,
            "class_victories": {k: CAMPAIGN_CLEAR_CLASS_VICTORIES for k in CAMPAIGN_CLASS_KEYS},
            "cleared": True,
        },
        "endings": {"unlocked": []},
    }


def _save_empty() -> dict:
    return {
        "campaign": {
            "points": 0,
            "runs": 0,
            "victories": 0,
            "class_victories": {"ANALYST": 0, "GHOST": 0, "CRACKER": 0},
            "cleared": False,
        },
        "endings": {"unlocked": []},
    }


# ── 구조 검증 ─────────────────────────────────────────────────────────────────

def test_endings_dict_has_11_entries() -> None:
    assert len(ENDINGS) == 11


def test_all_endings_have_required_fields() -> None:
    for ending_id, ending in ENDINGS.items():
        assert ending.ending_id == ending_id
        assert ending.title
        assert ending.subtitle
        assert ending.flavor_text
        assert ending.color
        assert ending.border_style
        assert isinstance(ending.priority, int) and ending.priority > 0


def test_ending_priorities_are_unique() -> None:
    priorities = [e.priority for e in ENDINGS.values()]
    assert len(priorities) == len(set(priorities))


def test_new_endings_present() -> None:
    for ending_id in ("SPEEDRUN_END", "CRACKER_END", "VETERAN_END",
                      "MYSTERY_END", "COLLECTOR_END", "COMEBACK_END"):
        assert ending_id in ENDINGS, f"{ending_id} 누락"


# ── evaluate_ending: 기존 5종 ─────────────────────────────────────────────────

def test_no_ending_on_defeat() -> None:
    result = evaluate_ending(_run(is_victory=False), _save_empty())
    assert result is None


def test_true_end_on_campaign_cleared() -> None:
    # TRUE_END(priority 1) > ANALYST_END(priority 4): 캠페인 클리어 + 완벽 런
    result = evaluate_ending(_run(), _save_cleared())
    assert result is not None
    assert result.ending_id == "TRUE_END"


def test_ascension_end_on_asc20_victory() -> None:
    # ASCENSION_END(priority 2) > ANALYST_END(priority 4) when asc >= 20
    result = evaluate_ending(_run(ascension_level=20), _save_empty())
    assert result is not None
    assert result.ending_id == "ASCENSION_END"


def test_ghost_end_on_trace_le_10() -> None:
    # GHOST_END(priority 3) > ANALYST_END(priority 4): trace=10 + zero errors
    result = evaluate_ending(_run(trace_final=10), _save_empty())
    assert result is not None
    assert result.ending_id == "GHOST_END"

    # trace > 10 + zero errors → ANALYST_END (not GHOST_END)
    result2 = evaluate_ending(_run(trace_final=11), _save_empty())
    assert result2 is None or result2.ending_id != "GHOST_END"


def test_analyst_end_on_zero_errors_and_6_correct() -> None:
    # zero wrong + zero timeout + correct >= 6 (no higher-priority condition)
    result = evaluate_ending(
        _run(wrong_analyzes=0, timeout_events=0, correct_answers=6, ascension_level=0),
        _save_empty(),
    )
    assert result is not None
    assert result.ending_id == "ANALYST_END"

    # wrong=1 → ANALYST_END 불가
    result2 = evaluate_ending(
        _run(wrong_analyzes=1, timeout_events=0, correct_answers=6), _save_empty()
    )
    assert result2 is None or result2.ending_id != "ANALYST_END"


def test_survivor_end_on_trace_ge_90() -> None:
    # SURVIVOR_END(priority 5): trace >= 90, wrong=1 (ANALYST_END 충돌 방지)
    result = evaluate_ending(
        _run(trace_final=90, wrong_analyzes=1), _save_empty()
    )
    assert result is not None
    assert result.ending_id == "SURVIVOR_END"

    result2 = evaluate_ending(
        _run(trace_final=89, wrong_analyzes=1), _save_empty()
    )
    assert result2 is None or result2.ending_id != "SURVIVOR_END"


# ── evaluate_ending: 신규 3종 ─────────────────────────────────────────────────

def test_speedrun_end_requires_zero_errors_and_asc10() -> None:
    # correct_answers=4 → ANALYST_END 미충족(requires >=6), SPEEDRUN_END 충족
    result = evaluate_ending(
        _run(wrong_analyzes=0, timeout_events=0, ascension_level=10, correct_answers=4),
        _save_empty(),
    )
    assert result is not None
    assert result.ending_id == "SPEEDRUN_END"

    # 오답 있으면 해당 없음
    result2 = evaluate_ending(
        _run(wrong_analyzes=1, timeout_events=0, ascension_level=10, correct_answers=4),
        _save_empty(),
    )
    assert result2 is None or result2.ending_id != "SPEEDRUN_END"

    # ASC 9 이하이면 해당 없음
    result3 = evaluate_ending(
        _run(wrong_analyzes=0, timeout_events=0, ascension_level=9, correct_answers=4),
        _save_empty(),
    )
    assert result3 is None or result3.ending_id != "SPEEDRUN_END"


def test_cracker_end_requires_cracker_zero_wrong_nightmare() -> None:
    # correct_answers=4 → ANALYST_END 미충족(requires >=6), CRACKER_END 충족
    result = evaluate_ending(
        _run(
            class_key="CRACKER",
            wrong_analyzes=0,
            correct_answers=4,
            cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
        ),
        _save_empty(),
    )
    assert result is not None
    assert result.ending_id == "CRACKER_END"

    # 오답 있으면 해당 없음
    result2 = evaluate_ending(
        _run(
            class_key="CRACKER",
            wrong_analyzes=1,
            correct_answers=4,
            cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
        ),
        _save_empty(),
    )
    assert result2 is None or result2.ending_id != "CRACKER_END"

    # NIGHTMARE 없으면 해당 없음
    result3 = evaluate_ending(
        _run(class_key="CRACKER", wrong_analyzes=0, correct_answers=4,
             cleared_difficulties=["Easy", "Hard"]),
        _save_empty(),
    )
    assert result3 is None or result3.ending_id != "CRACKER_END"

    # ANALYST 클래스는 해당 없음
    result4 = evaluate_ending(
        _run(
            class_key="ANALYST",
            wrong_analyzes=0,
            correct_answers=4,
            cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
        ),
        _save_empty(),
    )
    assert result4 is None or result4.ending_id != "CRACKER_END"


def test_veteran_end_requires_asc15_and_3_wrong() -> None:
    result = evaluate_ending(
        _run(ascension_level=15, wrong_analyzes=3), _save_empty()
    )
    assert result is not None
    assert result.ending_id == "VETERAN_END"

    # ASC 14 이하면 해당 없음
    result2 = evaluate_ending(
        _run(ascension_level=14, wrong_analyzes=3), _save_empty()
    )
    assert result2 is None or result2.ending_id != "VETERAN_END"

    # 오답 2회 이하면 해당 없음
    result3 = evaluate_ending(
        _run(ascension_level=15, wrong_analyzes=2), _save_empty()
    )
    assert result3 is None or result3.ending_id != "VETERAN_END"


def test_priority_true_end_beats_ascension_end() -> None:
    """캠페인 클리어 + ASC 20 동시 충족 시 TRUE_END(priority 1) 우선."""
    result = evaluate_ending(_run(ascension_level=20), _save_cleared())
    assert result is not None
    assert result.ending_id == "TRUE_END"


# ── evaluate_ending: 신규 3종 (MYSTERY / COLLECTOR / COMEBACK) ────────────────

def test_mystery_end_requires_3_engagements_all_good() -> None:
    # mystery_engaged >= 3, 모두 성공 → MYSTERY_END
    result = evaluate_ending(
        _run(mystery_engaged=3, mystery_good=3, wrong_analyzes=1),  # wrong=1 → ANALYST_END 회피
        _save_empty(),
    )
    assert result is not None
    assert result.ending_id == "MYSTERY_END"

    # 개입 2회는 미충족
    result2 = evaluate_ending(
        _run(mystery_engaged=2, mystery_good=2, wrong_analyzes=1),
        _save_empty(),
    )
    assert result2 is None or result2.ending_id != "MYSTERY_END"

    # 개입 중 실패가 있으면 미충족
    result3 = evaluate_ending(
        _run(mystery_engaged=3, mystery_good=2, wrong_analyzes=1),
        _save_empty(),
    )
    assert result3 is None or result3.ending_id != "MYSTERY_END"


def test_collector_end_requires_4_artifacts() -> None:
    # artifacts_held >= 4 → COLLECTOR_END (wrong=1 → ANALYST_END 회피)
    result = evaluate_ending(
        _run(artifacts_held=4, wrong_analyzes=1),
        _save_empty(),
    )
    assert result is not None
    assert result.ending_id == "COLLECTOR_END"

    # 아티팩트 3개는 미충족
    result2 = evaluate_ending(
        _run(artifacts_held=3, wrong_analyzes=1),
        _save_empty(),
    )
    assert result2 is None or result2.ending_id != "COLLECTOR_END"


def test_comeback_end_requires_max95_and_final60() -> None:
    # max_trace_reached >= 95, trace_final <= 60 → COMEBACK_END (wrong=1, trace<90 → SURVIVOR/ANALYST 회피)
    result = evaluate_ending(
        _run(max_trace_reached=95, trace_final=55, wrong_analyzes=1),
        _save_empty(),
    )
    assert result is not None
    assert result.ending_id == "COMEBACK_END"

    # max_trace 94는 미충족
    result2 = evaluate_ending(
        _run(max_trace_reached=94, trace_final=55, wrong_analyzes=1),
        _save_empty(),
    )
    assert result2 is None or result2.ending_id != "COMEBACK_END"

    # 최종 trace 61은 미충족
    result3 = evaluate_ending(
        _run(max_trace_reached=95, trace_final=61, wrong_analyzes=1),
        _save_empty(),
    )
    assert result3 is None or result3.ending_id != "COMEBACK_END"


# ── record_ending_unlock ──────────────────────────────────────────────────────

def test_record_ending_unlock_returns_true_on_first_unlock() -> None:
    save = _save_empty()
    is_new = record_ending_unlock(save, "GHOST_END")
    assert is_new is True
    assert "GHOST_END" in save["endings"]["unlocked"]


def test_record_ending_unlock_returns_false_on_duplicate() -> None:
    save = _save_empty()
    record_ending_unlock(save, "GHOST_END")
    is_new = record_ending_unlock(save, "GHOST_END")
    assert is_new is False
    assert save["endings"]["unlocked"].count("GHOST_END") == 1


# ── get_endings_snapshot ──────────────────────────────────────────────────────

def test_get_endings_snapshot_total_is_11() -> None:
    save = _save_empty()
    snap = get_endings_snapshot(save)
    assert snap["total_count"] == 11
    assert snap["unlocked_count"] == 0


def test_get_endings_snapshot_counts_unlocked_correctly() -> None:
    save = _save_empty()
    record_ending_unlock(save, "GHOST_END")
    record_ending_unlock(save, "ANALYST_END")
    snap = get_endings_snapshot(save)
    assert snap["unlocked_count"] == 2
    assert set(snap["unlocked_ids"]) == {"GHOST_END", "ANALYST_END"}
