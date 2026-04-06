"""Template builder tests for ASC20 boss phase pack tools."""

from boss_phase_pack_tools import build_boss_phase_pack_template


def test_build_template_creates_entries_for_all_boss_scenarios() -> None:
    scenarios = [
        {
            "node_id": 1,
            "theme": "A",
            "is_boss": False,
            "target_keyword": "alpha",
        },
        {
            "node_id": 17,
            "theme": "BOSS-1",
            "is_boss": True,
            "target_keyword": "넷",
        },
        {
            "node_id": 18,
            "theme": "BOSS-2",
            "is_boss": True,
            "target_keyword": "들어가",
        },
    ]
    pack = build_boss_phase_pack_template(scenarios=scenarios, phase_count=3)
    overrides = pack["ascension_20_boss_overrides"]

    assert sorted(overrides.keys()) == ["17", "18"]
    assert len(overrides["17"]) == 3
    assert overrides["17"][0]["target_keyword"] == "넷"
    assert "PHASE-1" in overrides["17"][0]["text_log"]


def test_build_template_preserves_existing_phase_data() -> None:
    scenarios = [
        {
            "node_id": 27,
            "theme": "BOSS-3",
            "is_boss": True,
            "target_keyword": "아무도",
        }
    ]
    existing = {
        27: [
            {
                "text_log": "existing phase 1",
                "target_keyword": "kw1",
                "logical_flaw_explanation": "exp1",
            },
            {
                "text_log": "existing phase 2",
                "target_keyword": "kw2",
            },
        ]
    }
    pack = build_boss_phase_pack_template(
        scenarios=scenarios,
        phase_count=3,
        existing_overrides=existing,
    )
    phases = pack["ascension_20_boss_overrides"]["27"]
    assert phases[0]["text_log"] == "existing phase 1"
    assert phases[0]["target_keyword"] == "kw1"
    assert phases[1]["text_log"] == "existing phase 2"
    assert phases[2]["target_keyword"] == "아무도"


def test_build_template_keeps_existing_longer_phase_count() -> None:
    scenarios = [
        {
            "node_id": 48,
            "theme": "BOSS-8",
            "is_boss": True,
            "target_keyword": "접속",
        }
    ]
    existing = {
        48: [
            {"text_log": "p1", "target_keyword": "k1"},
            {"text_log": "p2", "target_keyword": "k2"},
            {"text_log": "p3", "target_keyword": "k3"},
            {"text_log": "p4", "target_keyword": "k4"},
        ]
    }
    pack = build_boss_phase_pack_template(
        scenarios=scenarios,
        phase_count=3,
        existing_overrides=existing,
    )
    phases = pack["ascension_20_boss_overrides"]["48"]
    assert len(phases) == 4
    assert phases[3]["target_keyword"] == "k4"
