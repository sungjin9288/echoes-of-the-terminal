"""데일리 챌린지 시스템 단위 테스트."""

from __future__ import annotations

from datetime import date

import pytest

from daily_challenge import (
    DAILY_STREAK_BONUS_CAP,
    DAILY_STREAK_BONUS_PER_DAY,
    GRADE_THRESHOLDS,
    calculate_daily_score,
    get_daily_seed,
    get_daily_state,
    get_performance_grade,
    get_today_str,
    get_weekly_stats,
    has_played_today,
    record_daily_result,
    select_daily_scenarios,
    _normalize_history,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _make_scenario(
    node_id: int = 1,
    difficulty: str = "Easy",
    is_boss: bool = False,
) -> dict:
    return {
        "node_id": node_id,
        "theme": "TEST",
        "difficulty": difficulty,
        "text_log": "test log",
        "target_keyword": "keyword",
        "penalty_rate": 20,
        "is_boss": is_boss,
    }


def _make_save(daily: dict | None = None) -> dict:
    return {"daily": daily or {}}


def _make_history_entry(
    date_str: str = "2026-01-01",
    score: int = 500,
    is_victory: bool = True,
    correct_answers: int = 6,
    trace_final: int = 30,
    class_key: str = "ANALYST",
    wrong_analyzes: int = 0,
    timeout_events: int = 0,
) -> dict:
    return {
        "date": date_str,
        "score": score,
        "is_victory": is_victory,
        "correct_answers": correct_answers,
        "trace_final": trace_final,
        "class_key": class_key,
        "wrong_analyzes": wrong_analyzes,
        "timeout_events": timeout_events,
    }


# ── get_today_str ──────────────────────────────────────────────────────────────

def test_get_today_str_format() -> None:
    today = get_today_str()
    parts = today.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 4  # year
    assert len(parts[1]) == 2  # month
    assert len(parts[2]) == 2  # day


# ── get_daily_seed ─────────────────────────────────────────────────────────────

def test_get_daily_seed_deterministic() -> None:
    """동일 날짜는 항상 동일한 시드를 반환한다."""
    seed1 = get_daily_seed("2026-01-01")
    seed2 = get_daily_seed("2026-01-01")
    assert seed1 == seed2


def test_get_daily_seed_different_dates() -> None:
    """다른 날짜는 다른 시드를 반환한다."""
    seed1 = get_daily_seed("2026-01-01")
    seed2 = get_daily_seed("2026-01-02")
    assert seed1 != seed2


def test_get_daily_seed_positive_int() -> None:
    """시드는 양의 정수여야 한다."""
    seed = get_daily_seed("2026-06-15")
    assert isinstance(seed, int)
    assert seed > 0


# ── get_performance_grade ─────────────────────────────────────────────────────

def test_grade_s_at_threshold() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["S"]) == "S"


def test_grade_s_above_threshold() -> None:
    assert get_performance_grade(9999) == "S"


def test_grade_a_at_threshold() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["A"]) == "A"


def test_grade_a_below_s() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["S"] - 1) == "A"


def test_grade_b_at_threshold() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["B"]) == "B"


def test_grade_b_below_a() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["A"] - 1) == "B"


def test_grade_c_at_threshold() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["C"]) == "C"


def test_grade_c_below_b() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["B"] - 1) == "C"


def test_grade_d_below_c() -> None:
    assert get_performance_grade(GRADE_THRESHOLDS["C"] - 1) == "D"


def test_grade_d_at_zero() -> None:
    assert get_performance_grade(0) == "D"


# ── calculate_daily_score ─────────────────────────────────────────────────────

def test_score_basic_victory() -> None:
    """승리 보너스 +500 확인."""
    score = calculate_daily_score(
        correct_answers=7,
        is_victory=True,
        trace_final=0,
        wrong_analyzes=0,
        timeout_events=0,
        base_reward=100,
        streak=0,
    )
    # base = int(100 * 1.5) = 150, +500 victory = 650
    assert score == 650


