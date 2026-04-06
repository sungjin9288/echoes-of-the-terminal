"""Campaign progression tests for 100h clear condition."""

from progression_system import (
    CAMPAIGN_CLEAR_CLASS_VICTORIES,
    CAMPAIGN_CLEAR_POINTS,
    CAMPAIGN_CLEAR_TOTAL_VICTORIES,
    calculate_campaign_gain,
    get_campaign_progress_snapshot,
    is_campaign_cleared,
    update_campaign_progress,
    _normalize_save_data,
)


def test_normalize_save_adds_campaign_defaults() -> None:
    normalized = _normalize_save_data({"data_fragments": 10, "perks": {}})
    campaign = normalized["campaign"]
    assert campaign["points"] == 0
    assert campaign["runs"] == 0
    assert campaign["victories"] == 0
    assert campaign["ascension_unlocked"] == 0
    assert campaign["class_victories"]["ANALYST"] == 0
    assert campaign["class_victories"]["GHOST"] == 0
    assert campaign["class_victories"]["CRACKER"] == 0
    assert campaign["cleared"] is False


def test_campaign_gain_adds_victory_bonus() -> None:
    assert calculate_campaign_gain(120, True) == 140
    assert calculate_campaign_gain(120, False) == 120


def test_update_campaign_progress_increments_run_and_class_victory() -> None:
    save_data = _normalize_save_data({})
    result = update_campaign_progress(
        save_data=save_data,
        gain=140,
        is_victory=True,
        class_key="ANALYST",
        ascension_level=0,
    )
    campaign = result["campaign"]
    assert campaign["runs"] == 1
    assert campaign["points"] == 140
    assert campaign["victories"] == 1
    assert campaign["class_victories"]["ANALYST"] == 1
    assert campaign["ascension_unlocked"] == 1
    assert campaign["cleared"] is False
    assert result["just_cleared"] is False


def test_update_campaign_progress_does_not_unlock_ascension_on_defeat() -> None:
    save_data = _normalize_save_data({})
    result = update_campaign_progress(
        save_data=save_data,
        gain=70,
        is_victory=False,
        class_key="ANALYST",
        ascension_level=0,
    )
    campaign = result["campaign"]
    assert campaign["runs"] == 1
    assert campaign["victories"] == 0
    assert campaign["ascension_unlocked"] == 0


def test_campaign_clear_condition_true_at_threshold() -> None:
    campaign = {
        "points": CAMPAIGN_CLEAR_POINTS,
        "runs": CAMPAIGN_CLEAR_TOTAL_VICTORIES,
        "victories": CAMPAIGN_CLEAR_TOTAL_VICTORIES,
        "class_victories": {
            "ANALYST": CAMPAIGN_CLEAR_CLASS_VICTORIES,
            "GHOST": CAMPAIGN_CLEAR_CLASS_VICTORIES,
            "CRACKER": CAMPAIGN_CLEAR_CLASS_VICTORIES,
        },
        "cleared": False,
    }
    assert is_campaign_cleared(campaign) is True


def test_campaign_snapshot_ratios_are_capped_to_one() -> None:
    snapshot = get_campaign_progress_snapshot(
        {
            "points": CAMPAIGN_CLEAR_POINTS * 2,
            "runs": CAMPAIGN_CLEAR_TOTAL_VICTORIES,
            "victories": CAMPAIGN_CLEAR_TOTAL_VICTORIES * 2,
            "class_victories": {
                "ANALYST": CAMPAIGN_CLEAR_CLASS_VICTORIES * 2,
                "GHOST": CAMPAIGN_CLEAR_CLASS_VICTORIES * 2,
                "CRACKER": CAMPAIGN_CLEAR_CLASS_VICTORIES * 2,
            },
            "cleared": True,
        }
    )
    assert snapshot["points_ratio"] == 1.0
    assert snapshot["victories_ratio"] == 1.0
    assert snapshot["cleared"] is True


def test_campaign_snapshot_contains_ascension_unlocked() -> None:
    snapshot = get_campaign_progress_snapshot(
        {
            "points": 0,
            "runs": 0,
            "victories": 0,
            "ascension_unlocked": 7,
            "class_victories": {"ANALYST": 0, "GHOST": 0, "CRACKER": 0},
            "cleared": False,
        }
    )
    assert snapshot["ascension_unlocked"] == 7
