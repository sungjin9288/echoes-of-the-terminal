"""개인 최고 기록 (Personal Records) 기능 유닛 테스트.

update_personal_records / get_personal_records API,
승리/패배 분기, 최고 기록 경신, 세이브 정규화, UI render_personal_records 연동 검증.
"""

from __future__ import annotations

import copy

import pytest

from progression_system import (
    DEFAULT_SAVE_DATA,
    get_personal_records,
    load_save,
    update_personal_records,
)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _empty_save() -> dict:
    return copy.deepcopy(DEFAULT_SAVE_DATA)


def _update(save: dict, **kwargs) -> None:
    """기본값으로 채운 런 기록을 업데이트하는 헬퍼."""
    defaults = dict(
        class_key="ANALYST",
        ascension=0,
        result="victory",
        trace_final=30,
        reward=100,
        correct_answers=5,
    )
    defaults.update(kwargs)
    update_personal_records(save, **defaults)


# ── update_personal_records ──────────────────────────────────────────────────

class TestUpdatePersonalRecords:
    def test_first_victory_creates_entry(self) -> None:
        save = _empty_save()
        _update(save, class_key="ANALYST", ascension=0)
        records = save["personal_records"]
        assert "ANALYST_0" in records

    def test_run_count_increments_always(self) -> None:
        save = _empty_save()
        _update(save, result="victory")
        _update(save, result="shutdown")
        _update(save, result="aborted")
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["run_count"] == 3

    def test_victory_count_only_increments_on_victory(self) -> None:
        save = _empty_save()
        _update(save, result="victory")
        _update(save, result="shutdown")
        _update(save, result="victory")
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["victory_count"] == 2

    def test_best_trace_set_on_first_victory(self) -> None:
        save = _empty_save()
        _update(save, result="victory", trace_final=40)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_trace"] == 40

    def test_best_trace_updated_when_lower(self) -> None:
        save = _empty_save()
        _update(save, result="victory", trace_final=40)
        _update(save, result="victory", trace_final=20)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_trace"] == 20

    def test_best_trace_not_updated_when_higher(self) -> None:
        save = _empty_save()
        _update(save, result="victory", trace_final=20)
        _update(save, result="victory", trace_final=50)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_trace"] == 20

    def test_best_trace_none_when_no_victory(self) -> None:
        save = _empty_save()
        _update(save, result="shutdown", trace_final=90)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_trace"] is None

    def test_best_reward_updated_when_higher(self) -> None:
        save = _empty_save()
        _update(save, result="victory", reward=100)
        _update(save, result="victory", reward=200)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_reward"] == 200

    def test_best_reward_not_updated_when_lower(self) -> None:
        save = _empty_save()
        _update(save, result="victory", reward=200)
        _update(save, result="victory", reward=50)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_reward"] == 200

    def test_best_correct_updated_when_higher(self) -> None:
        save = _empty_save()
        _update(save, result="victory", correct_answers=5)
        _update(save, result="victory", correct_answers=7)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_correct"] == 7

    def test_shutdown_does_not_update_best_fields(self) -> None:
        save = _empty_save()
        _update(save, result="victory", trace_final=40, reward=100, correct_answers=5)
        _update(save, result="shutdown", trace_final=5, reward=9999, correct_answers=99)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_trace"] == 40
        assert entry["best_reward"] == 100
        assert entry["best_correct"] == 5

    def test_separate_entries_per_class_and_ascension(self) -> None:
        save = _empty_save()
        _update(save, class_key="ANALYST", ascension=0)
        _update(save, class_key="GHOST", ascension=0)
        _update(save, class_key="ANALYST", ascension=5)
        assert len(save["personal_records"]) == 3
        assert "ANALYST_0" in save["personal_records"]
        assert "GHOST_0" in save["personal_records"]
        assert "ANALYST_5" in save["personal_records"]

    def test_ascension_clamped_non_negative(self) -> None:
        save = _empty_save()
        _update(save, ascension=-3)
        assert "ANALYST_0" in save["personal_records"]

    def test_corrupted_personal_records_reset(self) -> None:
        save = _empty_save()
        save["personal_records"] = "corrupted"  # type: ignore[assignment]
        _update(save)
        assert isinstance(save["personal_records"], dict)
        assert len(save["personal_records"]) == 1

    def test_trace_clamped_0_to_100(self) -> None:
        save = _empty_save()
        _update(save, result="victory", trace_final=150)
        entry = save["personal_records"]["ANALYST_0"]
        assert entry["best_trace"] == 100

        save2 = _empty_save()
        _update(save2, result="victory", trace_final=-10)
        entry2 = save2["personal_records"]["ANALYST_0"]
        assert entry2["best_trace"] == 0


