"""Pack 29 (ABYSSAL_COURT) 스모크 + 검증 테스트.

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


PACK29_PATH = _pack_path("pack_29_abyssal_court.json")

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


# ── Pack 29 — ABYSSAL COURT ───────────────────────────────────────────────────

class TestPack29AbyssalCourt:
    def test_file_exists(self) -> None:
        assert PACK29_PATH.exists(), f"팩 파일 없음: {PACK29_PATH}"

    def test_loads_without_error(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        assert pack is not None

    def test_metadata(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        assert pack.metadata.pack_id == "pack_29"
        assert "ABYSSAL" in pack.metadata.name.upper() or "COURT" in pack.metadata.name.upper()

    def test_scenario_count(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        assert len(pack.scenarios) == 5

    def test_node_id_range(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        ids = [s["node_id"] for s in pack.scenarios]
        assert min(ids) == 1029
        assert max(ids) == 1033

    def test_node_ids_are_sequential(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        ids = sorted(s["node_id"] for s in pack.scenarios)
        assert ids == list(range(1029, 1034))

    def test_all_required_fields_present(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        _assert_pack_valid(pack, "pack_29", 5)

    def test_difficulty_distribution(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        diffs = [s["difficulty"] for s in pack.scenarios]
        assert diffs.count("Easy") == 2
        assert diffs.count("Hard") == 2
        assert diffs.count("NIGHTMARE") == 1

    def test_themes_are_abyssal_court_prefixed(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        for s in pack.scenarios:
            assert s["theme"].startswith("ABYSSAL_COURT_"), (
                f"node_id {s['node_id']} 테마 오류: {s['theme']}"
            )

    def test_no_is_boss_true(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        for s in pack.scenarios:
            assert not s.get("is_boss", False)

    def test_text_log_non_empty(self) -> None:
        pack = load_scenario_pack(PACK29_PATH)
        for s in pack.scenarios:
            assert len(s["text_log"]) > 100, f"node_id {s['node_id']} text_log가 너무 짧음"

    def test_keywords_in_text_log(self) -> None:
        """target_keyword가 text_log 내에 등장해야 한다."""
        pack = load_scenario_pack(PACK29_PATH)
        for s in pack.scenarios:
            assert s["target_keyword"] in s["text_log"], (
                f"node_id {s['node_id']} target_keyword '{s['target_keyword']}' "
                f"가 text_log에 없음"
            )

    def test_penalty_rate_matches_difficulty(self) -> None:
        """Easy≤30, Hard≤50, NIGHTMARE≤80 범위 권장 기준 검증."""
        pack = load_scenario_pack(PACK29_PATH)
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
        """Pack 29 시나리오별 예상 키워드 검증."""
        pack = load_scenario_pack(PACK29_PATH)
        keyword_map = {s["node_id"]: s["target_keyword"] for s in pack.scenarios}
        assert keyword_map[1029] == "햇빛"
        assert keyword_map[1030] == "위성전화"
        assert keyword_map[1031] == "잠수복"
        assert keyword_map[1032] == "산소"
        assert keyword_map[1033] == "감압"

    def test_logical_flaw_explanation_present(self) -> None:
        """모든 시나리오에 logical_flaw_explanation 필드가 있어야 한다."""
        pack = load_scenario_pack(PACK29_PATH)
        for s in pack.scenarios:
            assert "logical_flaw_explanation" in s, (
                f"node_id {s['node_id']} logical_flaw_explanation 누락"
            )
            assert len(s["logical_flaw_explanation"]) > 20, (
                f"node_id {s['node_id']} logical_flaw_explanation가 너무 짧음"
            )

    def test_nightmare_highest_penalty(self) -> None:
        """NIGHTMARE 시나리오가 팩 내에서 가장 높은 패널티를 가져야 한다."""
        pack = load_scenario_pack(PACK29_PATH)
        nightmare = [s for s in pack.scenarios if s["difficulty"] == "NIGHTMARE"]
        others = [s for s in pack.scenarios if s["difficulty"] != "NIGHTMARE"]
        assert nightmare, "NIGHTMARE 시나리오가 없음"
        assert max(s["penalty_rate"] for s in nightmare) > max(s["penalty_rate"] for s in others)

    def test_deep_sea_theme_in_text_logs(self) -> None:
        """심해 배경임을 나타내는 키워드가 text_log에 존재한다."""
        pack = load_scenario_pack(PACK29_PATH)
        deep_sea_words = {"심해", "수심", "해저", "잠수", "넵투누스"}
        for s in pack.scenarios:
            found = any(w in s["text_log"] for w in deep_sea_words)
            assert found, f"node_id {s['node_id']}: 심해 배경 키워드 없음"


# ── 팩 간 node_id 충돌 검사 ───────────────────────────────────────────────────

class TestCrossPackConflictsV14:
    def test_no_node_id_overlap_with_pack28(self) -> None:
        pack28_path = _pack_path("pack_28_orbital_tribunal.json")
        if not pack28_path.exists():
            pytest.skip("pack_28 파일 없음")
        pack28 = load_scenario_pack(pack28_path)
        pack29 = load_scenario_pack(PACK29_PATH)
        ids28 = {s["node_id"] for s in pack28.scenarios}
        ids29 = {s["node_id"] for s in pack29.scenarios}
        overlap = ids28 & ids29
        assert not overlap, f"팩 28/29 node_id 충돌: {overlap}"

    def test_no_overlap_with_pack27_and_pack28(self) -> None:
        pack27_path = _pack_path("pack_27_biomech_asylum.json")
        pack28_path = _pack_path("pack_28_orbital_tribunal.json")
        if not pack27_path.exists() or not pack28_path.exists():
            pytest.skip("이전 팩 파일 없음")
        pack27 = load_scenario_pack(pack27_path)
        pack28 = load_scenario_pack(pack28_path)
        pack29 = load_scenario_pack(PACK29_PATH)
        all_ids = (
            {s["node_id"] for s in pack27.scenarios}
            | {s["node_id"] for s in pack28.scenarios}
            | {s["node_id"] for s in pack29.scenarios}
        )
        total = len(pack27.scenarios) + len(pack28.scenarios) + len(pack29.scenarios)
        assert len(all_ids) == total, "팩 27/28/29 사이 node_id 중복 존재"

    def test_load_all_packs_includes_pack29(self) -> None:
        packs_dir = Path(__file__).parent.parent / "packs"
        scenarios, warnings = load_all_packs(packs_dir=packs_dir)
        ids = {s["node_id"] for s in scenarios}
        for nid in range(1029, 1034):
            assert nid in ids, f"node_id {nid}가 load_all_packs 결과에 없음"

    def test_all_packs_globally_unique_node_ids(self) -> None:
        """전체 팩 로드 후 node_id가 전역적으로 고유해야 한다."""
        packs_dir = Path(__file__).parent.parent / "packs"
        all_scenarios, _ = load_all_packs(packs_dir=packs_dir)
        all_ids = [s["node_id"] for s in all_scenarios]
        assert len(all_ids) == len(set(all_ids)), "전체 팩 로드 후 node_id 중복 발견"
