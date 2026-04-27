"""v1.14.0 — 리더보드 임포트/익스포트 테스트.

검증 범위:
1. export_leaderboard: 파일 생성, 포맷, 서명
2. import_leaderboard: 정상 경로, 서명 불일치 거부, 포맷 오류, 중복 병합, LEADERBOARD_MAX 상한
3. _compute_lb_signature: 결정성 및 변조 탐지
4. 왕복(export → import) 통합 테스트
"""

from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from progression_system import (
    LEADERBOARD_MAX,
    LeaderboardImportError,
    _compute_lb_signature,
    export_leaderboard,
    get_leaderboard,
    import_leaderboard,
    update_leaderboard,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_save_data(board: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "data_fragments": 0,
        "perks": {},
        "campaign": {},
        "achievements": {"unlocked": []},
        "leaderboard": board or [],
    }


def _make_entry(
    score: int = 500,
    date: str = "2026-04-20",
    class_key: str = "ANALYST",
    ascension: int = 0,
    result: str = "victory",
    trace_final: int = 30,
    reward: int = 100,
    correct_answers: int = 7,
    rank: int = 1,
) -> dict[str, Any]:
    return {
        "rank": rank,
        "score": score,
        "date": date,
        "class_key": class_key,
        "ascension": ascension,
        "result": result,
        "trace_final": trace_final,
        "reward": reward,
        "correct_answers": correct_answers,
    }


# ── TestComputeSignature ───────────────────────────────────────────────────

class TestComputeSignature:
    def test_same_input_same_signature(self) -> None:
        board = [_make_entry(score=1000), _make_entry(score=500, date="2026-04-19")]
        sig1 = _compute_lb_signature(board)
        sig2 = _compute_lb_signature(board)
        assert sig1 == sig2

    def test_different_score_different_signature(self) -> None:
        sig1 = _compute_lb_signature([_make_entry(score=1000)])
        sig2 = _compute_lb_signature([_make_entry(score=999)])
        assert sig1 != sig2

    def test_empty_board_produces_signature(self) -> None:
        sig = _compute_lb_signature([])
        assert isinstance(sig, str) and len(sig) == 64  # sha256 hex

    def test_order_matters(self) -> None:
        e1 = _make_entry(score=1000)
        e2 = _make_entry(score=500, date="2026-04-19")
        sig_ab = _compute_lb_signature([e1, e2])
        sig_ba = _compute_lb_signature([e2, e1])
        assert sig_ab != sig_ba

    def test_returns_hex_string(self) -> None:
        sig = _compute_lb_signature([_make_entry()])
        assert all(c in "0123456789abcdef" for c in sig)


# ── TestExportLeaderboard ──────────────────────────────────────────────────

class TestExportLeaderboard:
    def test_file_created(self, tmp_path) -> None:
        save = _make_save_data([_make_entry()])
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        assert Path(out).exists()

    def test_export_format_field(self, tmp_path) -> None:
        save = _make_save_data([_make_entry()])
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert data["format"] == "echoes_leaderboard_v1"

    def test_export_contains_leaderboard(self, tmp_path) -> None:
        save = _make_save_data([_make_entry(score=999)])
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert len(data["leaderboard"]) == 1
        assert data["leaderboard"][0]["score"] == 999

    def test_export_signature_present(self, tmp_path) -> None:
        save = _make_save_data([_make_entry()])
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert "signature" in data
        assert len(data["signature"]) == 64

    def test_signature_is_valid(self, tmp_path) -> None:
        board = [_make_entry(score=1200)]
        save = _make_save_data(board)
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        expected_sig = _compute_lb_signature(data["leaderboard"])
        assert data["signature"] == expected_sig

    def test_export_empty_board(self, tmp_path) -> None:
        save = _make_save_data([])
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        assert data["leaderboard"] == []

    def test_creates_parent_directory(self, tmp_path) -> None:
        save = _make_save_data([_make_entry()])
        out = str(tmp_path / "sub" / "dir" / "lb.json")
        export_leaderboard(save, out)
        assert Path(out).exists()

    def test_export_raises_oserror_on_invalid_path(self, tmp_path: Path) -> None:
        # 부모 경로에 파일이 존재하면 mkdir 가 NotADirectoryError(OSError) 를 발생시킨다.
        # Unix/Windows 공통 동작.
        blocker = tmp_path / "not_a_dir"
        blocker.write_text("I am a file, not a dir")
        invalid = str(blocker / "leaderboard.json")
        save = _make_save_data([_make_entry()])
        with pytest.raises(OSError):
            export_leaderboard(save, invalid)


# ── TestImportLeaderboard ──────────────────────────────────────────────────

class TestImportLeaderboard:
    def _write_export_file(
        self,
        path: str,
        board: list[dict[str, Any]],
        format_val: str = "echoes_leaderboard_v1",
        tamper: bool = False,
    ) -> None:
        sig = _compute_lb_signature(board)
        if tamper:
            sig = "0" * 64  # 의도적으로 잘못된 서명
        data = {"format": format_val, "leaderboard": board, "signature": sig}
        Path(path).write_text(json.dumps(data), encoding="utf-8")

    def test_normal_import(self, tmp_path) -> None:
        board = [_make_entry(score=800)]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, board)
        save = _make_save_data([])
        stats = import_leaderboard(f, save)
        assert stats["total"] >= 1

    def test_imported_entries_in_save(self, tmp_path) -> None:
        board = [_make_entry(score=800)]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, board)
        save = _make_save_data([])
        import_leaderboard(f, save)
        assert len(save["leaderboard"]) >= 1

    def test_signature_mismatch_raises(self, tmp_path) -> None:
        board = [_make_entry(score=800)]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, board, tamper=True)
        save = _make_save_data([])
        with pytest.raises(LeaderboardImportError, match="서명 불일치"):
            import_leaderboard(f, save)

    def test_wrong_format_raises(self, tmp_path) -> None:
        board = [_make_entry(score=800)]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, board, format_val="unknown_format")
        save = _make_save_data([])
        with pytest.raises(LeaderboardImportError, match="포맷"):
            import_leaderboard(f, save)

    def test_missing_file_raises(self, tmp_path) -> None:
        save = _make_save_data([])
        with pytest.raises(LeaderboardImportError, match="파일 읽기 실패"):
            import_leaderboard(str(tmp_path / "nonexistent.json"), save)

    def test_invalid_json_raises(self, tmp_path) -> None:
        f = str(tmp_path / "lb.json")
        Path(f).write_text("NOT_JSON", encoding="utf-8")
        save = _make_save_data([])
        with pytest.raises(LeaderboardImportError, match="파일 읽기 실패"):
            import_leaderboard(f, save)

    def test_leaderboard_not_list_raises(self, tmp_path) -> None:
        f = str(tmp_path / "lb.json")
        bad_board: dict = {}
        sig = _compute_lb_signature([])  # type: ignore[arg-type]
        # 서명은 빈 리스트 기준으로 맞추되 leaderboard 필드는 dict로 설정
        Path(f).write_text(
            json.dumps({"format": "echoes_leaderboard_v1", "leaderboard": {}, "signature": sig}),
            encoding="utf-8",
        )
        save = _make_save_data([])
        with pytest.raises(LeaderboardImportError):
            import_leaderboard(f, save)

    def test_merge_with_existing(self, tmp_path) -> None:
        existing = [_make_entry(score=1000, date="2026-04-20")]
        imported = [_make_entry(score=800, date="2026-04-19")]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, imported)
        save = _make_save_data(existing)
        import_leaderboard(f, save)
        scores = [e["score"] for e in save["leaderboard"]]
        assert 1000 in scores
        assert 800 in scores

    def test_merged_sorted_by_score_desc(self, tmp_path) -> None:
        existing = [_make_entry(score=500, date="2026-04-20")]
        imported = [_make_entry(score=900, date="2026-04-19")]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, imported)
        save = _make_save_data(existing)
        import_leaderboard(f, save)
        scores = [e["score"] for e in save["leaderboard"]]
        assert scores == sorted(scores, reverse=True)

    def test_duplicate_entries_deduplicated(self, tmp_path) -> None:
        entry = _make_entry(score=800, date="2026-04-20", class_key="ANALYST")
        existing = [entry]
        imported = [entry]  # 동일 항목
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, imported)
        save = _make_save_data(existing)
        import_leaderboard(f, save)
        assert len(save["leaderboard"]) == 1  # 중복 제거

    def test_cap_at_leaderboard_max(self, tmp_path) -> None:
        existing = [_make_entry(score=1000 - i, date=f"2026-01-{i+1:02d}") for i in range(LEADERBOARD_MAX)]
        imported = [_make_entry(score=500, date="2026-04-20", class_key="GHOST")]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, imported)
        save = _make_save_data(existing)
        import_leaderboard(f, save)
        assert len(save["leaderboard"]) <= LEADERBOARD_MAX

    def test_ranks_reassigned_after_import(self, tmp_path) -> None:
        imported = [_make_entry(score=800, date="2026-04-19")]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, imported)
        save = _make_save_data([_make_entry(score=1200, date="2026-04-20")])
        import_leaderboard(f, save)
        ranks = [e["rank"] for e in save["leaderboard"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_stats_added_count(self, tmp_path) -> None:
        imported = [
            _make_entry(score=700, date="2026-04-15"),
            _make_entry(score=600, date="2026-04-16"),
        ]
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, imported)
        save = _make_save_data([])
        stats = import_leaderboard(f, save)
        assert stats["added"] == 2
        assert stats["total"] == 2

    def test_returns_dict_with_required_keys(self, tmp_path) -> None:
        f = str(tmp_path / "lb.json")
        self._write_export_file(f, [_make_entry()])
        save = _make_save_data([])
        stats = import_leaderboard(f, save)
        assert "added" in stats
        assert "skipped" in stats
        assert "total" in stats


# ── TestRoundTrip ───────────────────────────────────────────────────────────

class TestRoundTrip:
    """export → import 왕복 통합 테스트."""

    def test_round_trip_preserves_entries(self, tmp_path) -> None:
        """내보낸 뒤 다른 세이브에 가져오면 항목이 보존된다."""
        board = [
            _make_entry(score=1200, date="2026-04-20", class_key="ANALYST"),
            _make_entry(score=900,  date="2026-04-19", class_key="GHOST"),
            _make_entry(score=600,  date="2026-04-18", class_key="CRACKER"),
        ]
        source_save = _make_save_data(board)
        out = str(tmp_path / "lb.json")
        export_leaderboard(source_save, out)

        target_save = _make_save_data([])
        import_leaderboard(out, target_save)

        imported_scores = {e["score"] for e in target_save["leaderboard"]}
        assert {1200, 900, 600} == imported_scores

    def test_round_trip_signature_verified(self, tmp_path) -> None:
        """내보낸 파일을 조작하면 가져오기가 실패한다."""
        save = _make_save_data([_make_entry(score=1000)])
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)

        # 파일 내 점수를 임의로 변조
        data = json.loads(Path(out).read_text(encoding="utf-8"))
        data["leaderboard"][0]["score"] = 9999
        Path(out).write_text(json.dumps(data), encoding="utf-8")

        target_save = _make_save_data([])
        with pytest.raises(LeaderboardImportError, match="서명 불일치"):
            import_leaderboard(out, target_save)

    def test_round_trip_merge_with_higher_score_wins(self, tmp_path) -> None:
        """임포트 후 점수 내림차순이 유지된다."""
        source_save = _make_save_data([_make_entry(score=800, date="2026-04-19")])
        out = str(tmp_path / "lb.json")
        export_leaderboard(source_save, out)

        target_save = _make_save_data([_make_entry(score=1500, date="2026-04-20")])
        import_leaderboard(out, target_save)

        scores = [e["score"] for e in target_save["leaderboard"]]
        assert scores[0] == 1500  # 최고점이 1위

    def test_round_trip_self_import_no_duplicates(self, tmp_path) -> None:
        """같은 세이브에서 익스포트 후 다시 임포트해도 중복이 없다."""
        board = [_make_entry(score=700, date="2026-04-20")]
        save = _make_save_data(board)
        out = str(tmp_path / "lb.json")
        export_leaderboard(save, out)
        import_leaderboard(out, save)
        assert len(save["leaderboard"]) == 1  # 중복 제거로 1개만 남음