def test_score_defeat_no_victory_bonus() -> None:
    """패배 시 승리 보너스 없음."""
    score = calculate_daily_score(
        correct_answers=3,
        is_victory=False,
        trace_final=0,
        wrong_analyzes=0,
        timeout_events=0,
        base_reward=100,
        streak=0,
    )
    # base = 150, no victory bonus
    assert score == 150


def test_score_streak_bonus_applied() -> None:
    """스트릭 보너스 = min(streak * 10, 200) 확인."""
    score_streak5 = calculate_daily_score(
        correct_answers=7,
        is_victory=True,
        trace_final=0,
        wrong_analyzes=0,
        timeout_events=0,
        base_reward=100,
        streak=5,
    )
    # base=150, victory=+500, streak=5*10=50 → 700
    assert score_streak5 == 700


def test_score_streak_bonus_capped() -> None:
    """스트릭 보너스는 DAILY_STREAK_BONUS_CAP(200)으로 상한 고정."""
    cap_streak = DAILY_STREAK_BONUS_CAP // DAILY_STREAK_BONUS_PER_DAY  # 20
    score_capped = calculate_daily_score(
        correct_answers=7,
        is_victory=True,
        trace_final=0,
        wrong_analyzes=0,
        timeout_events=0,
        base_reward=100,
        streak=cap_streak + 10,  # 초과해도 cap
    )
    score_at_cap = calculate_daily_score(
        correct_answers=7,
        is_victory=True,
        trace_final=0,
        wrong_analyzes=0,
        timeout_events=0,
        base_reward=100,
        streak=cap_streak,
    )
    assert score_capped == score_at_cap


def test_score_trace_penalty() -> None:
    """trace_final × 2 감점 확인."""
    score_trace0 = calculate_daily_score(
        correct_answers=7, is_victory=True,
        trace_final=0, wrong_analyzes=0, timeout_events=0,
        base_reward=100, streak=0,
    )
    score_trace50 = calculate_daily_score(
        correct_answers=7, is_victory=True,
        trace_final=50, wrong_analyzes=0, timeout_events=0,
        base_reward=100, streak=0,
    )
    assert score_trace0 - score_trace50 == 100  # 50 * 2


def test_score_wrong_penalty() -> None:
    """wrong_analyzes × 50 감점 확인."""
    score_0wrong = calculate_daily_score(
        correct_answers=7, is_victory=True,
        trace_final=0, wrong_analyzes=0, timeout_events=0,
        base_reward=100, streak=0,
    )
    score_2wrong = calculate_daily_score(
        correct_answers=7, is_victory=True,
        trace_final=0, wrong_analyzes=2, timeout_events=0,
        base_reward=100, streak=0,
    )
    assert score_0wrong - score_2wrong == 100  # 2 * 50


def test_score_timeout_penalty() -> None:
    """timeout_events × 30 감점 확인."""
    score_0timeout = calculate_daily_score(
        correct_answers=7, is_victory=True,
        trace_final=0, wrong_analyzes=0, timeout_events=0,
        base_reward=100, streak=0,
    )
    score_3timeout = calculate_daily_score(
        correct_answers=7, is_victory=True,
        trace_final=0, wrong_analyzes=0, timeout_events=3,
        base_reward=100, streak=0,
    )
    assert score_0timeout - score_3timeout == 90  # 3 * 30


def test_score_minimum_zero() -> None:
    """점수 최솟값은 0이다."""
    score = calculate_daily_score(
        correct_answers=0,
        is_victory=False,
        trace_final=100,
        wrong_analyzes=100,
        timeout_events=100,
        base_reward=0,
        streak=0,
    )
    assert score == 0


# ── get_daily_state ───────────────────────────────────────────────────────────