# ── get_personal_records ─────────────────────────────────────────────────────

class TestGetPersonalRecords:
    def test_empty_returns_empty_list(self) -> None:
        save = _empty_save()
        assert get_personal_records(save) == []

    def test_returns_sorted_by_class_then_ascension(self) -> None:
        save = _empty_save()
        _update(save, class_key="GHOST", ascension=5)
        _update(save, class_key="ANALYST", ascension=10)
        _update(save, class_key="ANALYST", ascension=0)
        records = get_personal_records(save)
        assert records[0]["class_key"] == "ANALYST"
        assert records[0]["ascension"] == 0
        assert records[1]["class_key"] == "ANALYST"
        assert records[1]["ascension"] == 10
        assert records[2]["class_key"] == "GHOST"

    def test_filter_by_class_key(self) -> None:
        save = _empty_save()
        _update(save, class_key="ANALYST", ascension=0)
        _update(save, class_key="GHOST", ascension=0)
        records = get_personal_records(save, class_key="ANALYST")
        assert len(records) == 1
        assert records[0]["class_key"] == "ANALYST"

    def test_filter_case_insensitive(self) -> None:
        save = _empty_save()
        _update(save, class_key="CRACKER", ascension=0)
        records = get_personal_records(save, class_key="cracker")
        assert len(records) == 1

    def test_corrupted_records_returns_empty(self) -> None:
        save = _empty_save()
        save["personal_records"] = None  # type: ignore[assignment]
        assert get_personal_records(save) == []


# ── 세이브 정규화 ─────────────────────────────────────────────────────────────

class TestSaveNormalization:
    def test_missing_personal_records_defaults_to_empty_dict(self, tmp_path) -> None:
        import json
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data.pop("personal_records", None)
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert result["personal_records"] == {}

    def test_corrupted_personal_records_normalized(self, tmp_path) -> None:
        import json
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data["personal_records"] = 42  # 잘못된 타입
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert result["personal_records"] == {}


# ── render_personal_records UI 연동 ──────────────────────────────────────────

class TestRenderPersonalRecords:
    def test_renders_without_error_empty(self, monkeypatch) -> None:
        from ui_renderer import render_personal_records
        printed: list = []
        monkeypatch.setattr("ui_renderer.console.print", lambda *a, **kw: printed.append(a))
        render_personal_records([])
        assert printed

    def test_renders_records_with_victory(self, monkeypatch) -> None:
        from io import StringIO
        from rich.console import Console
        import ui_renderer

        buf = StringIO()
        test_console = Console(file=buf, highlight=False, markup=True, width=200)
        monkeypatch.setattr(ui_renderer, "console", test_console)

        records = [
            {
                "class_key": "ANALYST", "ascension": 3,
                "run_count": 5, "victory_count": 3,
                "best_trace": 15, "best_reward": 200, "best_correct": 7,
            },
            {
                "class_key": "GHOST", "ascension": 0,
                "run_count": 2, "victory_count": 0,
                "best_trace": None, "best_reward": 0, "best_correct": 0,
            },
        ]
        from ui_renderer import render_personal_records
        render_personal_records(records)
        output = buf.getvalue()
        assert "ANALYST" in output
        assert "GHOST" in output
        assert "PERSONAL RECORDS" in output
