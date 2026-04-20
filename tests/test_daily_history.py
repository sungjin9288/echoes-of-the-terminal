"""v1.13.0 — 일일 도전 결과 히스토리 테스트.

검증 범위:
1. render_daily_history 바 차트 렌더링 (빈 히스토리, 단일/복수 항목, 등급·바·오답 표시)
2. daily_streak_3/7/30 업적 해금 조건
3. render_records_screen이 히스토리 호출하는지 통합 검증
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

from daily_challenge import (
    DAILY_HISTORY_MAX,
    _normalize_history,
    get_daily_state,
    get_performance_grade,
    record_daily_result,
)
from achievement_system import evaluate_achievements


# ── 테스트 헬퍼 ──────────────────────────────────────────────────────────────

def _make_entry(
    date_str: str = "2026-04-20",
    score: int = 500,
    is_victory: bool = True,
    correct_answers: int = 5,
    trace_final: int = 30,
    class_key: str = "ANALYST",
    wrong_analyzes: int = 0,
    timeout_events: int = 0,
) -> dict[str, Any]:
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


def _make_save_data(streak: int = 0, history: list | None = None) -> dict[str, Any]:
    return {
        "data_fragments": 0,
        "perks": {},
        "campaign": {"runs": 0, "victories": 0, "points": 0, "ascension_unlocked": 0},
        "achievements": {"unlocked": []},
        "daily": {
            "streak": streak,
            "best_score": 0,
            "total_plays": 0,
            "last_played_date": "",
            "history": history or [],
        },
    }


# ── TestRenderDailyHistoryBarChart ───────────────────────────────────────────

class TestRenderDailyHistoryBarChart:
    """render_daily_history의 바 차트 렌더링을 검증한다."""

    def test_empty_history_prints_message(self, monkeypatch) -> None:
        """히스토리가 없으면 안내 메시지를 출력한다."""
        import ui_renderer
        printed: list[str] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: printed.append(str(a[0])))
        ui_renderer.render_daily_history([])
        assert any("히스토리" in p for p in printed)

    def test_single_entry_renders_table(self, monkeypatch) -> None:
        """단일 항목이 있으면 테이블을 출력한다."""
        import ui_renderer
        from rich.table import Table
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        ui_renderer.render_daily_history([_make_entry(score=800)])
        assert any(isinstance(r, Table) for r in rendered)

    def _get_column_cells(self, table: Any, col_index: int) -> list[Any]:
        """Rich Table의 지정 컬럼 셀 목록을 반환한다."""
        from rich.table import Table
        from rich.text import Text
        col = table.columns[col_index]
        return list(col._cells)

    def _all_cells(self, table: Any) -> list[Any]:
        """Rich Table의 모든 셀을 1차원 리스트로 반환한다."""
        cells = []
        for col in table.columns:
            cells.extend(col._cells)
        return cells

    def test_bar_proportional_to_max_score(self, monkeypatch) -> None:
        """최고 점수 행은 바가 가득 차고, 0점 행은 비어 있어야 한다."""
        import ui_renderer
        from rich.table import Table
        from rich.text import Text
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        history = [
            _make_entry(date_str="2026-04-19", score=0, is_victory=False),
            _make_entry(date_str="2026-04-20", score=1000, is_victory=True),
        ]
        ui_renderer.render_daily_history(history)
        table = next(r for r in rendered if isinstance(r, Table))
        # 바 차트 컬럼(index=2)의 셀 확인
        bar_cells = self._get_column_cells(table, 2)
        bar_texts = [c for c in bar_cells if isinstance(c, Text)]
        filled_bars = [t.plain for t in bar_texts if "█" in t.plain]
        empty_bars = [t.plain for t in bar_texts if t.plain.count("░") == 16]
        assert len(filled_bars) >= 1
        assert len(empty_bars) >= 1

    def test_victory_bar_green_fail_bar_red(self, monkeypatch) -> None:
        """승리 바는 green, 패배 바는 red 스타일이어야 한다."""
        import ui_renderer
        from rich.table import Table
        from rich.text import Text
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        history = [
            _make_entry(date_str="2026-04-19", score=300, is_victory=False),
            _make_entry(date_str="2026-04-20", score=800, is_victory=True),
        ]
        ui_renderer.render_daily_history(history)
        table = next(r for r in rendered if isinstance(r, Table))
        bar_cells = self._get_column_cells(table, 2)
        bar_texts = [c for c in bar_cells if isinstance(c, Text)]
        styles = [str(t.style) for t in bar_texts]
        assert any("green" in s for s in styles)
        assert any("red" in s for s in styles)

    def test_grade_displayed_per_entry(self, monkeypatch) -> None:
        """각 항목의 등급(S/A/B/C/D)이 테이블에 포함되어야 한다."""
        import ui_renderer
        from rich.table import Table
        from rich.text import Text
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        history = [
            _make_entry(score=1100),  # S
            _make_entry(date_str="2026-04-19", score=750),  # A
        ]
        ui_renderer.render_daily_history(history)
        table = next(r for r in rendered if isinstance(r, Table))
        # 등급 컬럼(index=4)
        grade_cells = self._get_column_cells(table, 4)
        grade_plains = [c.plain if isinstance(c, Text) else str(c) for c in grade_cells]
        assert "S" in grade_plains
        assert "A" in grade_plains

    def test_wrong_analyzes_displayed(self, monkeypatch) -> None:
        """오답 횟수가 테이블 오답 컬럼에 표시되어야 한다."""
        import ui_renderer
        from rich.table import Table
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        history = [_make_entry(score=600, wrong_analyzes=3)]
        ui_renderer.render_daily_history(history)
        table = next(r for r in rendered if isinstance(r, Table))
        # 오답 컬럼(index=5)
        wrong_cells = self._get_column_cells(table, 5)
        wrong_strs = [c.plain if hasattr(c, "plain") else str(c) for c in wrong_cells]
        assert "3" in wrong_strs

    def test_max_14_entries_rendered(self, monkeypatch) -> None:
        """히스토리가 14개 초과여도 최신 14개만 렌더링한다."""
        import ui_renderer
        from rich.table import Table
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        history = [_make_entry(date_str=f"2026-01-{i:02d}", score=100 * i) for i in range(1, 20)]
        ui_renderer.render_daily_history(history)
        table = next(r for r in rendered if isinstance(r, Table))
        assert len(table.rows) <= 14

    def test_table_title_contains_history(self, monkeypatch) -> None:
        """테이블 제목에 'HISTORY'가 포함된다."""
        import ui_renderer
        from rich.table import Table
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        ui_renderer.render_daily_history([_make_entry()])
        table = next(r for r in rendered if isinstance(r, Table))
        assert "HISTORY" in (table.title or "").upper()

    def test_most_recent_entry_first(self, monkeypatch) -> None:
        """최신 날짜가 테이블 날짜 컬럼의 첫 번째 셀로 표시된다."""
        import ui_renderer
        from rich.table import Table
        rendered: list[Any] = []
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: rendered.append(a[0]))
        history = [
            _make_entry(date_str="2026-04-01", score=100),
            _make_entry(date_str="2026-04-10", score=200),
            _make_entry(date_str="2026-04-20", score=800),
        ]
        ui_renderer.render_daily_history(history)
        table = next(r for r in rendered if isinstance(r, Table))
        # 날짜 컬럼(index=0)의 첫 번째 셀이 최신 날짜
        date_cells = self._get_column_cells(table, 0)
        first_date = date_cells[0].plain if hasattr(date_cells[0], "plain") else str(date_cells[0])
        assert "2026-04-20" in first_date


# ── TestDailyStreakAchievements ────────────────────────────────────────────

class TestDailyStreakAchievements:
    """daily_streak_3/7/30 업적 해금 조건을 검증한다."""

    def test_streak_2_unlocks_nothing(self) -> None:
        """streak 2일이면 streak 업적 미해금."""
        save = _make_save_data(streak=2)
        result = evaluate_achievements(save)
        unlocked_ids = {a["id"] for a in result}
        assert "daily_streak_3" not in unlocked_ids
        assert "daily_streak_7" not in unlocked_ids

    def test_streak_3_unlocks_streak_3(self) -> None:
        """streak 3일이면 daily_streak_3 해금."""
        save = _make_save_data(streak=3)
        result = evaluate_achievements(save)
        unlocked_ids = {a["id"] for a in result}
        assert "daily_streak_3" in unlocked_ids
        assert "daily_streak_7" not in unlocked_ids

    def test_streak_7_unlocks_3_and_7(self) -> None:
        """streak 7일이면 daily_streak_3, daily_streak_7 모두 해금."""
        save = _make_save_data(streak=7)
        result = evaluate_achievements(save)
        unlocked_ids = {a["id"] for a in result}
        assert "daily_streak_3" in unlocked_ids
        assert "daily_streak_7" in unlocked_ids
        assert "daily_streak_30" not in unlocked_ids

    def test_streak_30_unlocks_all_three(self) -> None:
        """streak 30일이면 세 streak 업적 모두 해금."""
        save = _make_save_data(streak=30)
        result = evaluate_achievements(save)
        unlocked_ids = {a["id"] for a in result}
        assert "daily_streak_3" in unlocked_ids
        assert "daily_streak_7" in unlocked_ids
        assert "daily_streak_30" in unlocked_ids

    def test_streak_50_also_unlocks_all_three(self) -> None:
        """streak 30 이상이면 세 streak 업적 모두 해금."""
        save = _make_save_data(streak=50)
        result = evaluate_achievements(save)
        unlocked_ids = {a["id"] for a in result}
        assert "daily_streak_30" in unlocked_ids

    def test_already_unlocked_streak_not_duplicated(self) -> None:
        """이미 해금된 streak 업적은 newly_unlocked에 재등장하지 않는다."""
        save = _make_save_data(streak=7)
        save["achievements"] = {"unlocked": ["daily_streak_3", "daily_streak_7"]}
        result = evaluate_achievements(save)
        unlocked_ids = [a["id"] for a in result]
        assert unlocked_ids.count("daily_streak_3") == 0
        assert unlocked_ids.count("daily_streak_7") == 0

    def test_missing_daily_field_no_crash(self) -> None:
        """daily 필드가 없어도 예외 없이 처리된다."""
        save = _make_save_data(streak=0)
        del save["daily"]
        result = evaluate_achievements(save)
        assert isinstance(result, list)

    def test_daily_not_dict_no_crash(self) -> None:
        """daily 필드가 dict가 아니어도 예외 없이 처리된다."""
        save = _make_save_data(streak=0)
        save["daily"] = "corrupted"
        result = evaluate_achievements(save)
        assert isinstance(result, list)

    def test_streak_in_achievement_data(self) -> None:
        """세 streak 업적이 ACHIEVEMENT_INDEX에 등록되어 있다."""
        from achievement_data import ACHIEVEMENT_INDEX
        assert "daily_streak_3" in ACHIEVEMENT_INDEX
        assert "daily_streak_7" in ACHIEVEMENT_INDEX
        assert "daily_streak_30" in ACHIEVEMENT_INDEX

    def test_streak_achievement_metadata(self) -> None:
        """streak 업적에 title과 desc가 있다."""
        from achievement_data import ACHIEVEMENT_INDEX
        for aid in ("daily_streak_3", "daily_streak_7", "daily_streak_30"):
            entry = ACHIEVEMENT_INDEX[aid]
            assert entry.get("title")
            assert entry.get("desc")


# ── TestRecordsScreenDailyHistory ──────────────────────────────────────────

class TestRecordsScreenDailyHistory:
    """render_records_screen이 히스토리 바 차트를 호출하는지 통합 검증한다."""

    def _make_snapshots(self, history: list | None = None) -> dict[str, Any]:
        daily_state = {
            "streak": 5,
            "best_score": 800,
            "total_plays": 10,
            "last_played_date": "2026-04-20",
            "history": history or [],
        }
        return dict(
            achievement_snapshot={"unlocked_count": 0, "total_count": 118, "unlocked_ids": [], "unlocked_entries": []},
            endings_snapshot={"unlocked": [], "unlocked_count": 0},
            campaign_snapshot={
                "points": 0, "points_target": 60000,
                "victories": 0, "victories_target": 450,
                "class_victories": {}, "class_target": 120,
                "ascension_unlocked": 0, "cleared": False,
            },
            daily_state=daily_state,
        )

    def test_render_daily_history_called_when_history_exists(self, monkeypatch) -> None:
        """히스토리가 있을 때 render_daily_history가 호출된다."""
        import ui_renderer
        calls: list[str] = []
        monkeypatch.setattr(ui_renderer, "render_daily_history", lambda h: calls.append("called"))
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: None)
        snaps = self._make_snapshots(history=[_make_entry()])
        ui_renderer.render_records_screen(**snaps)
        assert "called" in calls

    def test_render_daily_history_not_called_when_empty(self, monkeypatch) -> None:
        """히스토리가 비었으면 render_daily_history가 호출되지 않는다."""
        import ui_renderer
        calls: list[str] = []
        monkeypatch.setattr(ui_renderer, "render_daily_history", lambda h: calls.append("called"))
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: None)
        snaps = self._make_snapshots(history=[])
        ui_renderer.render_records_screen(**snaps)
        assert calls == []

    def test_render_daily_history_receives_correct_history(self, monkeypatch) -> None:
        """render_daily_history에 daily_state["history"]가 전달된다."""
        import ui_renderer
        received: list[Any] = []
        monkeypatch.setattr(ui_renderer, "render_daily_history", lambda h: received.append(h))
        monkeypatch.setattr(ui_renderer.console, "print", lambda *a, **kw: None)
        hist = [_make_entry(date_str=f"2026-04-{i:02d}", score=100 * i) for i in range(1, 6)]
        snaps = self._make_snapshots(history=hist)
        ui_renderer.render_records_screen(**snaps)
        assert received and received[0] == hist


# ── TestNormalizeHistoryRingBuffer ──────────────────────────────────────────

class TestNormalizeHistoryRingBuffer:
    """_normalize_history가 30일 링버퍼를 올바르게 유지하는지 검증한다."""

    def test_empty_list_returns_empty(self) -> None:
        assert _normalize_history([]) == []

    def test_non_list_returns_empty(self) -> None:
        assert _normalize_history("invalid") == []  # type: ignore[arg-type]
        assert _normalize_history(None) == []  # type: ignore[arg-type]

    def test_entries_capped_at_30(self) -> None:
        entries = [_make_entry(date_str=f"2026-01-{i:02d}") for i in range(1, 35)]
        result = _normalize_history(entries)
        assert len(result) == DAILY_HISTORY_MAX

    def test_most_recent_30_kept(self) -> None:
        entries = [_make_entry(date_str=f"2026-01-{i:02d}", score=i * 10) for i in range(1, 35)]
        result = _normalize_history(entries)
        # 마지막 30개를 유지 (1~4번 제거, 5~34번 유지)
        scores = [e["score"] for e in result]
        assert 40 not in scores  # score=40 (4번째) 제거됨
        assert 50 in scores      # score=50 (5번째) 유지됨
        assert 340 in scores     # score=340 (34번째) 유지됨

    def test_invalid_entry_skipped(self) -> None:
        entries = [_make_entry(), "not_a_dict", None, _make_entry(date_str="2026-04-19")]
        result = _normalize_history(entries)  # type: ignore[arg-type]
        assert len(result) == 2

    def test_score_clamped_to_zero(self) -> None:
        entry = _make_entry(score=-100)
        result = _normalize_history([entry])
        assert result[0]["score"] == 0

    def test_required_fields_present(self) -> None:
        result = _normalize_history([_make_entry()])
        assert all(
            key in result[0]
            for key in ("date", "score", "is_victory", "correct_answers",
                        "trace_final", "class_key", "wrong_analyzes", "timeout_events")
        )


# ── TestRecordDailyResult ──────────────────────────────────────────────────

class TestRecordDailyResult:
    """record_daily_result의 세이브 기록 기능을 검증한다."""

    def _save(self) -> dict[str, Any]:
        return {
            "data_fragments": 0,
            "daily": {},
        }

    def test_first_play_streak_is_1(self) -> None:
        save = self._save()
        result = record_daily_result(save, "2026-04-20", 500, True, 5, 20, "ANALYST", 0)
        assert result["streak"] == 1

    def test_consecutive_day_increments_streak(self) -> None:
        save = self._save()
        record_daily_result(save, "2026-04-19", 500, True, 5, 20, "ANALYST", 0)
        result = record_daily_result(save, "2026-04-20", 600, True, 6, 10, "ANALYST", 0)
        assert result["streak"] == 2

    def test_gap_resets_streak(self) -> None:
        save = self._save()
        record_daily_result(save, "2026-04-10", 500, True, 5, 20, "ANALYST", 0)
        # 10일 후
        result = record_daily_result(save, "2026-04-20", 600, True, 6, 10, "ANALYST", 0)
        assert result["streak"] == 1

    def test_best_score_updated(self) -> None:
        save = self._save()
        record_daily_result(save, "2026-04-19", 300, False, 3, 60, "GHOST", 2)
        result = record_daily_result(save, "2026-04-20", 900, True, 8, 5, "GHOST", 0)
        assert result["best_score"] == 900

    def test_history_appended(self) -> None:
        save = self._save()
        record_daily_result(save, "2026-04-20", 500, True, 5, 20, "ANALYST", 0)
        assert len(save["daily"]["history"]) == 1
        assert save["daily"]["history"][0]["score"] == 500

    def test_history_capped_at_30_entries(self) -> None:
        save = self._save()
        for i in range(35):
            date_str = f"2026-01-{i % 28 + 1:02d}"
            record_daily_result(save, date_str, i * 10, True, 5, 20, "ANALYST", 0)
        assert len(save["daily"]["history"]) <= DAILY_HISTORY_MAX

    def test_total_plays_increments(self) -> None:
        save = self._save()
        record_daily_result(save, "2026-04-19", 500, True, 5, 20, "ANALYST", 0)
        record_daily_result(save, "2026-04-20", 600, True, 5, 20, "ANALYST", 0)
        assert save["daily"]["total_plays"] == 2
