"""다이버 프로필 카드 기능 유닛 테스트.

get_diver_profile API, 칭호 계산 로직, 주력 클래스 도출, 엣지 케이스,
UI render_diver_profile 연동 검증.
"""

from __future__ import annotations

import copy

import pytest

from progression_system import (
    DEFAULT_SAVE_DATA,
    _compute_diver_title,
    _compute_signature_class,
    get_diver_profile,
)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _empty_save() -> dict:
    return copy.deepcopy(DEFAULT_SAVE_DATA)


def _save_with_stats(
    total_runs: int = 0,
    total_victories: int = 0,
    best_ascension: int = 0,
    most_seen_ending: str = "",
) -> dict:
    save = _empty_save()
    save["stats"]["total_runs"] = total_runs
    save["stats"]["total_victories"] = total_victories
    save["stats"]["total_trace_sum"] = total_runs * 50  # avg 50%
    save["stats"]["total_trace_counted"] = total_runs
    save["stats"]["best_ascension_cleared"] = best_ascension
    save["stats"]["most_seen_ending"] = most_seen_ending
    return save


# ── _compute_diver_title ──────────────────────────────────────────────────────

class TestComputeDiverTitle:
    def test_high_win_rate_gives_legendary(self) -> None:
        assert _compute_diver_title(80.0, 0) == "전설적 다이버"

    def test_win_rate_exactly_80_gives_legendary(self) -> None:
        assert _compute_diver_title(80.0, 0) == "전설적 다이버"

    def test_win_rate_60_to_79_gives_skilled(self) -> None:
        assert _compute_diver_title(65.0, 0) == "숙련된 다이버"

    def test_win_rate_40_to_59_gives_growing(self) -> None:
        assert _compute_diver_title(50.0, 0) == "성장하는 다이버"

    def test_low_win_rate_gives_default(self) -> None:
        assert _compute_diver_title(10.0, 0) == "데이터 다이버"

    def test_zero_runs_default_title(self) -> None:
        assert _compute_diver_title(0.0, 0) == "데이터 다이버"

    def test_ascension_18_plus_gives_master(self) -> None:
        assert _compute_diver_title(10.0, 18) == "어센션 마스터"

    def test_ascension_12_to_17_gives_expert(self) -> None:
        assert _compute_diver_title(10.0, 12) == "어센션 전문가"

    def test_ascension_6_to_11_gives_challenger(self) -> None:
        assert _compute_diver_title(10.0, 6) == "고난이도 도전자"

    def test_ascension_overrides_win_rate(self) -> None:
        # 승률 80%라도 어센션 20이면 어센션 칭호가 우선
        assert _compute_diver_title(90.0, 20) == "어센션 마스터"


# ── _compute_signature_class ──────────────────────────────────────────────────

class TestComputeSignatureClass:
    def test_most_played_class_returned(self) -> None:
        records = {
            "ANALYST_0": {"class_key": "ANALYST", "run_count": 10},
            "GHOST_0": {"class_key": "GHOST", "run_count": 3},
            "CRACKER_0": {"class_key": "CRACKER", "run_count": 5},
        }
        assert _compute_signature_class(records) == "ANALYST"

    def test_empty_records_returns_dash(self) -> None:
        assert _compute_signature_class({}) == "—"

    def test_corrupted_records_returns_dash(self) -> None:
        assert _compute_signature_class(None) == "—"  # type: ignore[arg-type]

    def test_same_count_returns_any(self) -> None:
        records = {
            "ANALYST_0": {"class_key": "ANALYST", "run_count": 5},
            "GHOST_0": {"class_key": "GHOST", "run_count": 5},
        }
        result = _compute_signature_class(records)
        assert result in {"ANALYST", "GHOST"}


# ── get_diver_profile ─────────────────────────────────────────────────────────

class TestGetDiverProfile:
    def test_returns_all_required_keys(self) -> None:
        save = _empty_save()
        profile = get_diver_profile(save)
        required = {
            "title", "signature_class", "total_runs", "win_rate",
            "avg_trace", "best_ascension", "favorite_ending",
            "best_lb_score", "achievements_count", "campaign_cleared",
        }
        assert required.issubset(profile.keys())

    def test_zero_runs_gives_default_title(self) -> None:
        save = _empty_save()
        profile = get_diver_profile(save)
        assert profile["title"] == "데이터 다이버"
        assert profile["total_runs"] == 0
        assert profile["win_rate"] == 0.0

    def test_win_rate_computed_correctly(self) -> None:
        save = _save_with_stats(total_runs=10, total_victories=8)
        profile = get_diver_profile(save)
        assert profile["win_rate"] == 80.0
        assert profile["title"] == "전설적 다이버"

    def test_best_lb_score_from_leaderboard(self) -> None:
        save = _empty_save()
        save["leaderboard"] = [{"rank": 1, "score": 999}]
        profile = get_diver_profile(save)
        assert profile["best_lb_score"] == 999

    def test_best_lb_score_zero_when_empty(self) -> None:
        save = _empty_save()
        profile = get_diver_profile(save)
        assert profile["best_lb_score"] == 0

    def test_achievements_count_from_unlocked(self) -> None:
        save = _empty_save()
        save["achievements"]["unlocked"] = ["ach1", "ach2", "ach3"]
        profile = get_diver_profile(save)
        assert profile["achievements_count"] == 3

    def test_campaign_cleared_flag(self) -> None:
        save = _empty_save()
        save["campaign"]["cleared"] = True
        profile = get_diver_profile(save)
        assert profile["campaign_cleared"] is True

    def test_favorite_ending_dash_when_empty(self) -> None:
        save = _empty_save()
        profile = get_diver_profile(save)
        assert profile["favorite_ending"] == "—"

    def test_avg_trace_computed(self) -> None:
        save = _save_with_stats(total_runs=4)
        # total_trace_sum = 200 (4 * 50), counted = 4
        profile = get_diver_profile(save)
        assert profile["avg_trace"] == 50.0


# ── render_diver_profile UI 연동 ──────────────────────────────────────────────

class TestRenderDiverProfile:
    def test_renders_without_error(self, monkeypatch) -> None:
        from ui_renderer import render_diver_profile
        printed: list = []
        monkeypatch.setattr("ui_renderer.console.print", lambda *a, **kw: printed.append(a))
        render_diver_profile({
            "title": "전설적 다이버", "signature_class": "ANALYST",
            "total_runs": 50, "win_rate": 82.0, "avg_trace": 25.0,
            "best_ascension": 15, "favorite_ending": "silent_trace",
            "best_lb_score": 1200, "achievements_count": 30,
            "campaign_cleared": True,
        })
        assert printed

    def test_renders_title_and_class_in_output(self, monkeypatch) -> None:
        from io import StringIO
        from rich.console import Console
        import ui_renderer
        from ui_renderer import render_diver_profile

        buf = StringIO()
        test_console = Console(file=buf, highlight=False, markup=True, width=200)
        monkeypatch.setattr(ui_renderer, "console", test_console)

        render_diver_profile({
            "title": "어센션 마스터", "signature_class": "GHOST",
            "total_runs": 30, "win_rate": 60.0, "avg_trace": 40.0,
            "best_ascension": 20, "favorite_ending": "ghost_protocol",
            "best_lb_score": 800, "achievements_count": 20,
            "campaign_cleared": False,
        })
        output = buf.getvalue()
        assert "어센션 마스터" in output
        assert "GHOST" in output
        assert "DIVER PROFILE" in output
