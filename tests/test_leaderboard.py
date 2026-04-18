"""로컬 리더보드 기능 유닛 테스트.

calculate_run_score / update_leaderboard / get_leaderboard API,
점수 계산 공식, Top-10 제한, 순위 재계산, 세이브 정규화, UI render_leaderboard 연동 검증.
"""

from __future__ import annotations

import copy

import pytest

from progression_system import (
    DEFAULT_SAVE_DATA,
    LEADERBOARD_MAX,
    calculate_run_score,
    get_leaderboard,
    load_save,
    update_leaderboard,
)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _empty_save() -> dict:
    return copy.deepcopy(DEFAULT_SAVE_DATA)


def _insert(save: dict, **kwargs) -> int | None:
    """기본값으로 채운 런 기록을 리더보드에 삽입하는 헬퍼."""
    defaults = dict(
        date="2026-01-01",
        class_key="ANALYST",
        ascension=0,
        result="victory",
        trace_final=30,
        reward=100,
        correct_answers=5,
    )
    defaults.update(kwargs)
    return update_leaderboard(save, **defaults)


# ── calculate_run_score ───────────────────────────────────────────────────────

class TestCalculateRunScore:
    def test_victory_adds_bonus(self) -> None:
        score_win = calculate_run_score("victory", 30, 100, 5, 0)
        score_shutdown = calculate_run_score("shutdown", 30, 100, 5, 0)
        assert score_win > score_shutdown

    def test_lower_trace_gives_higher_score(self) -> None:
        low = calculate_run_score("victory", 10, 100, 5, 0)
        high = calculate_run_score("victory", 80, 100, 5, 0)
        assert low > high

    def test_higher_ascension_gives_higher_score(self) -> None:
        asc5 = calculate_run_score("victory", 30, 100, 5, 5)
        asc0 = calculate_run_score("victory", 30, 100, 5, 0)
        assert asc5 > asc0

    def test_more_correct_answers_gives_higher_score(self) -> None:
        s7 = calculate_run_score("victory", 30, 100, 7, 0)
        s3 = calculate_run_score("victory", 30, 100, 3, 0)
        assert s7 > s3

    def test_score_always_non_negative(self) -> None:
        assert calculate_run_score("shutdown", 100, 0, 0, 0) >= 0

    def test_trace_clamped(self) -> None:
        s = calculate_run_score("victory", 150, 0, 0, 0)
        # trace 150은 100으로 클램핑 → (100-100)*2 = 0
        assert s >= 0

    def test_formula_components(self) -> None:
        # score = reward + (100-trace)*2 + correct*10 + asc*30 + 200(victory)
        expected = 100 + (100 - 30) * 2 + 5 * 10 + 0 * 30 + 200
        assert calculate_run_score("victory", 30, 100, 5, 0) == expected


# ── update_leaderboard ────────────────────────────────────────────────────────

