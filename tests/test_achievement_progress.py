"""업적 진행률(achievement_progress) 계산 및 UI 출력 검증."""

from __future__ import annotations

from copy import deepcopy
from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from achievement_progress import (
    PROGRESS_SPECS,
    compute_achievement_progress,
    format_progress_bar,
    get_locked_progress_entries,
)


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────

def _empty_save() -> dict[str, Any]:
    return {
        "data_fragments": 0,
        "perks": {},
        "campaign": {
            "points": 0,
            "runs": 0,
            "victories": 0,
            "ascension_unlocked": 0,
            "class_victories": {"ANALYST": 0, "GHOST": 0, "CRACKER": 0},
            "cleared": False,
        },
        "achievements": {"unlocked": []},
        "endings": {"unlocked": []},
        "mystery_stats": {"total_engaged": 0, "total_good": 0},
    }


# ── format_progress_bar ──────────────────────────────────────────────────

class TestFormatProgressBar:
    def test_zero_progress(self) -> None:
        assert format_progress_bar(0, 10, width=10) == "[" + "░" * 10 + "]"

    def test_full_progress(self) -> None:
        assert format_progress_bar(10, 10, width=10) == "[" + "▓" * 10 + "]"

    def test_half_progress(self) -> None:
        bar = format_progress_bar(5, 10, width=10)
        assert bar.count("▓") == 5
        assert bar.count("░") == 5

    def test_over_target_capped(self) -> None:
        # 실제 current > target은 caller에서 capping, 하지만 bar 자체도 clamp해야 함
        bar = format_progress_bar(100, 10, width=10)
        assert "▓" * 10 in bar

    def test_zero_target(self) -> None:
        bar = format_progress_bar(5, 0, width=10)
        # target 0 → 빈 바
        assert bar.count("▓") == 0

    def test_zero_width(self) -> None:
        assert format_progress_bar(5, 10, width=0) == ""


# ── compute_achievement_progress ─────────────────────────────────────────

class TestComputeProgress:
    def test_unknown_id_returns_none(self) -> None:
        save = _empty_save()
        assert compute_achievement_progress("does_not_exist", save) is None

    def test_first_shutdown_has_no_progress(self) -> None:
        # first_shutdown은 이벤트 트리거 업적 — 진행률 추적 대상 아님
        save = _empty_save()
        assert compute_achievement_progress("first_shutdown", save) is None

    def test_runs_10_zero(self) -> None:
        save = _empty_save()
        assert compute_achievement_progress("runs_10", save) == (0, 10)

    def test_runs_10_partial(self) -> None:
        save = _empty_save()
        save["campaign"]["runs"] = 7
        assert compute_achievement_progress("runs_10", save) == (7, 10)

    def test_runs_10_over_caps_to_target(self) -> None:
        save = _empty_save()
        save["campaign"]["runs"] = 25
        assert compute_achievement_progress("runs_10", save) == (10, 10)

    def test_victories_25(self) -> None:
        save = _empty_save()
        save["campaign"]["victories"] = 13
        assert compute_achievement_progress("victories_25", save) == (13, 25)

    def test_campaign_points_10000(self) -> None:
        save = _empty_save()
        save["campaign"]["points"] = 4321
        assert compute_achievement_progress("campaign_points_10000", save) == (4321, 10000)

    def test_class_master(self) -> None:
        save = _empty_save()
        save["campaign"]["class_victories"]["ANALYST"] = 3
        assert compute_achievement_progress("analyst_master", save) == (3, 5)

    def test_class_trinity_min(self) -> None:
        # 세 클래스 승수 중 최솟값이 기준
        save = _empty_save()
        save["campaign"]["class_victories"] = {"ANALYST": 5, "GHOST": 2, "CRACKER": 7}
        assert compute_achievement_progress("triple_master", save) == (2, 5)

    def test_data_fragments(self) -> None:
        save = _empty_save()
        save["data_fragments"] = 777
        assert compute_achievement_progress("data_fragments_500", save) == (500, 500)
        assert compute_achievement_progress("data_fragments_2000", save) == (777, 2000)

    def test_endings_3(self) -> None:
        save = _empty_save()
        save["endings"]["unlocked"] = ["ending_a", "ending_b"]
        assert compute_achievement_progress("endings_3", save) == (2, 3)

    def test_perk_hoarder_counts_truthy(self) -> None:
        save = _empty_save()
        save["perks"] = {"a": True, "b": True, "c": False, "d": True}
        assert compute_achievement_progress("perk_hoarder_5", save) == (3, 5)

    def test_mystery_good_5(self) -> None:
        save = _empty_save()
        save["mystery_stats"]["total_good"] = 4
        assert compute_achievement_progress("mystery_good_5", save) == (4, 5)

    def test_ascension_unlocked(self) -> None:
        save = _empty_save()
        save["campaign"]["ascension_unlocked"] = 12
        assert compute_achievement_progress("ascension_unlocked_10", save) == (10, 10)
        assert compute_achievement_progress("ascension_unlocked_15", save) == (12, 15)


