"""run_history 기능 유닛 테스트.

add_run_to_history / get_run_history API,
최대 개수 제한, 역순 정렬, 세이브 정규화, UI render_run_history 연동 검증.
"""

from __future__ import annotations

import copy

import pytest

from progression_system import (
    DEFAULT_SAVE_DATA,
    RUN_HISTORY_MAX,
    add_run_to_history,
    get_run_history,
    load_save,
)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _empty_save() -> dict:
    return copy.deepcopy(DEFAULT_SAVE_DATA)


def _add(save: dict, **kwargs) -> None:
    """기본값으로 채운 런 기록을 추가하는 헬퍼."""
    defaults = dict(
        date="2026-01-01",
        class_key="ANALYST",
        ascension=0,
        result="victory",
        trace_final=30,
        reward=100,
        correct_answers=5,
        ending_id="",
    )
    defaults.update(kwargs)
    add_run_to_history(save, **defaults)


# ── add_run_to_history ───────────────────────────────────────────────────────

class TestAddRunToHistory:
    def test_first_entry_added(self) -> None:
        save = _empty_save()
        _add(save, result="victory")
        assert len(save["run_history"]) == 1

    def test_entry_contains_expected_fields(self) -> None:
        save = _empty_save()
        _add(save, date="2026-04-18", class_key="GHOST", ascension=5,
             result="shutdown", trace_final=95, reward=60, correct_answers=3, ending_id="ghost_end")
        rec = save["run_history"][0]
        assert rec["date"] == "2026-04-18"
        assert rec["class_key"] == "GHOST"
        assert rec["ascension"] == 5
        assert rec["result"] == "shutdown"
        assert rec["trace_final"] == 95
        assert rec["reward"] == 60
        assert rec["correct_answers"] == 3
        assert rec["ending_id"] == "ghost_end"

    def test_multiple_entries_appended_in_order(self) -> None:
        save = _empty_save()
        _add(save, date="2026-01-01")
        _add(save, date="2026-01-02")
        _add(save, date="2026-01-03")
        assert save["run_history"][0]["date"] == "2026-01-01"
        assert save["run_history"][-1]["date"] == "2026-01-03"

    def test_max_limit_enforced(self) -> None:
        save = _empty_save()
        for i in range(RUN_HISTORY_MAX + 5):
            _add(save, date=f"2026-01-{i+1:02d}")
        assert len(save["run_history"]) == RUN_HISTORY_MAX

    def test_oldest_entries_dropped_first(self) -> None:
        save = _empty_save()
        for i in range(RUN_HISTORY_MAX + 3):
            _add(save, date=f"2026-01-{i+1:02d}")
        # 처음 3개는 삭제되어야 함
        assert save["run_history"][0]["date"] == "2026-01-04"

    def test_trace_clamped_above_100(self) -> None:
        save = _empty_save()
        _add(save, trace_final=150)
        assert save["run_history"][0]["trace_final"] == 100

    def test_trace_clamped_below_0(self) -> None:
        save = _empty_save()
        _add(save, trace_final=-10)
        assert save["run_history"][0]["trace_final"] == 0

    def test_ascension_non_negative(self) -> None:
        save = _empty_save()
        _add(save, ascension=-5)
        assert save["run_history"][0]["ascension"] == 0

    def test_reward_non_negative(self) -> None:
        save = _empty_save()
        _add(save, reward=-100)
        assert save["run_history"][0]["reward"] == 0

    def test_missing_run_history_field_initialized(self) -> None:
        """run_history 키가 없는 save_data에도 정상 동작해야 한다."""
        save = _empty_save()
        del save["run_history"]
        _add(save)
        assert len(save["run_history"]) == 1

    def test_corrupted_run_history_reset(self) -> None:
        """run_history가 리스트가 아니면 초기화 후 추가해야 한다."""
        save = _empty_save()
        save["run_history"] = "corrupted"  # type: ignore[assignment]
        _add(save)
        assert isinstance(save["run_history"], list)
        assert len(save["run_history"]) == 1


# ── get_run_history ──────────────────────────────────────────────────────────

class TestGetRunHistory:
    def test_empty_returns_empty_list(self) -> None:
        save = _empty_save()
        assert get_run_history(save) == []

    def test_returns_most_recent_first(self) -> None:
        save = _empty_save()
        _add(save, date="2026-01-01")
        _add(save, date="2026-01-02")
        _add(save, date="2026-01-03")
        history = get_run_history(save)
        assert history[0]["date"] == "2026-01-03"
        assert history[-1]["date"] == "2026-01-01"

    def test_returns_copy_not_reference(self) -> None:
        """반환된 리스트를 수정해도 원본에 영향이 없어야 한다."""
        save = _empty_save()
        _add(save, date="2026-01-01")
        history = get_run_history(save)
        history.clear()
        assert len(save["run_history"]) == 1

    def test_corrupted_history_returns_empty(self) -> None:
        save = _empty_save()
        save["run_history"] = None  # type: ignore[assignment]
        assert get_run_history(save) == []


# ── 세이브 정규화 ─────────────────────────────────────────────────────────────

class TestSaveNormalization:
    def test_missing_run_history_defaults_to_empty_list(self, tmp_path) -> None:
        import json, copy
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data.pop("run_history", None)
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert result["run_history"] == []

    def test_corrupted_run_history_normalized(self, tmp_path) -> None:
        import json, copy
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data["run_history"] = 42  # 잘못된 타입
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert result["run_history"] == []

    def test_valid_run_history_preserved(self, tmp_path) -> None:
        import json, copy
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data["run_history"] = [
            {"date": "2026-04-18", "class_key": "ANALYST", "ascension": 0,
             "result": "victory", "trace_final": 30, "reward": 100,
             "correct_answers": 5, "ending_id": ""},
        ]
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert len(result["run_history"]) == 1
        assert result["run_history"][0]["date"] == "2026-04-18"


# ── render_run_history UI 연동 ────────────────────────────────────────────────

class TestRenderRunHistory:
    def test_renders_without_error_empty(self, monkeypatch) -> None:
        from ui_renderer import render_run_history
        printed: list = []
        monkeypatch.setattr("ui_renderer.console.print", lambda *a, **kw: printed.append(a))
        render_run_history([])
        assert printed  # 최소 1회 호출

    def test_renders_victory_and_shutdown(self, monkeypatch) -> None:
        """render_run_history가 Rich Table에 VICTORY·SHUTDOWN 셀을 추가해야 한다."""
        from io import StringIO
        from rich.console import Console
        from ui_renderer import render_run_history
        import ui_renderer

        # 실제 콘솔을 StringIO 기반 콘솔로 교체해 렌더링 결과를 캡처한다
        buf = StringIO()
        test_console = Console(file=buf, highlight=False, markup=True, width=200)
        monkeypatch.setattr(ui_renderer, "console", test_console)

        history = [
            {"date": "2026-04-18", "class_key": "ANALYST", "ascension": 3,
             "result": "victory", "trace_final": 20, "reward": 150,
             "correct_answers": 7, "ending_id": "silent_trace"},
            {"date": "2026-04-17", "class_key": "GHOST", "ascension": 0,
             "result": "shutdown", "trace_final": 100, "reward": 40,
             "correct_answers": 2, "ending_id": ""},
        ]
        render_run_history(history)
        output = buf.getvalue()
        assert "VICTORY" in output
        assert "SHUTDOWN" in output