class TestUpdateLeaderboard:
    def test_first_entry_returns_rank_1(self) -> None:
        save = _empty_save()
        rank = _insert(save)
        assert rank == 1

    def test_entry_added_to_leaderboard(self) -> None:
        save = _empty_save()
        _insert(save)
        assert len(save["leaderboard"]) == 1

    def test_higher_score_gets_higher_rank(self) -> None:
        save = _empty_save()
        _insert(save, reward=10, trace_final=90, correct_answers=1, ascension=0, result="shutdown")
        rank = _insert(save, reward=300, trace_final=5, correct_answers=7, ascension=5)
        assert rank == 1

    def test_max_limit_enforced(self) -> None:
        save = _empty_save()
        for i in range(LEADERBOARD_MAX + 3):
            _insert(save, reward=i * 10)
        assert len(save["leaderboard"]) == LEADERBOARD_MAX

    def test_low_score_not_inserted_when_board_full(self) -> None:
        save = _empty_save()
        for _ in range(LEADERBOARD_MAX):
            _insert(save, reward=500, trace_final=0, correct_answers=7, ascension=10)
        rank = _insert(save, reward=0, trace_final=100, correct_answers=0, ascension=0, result="shutdown")
        assert rank is None
        assert len(save["leaderboard"]) == LEADERBOARD_MAX

    def test_ranks_are_consecutive_1_based(self) -> None:
        save = _empty_save()
        for i in range(5):
            _insert(save, reward=i * 20)
        ranks = [e["rank"] for e in save["leaderboard"]]
        assert ranks == list(range(1, 6))

    def test_entries_sorted_by_score_desc(self) -> None:
        save = _empty_save()
        _insert(save, reward=50)
        _insert(save, reward=200)
        _insert(save, reward=10)
        scores = [e["score"] for e in save["leaderboard"]]
        assert scores == sorted(scores, reverse=True)

    def test_corrupted_leaderboard_reset(self) -> None:
        save = _empty_save()
        save["leaderboard"] = "corrupted"  # type: ignore[assignment]
        _insert(save)
        assert isinstance(save["leaderboard"], list)
        assert len(save["leaderboard"]) == 1

    def test_entry_contains_expected_fields(self) -> None:
        save = _empty_save()
        _insert(save, date="2026-04-18", class_key="GHOST", ascension=3,
                result="victory", trace_final=25, reward=150, correct_answers=6)
        entry = save["leaderboard"][0]
        assert entry["date"] == "2026-04-18"
        assert entry["class_key"] == "GHOST"
        assert entry["ascension"] == 3
        assert entry["result"] == "victory"
        assert entry["trace_final"] == 25
        assert entry["reward"] == 150
        assert entry["correct_answers"] == 6
        assert "score" in entry and entry["score"] > 0


# ── get_leaderboard ───────────────────────────────────────────────────────────

class TestGetLeaderboard:
    def test_empty_returns_empty_list(self) -> None:
        save = _empty_save()
        assert get_leaderboard(save) == []

    def test_returns_copy_not_reference(self) -> None:
        save = _empty_save()
        _insert(save)
        board = get_leaderboard(save)
        board.clear()
        assert len(save["leaderboard"]) == 1

    def test_corrupted_returns_empty(self) -> None:
        save = _empty_save()
        save["leaderboard"] = None  # type: ignore[assignment]
        assert get_leaderboard(save) == []


# ── 세이브 정규화 ─────────────────────────────────────────────────────────────

class TestSaveNormalization:
    def test_missing_leaderboard_defaults_to_empty_list(self, tmp_path) -> None:
        import json
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data.pop("leaderboard", None)
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert result["leaderboard"] == []

    def test_corrupted_leaderboard_normalized(self, tmp_path) -> None:
        import json
        save_path = tmp_path / "save.json"
        data = copy.deepcopy(DEFAULT_SAVE_DATA)
        data["leaderboard"] = 42  # 잘못된 타입
        save_path.write_text(json.dumps(data), encoding="utf-8")
        result = load_save(file_path=str(save_path))
        assert result["leaderboard"] == []


# ── render_leaderboard UI 연동 ────────────────────────────────────────────────

class TestRenderLeaderboard:
    def test_renders_without_error_empty(self, monkeypatch) -> None:
        from ui_renderer import render_leaderboard
        printed: list = []
        monkeypatch.setattr("ui_renderer.console.print", lambda *a, **kw: printed.append(a))
        render_leaderboard([])
        assert printed

    def test_renders_entries_and_highlights_new_rank(self, monkeypatch) -> None:
        from io import StringIO
        from rich.console import Console
        import ui_renderer

        buf = StringIO()
        test_console = Console(file=buf, highlight=False, markup=True, width=200)
        monkeypatch.setattr(ui_renderer, "console", test_console)

        entries = [
            {"rank": 1, "score": 500, "date": "2026-04-18", "class_key": "ANALYST",
             "ascension": 5, "result": "victory", "trace_final": 10, "reward": 150,
             "correct_answers": 7},
            {"rank": 2, "score": 300, "date": "2026-04-17", "class_key": "GHOST",
             "ascension": 0, "result": "shutdown", "trace_final": 100, "reward": 30,
             "correct_answers": 2},
        ]
        from ui_renderer import render_leaderboard
        render_leaderboard(entries, new_rank=1)
        output = buf.getvalue()
        assert "LEADERBOARD" in output
        assert "ANALYST" in output
        assert "GHOST" in output
        # 새 순위 항목에 ★ 표시
        assert "★" in output