def test_get_daily_state_defaults() -> None:
    """빈 세이브에서 기본값 반환."""
    state = get_daily_state({})
    assert state["last_played_date"] == ""
    assert state["history"] == []
    assert state["best_score"] == 0
    assert state["streak"] == 0
    assert state["total_plays"] == 0


def test_get_daily_state_invalid_daily_field() -> None:
    """daily 필드가 dict가 아니면 기본값 사용."""
    state = get_daily_state({"daily": "invalid"})
    assert state["best_score"] == 0


def test_get_daily_state_negative_values_clamped() -> None:
    """음수 값은 0으로 클램핑된다."""
    state = get_daily_state({"daily": {"best_score": -100, "streak": -5, "total_plays": -1}})
    assert state["best_score"] == 0
    assert state["streak"] == 0
    assert state["total_plays"] == 0


# ── has_played_today ──────────────────────────────────────────────────────────

def test_has_played_today_true() -> None:
    state = {"last_played_date": "2026-04-09"}
    assert has_played_today(state, "2026-04-09") is True


def test_has_played_today_false_different_date() -> None:
    state = {"last_played_date": "2026-04-08"}
    assert has_played_today(state, "2026-04-09") is False


def test_has_played_today_false_empty() -> None:
    assert has_played_today({}, "2026-04-09") is False


# ── _normalize_history ────────────────────────────────────────────────────────

def test_normalize_history_includes_timeout_events() -> None:
    """timeout_events 필드가 히스토리에 포함된다."""
    raw = [{"date": "2026-01-01", "score": 500, "is_victory": True,
             "correct_answers": 6, "trace_final": 30, "class_key": "ANALYST",
             "wrong_analyzes": 0, "timeout_events": 2}]
    result = _normalize_history(raw)
    assert len(result) == 1
    assert result[0]["timeout_events"] == 2


def test_normalize_history_clamps_negatives() -> None:
    """음수 필드는 0으로 클램핑된다."""
    raw = [{"date": "2026-01-01", "score": -50, "is_victory": False,
             "correct_answers": -1, "trace_final": -10, "class_key": "GHOST",
             "wrong_analyzes": -3, "timeout_events": -1}]
    result = _normalize_history(raw)
    assert result[0]["score"] == 0
    assert result[0]["correct_answers"] == 0
    assert result[0]["trace_final"] == 0
    assert result[0]["wrong_analyzes"] == 0
    assert result[0]["timeout_events"] == 0


def test_normalize_history_skips_non_dict() -> None:
    """dict가 아닌 항목은 무시된다."""
    raw = [{"date": "2026-01-01", "score": 100, "is_victory": True,
             "correct_answers": 5, "trace_final": 20, "class_key": "CRACKER",
             "wrong_analyzes": 0, "timeout_events": 0},
           "invalid_string",
           42]
    result = _normalize_history(raw)
    assert len(result) == 1


def test_normalize_history_invalid_input() -> None:
    """list가 아닌 입력은 빈 리스트 반환."""
    assert _normalize_history("bad") == []
    assert _normalize_history(None) == []
    assert _normalize_history(42) == []


# ── get_weekly_stats ──────────────────────────────────────────────────────────

def test_weekly_stats_empty_history() -> None:
    stats = get_weekly_stats([], "2026-04-09")
    assert stats["days_played"] == 0
    assert stats["victories"] == 0
    assert stats["best_score"] == 0
    assert stats["average_score"] == 0.0
    assert stats["best_grade"] == "D"


def test_weekly_stats_invalid_today() -> None:
    """잘못된 today_str은 기본값 반환."""
    stats = get_weekly_stats([_make_history_entry()], "not-a-date")
    assert stats["days_played"] == 0


def test_weekly_stats_counts_days_in_window() -> None:
    """7일 이내 항목만 집계된다."""
    history = [
        _make_history_entry(date_str="2026-04-09", score=800),   # today
        _make_history_entry(date_str="2026-04-08", score=600),   # 1 day ago
        _make_history_entry(date_str="2026-04-03", score=400),   # 6 days ago
        _make_history_entry(date_str="2026-04-02", score=300),   # 7 days ago (excluded)
    ]
    stats = get_weekly_stats(history, "2026-04-09")
    assert stats["days_played"] == 3


