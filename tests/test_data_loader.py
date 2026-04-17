"""data_loader.py 단위 테스트."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from data_loader import (
    REQUIRED_KEYS,
    _resolve_resource_path,
    load_argos_taunts,
    load_boss_phase_pack,
    load_scenarios,
)


# ── 헬퍼: 임시 JSON 파일 생성 ─────────────────────────────────────────────────

def _write_json(tmp_path: Path, filename: str, data: Any) -> str:
    """tmp_path 아래에 JSON 파일을 작성하고 절대 경로를 반환한다."""
    p = tmp_path / filename
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _valid_scenario(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "node_id": 1,
        "theme": "A",
        "difficulty": "Easy",
        "text_log": "로그 내용",
        "target_keyword": "GPS",
        "penalty_rate": 20,
    }
    base.update(overrides)
    return base


# ── _resolve_resource_path ────────────────────────────────────────────────────

def test_resolve_resource_path_absolute_returned_as_is(tmp_path: Path) -> None:
    target = tmp_path / "test.json"
    target.touch()
    result = _resolve_resource_path(str(target))
    assert result == target


def test_resolve_resource_path_uses_cwd_when_exists(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "scenarios.json").touch()
    monkeypatch.chdir(tmp_path)
    result = _resolve_resource_path("scenarios.json")
    assert result == (tmp_path / "scenarios.json").resolve()


def test_resolve_resource_path_uses_meipass_when_cwd_missing(
    tmp_path: Path, monkeypatch
) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "argos_taunts.json").touch()

    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
    # CWD에는 해당 파일 없음 → _MEIPASS에서 찾아야 함
    monkeypatch.chdir(tmp_path)

    result = _resolve_resource_path("argos_taunts.json")
    assert result == (bundle_dir / "argos_taunts.json").resolve()


# ── load_scenarios ────────────────────────────────────────────────────────────

def test_load_scenarios_valid_file_returns_list(tmp_path: Path) -> None:
    scenarios = [_valid_scenario(node_id=1), _valid_scenario(node_id=2)]
    path = _write_json(tmp_path, "s.json", scenarios)
    result = load_scenarios(path)
    assert len(result) == 2
    assert result[0]["node_id"] == 1


def test_load_scenarios_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_scenarios(str(tmp_path / "nonexistent.json"))


def test_load_scenarios_invalid_json_raises_decode_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ broken json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_scenarios(str(bad))


def test_load_scenarios_root_not_list_raises_value_error(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "s.json", {"key": "not a list"})
    with pytest.raises(ValueError, match="리스트"):
        load_scenarios(path)


def test_load_scenarios_missing_required_key_raises_value_error(tmp_path: Path) -> None:
    scenario = _valid_scenario()
    del scenario["target_keyword"]
    path = _write_json(tmp_path, "s.json", [scenario])
    with pytest.raises(ValueError, match="target_keyword"):
        load_scenarios(path)


def test_load_scenarios_non_dict_item_raises_value_error(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "s.json", [_valid_scenario(), "not_a_dict"])
    with pytest.raises(ValueError, match="딕셔너리"):
        load_scenarios(path)


def test_load_scenarios_includes_optional_fields(tmp_path: Path) -> None:
    scenario = _valid_scenario(logical_flaw_explanation="설명", is_boss=True)
    path = _write_json(tmp_path, "s.json", [scenario])
    result = load_scenarios(path)
    assert result[0]["is_boss"] is True
    assert result[0]["logical_flaw_explanation"] == "설명"


# ── load_argos_taunts ─────────────────────────────────────────────────────────

def test_load_argos_taunts_valid_file_returns_dict(tmp_path: Path) -> None:
    data = {"node_clear": ["잘 했다", "계속 진행해"], "wrong_analyze": ["실패야"]}
    path = _write_json(tmp_path, "taunts.json", data)
    result = load_argos_taunts(path)
    assert "node_clear" in result
    assert len(result["node_clear"]) == 2


def test_load_argos_taunts_strips_whitespace_lines(tmp_path: Path) -> None:
    data = {"cat": [" line1 ", "  ", "line2"]}
    path = _write_json(tmp_path, "taunts.json", data)
    result = load_argos_taunts(path)
    assert result["cat"] == ["line1", "line2"]


def test_load_argos_taunts_root_not_dict_raises(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "taunts.json", ["not", "a", "dict"])
    with pytest.raises(ValueError, match="딕셔너리"):
        load_argos_taunts(path)


def test_load_argos_taunts_value_not_list_raises(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "taunts.json", {"cat": "not a list"})
    with pytest.raises(ValueError, match="리스트"):
        load_argos_taunts(path)


def test_load_argos_taunts_non_string_line_raises(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "taunts.json", {"cat": ["ok", 42]})
    with pytest.raises(ValueError, match="문자열"):
        load_argos_taunts(path)


def test_load_argos_taunts_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_argos_taunts(str(tmp_path / "nope.json"))


# ── load_boss_phase_pack ──────────────────────────────────────────────────────

def _valid_boss_pack(node_id: int = 17) -> dict[str, Any]:
    return {
        "version": 1,
        "ascension_20_boss_overrides": {
            str(node_id): [
                {"text_log": "phase 1 log", "target_keyword": "alpha"},
                {"text_log": "phase 2 log", "target_keyword": "beta"},
                {"text_log": "phase 3 log", "target_keyword": "gamma"},
            ]
        },
    }


def test_load_boss_phase_pack_valid_returns_int_keyed_dict(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "bpp.json", _valid_boss_pack(node_id=17))
    result = load_boss_phase_pack(path)
    assert 17 in result
    assert len(result[17]) == 3
    assert result[17][0]["target_keyword"] == "alpha"


def test_load_boss_phase_pack_includes_logical_flaw(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "ascension_20_boss_overrides": {
            "5": [
                {
                    "text_log": "some log",
                    "target_keyword": "kw",
                    "logical_flaw_explanation": "설명입니다",
                }
            ]
        },
    }
    path = _write_json(tmp_path, "bpp.json", data)
    result = load_boss_phase_pack(path)
    assert result[5][0]["logical_flaw_explanation"] == "설명입니다"


def test_load_boss_phase_pack_missing_required_field_raises(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "ascension_20_boss_overrides": {
            "1": [{"text_log": "log"}]  # target_keyword 누락
        },
    }
    path = _write_json(tmp_path, "bpp.json", data)
    with pytest.raises(ValueError, match="target_keyword"):
        load_boss_phase_pack(path)


def test_load_boss_phase_pack_non_integer_node_id_raises(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "ascension_20_boss_overrides": {
            "abc": [{"text_log": "log", "target_keyword": "kw"}]
        },
    }
    path = _write_json(tmp_path, "bpp.json", data)
    with pytest.raises(ValueError, match="정수"):
        load_boss_phase_pack(path)


def test_load_boss_phase_pack_negative_node_id_raises(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "ascension_20_boss_overrides": {
            "-1": [{"text_log": "log", "target_keyword": "kw"}]
        },
    }
    path = _write_json(tmp_path, "bpp.json", data)
    with pytest.raises(ValueError, match="양수"):
        load_boss_phase_pack(path)


def test_load_boss_phase_pack_empty_phase_list_raises(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "ascension_20_boss_overrides": {"3": []},
    }
    path = _write_json(tmp_path, "bpp.json", data)
    with pytest.raises(ValueError, match="비어있지 않은"):
        load_boss_phase_pack(path)


def test_load_boss_phase_pack_missing_overrides_key_raises(tmp_path: Path) -> None:
    path = _write_json(tmp_path, "bpp.json", {"version": 1})
    with pytest.raises(ValueError, match="ascension_20_boss_overrides"):
        load_boss_phase_pack(path)


def test_load_boss_phase_pack_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_boss_phase_pack(str(tmp_path / "nope.json"))
