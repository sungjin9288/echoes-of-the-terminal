"""Pack 24 (DYSTOPIAN_COURT) & Pack 25 (NEON_UNDERGROUND) 스모크 + 검증 테스트.

pack_loader 인프라를 통해 두 신규 팩이 올바르게 로드되고
시나리오 구조 / node_id 범위 / 난이도 분포를 충족하는지 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pack_loader import LoadedPack, PackMetadata, load_scenario_pack


# ── 경로 헬퍼 ────────────────────────────────────────────────────────────────

def _pack_path(filename: str) -> Path:
    return Path(__file__).parent.parent / "packs" / filename


PACK24_PATH = _pack_path("pack_24_dystopian_court.json")
PACK25_PATH = _pack_path("pack_25_neon_underground.json")

REQUIRED_FIELDS = {"node_id", "theme", "difficulty", "text_log", "target_keyword", "penalty_rate"}
VALID_DIFFICULTIES = {"Easy", "Hard", "NIGHTMARE"}


# ── 공통 검증 헬퍼 ────────────────────────────────────────────────────────────

def _assert_pack_valid(pack: LoadedPack, expected_pack_id: str, expected_count: int) -> None:
    assert isinstance(pack.metadata, PackMetadata)
    assert pack.metadata.pack_id == expected_pack_id
    assert len(pack.scenarios) == expected_count
    # 모든 시나리오가 필수 필드를 보유해야 한다
    for scenario in pack.scenarios:
        missing = REQUIRED_FIELDS - scenario.keys()
        assert not missing, f"시나리오 {scenario.get('node_id')} 누락 필드: {missing}"
    # 난이도 값 유효성
    for scenario in pack.scenarios:
        assert scenario["difficulty"] in VALID_DIFFICULTIES, (
            f"node_id {scenario['node_id']} 잘못된 난이도: {scenario['difficulty']}"
        )
    # penalty_rate 범위
    for scenario in pack.scenarios:
        assert 10 <= scenario["penalty_rate"] <= 80, (
            f"node_id {scenario['node_id']} penalty_rate 범위 초과: {scenario['penalty_rate']}"
        )
    # target_keyword 공백 없는 단일 단어
    for scenario in pack.scenarios:
        kw = scenario["target_keyword"]
        assert kw and " " not in kw, (
            f"node_id {scenario['node_id']} target_keyword에 공백 포함: '{kw}'"
        )
    # node_id 유일성 (팩 내부)
    ids = [s["node_id"] for s in pack.scenarios]
    assert len(ids) == len(set(ids)), "팩 내 node_id 중복 존재"


# ── Pack 24 — DYSTOPIAN COURT ─────────────────────────────────────────────────

class TestPack24DystopianCourt:
    def test_file_exists(self) -> None:
        assert PACK24_PATH.exists(), f"팩 파일 없음: {PACK24_PATH}"

    def test_loads_without_error(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        assert pack is not None

    def test_metadata(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        assert pack.metadata.pack_id == "pack_24"
        assert "DYSTOPIAN" in pack.metadata.name.upper()

    def test_scenario_count(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        assert len(pack.scenarios) == 5

    def test_node_id_range(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        ids = [s["node_id"] for s in pack.scenarios]
        assert min(ids) == 1004
        assert max(ids) == 1008

    def test_all_required_fields_present(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        _assert_pack_valid(pack, "pack_24", 5)

    def test_difficulty_distribution(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        diffs = [s["difficulty"] for s in pack.scenarios]
        assert diffs.count("Easy") == 2
        assert diffs.count("Hard") == 2
        assert diffs.count("NIGHTMARE") == 1

    def test_themes_are_dystopian_court_prefixed(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        for s in pack.scenarios:
            assert s["theme"].startswith("DYSTOPIAN_COURT_"), (
                f"node_id {s['node_id']} 테마 오류: {s['theme']}"
            )

    def test_no_is_boss_true(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        for s in pack.scenarios:
            assert not s.get("is_boss", False)

    def test_text_log_non_empty(self) -> None:
        pack = load_scenario_pack(PACK24_PATH)
        for s in pack.scenarios:
            assert len(s["text_log"]) > 50, f"node_id {s['node_id']} text_log가 너무 짧음"


# ── Pack 25 — NEON UNDERGROUND ────────────────────────────────────────────────

class TestPack25NeonUnderground:
    def test_file_exists(self) -> None:
        assert PACK25_PATH.exists(), f"팩 파일 없음: {PACK25_PATH}"

    def test_loads_without_error(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        assert pack is not None

    def test_metadata(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        assert pack.metadata.pack_id == "pack_25"
        assert "NEON" in pack.metadata.name.upper()

    def test_scenario_count(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        assert len(pack.scenarios) == 5

    def test_node_id_range(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        ids = [s["node_id"] for s in pack.scenarios]
        assert min(ids) == 1009
        assert max(ids) == 1013

    def test_all_required_fields_present(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        _assert_pack_valid(pack, "pack_25", 5)

    def test_difficulty_distribution(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        diffs = [s["difficulty"] for s in pack.scenarios]
        assert diffs.count("Easy") == 2
        assert diffs.count("Hard") == 2
        assert diffs.count("NIGHTMARE") == 1

    def test_themes_are_neon_underground_prefixed(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        for s in pack.scenarios:
            assert s["theme"].startswith("NEON_UNDERGROUND_"), (
                f"node_id {s['node_id']} 테마 오류: {s['theme']}"
            )

    def test_no_is_boss_true(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        for s in pack.scenarios:
            assert not s.get("is_boss", False)

    def test_text_log_non_empty(self) -> None:
        pack = load_scenario_pack(PACK25_PATH)
        for s in pack.scenarios:
            assert len(s["text_log"]) > 50, f"node_id {s['node_id']} text_log가 너무 짧음"


# ── 팩 간 node_id 충돌 검사 ───────────────────────────────────────────────────

class TestCrossPackConflicts:
    def test_no_node_id_overlap_between_pack24_and_pack25(self) -> None:
        pack24 = load_scenario_pack(PACK24_PATH)
        pack25 = load_scenario_pack(PACK25_PATH)
        ids24 = {s["node_id"] for s in pack24.scenarios}
        ids25 = {s["node_id"] for s in pack25.scenarios}
        overlap = ids24 & ids25
        assert not overlap, f"팩 24/25 node_id 충돌: {overlap}"

    def test_no_node_id_overlap_with_pack23(self) -> None:
        """기존 Pack 23과 신규 팩 간 node_id 충돌이 없어야 한다."""
        pack23_path = _pack_path("pack_23_cyber_noir.json")
        if not pack23_path.exists():
            pytest.skip("pack_23 파일 없음")
        pack23 = load_scenario_pack(pack23_path)
        pack24 = load_scenario_pack(PACK24_PATH)
        pack25 = load_scenario_pack(PACK25_PATH)
        all_ids = (
            {s["node_id"] for s in pack23.scenarios}
            | {s["node_id"] for s in pack24.scenarios}
            | {s["node_id"] for s in pack25.scenarios}
        )
        total = (
            len(pack23.scenarios) + len(pack24.scenarios) + len(pack25.scenarios)
        )
        assert len(all_ids) == total, "팩 23/24/25 사이 node_id 중복 존재"

    def test_load_all_packs_includes_new_packs(self) -> None:
        from pack_loader import load_all_packs
        from pathlib import Path
        packs_dir = Path(__file__).parent.parent / "packs"
        scenarios, warnings = load_all_packs(packs_dir=packs_dir)
        ids = {s["node_id"] for s in scenarios}
        # Pack 24 & 25의 node_id가 전부 포함되어야 한다
        for nid in range(1004, 1014):
            assert nid in ids, f"node_id {nid}가 load_all_packs 결과에 없음"