def test_weekly_stats_best_score() -> None:
    history = [
        _make_history_entry(date_str="2026-04-09", score=800),
        _make_history_entry(date_str="2026-04-08", score=1200),
    ]
    stats = get_weekly_stats(history, "2026-04-09")
    assert stats["best_score"] == 1200
    assert stats["best_grade"] == "S"


def test_weekly_stats_victories_count() -> None:
    history = [
        _make_history_entry(date_str="2026-04-09", score=600, is_victory=True),
        _make_history_entry(date_str="2026-04-08", score=300, is_victory=False),
        _make_history_entry(date_str="2026-04-07", score=700, is_victory=True),
    ]
    stats = get_weekly_stats(history, "2026-04-09")
    assert stats["victories"] == 2


def test_weekly_stats_average_score() -> None:
    history = [
        _make_history_entry(date_str="2026-04-09", score=400),
        _make_history_entry(date_str="2026-04-08", score=600),
    ]
    stats = get_weekly_stats(history, "2026-04-09")
    assert stats["average_score"] == 500.0


# ── record_daily_result ───────────────────────────────────────────────────────

def test_record_daily_result_first_play() -> None:
    """처음 플레이 시 streak=1, total_plays=1."""
    save = {}
    state = record_daily_result(
        save_data=save,
        date_str="2026-04-09",
        score=700,
        is_victory=True,
        correct_answers=7,
        trace_final=20,
        class_key="ANALYST",
        wrong_analyzes=0,
        timeout_events=0,
    )
    assert state["streak"] == 1
    assert state["total_plays"] == 1
    assert state["last_played_date"] == "2026-04-09"
    assert state["best_score"] == 700


def test_record_daily_result_streak_increment() -> None:
    """연속 플레이 시 streak 증가."""
    save = {"daily": {"last_played_date": "2026-04-08", "streak": 3, "total_plays": 5, "best_score": 0, "history": []}}
    state = record_daily_result(
        save_data=save,
        date_str="2026-04-09",
        score=500,
        is_victory=True,
        correct_answers=5,
        trace_final=30,
        class_key="GHOST",
        wrong_analyzes=1,
        timeout_events=0,
    )
    assert state["streak"] == 4


def test_record_daily_result_streak_reset_on_gap() -> None:
    """하루 이상 건너뛰면 streak=1로 리셋."""
    save = {"daily": {"last_played_date": "2026-04-06", "streak": 5, "total_plays": 5, "best_score": 0, "history": []}}
    state = record_daily_result(
        save_data=save,
        date_str="2026-04-09",
        score=400,
        is_victory=False,
        correct_answers=3,
        trace_final=80,
        class_key="CRACKER",
        wrong_analyzes=2,
        timeout_events=1,
    )
    assert state["streak"] == 1


def test_record_daily_result_updates_best_score() -> None:
    """새 점수가 기존 최고 점수보다 높으면 갱신."""
    save = {"daily": {"last_played_date": "2026-04-08", "streak": 1, "total_plays": 1, "best_score": 300, "history": []}}
    state = record_daily_result(
        save_data=save,
        date_str="2026-04-09",
        score=800,
        is_victory=True,
        correct_answers=7,
        trace_final=10,
        class_key="ANALYST",
        wrong_analyzes=0,
        timeout_events=0,
    )
    assert state["best_score"] == 800


def test_record_daily_result_does_not_decrease_best_score() -> None:
    """새 점수가 낮으면 최고 점수 유지."""
    save = {"daily": {"last_played_date": "2026-04-08", "streak": 1, "total_plays": 1, "best_score": 900, "history": []}}
    state = record_daily_result(
        save_data=save,
        date_str="2026-04-09",
        score=400,
        is_victory=True,
        correct_answers=5,
        trace_final=40,
        class_key="ANALYST",
        wrong_analyzes=1,
        timeout_events=0,
    )
    assert state["best_score"] == 900


