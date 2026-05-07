"""Pack 28 (ORBITAL_TRIBUNAL) 스모크 + 검증 테스트.

pack_loader 인프라를 통해 신규 팩이 올바르게 로드되고
시나리오 구조 / node_id 범위 / 난이도 분포를 충족하는지 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pack_loader import LoadedPack, PackMetadata, load_scenario_pack, load_all_packs


# ── 경로 헬퍼 ────────────────────────────────────────────────────────────────

def _pack_path(filename: str) -> Path:
    return Path(__file__).parent.parent / "packs" / filename


PACK28_PATH = _pack_path("pack_28_orbital_tribunal.json")

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


# ── Pack 28 — ORBITAL TRIBUNAL ────────────────────────────────────────────────

class TestPack28OrbitalTribunal:
    def test_file_exists(self) -> None:
        assert PACK28_PATH.exists(), f"팩 파일 없음: {PACK28_PATH}"

    def test_loads_without_error(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        assert pack is not None

    def test_metadata(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        assert pack.metadata.pack_id == "pack_28"
        assert "ORBITAL" in pack.metadata.name.upper() or "TRIBUNAL" in pack.metadata.name.upper()

    def test_scenario_count(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        assert len(pack.scenarios) == 5

    def test_node_id_range(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        ids = [s["node_id"] for s in pack.scenarios]
        assert min(ids) == 1024
        assert max(ids) == 1028

    def test_node_ids_are_sequential(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        ids = sorted(s["node_id"] for s in pack.scenarios)
        assert ids == list(range(1024, 1029))

    def test_all_required_fields_present(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        _assert_pack_valid(pack, "pack_28", 5)

    def test_difficulty_distribution(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        diffs = [s["difficulty"] for s in pack.scenarios]
        assert diffs.count("Easy") == 2
        assert diffs.count("Hard") == 2
        assert diffs.count("NIGHTMARE") == 1

    def test_themes_are_orbital_tribunal_prefixed(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        for s in pack.scenarios:
            assert s["theme"].startswith("ORBITAL_TRIBUNAL_"), (
                f"node_id {s['node_id']} 테마 오류: {s['theme']}"
            )

    def test_no_is_boss_true(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        for s in pack.scenarios:
            assert not s.get("is_boss", False)

    def test_text_log_non_empty(self) -> None:
        pack = load_scenario_pack(PACK28_PATH)
        for s in pack.scenarios:
            assert len(s["text_log"]) > 100, f"node_id {s['node_id']} text_log가 너무 짧음"

    def test_keywords_in_text_log(self) -> None:
        """target_keyword가 text_log 내에 등장해야 한다."""
        pack = load_scenario_pack(PACK28_PATH)
        for s in pack.scenarios:
            assert s["target_keyword"] in s["text_log"], (
                f"node_id {s['node_id']} target_keyword '{s['target_keyword']}' "
                f"가 text_log에 없음"
            )

    def test_penalty_rate_matches_difficulty(self) -> None:
        """Easy≤30, Hard≤50, NIGHTMARE≤80 범위 권장 기준 검증."""
        pack = load_scenario_pack(PACK28_PATH)
        for s in pack.scenarios:
            diff = s["difficulty"]
            rate = s["penalty_rate"]
            if diff == "Easy":
                assert rate <= 30, f"node_id {s['node_id']}: Easy 패널티 {rate}%가 30% 초과"
            elif diff == "Hard":
                assert rate <= 50, f"node_id {s['node_id']}: Hard 패널티 {rate}%가 50% 초과"
            elif diff == "NIGHTMARE":
                assert rate <= 80, f"node_id {s['node_id']}: NIGHTMARE 패널티 {rate}%가 80% 초과"

    def test_expected_keywords(self) -> None:
        """Pack 28 시나리오별 예상 키워드 검증."""
        pack = load_scenario_pack(PACK28_PATH)
        keyword_map = {s["node_id"]: s["target_keyword"] for s in pack.scenarios}
        assert keyword_map[1024] == "무중력"
        assert keyword_map[1025] == "바람"
        assert keyword_map[1026] == "호흡기"
        assert keyword_map[1027] == "천둥"
        assert keyword_map[1028] == "노을"

    def test_logical_flaw_explanation_present(self) -> None:
        """모든 시나리오에 logical_flaw_explanation 필드가 있어야 한다."""
        pack = load_scenario_pack(PACK28_PATH)
        for s in pack.scenarios:
            assert "logical_flaw_explanation" in s, (
                f"node_id {s['node_id']} logical_flaw_explanation 누락"
            )
            assert len(s["logical_flaw_explanation"]) > 20, (
                f"node_id {s['node_id']} logical_flaw_explanation가 너무 짧음"
            )

    def test_nightmare_scenario_has_highest_penalty(self) -> None:
        """NIGHTMARE 시나리오가 팩 내에서 가장 높은 패널티를 가져야 한다."""
        pack = load_scenario_pack(PACK28_PATH)
        nightmare = [s for s in pack.scenarios if s["difficulty"] == "NIGHTMARE"]
        others = [s for s in pack.scenarios if s["difficulty"] != "NIGHTMARE"]
        assert nightmare, "NIGHTMARE 시나리오가 없음"
        max_nightmare = max(s["penalty_rate"] for s in nightmare)
        max_others = max(s["penalty_rate"] for s in others)
        assert max_nightmare > max_others, (
            f"NIGHTMARE 패널티({max_nightmare})가 다른 난이도 최대값({max_others})보다 높아야 함"
        )


# ── 팩 간 node_id 충돌 검사 ───────────────────────────────────────────────────

class TestCrossPackConflictsV13:
    def test_no_node_id_overlap_with_pack27(self) -> None:
        pack27_path = _pack_path("pack_27_biomech_asylum.json")
        if not pack27_path.exists():
            pytest.skip("pack_27 파일 없음")
        pack27 = load_scenario_pack(pack27_path)
        pack28 = load_scenario_pack(PACK28_PATH)
        ids27 = {s["node_id"] for s in pack27.scenarios}
        ids28 = {s["node_id"] for s in pack28.scenarios}
        overlap = ids27 & ids28
        assert not overlap, f"팩 27/28 node_id 충돌: {overlap}"

    def test_no_overlap_with_pack26_and_pack27(self) -> None:
        pack26_path = _pack_path("pack_26_quantum_heist.json")
        pack27_path = _pack_path("pack_27_biomech_asylum.json")
        if not pack26_path.exists() or not pack27_path.exists():
            pytest.skip("pack_26 또는 pack_27 파일 없음")
        pack26 = load_scenario_pack(pack26_path)
        pack27 = load_scenario_pack(pack27_path)
        pack28 = load_scenario_pack(PACK28_PATH)
        all_ids = (
            {s["node_id"] for s in pack26.scenarios}
            | {s["node_id"] for s in pack27.scenarios}
            | {s["node_id"] for s in pack28.scenarios}
        )
        total = len(pack26.scenarios) + len(pack27.scenarios) + len(pack28.scenarios)
        assert len(all_ids) == total, "팩 26/27/28 사이 node_id 중복 존재"

    def test_load_all_packs_includes_pack28(self) -> None:
        packs_dir = Path(__file__).parent.parent / "packs"
        scenarios, warnings = load_all_packs(packs_dir=packs_dir)
        ids = {s["node_id"] for s in scenarios}
        for nid in range(1024, 1029):
            assert nid in ids, f"node_id {nid}가 load_all_packs 결과에 없음"

    def test_pack28_unique_among_all_packs(self) -> None:
        """Pack 28의 모든 node_id가 전체 팩 로드 결과에서 고유해야 한다."""
        packs_dir = Path(__file__).parent.parent / "packs"
        all_scenarios, _ = load_all_packs(packs_dir=packs_dir)
        all_ids = [s["node_id"] for s in all_scenarios]
        assert len(all_ids) == len(set(all_ids)), "전체 팩 로드 후 node_id 중복 발견"
