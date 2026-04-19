"""Pack 26 (QUANTUM_HEIST) & Pack 27 (BIOMECH_ASYLUM) 스모크 + 검증 테스트.

pack_loader 인프라를 통해 두 신규 팩이 올바르게 로드되고
시나리오 구조 / node_id 범위 / 난이도 분포를 충족하는지 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pack_loader import LoadedPack, PackMetadata, load_scenario_pack, load_all_packs


# ── 경로 헬퍼 ────────────────────────────────────────────────────────────────

def _pack_path(filename: str) -> Path:
    return Path(__file__).parent.parent / "packs" / filename


PACK26_PATH = _pack_path("pack_26_quantum_heist.json")
PACK27_PATH = _pack_path("pack_27_biomech_asylum.json")

REQUIRED_FIELDS = {"node_id", "theme", "difficulty", "text_log", "target_keyword", "penalty_rate"}
VALID_DIFFICULTIES = {"Easy", "Hard", "NIGHTMARE"}


# ── 공통 검증 헬퍼 ────────────────────────────────────────────────────────────

def _assert_pack_valid(pack: LoadedPack, expected_pack_id: str, expected_count: int) -> None:
    assert isinstance(pack.metadata, PackMetadata)
    assert pack.metadata.pack_id == expected_pack_id
    assert len(pack.scenarios) == expected_count
    for scenario in pack.scenarios:
        missing = REQUIRED_FIELDS - scenario.keys()
        assert not missing, f"시나리오 {scenario.get('node_id')} 누락 필드: {missing}"
    for scenario in pack.scenarios:
        assert scenario["difficulty"] in VALID_DIFFICULTIES, (
            f"node_id {scenario['node_id']} 잘못된 난이도: {scenario['difficulty']}"
        )
    for scenario in pack.scenarios:
        assert 10 <= scenario["penalty_rate"] <= 80, (
            f"node_id {scenario['node_id']} penalty_rate 범위 초과: {scenario['penalty_rate']}"
        )
    for scenario in pack.scenarios:
        kw = scenario["target_keyword"]
        assert kw and " " not in kw, (
            f"node_id {scenario['node_id']} target_keyword에 공백 포함: '{kw}'"
        )
    ids = [s["node_id"] for s in pack.scenarios]
    assert len(ids) == len(set(ids)), "팩 내 node_id 중복 존재"


# ── Pack 26 — QUANTUM HEIST ───────────────────────────────────────────────────

class TestPack26QuantumHeist:
    def test_file_exists(self) -> None:
        assert PACK26_PATH.exists(), f"팩 파일 없음: {PACK26_PATH}"

    def test_loads_without_error(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        assert pack is not None

    def test_metadata(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        assert pack.metadata.pack_id == "pack_26"
        assert "QUANTUM" in pack.metadata.name.upper()

    def test_scenario_count(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        assert len(pack.scenarios) == 5

    def test_node_id_range(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        ids = [s["node_id"] for s in pack.scenarios]
        assert min(ids) == 1014
        assert max(ids) == 1018

    def test_all_required_fields_present(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        _assert_pack_valid(pack, "pack_26", 5)

    def test_difficulty_distribution(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        diffs = [s["difficulty"] for s in pack.scenarios]
        assert diffs.count("Easy") == 2
        assert diffs.count("Hard") == 2
        assert diffs.count("NIGHTMARE") == 1

    def test_themes_are_quantum_heist_prefixed(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        for s in pack.scenarios:
            assert s["theme"].startswith("QUANTUM_HEIST_"), (
                f"node_id {s['node_id']} 테마 오류: {s['theme']}"
            )

    def test_no_is_boss_true(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        for s in pack.scenarios:
            assert not s.get("is_boss", False)

    def test_text_log_non_empty(self) -> None:
        pack = load_scenario_pack(PACK26_PATH)
        for s in pack.scenarios:
            assert len(s["text_log"]) > 50, f"node_id {s['node_id']} text_log가 너무 짧음"

    def test_keywords_in_text_log(self) -> None:
        """target_keyword가 text_log 내에 등장해야 한다."""
        pack = load_scenario_pack(PACK26_PATH)
        for s in pack.scenarios:
            assert s["target_keyword"] in s["text_log"], (
                f"node_id {s['node_id']} target_keyword '{s['target_keyword']}' "
                f"가 text_log에 없음"
            )


# ── Pack 27 — BIOMECH ASYLUM ──────────────────────────────────────────────────

class TestPack27BiomechAsylum:
    def test_file_exists(self) -> None:
        assert PACK27_PATH.exists(), f"팩 파일 없음: {PACK27_PATH}"

    def test_loads_without_error(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        assert pack is not None

    def test_metadata(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        assert pack.metadata.pack_id == "pack_27"
        assert "BIOMECH" in pack.metadata.name.upper()

    def test_scenario_count(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        assert len(pack.scenarios) == 5

    def test_node_id_range(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        ids = [s["node_id"] for s in pack.scenarios]
        assert min(ids) == 1019
        assert max(ids) == 1023

    def test_all_required_fields_present(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        _assert_pack_valid(pack, "pack_27", 5)

    def test_difficulty_distribution(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        diffs = [s["difficulty"] for s in pack.scenarios]
        assert diffs.count("Easy") == 2
        assert diffs.count("Hard") == 2
        assert diffs.count("NIGHTMARE") == 1

    def test_themes_are_biomech_asylum_prefixed(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        for s in pack.scenarios:
            assert s["theme"].startswith("BIOMECH_ASYLUM_"), (
                f"node_id {s['node_id']} 테마 오류: {s['theme']}"
            )

    def test_no_is_boss_true(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        for s in pack.scenarios:
            assert not s.get("is_boss", False)

    def test_text_log_non_empty(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        for s in pack.scenarios:
            assert len(s["text_log"]) > 50, f"node_id {s['node_id']} text_log가 너무 짧음"

    def test_keywords_in_text_log(self) -> None:
        pack = load_scenario_pack(PACK27_PATH)
        for s in pack.scenarios:
            assert s["target_keyword"] in s["text_log"], (
                f"node_id {s['node_id']} target_keyword '{s['target_keyword']}' "
                f"가 text_log에 없음"
            )


# ── 팩 간 node_id 충돌 검사 ───────────────────────────────────────────────────

class TestCrossPackConflictsV12:
    def test_no_node_id_overlap_between_pack26_and_pack27(self) -> None:
        pack26 = load_scenario_pack(PACK26_PATH)
        pack27 = load_scenario_pack(PACK27_PATH)
        ids26 = {s["node_id"] for s in pack26.scenarios}
        ids27 = {s["node_id"] for s in pack27.scenarios}
        overlap = ids26 & ids27
        assert not overlap, f"팩 26/27 node_id 충돌: {overlap}"

    def test_no_overlap_with_pack25(self) -> None:
        """기존 Pack 25와 신규 팩 간 node_id 충돌이 없어야 한다."""
        pack25_path = _pack_path("pack_25_neon_underground.json")
        if not pack25_path.exists():
            pytest.skip("pack_25 파일 없음")
        pack25 = load_scenario_pack(pack25_path)
        pack26 = load_scenario_pack(PACK26_PATH)
        pack27 = load_scenario_pack(PACK27_PATH)
        all_ids = (
            {s["node_id"] for s in pack25.scenarios}
            | {s["node_id"] for s in pack26.scenarios}
            | {s["node_id"] for s in pack27.scenarios}
        )
        total = len(pack25.scenarios) + len(pack26.scenarios) + len(pack27.scenarios)
        assert len(all_ids) == total, "팩 25/26/27 사이 node_id 중복 존재"

    def test_load_all_packs_includes_new_packs(self) -> None:
        packs_dir = Path(__file__).parent.parent / "packs"
        scenarios, warnings = load_all_packs(packs_dir=packs_dir)
        ids = {s["node_id"] for s in scenarios}
        for nid in range(1014, 1024):
            assert nid in ids, f"node_id {nid}가 load_all_packs 결과에 없음"

    def test_penalty_rate_matches_difficulty(self) -> None:
        """Easy≤30, Hard≤50, NIGHTMARE≤80 범위 권장 기준 검증."""
        for pack_path in (PACK26_PATH, PACK27_PATH):
            pack = load_scenario_pack(pack_path)
            for s in pack.scenarios:
                diff = s["difficulty"]
                rate = s["penalty_rate"]
                if diff == "Easy":
                    assert rate <= 30, f"{pack_path.name} node_id {s['node_id']}: Easy 패널티 {rate}%가 30% 초과"
                elif diff == "Hard":
                    assert rate <= 50, f"{pack_path.name} node_id {s['node_id']}: Hard 패널티 {rate}%가 50% 초과"
                elif diff == "NIGHTMARE":
                    assert rate <= 80, f"{pack_path.name} node_id {s['node_id']}: NIGHTMARE 패널티 {rate}%가 80% 초과"