def test_record_daily_result_stores_timeout_events() -> None:
    """timeout_events가 히스토리에 저장된다."""
    save = {}
    state = record_daily_result(
        save_data=save,
        date_str="2026-04-09",
        score=300,
        is_victory=False,
        correct_answers=4,
        trace_final=70,
        class_key="CRACKER",
        wrong_analyzes=1,
        timeout_events=3,
    )
    history = state["history"]
    assert len(history) == 1
    assert history[0]["timeout_events"] == 3


def test_record_daily_result_history_capped() -> None:
    """히스토리는 DAILY_HISTORY_MAX(30)개로 제한된다."""
    from daily_challenge import DAILY_HISTORY_MAX
    existing_history = [
        {
            "date": f"2026-01-{i:02d}", "score": 100, "is_victory": True,
            "correct_answers": 5, "trace_final": 20, "class_key": "ANALYST",
            "wrong_analyzes": 0, "timeout_events": 0,
        }
        for i in range(1, DAILY_HISTORY_MAX + 1)
    ]
    save = {"daily": {"last_played_date": "2026-01-30", "streak": 30,
                       "total_plays": 30, "best_score": 100, "history": existing_history}}
    state = record_daily_result(
        save_data=save,
        date_str="2026-01-31",
        score=200,
        is_victory=True,
        correct_answers=6,
        trace_final=15,
        class_key="ANALYST",
        wrong_analyzes=0,
        timeout_events=0,
    )
    assert len(state["history"]) == DAILY_HISTORY_MAX
    assert state["history"][-1]["date"] == "2026-01-31"


# ── select_daily_scenarios ────────────────────────────────────────────────────

def test_select_daily_scenarios_deterministic() -> None:
    """같은 날짜는 항상 같은 시나리오를 선택한다."""
    scenarios = (
        [_make_scenario(i, "Easy") for i in range(1, 10)]
        + [_make_scenario(i, "Hard") for i in range(10, 20)]
        + [_make_scenario(100, "NIGHTMARE", is_boss=True)]
    )
    pool1, boss1 = select_daily_scenarios(scenarios, "2026-04-09")
    pool2, boss2 = select_daily_scenarios(scenarios, "2026-04-09")
    assert [s["node_id"] for s in pool1] == [s["node_id"] for s in pool2]
    assert (boss1 is None) == (boss2 is None)
    if boss1 and boss2:
        assert boss1["node_id"] == boss2["node_id"]


def test_select_daily_scenarios_different_dates() -> None:
    """다른 날짜는 다른 시나리오 풀을 선택할 수 있다."""
    scenarios = (
        [_make_scenario(i, "Easy") for i in range(1, 20)]
        + [_make_scenario(i, "Hard") for i in range(20, 40)]
    )
    pool1, _ = select_daily_scenarios(scenarios, "2026-04-09")
    pool2, _ = select_daily_scenarios(scenarios, "2026-04-10")
    ids1 = [s["node_id"] for s in pool1]
    ids2 = [s["node_id"] for s in pool2]
    # 다른 날짜라면 동일하지 않아야 한다 (확률적으로 99.9%+ 다름)
    assert ids1 != ids2


def test_select_daily_scenarios_boss_separated() -> None:
    """보스 시나리오는 combat_pool에 포함되지 않는다."""
    scenarios = (
        [_make_scenario(i, "Easy") for i in range(1, 10)]
        + [_make_scenario(i, "Hard") for i in range(10, 20)]
        + [_make_scenario(100, "NIGHTMARE", is_boss=True)]
    )
    pool, boss = select_daily_scenarios(scenarios, "2026-04-09")
    assert all(not s.get("is_boss", False) for s in pool)
    if boss:
        assert boss.get("is_boss", False)
