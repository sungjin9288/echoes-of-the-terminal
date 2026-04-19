"""런 타임라인(Run Timeline) 기록·저장·마이그레이션·UI 렌더 검증."""

from __future__ import annotations

from copy import deepcopy
from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from progression_system import (
    _make_run_record,
    _migrate_v2_to_v3,
    add_run_to_history,
    get_run_history,
)


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────

def _minimal_save() -> dict[str, Any]:
    return {
        "schema_version": 3,
        "data_fragments": 0,
        "perks": {},
        "campaign": {"runs": 0, "victories": 0, "ascension_unlocked": 0,
                     "class_victories": {"ANALYST": 0, "GHOST": 0, "CRACKER": 0},
                     "points": 0, "cleared": False},
        "achievements": {"unlocked": []},
        "daily": {"last_played_date": "", "history": [], "best_score": 0, "streak": 0, "total_plays": 0},
        "endings": {"unlocked": []},
        "stats": {"total_runs": 0, "total_victories": 0, "total_trace_sum": 0,
                  "total_trace_counted": 0, "best_ascension_cleared": 0, "most_seen_ending": ""},
        "mystery_stats": {"total_engaged": 0, "total_good": 0},
        "run_history": [],
        "personal_records": {},
        "leaderboard": [],
        "theme": "default",
        "language": "ko",
        "tutorial_completed": True,
    }


def _sample_timeline() -> list[dict[str, Any]]:
    return [
        {"event": "correct", "node": 1, "detail": "Easy", "keyword": "GPS"},
        {"event": "wrong", "node": 2, "detail": "오답: 위성"},
        {"event": "timeout", "node": 3, "detail": "+10%"},
        {"event": "artifact", "node": 4, "detail": "trace_shield"},
        {"event": "mystery_skip", "node": 5, "detail": "낡은 서버"},
        {"event": "mystery_engage", "node": 6, "detail": "비밀 창고 (좋은 결과)"},
        {"event": "rest", "node": 7, "detail": "추적도 -20%"},
        {"event": "correct", "node": 8, "detail": "NIGHTMARE", "keyword": "블록체인"},
    ]


# ── _make_run_record timeline 필드 ────────────────────────────────────────

class TestMakeRunRecordTimeline:
    def test_without_timeline_defaults_empty(self) -> None:
        record = _make_run_record(
            date="2026-04-19",
            class_key="ANALYST",
            ascension=0,
            result="victory",
            trace_final=30,
            reward=100,
        )
        assert "timeline" in record
        assert record["timeline"] == []

    def test_with_timeline_stored(self) -> None:
        tl = _sample_timeline()
        record = _make_run_record(
            date="2026-04-19",
            class_key="GHOST",
            ascension=5,
            result="shutdown",
            trace_final=100,
            reward=50,
            timeline=tl,
        )
        assert record["timeline"] == tl

    def test_timeline_is_copied_not_aliased(self) -> None:
        tl = [{"event": "correct", "node": 1, "detail": "Easy"}]
        record = _make_run_record(
            date="2026-04-19", class_key="CRACKER", ascension=0,
            result="victory", trace_final=0, reward=200, timeline=tl,
        )
        tl.append({"event": "wrong", "node": 2, "detail": "x"})
        # record["timeline"]은 원본 리스트와 독립
        assert len(record["timeline"]) == 1

    def test_none_timeline_defaults_empty(self) -> None:
        record = _make_run_record(
            date="2026-04-19", class_key="ANALYST", ascension=0,
            result="victory", trace_final=0, reward=0, timeline=None,
        )
        assert record["timeline"] == []

    def test_invalid_timeline_defaults_empty(self) -> None:
        record = _make_run_record(
            date="2026-04-19", class_key="ANALYST", ascension=0,
            result="victory", trace_final=0, reward=0, timeline="bad",  # type: ignore[arg-type]
        )
        assert record["timeline"] == []


# ── add_run_to_history + timeline 영속 ────────────────────────────────────

class TestAddRunToHistoryTimeline:
    def test_timeline_persisted_in_history(self) -> None:
        save = _minimal_save()
        tl = _sample_timeline()
        add_run_to_history(
            save,
            date="2026-04-19",
            class_key="ANALYST",
            ascension=0,
            result="victory",
            trace_final=20,
            reward=150,
            timeline=tl,
        )
        history = get_run_history(save)
        assert len(history) == 1
        assert history[0]["timeline"] == tl

    def test_empty_timeline_stored(self) -> None:
        save = _minimal_save()
        add_run_to_history(
            save,
            date="2026-04-19",
            class_key="GHOST",
            ascension=3,
            result="shutdown",
            trace_final=100,
            reward=60,
        )
        history = get_run_history(save)
        assert history[0]["timeline"] == []

    def test_multiple_runs_each_have_own_timeline(self) -> None:
        save = _minimal_save()
        tl1 = [{"event": "correct", "node": 1, "detail": "Easy"}]
        tl2 = [{"event": "wrong", "node": 1, "detail": "오답: test"}]
        add_run_to_history(save, date="2026-04-18", class_key="ANALYST",
                           ascension=0, result="victory", trace_final=10,
                           reward=100, timeline=tl1)
        add_run_to_history(save, date="2026-04-19", class_key="GHOST",
                           ascension=0, result="shutdown", trace_final=100,
                           reward=50, timeline=tl2)
        history = get_run_history(save)
        # 최신순: [tl2, tl1]
        assert history[0]["timeline"] == tl2
        assert history[1]["timeline"] == tl1


