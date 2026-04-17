"""Campaign progression tests for 100h clear condition and perk system."""

from progression_system import (
    CAMPAIGN_CLEAR_CLASS_VICTORIES,
    CAMPAIGN_CLEAR_POINTS,
    CAMPAIGN_CLEAR_TOTAL_VICTORIES,
    PERK_DESC_MAP,
    PERK_LABEL_MAP,
    PERK_MENU_MAP,
    PERK_PRICES,
    calculate_campaign_gain,
    get_campaign_progress_snapshot,
    get_run_stats_snapshot,
    is_campaign_cleared,
    update_campaign_progress,
    update_run_stats,
    _migrate_save,
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


# ── 퍼크 시스템 구조 검증 (13종) ──────────────────────────────────────────────

def test_perk_menu_map_has_10_entries() -> None:
    assert len(PERK_MENU_MAP) == 13


def test_all_perk_maps_cover_same_keys() -> None:
    perk_ids = set(PERK_MENU_MAP.values())
    assert perk_ids == set(PERK_LABEL_MAP.keys())
    assert perk_ids == set(PERK_DESC_MAP.keys())
    assert perk_ids == set(PERK_PRICES.keys())


def test_perk_prices_are_positive_integers() -> None:
    for perk_id, price in PERK_PRICES.items():
        assert isinstance(price, int) and price > 0, (
            f"{perk_id} 가격이 유효하지 않음: {price}"
        )


def test_new_perks_exist_in_all_maps() -> None:
    new_perks = [
        "node_scanner", "trace_dampener",
        "fragment_amplifier", "elite_shield", "keyword_echo",
    ]
    for perk_id in new_perks:
        assert perk_id in PERK_LABEL_MAP, f"{perk_id} LABEL_MAP 누락"
        assert perk_id in PERK_DESC_MAP, f"{perk_id} DESC_MAP 누락"
        assert perk_id in PERK_PRICES, f"{perk_id} PRICES 누락"
        assert perk_id in set(PERK_MENU_MAP.values()), f"{perk_id} MENU_MAP 누락"


def test_perk_menu_keys_are_single_chars() -> None:
    for key in PERK_MENU_MAP:
        assert len(key) == 1, f"메뉴 키가 단일 문자가 아님: '{key}'"


def test_v90_perks_exist_in_all_maps() -> None:
    """v9.0 신규 퍼크 3종이 모든 맵에 등록되어 있는지 검증."""
    new_perks = ["adaptive_shield", "data_recovery", "swift_analysis"]
    for perk_id in new_perks:
        assert perk_id in PERK_LABEL_MAP, f"{perk_id} LABEL_MAP 누락"
        assert perk_id in PERK_DESC_MAP, f"{perk_id} DESC_MAP 누락"
        assert perk_id in PERK_PRICES, f"{perk_id} PRICES 누락"
        assert perk_id in set(PERK_MENU_MAP.values()), f"{perk_id} MENU_MAP 누락"


def test_v90_perk_prices_are_valid() -> None:
    """v9.0 신규 퍼크 가격이 양의 정수인지 검증."""
    assert PERK_PRICES["adaptive_shield"] == 55
    assert PERK_PRICES["data_recovery"] == 25
    assert PERK_PRICES["swift_analysis"] == 75


# ── 세이브 스키마 마이그레이션 테스트 ─────────────────────────────────────────

def test_migrate_save_v0_migrates_to_current() -> None:
    """schema_version 없는 구버전(v0) 세이브가 현재 버전으로 마이그레이션된다."""
    old_save = {"data_fragments": 42, "perks": {}}
    migrated = _migrate_save(old_save)
    assert migrated["schema_version"] == 2
    assert migrated["data_fragments"] == 42
    # 기존 유저 → tutorial_completed=True
    assert migrated["tutorial_completed"] is True


def test_migrate_save_v1_upgrades_to_v2() -> None:
    """v1 세이브가 v2로 마이그레이션되며 tutorial_completed=True가 추가된다."""
    v1_save = {"schema_version": 1, "data_fragments": 10}
    migrated = _migrate_save(v1_save)
    assert migrated["schema_version"] == 2
    assert migrated["tutorial_completed"] is True
    assert migrated["data_fragments"] == 10


def test_migrate_save_v2_is_idempotent() -> None:
    """이미 v2인 세이브는 재마이그레이션해도 값이 변하지 않는다."""
    v2_save = {"schema_version": 2, "data_fragments": 10, "tutorial_completed": False}
    migrated = _migrate_save(v2_save)
    assert migrated["schema_version"] == 2
    assert migrated["tutorial_completed"] is False


def test_migrate_save_does_not_mutate_input() -> None:
    """마이그레이션은 원본 딕셔너리를 변경하지 않는다."""
    original = {"data_fragments": 5}
    _migrate_save(original)
    assert "schema_version" not in original


def test_normalize_save_data_sets_schema_version_on_fresh_data() -> None:
    """_normalize_save_data는 v0 빈 세이브를 최신 버전으로 마이그레이션한다.

    실제 첫 실행은 FileNotFoundError → DEFAULT_SAVE_DATA 경로를 사용하며,
    _normalize_save_data({})는 기존 유저의 빈 v0 세이브 시나리오를 나타낸다.
    """
    normalized = _normalize_save_data({})
    assert normalized["schema_version"] == 2
    # 기존 유저(v0 이상) → tutorial 완료로 표시
    assert normalized["tutorial_completed"] is True


def test_normalize_save_data_existing_player_has_tutorial_completed_true() -> None:
    """기존 v1 세이브 정규화 시 tutorial_completed=True가 설정된다."""
    old = {"schema_version": 1, "data_fragments": 100}
    normalized = _normalize_save_data(old)
    assert normalized["tutorial_completed"] is True


# ── update_run_stats / get_run_stats_snapshot 테스트 ─────────────────────────

def test_update_run_stats_increments_total_runs() -> None:
    save_data: dict = {"stats": {}}
    update_run_stats(save_data, is_victory=False, final_trace=80, ascension_level=0)
    assert save_data["stats"]["total_runs"] == 1
    assert save_data["stats"]["total_victories"] == 0


def test_update_run_stats_victory_increments_victories_and_best_ascension() -> None:
    save_data: dict = {"stats": {}}
    update_run_stats(save_data, is_victory=True, final_trace=30, ascension_level=5)
    assert save_data["stats"]["total_victories"] == 1
    assert save_data["stats"]["best_ascension_cleared"] == 5


def test_update_run_stats_accumulates_trace() -> None:
    save_data: dict = {"stats": {}}
    update_run_stats(save_data, is_victory=True, final_trace=40, ascension_level=0)
    update_run_stats(save_data, is_victory=False, final_trace=60, ascension_level=0)
    assert save_data["stats"]["total_trace_sum"] == 100
    assert save_data["stats"]["total_trace_counted"] == 2


def test_update_run_stats_does_not_mutate_if_victory_false_for_best_ascension() -> None:
    save_data: dict = {"stats": {"best_ascension_cleared": 10}}
    update_run_stats(save_data, is_victory=False, final_trace=50, ascension_level=20)
    # 패배 시에는 best_ascension_cleared 갱신 안 함
    assert save_data["stats"]["best_ascension_cleared"] == 10


def test_get_run_stats_snapshot_calculates_win_rate() -> None:
    stats = {
        "total_runs": 10,
        "total_victories": 4,
        "total_trace_sum": 300,
        "total_trace_counted": 10,
        "best_ascension_cleared": 7,
        "most_seen_ending": "silent_victory",
    }
    snap = get_run_stats_snapshot(stats)
    assert snap["total_runs"] == 10
    assert snap["total_victories"] == 4
    assert snap["win_rate"] == 40.0
    assert snap["avg_trace"] == 30.0
    assert snap["best_ascension_cleared"] == 7
    assert snap["most_seen_ending"] == "silent_victory"


def test_get_run_stats_snapshot_handles_zero_runs() -> None:
    snap = get_run_stats_snapshot({})
    assert snap["win_rate"] == 0.0
    assert snap["avg_trace"] == 0.0
