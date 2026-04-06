"""Boss phase pack loader tests."""

import json

import pytest

from data_loader import load_boss_phase_pack


def test_load_boss_phase_pack_returns_normalized_mapping(tmp_path) -> None:
    file_path = tmp_path / "boss_phase_pack.json"
    payload = {
        "version": 1,
        "ascension_20_boss_overrides": {
            "17": [
                {"text_log": "log-1", "target_keyword": "kw-1"},
                {
                    "text_log": "log-2",
                    "target_keyword": "kw-2",
                    "logical_flaw_explanation": "exp-2",
                },
            ]
        },
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    loaded = load_boss_phase_pack(str(file_path))
    assert 17 in loaded
    assert loaded[17][0]["text_log"] == "log-1"
    assert loaded[17][1]["target_keyword"] == "kw-2"
    assert loaded[17][1]["logical_flaw_explanation"] == "exp-2"


def test_load_boss_phase_pack_raises_on_missing_required_field(tmp_path) -> None:
    file_path = tmp_path / "boss_phase_pack.json"
    payload = {
        "version": 1,
        "ascension_20_boss_overrides": {
            "17": [{"text_log": "log-only"}]
        },
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError):
        load_boss_phase_pack(str(file_path))