# ── 스키마 v2 → v3 마이그레이션 ───────────────────────────────────────────

class TestMigrateV2ToV3:
    def test_schema_version_bumped_to_3(self) -> None:
        data = {"schema_version": 2, "run_history": []}
        result = _migrate_v2_to_v3(data)
        assert result["schema_version"] == 3

    def test_existing_entries_get_empty_timeline(self) -> None:
        data = {
            "schema_version": 2,
            "run_history": [
                {"date": "2026-04-01", "result": "victory", "trace_final": 0},
                {"date": "2026-04-02", "result": "shutdown", "trace_final": 100},
            ],
        }
        result = _migrate_v2_to_v3(data)
        for entry in result["run_history"]:
            assert "timeline" in entry
            assert entry["timeline"] == []

    def test_entries_that_already_have_timeline_are_preserved(self) -> None:
        tl = [{"event": "correct", "node": 1, "detail": "Easy"}]
        data = {
            "schema_version": 2,
            "run_history": [{"date": "2026-04-03", "timeline": tl}],
        }
        result = _migrate_v2_to_v3(data)
        # 이미 timeline 필드가 있으면 덮어쓰지 않음
        assert result["run_history"][0]["timeline"] == tl

    def test_missing_run_history_handled(self) -> None:
        data = {"schema_version": 2}
        result = _migrate_v2_to_v3(data)
        assert result["schema_version"] == 3
        # run_history 없으면 그대로

    def test_original_not_mutated(self) -> None:
        original = {"schema_version": 2, "run_history": [{"date": "x"}]}
        _migrate_v2_to_v3(original)
        assert "timeline" not in original["run_history"][0]


# ── UI 렌더: render_run_timeline ─────────────────────────────────────────

def _capture_timeline(entry: dict[str, Any]) -> str:
    from ui_renderer import render_run_timeline
    import ui_renderer

    buf = StringIO()
    new_console = Console(file=buf, width=200, legacy_windows=False)
    original = ui_renderer.console
    ui_renderer.console = new_console
    try:
        render_run_timeline(entry)
    finally:
        ui_renderer.console = original
    return buf.getvalue()


class TestRenderRunTimeline:
    def test_renders_event_icons(self) -> None:
        entry = {
            "date": "2026-04-19",
            "class_key": "ANALYST",
            "ascension": 0,
            "result": "victory",
            "timeline": _sample_timeline(),
        }
        output = _capture_timeline(entry)
        assert "✓" in output    # correct
        assert "✗" in output    # wrong
        assert "⏱" in output    # timeout
        assert "◆" in output    # artifact
        assert "?" in output    # mystery_engage
        assert "—" in output    # mystery_skip
        assert "♥" in output    # rest

    def test_renders_node_numbers(self) -> None:
        entry = {
            "date": "2026-04-19",
            "class_key": "GHOST",
            "ascension": 5,
            "result": "shutdown",
            "timeline": [{"event": "correct", "node": 3, "detail": "Hard"}],
        }
        output = _capture_timeline(entry)
        assert "N03" in output

    def test_empty_timeline_shows_no_data_message(self) -> None:
        entry = {
            "date": "2026-04-19",
            "class_key": "CRACKER",
            "ascension": 0,
            "result": "victory",
            "timeline": [],
        }
        output = _capture_timeline(entry)
        assert "타임라인 데이터 없음" in output

    def test_missing_timeline_key_shows_no_data_message(self) -> None:
        entry = {
            "date": "2026-04-19",
            "class_key": "ANALYST",
            "ascension": 0,
            "result": "victory",
            # timeline 키 없음
        }
        output = _capture_timeline(entry)
        assert "타임라인 데이터 없음" in output

    def test_header_contains_class_and_result(self) -> None:
        entry = {
            "date": "2026-04-19",
            "class_key": "GHOST",
            "ascension": 10,
            "result": "victory",
            "timeline": [{"event": "rest", "node": 2, "detail": "추적도 -20%"}],
        }
        output = _capture_timeline(entry)
        assert "GHOST" in output
        assert "2026-04-19" in output
        assert "VICTORY" in output

    def test_detail_text_shown(self) -> None:
        entry = {
            "date": "2026-04-19",
            "class_key": "ANALYST",
            "ascension": 0,
            "result": "shutdown",
            "timeline": [{"event": "wrong", "node": 1, "detail": "오답: 위성"}],
        }
        output = _capture_timeline(entry)
        assert "오답: 위성" in output
