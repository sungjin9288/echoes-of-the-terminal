"""pack_loader.py 유닛 / 통합 테스트.

PackMetadata · LoadedPack 구조, 단일 팩 로딩, 디렉터리 탐색,
전체 팩 병합, node_id 중복 감지, 오류 처리를 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pack_loader import (
    LoadedPack,
    PackMetadata,
    discover_packs,
    load_all_packs,
    load_scenario_pack,
)


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _make_scenario(node_id: int = 9001, difficulty: str = "Easy") -> dict:
    return {
        "node_id": node_id,
        "theme": "TEST",
        "difficulty": difficulty,
        "text_log": "테스트용 조서입니다.",
        "target_keyword": "테스트",
        "penalty_rate": 20,
    }


def _make_pack_file(
    tmp_path: Path,
    filename: str = "pack_test.json",
    *,
    pack_id: str = "pack_test",
    name: str = "테스트 팩",
    scenarios: list[dict] | None = None,
    extra: dict | None = None,
) -> Path:
    """임시 디렉터리에 팩 JSON 파일을 작성하고 경로를 반환한다."""
    data: dict = {
        "pack_id": pack_id,
        "name": name,
        "version": "1.0",
        "author": "Tester",
        "scenarios": scenarios if scenarios is not None else [_make_scenario()],
    }
    if extra:
        data.update(extra)
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── PackMetadata / LoadedPack 구조 ───────────────────────────────────────────

class TestPackMetadata:
    def test_frozen_dataclass(self) -> None:
        meta = PackMetadata(pack_id="p1", name="팩1")
        with pytest.raises((AttributeError, TypeError)):
            meta.pack_id = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        meta = PackMetadata(pack_id="p1", name="팩1")
        assert meta.version == "1.0"
        assert meta.author == "Unknown"
        assert meta.scenario_count == 0

    def test_custom_fields(self) -> None:
        meta = PackMetadata(pack_id="p23", name="팩23", version="2.1", author="Dev", scenario_count=5)
        assert meta.scenario_count == 5


# ── load_scenario_pack ───────────────────────────────────────────────────────

class TestLoadScenarioPack:
    def test_load_valid_pack(self, tmp_path: Path) -> None:
        path = _make_pack_file(tmp_path, scenarios=[_make_scenario(9001), _make_scenario(9002)])
        result = load_scenario_pack(path)
        assert isinstance(result, LoadedPack)
        assert result.metadata.pack_id == "pack_test"
        assert result.metadata.scenario_count == 2
        assert len(result.scenarios) == 2

    def test_scenarios_tuple_immutable(self, tmp_path: Path) -> None:
        """scenarios 필드는 튜플(불변)이어야 한다."""
        path = _make_pack_file(tmp_path)
        result = load_scenario_pack(path)
        assert isinstance(result.scenarios, tuple)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_scenario_pack(tmp_path / "nonexistent.json")

    def test_missing_required_meta_field_raises(self, tmp_path: Path) -> None:
        bad = {"name": "이름만 있음", "scenarios": [_make_scenario()]}
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError, match="필수 필드"):
            load_scenario_pack(p)

    def test_root_not_dict_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "list_root.json"
        p.write_text(json.dumps([_make_scenario()]), encoding="utf-8")
        with pytest.raises(ValueError, match="딕셔너리"):
            load_scenario_pack(p)

    def test_scenarios_not_list_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad_scenarios.json"
        p.write_text(json.dumps({"pack_id": "x", "name": "x", "scenarios": "wrong"}), encoding="utf-8")
        with pytest.raises(ValueError, match="리스트"):
            load_scenario_pack(p)

    def test_scenario_missing_required_key_raises(self, tmp_path: Path) -> None:
        bad_scenario = {k: v for k, v in _make_scenario().items() if k != "target_keyword"}
        path = _make_pack_file(tmp_path, scenarios=[bad_scenario])
        with pytest.raises(ValueError, match="필수 필드"):
            load_scenario_pack(path)

    def test_invalid_difficulty_raises(self, tmp_path: Path) -> None:
        s = _make_scenario()
        s["difficulty"] = "Medium"
        path = _make_pack_file(tmp_path, scenarios=[s])
        with pytest.raises(ValueError, match="difficulty"):
            load_scenario_pack(path)

    def test_all_valid_difficulties(self, tmp_path: Path) -> None:
        for diff in ("Easy", "Hard", "NIGHTMARE"):
            s = _make_scenario()
            s["difficulty"] = diff
            path = _make_pack_file(tmp_path, filename=f"pack_{diff}.json", scenarios=[s])
            result = load_scenario_pack(path)
            assert result.scenarios[0]["difficulty"] == diff

    def test_optional_fields_preserved(self, tmp_path: Path) -> None:
        """author, version 등 선택적 메타 필드가 올바르게 읽혀야 한다."""
        p = tmp_path / "opt.json"
        p.write_text(json.dumps({
            "pack_id": "opt_pack",
            "name": "옵션 팩",
            "version": "3.0",
            "author": "커스텀 작가",
            "scenarios": [_make_scenario()],
        }), encoding="utf-8")
        result = load_scenario_pack(p)
        assert result.metadata.version == "3.0"
        assert result.metadata.author == "커스텀 작가"

    def test_file_too_large_raises(self, tmp_path: Path, monkeypatch) -> None:
        import pack_loader
        monkeypatch.setattr(pack_loader, "_MAX_PACK_FILE_SIZE", 10)
        path = _make_pack_file(tmp_path)
        with pytest.raises(ValueError, match="크기"):
            load_scenario_pack(path)


# ── discover_packs ───────────────────────────────────────────────────────────

class TestDiscoverPacks:
    def test_no_directory_returns_empty(self, tmp_path: Path) -> None:
        result = discover_packs(tmp_path / "nonexistent")
        assert result == []

    def test_discovers_pack_files_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "pack_03.json").touch()
        (tmp_path / "pack_01.json").touch()
        (tmp_path / "pack_02.json").touch()
        (tmp_path / "other.json").touch()   # 패턴 미일치, 무시
        result = discover_packs(tmp_path)
        names = [p.name for p in result]
        assert names == ["pack_01.json", "pack_02.json", "pack_03.json"]

    def test_non_pack_files_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").touch()
        (tmp_path / "scenarios.json").touch()
        result = discover_packs(tmp_path)
        assert result == []


# ── load_all_packs ───────────────────────────────────────────────────────────

class TestLoadAllPacks:
    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        scenarios, meta = load_all_packs(tmp_path)
        assert scenarios == []
        assert meta == []

    def test_single_pack_merged(self, tmp_path: Path) -> None:
        _make_pack_file(tmp_path, "pack_01.json", scenarios=[_make_scenario(9001)])
        scenarios, meta = load_all_packs(tmp_path)
        assert len(scenarios) == 1
        assert scenarios[0]["node_id"] == 9001
        assert len(meta) == 1

    def test_multiple_packs_merged_in_order(self, tmp_path: Path) -> None:
        _make_pack_file(tmp_path, "pack_01.json", pack_id="p1", name="P1",
                        scenarios=[_make_scenario(9001)])
        _make_pack_file(tmp_path, "pack_02.json", pack_id="p2", name="P2",
                        scenarios=[_make_scenario(9002)])
        scenarios, meta = load_all_packs(tmp_path)
        assert len(scenarios) == 2
        assert [s["node_id"] for s in scenarios] == [9001, 9002]
        assert [m.pack_id for m in meta] == ["p1", "p2"]

    def test_duplicate_node_id_across_packs_raises(self, tmp_path: Path) -> None:
        _make_pack_file(tmp_path, "pack_01.json", pack_id="p1", name="P1",
                        scenarios=[_make_scenario(9001)])
        _make_pack_file(tmp_path, "pack_02.json", pack_id="p2", name="P2",
                        scenarios=[_make_scenario(9001)])  # 중복!
        with pytest.raises(ValueError, match="중복"):
            load_all_packs(tmp_path)

    def test_known_node_ids_conflict_raises(self, tmp_path: Path) -> None:
        _make_pack_file(tmp_path, "pack_01.json", scenarios=[_make_scenario(100)])
        with pytest.raises(ValueError, match="중복"):
            load_all_packs(tmp_path, known_node_ids={100})

    def test_known_node_ids_no_conflict_passes(self, tmp_path: Path) -> None:
        _make_pack_file(tmp_path, "pack_01.json", scenarios=[_make_scenario(9001)])
        scenarios, meta = load_all_packs(tmp_path, known_node_ids={1, 2, 3})
        assert len(scenarios) == 1


# ── load_scenarios_with_packs (data_loader 통합) ─────────────────────────────

class TestLoadScenariosWithPacks:
    def test_base_only_no_packs(self, tmp_path: Path) -> None:
        """packs 디렉터리 없을 때 기본 시나리오만 반환."""
        from data_loader import load_scenarios_with_packs
        import json as _json, copy
        import progression_system as ps

        base = [_make_scenario(1), _make_scenario(2)]
        base_file = tmp_path / "scenarios.json"
        base_file.write_text(_json.dumps(base), encoding="utf-8")

        empty_packs = tmp_path / "empty_packs"
        scenarios, meta = load_scenarios_with_packs(str(base_file), str(empty_packs))
        assert len(scenarios) == 2
        assert meta == []

    def test_base_plus_pack(self, tmp_path: Path) -> None:
        """기본 시나리오 + 팩 시나리오 합산."""
        import json as _json
        from data_loader import load_scenarios_with_packs

        base = [_make_scenario(1), _make_scenario(2)]
        base_file = tmp_path / "scenarios.json"
        base_file.write_text(_json.dumps(base), encoding="utf-8")

        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        _make_pack_file(packs_dir, "pack_01.json", scenarios=[_make_scenario(9001)])

        scenarios, meta = load_scenarios_with_packs(str(base_file), str(packs_dir))
        assert len(scenarios) == 3
        assert len(meta) == 1

    def test_node_id_conflict_between_base_and_pack_raises(self, tmp_path: Path) -> None:
        """기본 시나리오와 팩 시나리오 간 node_id 충돌 시 ValueError."""
        import json as _json
        from data_loader import load_scenarios_with_packs

        base = [_make_scenario(1)]
        base_file = tmp_path / "scenarios.json"
        base_file.write_text(_json.dumps(base), encoding="utf-8")

        packs_dir = tmp_path / "packs"
        packs_dir.mkdir()
        _make_pack_file(packs_dir, "pack_01.json", scenarios=[_make_scenario(1)])  # 충돌

        with pytest.raises(ValueError, match="중복"):
            load_scenarios_with_packs(str(base_file), str(packs_dir))


# ── 실제 Pack 23 파일 smoke test ─────────────────────────────────────────────

def test_pack_23_demo_file_loads() -> None:
    """packs/pack_23_cyber_noir.json이 오류 없이 로드되어야 한다."""
    pack_file = Path(__file__).resolve().parent.parent / "packs" / "pack_23_cyber_noir.json"
    if not pack_file.exists():
        pytest.skip("pack_23_cyber_noir.json 파일 없음")
    result = load_scenario_pack(pack_file)
    assert result.metadata.pack_id == "pack_23"
    assert len(result.scenarios) == 3
    assert all(s["node_id"] >= 1001 for s in result.scenarios)