# ── 손상된 save_data 방어 ─────────────────────────────────────────────────

class TestRobustness:
    def test_missing_fields_default_to_zero(self) -> None:
        assert compute_achievement_progress("runs_10", {}) == (0, 10)
        assert compute_achievement_progress("endings_1", {}) == (0, 1)

    def test_non_dict_campaign(self) -> None:
        save = {"campaign": "invalid"}
        assert compute_achievement_progress("runs_10", save) == (0, 10)

    def test_non_int_field(self) -> None:
        save = _empty_save()
        save["campaign"]["runs"] = "not_a_number"
        assert compute_achievement_progress("runs_10", save) == (0, 10)


# ── get_locked_progress_entries ──────────────────────────────────────────

class TestLockedProgressEntries:
    def test_empty_save_returns_all_locked(self) -> None:
        save = _empty_save()
        entries = get_locked_progress_entries(save, top_n=100)
        # 모든 PROGRESS_SPECS 엔트리가 후보
        assert len(entries) == len(PROGRESS_SPECS)
        for entry in entries:
            assert "id" in entry
            assert "title" in entry
            assert "current" in entry
            assert "target" in entry
            assert "ratio" in entry
            assert 0.0 <= entry["ratio"] <= 1.0

    def test_excludes_already_unlocked(self) -> None:
        save = _empty_save()
        save["achievements"]["unlocked"] = ["runs_10", "victories_5"]
        entries = get_locked_progress_entries(save, top_n=100)
        ids = {e["id"] for e in entries}
        assert "runs_10" not in ids
        assert "victories_5" not in ids
        assert "runs_25" in ids  # 여전히 locked

    def test_top_n_limit(self) -> None:
        save = _empty_save()
        entries = get_locked_progress_entries(save, top_n=3)
        assert len(entries) == 3

    def test_sorted_by_ratio_desc(self) -> None:
        save = _empty_save()
        save["campaign"]["runs"] = 9  # runs_10: 9/10 = 0.9
        save["campaign"]["victories"] = 1  # victories_5: 1/5 = 0.2
        entries = get_locked_progress_entries(save, top_n=5)
        # 첫 항목이 가장 높은 ratio
        assert entries[0]["id"] == "runs_10"
        # 연속 비내림차순
        ratios = [e["ratio"] for e in entries]
        assert ratios == sorted(ratios, reverse=True)

    def test_all_unlocked_returns_empty(self) -> None:
        save = _empty_save()
        save["achievements"]["unlocked"] = list(PROGRESS_SPECS.keys())
        entries = get_locked_progress_entries(save, top_n=10)
        assert entries == []


# ── UI 통합 — render_records_screen achievement_progress ──────────────────

class TestRecordsScreenProgressRender:
    def _capture(self, **kwargs: Any) -> str:
        from ui_renderer import render_records_screen
        import ui_renderer

        buf = StringIO()
        new_console = Console(file=buf, width=200, legacy_windows=False)
        original = ui_renderer.console
        ui_renderer.console = new_console
        try:
            render_records_screen(
                achievement_snapshot={"unlocked_count": 0, "total_count": 115, "unlocked_entries": []},
                endings_snapshot={"unlocked_ids": [], "unlocked_entries": [], "total": 13},
                campaign_snapshot={
                    "points": 0, "points_target": 60000,
                    "victories": 0, "victories_target": 450,
                    "ascension_unlocked": 0,
                    "class_victories": {"ANALYST": 0, "GHOST": 0, "CRACKER": 0},
                    "class_target": 120,
                },
                daily_state={"streak": 0, "best_score": 0, "total_plays": 0, "last_played_date": "—"},
                **kwargs,
            )
        finally:
            ui_renderer.console = original
        return buf.getvalue()

    def test_render_with_progress_entries(self) -> None:
        progress = [
            {"id": "runs_10", "title": "단골 해커", "desc": "", "current": 7, "target": 10, "ratio": 0.7},
            {"id": "victories_5", "title": "연속 타격", "desc": "", "current": 2, "target": 5, "ratio": 0.4},
        ]
        output = self._capture(achievement_progress=progress)
        assert "진행 중" in output
        assert "단골 해커" in output
        assert "연속 타격" in output
        assert "7/10" in output
        assert "2/5" in output
        assert "▓" in output
        assert "░" in output

    def test_render_without_progress_shows_no_section(self) -> None:
        output = self._capture(achievement_progress=None)
        assert "진행 중" not in output

    def test_render_empty_progress_list(self) -> None:
        output = self._capture(achievement_progress=[])
        # 빈 리스트는 섹션 자체가 표시되지 않아야 함
        assert "진행 중" not in output
