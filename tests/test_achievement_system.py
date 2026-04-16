"""Achievement system unit tests (75→100종 업적 커버리지)."""

from achievement_system import (
    ACHIEVEMENTS,
    ACHIEVEMENT_INDEX,
    evaluate_achievements,
    get_achievement_snapshot,
    normalize_achievement_state,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _clean_save(
    *,
    runs: int = 0,
    victories: int = 0,
    points: int = 0,
    class_victories: dict | None = None,
    cleared: bool = False,
    perks: dict | None = None,
    endings_unlocked: list | None = None,
    achievements_unlocked: list | None = None,
) -> dict:
    return {
        "data_fragments": 0,
        "perks": perks or {},
        "achievements": {"unlocked": list(achievements_unlocked or [])},
        "campaign": {
            "runs": runs,
            "victories": victories,
            "points": points,
            "cleared": cleared,
            "ascension_unlocked": 0,
            "class_victories": class_victories or {"ANALYST": 0, "GHOST": 0, "CRACKER": 0},
        },
        "endings": {"unlocked": list(endings_unlocked or [])},
    }


def _run(
    *,
    result: str = "shutdown",
    is_victory: bool = False,
    class_key: str = "ANALYST",
    ascension_level: int = 0,
    wrong_analyzes: int = 0,
    timeout_events: int = 0,
    trace_final: int = 50,
    correct_answers: int = 0,
    cleared_difficulties: list | None = None,
    skill_used: bool = False,
    mystery_engaged: int = 0,
    mystery_good: int = 0,
    mystery_skipped: int = 0,
    artifacts_held: int = 0,
    cascade_triggered: bool = False,
    void_scanner_used: bool = False,
    mystery_frags_gained: int = 0,
) -> dict:
    return {
        "result": result,
        "is_victory": is_victory,
        "class_key": class_key,
        "ascension_level": ascension_level,
        "wrong_analyzes": wrong_analyzes,
        "timeout_events": timeout_events,
        "trace_final": trace_final,
        "correct_answers": correct_answers,
        "cleared_difficulties": cleared_difficulties or [],
        "skill_used": skill_used,
        "mystery_engaged": mystery_engaged,
        "mystery_good": mystery_good,
        "mystery_skipped": mystery_skipped,
        "artifacts_held": artifacts_held,
        "cascade_triggered": cascade_triggered,
        "void_scanner_used": void_scanner_used,
        "mystery_frags_gained": mystery_frags_gained,
    }


# ── 기본 구조 검증 ─────────────────────────────────────────────────────────────

def test_achievements_tuple_has_109_entries() -> None:
    # 100종 + MYSTERY 5종 + endings_8 1종 + artifact 3종 + perk 3종 + v9.4 3종 = 115종
    assert len(ACHIEVEMENTS) == 115


def test_achievement_index_matches_tuple() -> None:
    assert len(ACHIEVEMENT_INDEX) == len(ACHIEVEMENTS)
    for entry in ACHIEVEMENTS:
        assert entry["id"] in ACHIEVEMENT_INDEX
        assert ACHIEVEMENT_INDEX[entry["id"]] is entry


def test_all_achievements_have_required_fields() -> None:
    for entry in ACHIEVEMENTS:
        assert "id" in entry, f"missing id: {entry}"
        assert "title" in entry, f"missing title: {entry}"
        assert "desc" in entry, f"missing desc: {entry}"


def test_no_duplicate_achievement_ids() -> None:
    ids = [e["id"] for e in ACHIEVEMENTS]
    assert len(ids) == len(set(ids))


# ── normalize_achievement_state ───────────────────────────────────────────────

def test_normalize_rejects_unknown_ids() -> None:
    state = normalize_achievement_state({"unlocked": ["nonexistent_id", "first_shutdown"]})
    assert state["unlocked"] == ["first_shutdown"]


def test_normalize_deduplicates_ids() -> None:
    state = normalize_achievement_state(
        {"unlocked": ["first_shutdown", "first_shutdown", "first_breach"]}
    )
    assert state["unlocked"] == ["first_shutdown", "first_breach"]


def test_normalize_handles_bad_input() -> None:
    assert normalize_achievement_state(None) == {"unlocked": []}
    assert normalize_achievement_state("bad") == {"unlocked": []}
    assert normalize_achievement_state({"unlocked": 42}) == {"unlocked": []}


# ── get_achievement_snapshot ──────────────────────────────────────────────────

def test_snapshot_counts_match() -> None:
    save = _clean_save(achievements_unlocked=["first_shutdown", "first_breach"])
    snap = get_achievement_snapshot(save["achievements"])
    assert snap["unlocked_count"] == 2
    assert snap["total_count"] == 115
    assert snap["unlocked_ids"] == ["first_shutdown", "first_breach"]


# ── evaluate_achievements: 런 결과 기반 ──────────────────────────────────────

def test_first_shutdown_on_shutdown_result() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(result="shutdown"))
    ids = [a["id"] for a in newly]
    assert "first_shutdown" in ids


def test_first_breach_on_victory() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(result="victory", is_victory=True))
    ids = [a["id"] for a in newly]
    assert "first_breach" in ids


def test_class_first_victory_analyst() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(is_victory=True, class_key="ANALYST"))
    ids = [a["id"] for a in newly]
    assert "analyst_victory" in ids
    assert "ghost_victory" not in ids
    assert "cracker_victory" not in ids


def test_perfect_infiltration_requires_zero_errors() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, wrong_analyzes=0, timeout_events=0)
    )
    ids = [a["id"] for a in newly]
    assert "perfect_infiltration" in ids

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, wrong_analyzes=1, timeout_events=0)
    )
    ids2 = [a["id"] for a in newly2]
    assert "perfect_infiltration" not in ids2


def test_perfect_analyst_requires_analyst_class() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, class_key="GHOST", wrong_analyzes=0, timeout_events=0)
    )
    ids = [a["id"] for a in newly]
    assert "perfect_analyst" not in ids
    assert "perfect_ghost" in ids


def test_perfect_cracker_unlocks_on_cracker_no_errors() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, class_key="CRACKER", wrong_analyzes=0, timeout_events=0)
    )
    ids = [a["id"] for a in newly]
    assert "perfect_cracker" in ids


def test_zero_trace_win() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(is_victory=True, trace_final=0))
    ids = [a["id"] for a in newly]
    assert "zero_trace_win" in ids


def test_analyst_zero_trace_requires_analyst_and_trace_zero() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, class_key="ANALYST", trace_final=0)
    )
    ids = [a["id"] for a in newly]
    assert "analyst_zero_trace" in ids

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, class_key="GHOST", trace_final=0)
    )
    ids2 = [a["id"] for a in newly2]
    assert "analyst_zero_trace" not in ids2


def test_no_perk_win_requires_empty_perks() -> None:
    save_no_perk = _clean_save(perks={})
    newly = evaluate_achievements(save_no_perk, _run(is_victory=True))
    assert "no_perk_win" in [a["id"] for a in newly]

    save_with_perk = _clean_save(perks={"penalty_reduction": True})
    newly2 = evaluate_achievements(save_with_perk, _run(is_victory=True))
    assert "no_perk_win" not in [a["id"] for a in newly2]


def test_no_skill_win_requires_skill_not_used() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(is_victory=True, skill_used=False))
    assert "no_skill_win" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(save2, _run(is_victory=True, skill_used=True))
    assert "no_skill_win" not in [a["id"] for a in newly2]


def test_all_nodes_correct_requires_8_correct_and_no_wrong() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, correct_answers=8, wrong_analyzes=0)
    )
    assert "all_nodes_correct" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, correct_answers=8, wrong_analyzes=1)
    )
    assert "all_nodes_correct" not in [a["id"] for a in newly2]


def test_nightmare_clear_requires_nightmare_difficulty_in_run() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save,
        _run(is_victory=True, cleared_difficulties=["Easy", "Hard", "NIGHTMARE"]),
    )
    assert "nightmare_clear" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, cleared_difficulties=["Easy", "Hard"])
    )
    assert "nightmare_clear" not in [a["id"] for a in newly2]


def test_ascension_milestones() -> None:
    for asc, expected_id in [
        (3, "ascension_3"), (5, "ascension_5"), (7, "ascension_7"),
        (10, "ascension_10"), (12, "ascension_12"), (15, "ascension_15"),
        (17, "ascension_17"), (20, "ascension_20"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(save, _run(is_victory=True, ascension_level=asc))
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked at asc {asc}"


def test_ascension_20_class_specific() -> None:
    for class_key, expected_id in [
        ("ANALYST", "ascension_20_analyst"),
        ("GHOST", "ascension_20_ghost"),
        ("CRACKER", "ascension_20_cracker"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(
            save, _run(is_victory=True, class_key=class_key, ascension_level=20)
        )
        ids = [a["id"] for a in newly]
        assert expected_id in ids
        other_class_ids = {
            "ascension_20_analyst", "ascension_20_ghost", "ascension_20_cracker"
        } - {expected_id}
        for other in other_class_ids:
            assert other not in ids


def test_asc20_trinity_requires_all_three_class_asc20() -> None:
    save = _clean_save(
        achievements_unlocked=["ascension_20_analyst", "ascension_20_ghost"]
    )
    newly = evaluate_achievements(
        save, _run(is_victory=True, class_key="CRACKER", ascension_level=20)
    )
    ids = [a["id"] for a in newly]
    assert "asc20_trinity" in ids


def test_asc20_no_perk_requires_no_perks_at_asc20() -> None:
    save = _clean_save(perks={})
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=20)
    )
    assert "asc20_no_perk" in [a["id"] for a in newly]

    save2 = _clean_save(perks={"time_extension": True})
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, ascension_level=20)
    )
    assert "asc20_no_perk" not in [a["id"] for a in newly2]


# ── evaluate_achievements: 캠페인 누적 기반 ──────────────────────────────────

def test_run_milestones() -> None:
    for run_count, expected_id in [
        (10, "runs_10"), (25, "runs_25"), (50, "runs_50"),
        (100, "runs_100"), (200, "runs_200"), (300, "runs_300"), (500, "runs_500"),
    ]:
        save = _clean_save(runs=run_count)
        newly = evaluate_achievements(save)
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked at {run_count} runs"


def test_victory_milestones() -> None:
    for v_count, expected_id in [
        (5, "victories_5"), (25, "victories_25"),
        (50, "victories_50"), (100, "victories_100"),
        (200, "victories_200"), (500, "victories_500"),
    ]:
        save = _clean_save(victories=v_count)
        newly = evaluate_achievements(save)
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked at {v_count} victories"


def test_points_milestones() -> None:
    for pts, expected_id in [
        (10000, "campaign_points_10000"),
        (30000, "campaign_points_30000"),
        (50000, "campaign_points_50000"),
        (100000, "campaign_points_100000"),
        (200000, "campaign_points_200000"),
        (500000, "campaign_points_500000"),
    ]:
        save = _clean_save(points=pts)
        newly = evaluate_achievements(save)
        assert expected_id in [a["id"] for a in newly], f"{expected_id} not at {pts}"


def test_class_master_5_victories() -> None:
    for class_key, expected_id in [
        ("ANALYST", "analyst_master"),
        ("GHOST", "ghost_master"),
        ("CRACKER", "cracker_master"),
    ]:
        save = _clean_save(
            class_victories={"ANALYST": 0, "GHOST": 0, "CRACKER": 0, class_key: 5}
        )
        newly = evaluate_achievements(save)
        assert expected_id in [a["id"] for a in newly]


def test_triple_master_requires_all_classes_5() -> None:
    save = _clean_save(
        class_victories={"ANALYST": 5, "GHOST": 5, "CRACKER": 5}
    )
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "triple_master" in ids


def test_class_10_victories() -> None:
    for class_key, expected_id in [
        ("ANALYST", "analyst_10"),
        ("GHOST", "ghost_10"),
        ("CRACKER", "cracker_10"),
    ]:
        save = _clean_save(
            class_victories={"ANALYST": 0, "GHOST": 0, "CRACKER": 0, class_key: 10}
        )
        newly = evaluate_achievements(save)
        assert expected_id in [a["id"] for a in newly]


def test_triple_10_requires_all_classes_10() -> None:
    save = _clean_save(
        class_victories={"ANALYST": 10, "GHOST": 10, "CRACKER": 10}
    )
    newly = evaluate_achievements(save)
    assert "triple_10" in [a["id"] for a in newly]


def test_class_trinity_requires_at_least_1_each() -> None:
    save = _clean_save(
        class_victories={"ANALYST": 1, "GHOST": 1, "CRACKER": 1}
    )
    newly = evaluate_achievements(save)
    assert "class_trinity" in [a["id"] for a in newly]

    save2 = _clean_save(
        class_victories={"ANALYST": 1, "GHOST": 0, "CRACKER": 1}
    )
    newly2 = evaluate_achievements(save2)
    assert "class_trinity" not in [a["id"] for a in newly2]


def test_endings_milestones() -> None:
    # 3종: endings_3 해금, endings_8/all_endings 미해금
    save = _clean_save(endings_unlocked=["e1", "e2", "e3"])
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "endings_3" in ids
    assert "endings_8" not in ids
    assert "all_endings" not in ids

    # 8종: endings_3 + endings_8 해금, all_endings 미해금
    save2 = _clean_save(endings_unlocked=[f"e{i}" for i in range(1, 9)])
    newly2 = evaluate_achievements(save2)
    ids2 = [a["id"] for a in newly2]
    assert "endings_3" in ids2
    assert "endings_8" in ids2
    assert "all_endings" not in ids2

    # 11종: 전체 해금
    save3 = _clean_save(endings_unlocked=[f"e{i}" for i in range(1, 12)])
    newly3 = evaluate_achievements(save3)
    ids3 = [a["id"] for a in newly3]
    assert "endings_8" in ids3
    assert "all_endings" in ids3


def test_campaign_clear_unlocks_achievement() -> None:
    save = _clean_save(cleared=True)
    newly = evaluate_achievements(save)
    assert "campaign_clear" in [a["id"] for a in newly]


# ── 중복 해금 방지 ────────────────────────────────────────────────────────────

def test_already_unlocked_achievement_not_returned_again() -> None:
    save = _clean_save(achievements_unlocked=["first_shutdown"])
    newly = evaluate_achievements(save, _run(result="shutdown"))
    assert "first_shutdown" not in [a["id"] for a in newly]


def test_save_data_achievements_updated_in_place() -> None:
    save = _clean_save()
    evaluate_achievements(save, _run(result="shutdown"))
    assert "first_shutdown" in save["achievements"]["unlocked"]


# ── 신규 업적 (105종 확장) ────────────────────────────────────────────────────

def test_achievements_tuple_has_109_entries_v2() -> None:
    assert len(ACHIEVEMENTS) == 115


def test_victories_10_milestone() -> None:
    save = _clean_save(victories=10)
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "victories_10" in ids
    assert "victories_5" in ids
    assert "victories_25" not in ids


def test_perfect_asc5_requires_no_errors_and_asc5() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=5, wrong_analyzes=0, timeout_events=0)
    )
    assert "perfect_asc5" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, ascension_level=4, wrong_analyzes=0, timeout_events=0)
    )
    assert "perfect_asc5" not in [a["id"] for a in newly2]


def test_perfect_asc10_requires_asc10_and_no_errors() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=10, wrong_analyzes=0, timeout_events=0)
    )
    ids = [a["id"] for a in newly]
    assert "perfect_asc10" in ids
    assert "perfect_asc5" in ids


def test_perfect_class_asc10_unlocks_by_class() -> None:
    for class_key, expected_id in [
        ("ANALYST", "perfect_analyst_asc10"),
        ("GHOST", "perfect_ghost_asc10"),
        ("CRACKER", "perfect_cracker_asc10"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(
            save,
            _run(
                is_victory=True,
                class_key=class_key,
                ascension_level=10,
                wrong_analyzes=0,
                timeout_events=0,
            ),
        )
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked for {class_key}"


def test_no_skill_asc10_requires_both_conditions() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=10, skill_used=False)
    )
    assert "no_skill_asc10" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, ascension_level=9, skill_used=False)
    )
    assert "no_skill_asc10" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, ascension_level=10, skill_used=True)
    )
    assert "no_skill_asc10" not in [a["id"] for a in newly3]


def test_ghost_no_timeout_requires_ghost_and_zero_timeout() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, class_key="GHOST", timeout_events=0)
    )
    assert "ghost_no_timeout" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, class_key="GHOST", timeout_events=1)
    )
    assert "ghost_no_timeout" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, class_key="ANALYST", timeout_events=0)
    )
    assert "ghost_no_timeout" not in [a["id"] for a in newly3]


def test_cracker_nightmare_requires_cracker_and_nightmare_difficulty() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save,
        _run(
            is_victory=True,
            class_key="CRACKER",
            cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
        ),
    )
    assert "cracker_nightmare" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2,
        _run(
            is_victory=True,
            class_key="ANALYST",
            cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
        ),
    )
    assert "cracker_nightmare" not in [a["id"] for a in newly2]


def test_class_asc15_unlocks_by_class() -> None:
    for class_key, expected_id in [
        ("ANALYST", "analyst_asc15"),
        ("GHOST", "ghost_asc15"),
        ("CRACKER", "cracker_asc15"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(
            save, _run(is_victory=True, class_key=class_key, ascension_level=15)
        )
        assert expected_id in [a["id"] for a in newly]


def test_endings_1_on_first_ending() -> None:
    save = _clean_save(endings_unlocked=["ending_a"])
    newly = evaluate_achievements(save)
    assert "endings_1" in [a["id"] for a in newly]
    assert "endings_3" not in [a["id"] for a in newly]


def test_endings_8_requires_8_distinct_endings() -> None:
    # 7종은 미해금
    save7 = _clean_save(endings_unlocked=[f"e{i}" for i in range(1, 8)])
    ids7 = [a["id"] for a in evaluate_achievements(save7)]
    assert "endings_8" not in ids7

    # 8종이면 해금
    save8 = _clean_save(endings_unlocked=[f"e{i}" for i in range(1, 9)])
    ids8 = [a["id"] for a in evaluate_achievements(save8)]
    assert "endings_8" in ids8
    assert "all_endings" not in ids8  # 11종 미달


def test_all_endings_requires_11_distinct_endings() -> None:
    # 10종은 미해금
    save10 = _clean_save(endings_unlocked=[f"e{i}" for i in range(1, 11)])
    ids10 = [a["id"] for a in evaluate_achievements(save10)]
    assert "all_endings" not in ids10

    # 11종이면 해금
    save11 = _clean_save(endings_unlocked=[f"e{i}" for i in range(1, 12)])
    ids11 = [a["id"] for a in evaluate_achievements(save11)]
    assert "all_endings" in ids11


def test_perk_first_on_any_perk_unlocked() -> None:
    save = _clean_save(perks={"penalty_reduction": True})
    newly = evaluate_achievements(save)
    assert "perk_first" in [a["id"] for a in newly]

    save2 = _clean_save(perks={})
    newly2 = evaluate_achievements(save2)
    assert "perk_first" not in [a["id"] for a in newly2]


def test_ascension_unlocked_milestones() -> None:
    save = _clean_save()
    save["campaign"]["ascension_unlocked"] = 15
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "ascension_unlocked_5" in ids
    assert "ascension_unlocked_10" in ids
    assert "ascension_unlocked_15" in ids
    assert "ascension_unlocked_20" not in ids

    save2 = _clean_save()
    save2["campaign"]["ascension_unlocked"] = 20
    newly2 = evaluate_achievements(save2)
    ids2 = [a["id"] for a in newly2]
    assert "ascension_unlocked_20" in ids2


def test_data_fragments_milestones() -> None:
    save = _clean_save()
    save["data_fragments"] = 500
    newly = evaluate_achievements(save)
    assert "data_fragments_500" in [a["id"] for a in newly]
    assert "data_fragments_2000" not in [a["id"] for a in newly]

    save2 = _clean_save()
    save2["data_fragments"] = 2000
    newly2 = evaluate_achievements(save2)
    ids2 = [a["id"] for a in newly2]
    assert "data_fragments_500" in ids2
    assert "data_fragments_2000" in ids2

    save3 = _clean_save()
    save3["data_fragments"] = 10000
    newly3 = evaluate_achievements(save3)
    ids3 = [a["id"] for a in newly3]
    assert "data_fragments_5000" in ids3
    assert "data_fragments_10000" in ids3


# ── 신규 업적 v2.0 (25종) ────────────────────────────────────────────────────

def test_runs_300_500_milestones() -> None:
    save = _clean_save(runs=300)
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "runs_300" in ids
    assert "runs_500" not in ids

    save2 = _clean_save(runs=500)
    newly2 = evaluate_achievements(save2)
    assert "runs_500" in [a["id"] for a in newly2]


def test_victories_200_500_milestones() -> None:
    save = _clean_save(victories=200)
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "victories_200" in ids
    assert "victories_500" not in ids

    save2 = _clean_save(victories=500)
    newly2 = evaluate_achievements(save2)
    assert "victories_500" in [a["id"] for a in newly2]


def test_perfect_asc15_requires_asc15_and_no_errors() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=15, wrong_analyzes=0, timeout_events=0)
    )
    ids = [a["id"] for a in newly]
    assert "perfect_asc15" in ids

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, ascension_level=14, wrong_analyzes=0, timeout_events=0)
    )
    assert "perfect_asc15" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, ascension_level=15, wrong_analyzes=1, timeout_events=0)
    )
    assert "perfect_asc15" not in [a["id"] for a in newly3]


def test_no_skill_perfect_requires_no_skill_and_no_wrong() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, skill_used=False, wrong_analyzes=0)
    )
    assert "no_skill_perfect" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, skill_used=True, wrong_analyzes=0)
    )
    assert "no_skill_perfect" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, skill_used=False, wrong_analyzes=1)
    )
    assert "no_skill_perfect" not in [a["id"] for a in newly3]


def test_ghost_trace_zero_and_cracker_trace_zero() -> None:
    for class_key, expected_id in [
        ("GHOST", "ghost_trace_zero"),
        ("CRACKER", "cracker_trace_zero"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(
            save, _run(is_victory=True, class_key=class_key, trace_final=0)
        )
        assert expected_id in [a["id"] for a in newly]

    # ANALYST로는 해당 없음
    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, class_key="ANALYST", trace_final=0)
    )
    ids2 = [a["id"] for a in newly2]
    assert "ghost_trace_zero" not in ids2
    assert "cracker_trace_zero" not in ids2


def test_no_timeout_asc15_requires_asc15_and_zero_timeout() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=15, timeout_events=0)
    )
    assert "no_timeout_asc15" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, ascension_level=14, timeout_events=0)
    )
    assert "no_timeout_asc15" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, ascension_level=15, timeout_events=1)
    )
    assert "no_timeout_asc15" not in [a["id"] for a in newly3]


def test_survivor_requires_3_wrong_and_victory() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, wrong_analyzes=3)
    )
    assert "survivor" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, wrong_analyzes=2)
    )
    assert "survivor" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=False, wrong_analyzes=5)
    )
    assert "survivor" not in [a["id"] for a in newly3]


def test_analyst_nightmare_and_ghost_nightmare() -> None:
    for class_key, expected_id in [
        ("ANALYST", "analyst_nightmare"),
        ("GHOST", "ghost_nightmare"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(
            save,
            _run(
                is_victory=True,
                class_key=class_key,
                cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
            ),
        )
        assert expected_id in [a["id"] for a in newly]

    # CRACKER는 cracker_nightmare만 해당 (analyst/ghost_nightmare 아님)
    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2,
        _run(
            is_victory=True,
            class_key="CRACKER",
            cleared_difficulties=["Easy", "Hard", "NIGHTMARE"],
        ),
    )
    ids2 = [a["id"] for a in newly2]
    assert "analyst_nightmare" not in ids2
    assert "ghost_nightmare" not in ids2


def test_perfect_class_asc20_by_class() -> None:
    for class_key, expected_id in [
        ("ANALYST", "perfect_analyst_asc20"),
        ("GHOST", "perfect_ghost_asc20"),
        ("CRACKER", "perfect_cracker_asc20"),
    ]:
        save = _clean_save()
        newly = evaluate_achievements(
            save,
            _run(
                is_victory=True,
                class_key=class_key,
                ascension_level=20,
                wrong_analyzes=0,
                timeout_events=0,
            ),
        )
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked for {class_key}"


def test_ghost_asc20_no_timeout() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, class_key="GHOST", ascension_level=20, timeout_events=0)
    )
    assert "ghost_asc20_no_timeout" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, class_key="GHOST", ascension_level=19, timeout_events=0)
    )
    assert "ghost_asc20_no_timeout" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, class_key="GHOST", ascension_level=20, timeout_events=1)
    )
    assert "ghost_asc20_no_timeout" not in [a["id"] for a in newly3]


def test_no_skill_asc20_requires_asc20_and_no_skill() -> None:
    save = _clean_save()
    newly = evaluate_achievements(
        save, _run(is_victory=True, ascension_level=20, skill_used=False)
    )
    assert "no_skill_asc20" in [a["id"] for a in newly]

    save2 = _clean_save()
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, ascension_level=20, skill_used=True)
    )
    assert "no_skill_asc20" not in [a["id"] for a in newly2]

    save3 = _clean_save()
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, ascension_level=19, skill_used=False)
    )
    assert "no_skill_asc20" not in [a["id"] for a in newly3]


def test_no_skill_no_perk_requires_both_conditions() -> None:
    save = _clean_save(perks={})
    newly = evaluate_achievements(
        save, _run(is_victory=True, skill_used=False)
    )
    assert "no_skill_no_perk" in [a["id"] for a in newly]

    save2 = _clean_save(perks={"penalty_reduction": True})
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, skill_used=False)
    )
    assert "no_skill_no_perk" not in [a["id"] for a in newly2]

    save3 = _clean_save(perks={})
    newly3 = evaluate_achievements(
        save3, _run(is_victory=True, skill_used=True)
    )
    assert "no_skill_no_perk" not in [a["id"] for a in newly3]


def test_class_no_perk_by_class() -> None:
    for class_key, expected_id in [
        ("ANALYST", "analyst_no_perk"),
        ("GHOST", "ghost_no_perk"),
        ("CRACKER", "cracker_no_perk"),
    ]:
        save = _clean_save(perks={})
        newly = evaluate_achievements(
            save, _run(is_victory=True, class_key=class_key)
        )
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked for {class_key}"

    # 퍼크가 있으면 해당 없음
    save2 = _clean_save(perks={"time_extension": True})
    newly2 = evaluate_achievements(
        save2, _run(is_victory=True, class_key="ANALYST")
    )
    assert "analyst_no_perk" not in [a["id"] for a in newly2]


def test_data_fragments_5000_10000() -> None:
    save = _clean_save()
    save["data_fragments"] = 5000
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "data_fragments_5000" in ids
    assert "data_fragments_10000" not in ids

    save2 = _clean_save()
    save2["data_fragments"] = 10000
    newly2 = evaluate_achievements(save2)
    ids2 = [a["id"] for a in newly2]
    assert "data_fragments_5000" in ids2
    assert "data_fragments_10000" in ids2


def test_campaign_points_200000_500000() -> None:
    save = _clean_save(points=200000)
    newly = evaluate_achievements(save)
    ids = [a["id"] for a in newly]
    assert "campaign_points_200000" in ids
    assert "campaign_points_500000" not in ids

    save2 = _clean_save(points=500000)
    newly2 = evaluate_achievements(save2)
    assert "campaign_points_500000" in [a["id"] for a in newly2]


# ── MYSTERY 노드 업적 (105종 확장) ────────────────────────────────────────────

def test_mystery_new_achievements_present() -> None:
    mystery_ids = {
        "mystery_first_engage", "mystery_good_5", "mystery_engaged_20",
        "mystery_all_good_run", "mystery_all_skip_run",
    }
    all_ids = {a["id"] for a in ACHIEVEMENTS}
    assert mystery_ids.issubset(all_ids)


def test_mystery_first_engage_unlocks_on_first_engagement() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_engaged=1))
    ids = [a["id"] for a in newly]
    assert "mystery_first_engage" in ids


def test_mystery_first_engage_not_unlocked_on_skip_only() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_skipped=3))
    ids = [a["id"] for a in newly]
    assert "mystery_first_engage" not in ids


def test_mystery_good_5_requires_cumulative_5_good() -> None:
    save = _clean_save()
    # 4회 좋은 결과 → 미달
    evaluate_achievements(save, _run(mystery_engaged=4, mystery_good=4))
    newly2 = evaluate_achievements(save, _run(mystery_engaged=1, mystery_good=1))
    ids2 = [a["id"] for a in newly2]
    assert "mystery_good_5" in ids2


def test_mystery_good_5_not_unlocked_below_5() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_engaged=4, mystery_good=4))
    ids = [a["id"] for a in newly]
    assert "mystery_good_5" not in ids


def test_mystery_engaged_20_cumulative() -> None:
    save = _clean_save()
    # 3회 × 5 = 15회 — 미달
    for _ in range(3):
        evaluate_achievements(save, _run(mystery_engaged=5))
    ids_mid = [a["id"] for a in evaluate_achievements(save, _run(mystery_engaged=0))]
    assert "mystery_engaged_20" not in ids_mid
    # 5회 추가 → 총 20회 달성
    newly = evaluate_achievements(save, _run(mystery_engaged=5))
    ids = [a["id"] for a in newly]
    assert "mystery_engaged_20" in ids


def test_mystery_all_good_run_requires_min_2_engagements() -> None:
    save = _clean_save()
    # 1회 개입, 1회 성공 → 조건 미달 (최소 2회 필요)
    newly = evaluate_achievements(save, _run(mystery_engaged=1, mystery_good=1))
    ids = [a["id"] for a in newly]
    assert "mystery_all_good_run" not in ids


def test_mystery_all_good_run_unlocks_when_all_good() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_engaged=3, mystery_good=3))
    ids = [a["id"] for a in newly]
    assert "mystery_all_good_run" in ids


def test_mystery_all_good_run_not_unlocked_if_any_bad() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_engaged=3, mystery_good=2))
    ids = [a["id"] for a in newly]
    assert "mystery_all_good_run" not in ids


def test_mystery_all_skip_run_requires_min_2_skips() -> None:
    save = _clean_save()
    # 1회 스킵 → 조건 미달
    newly = evaluate_achievements(save, _run(mystery_skipped=1))
    ids = [a["id"] for a in newly]
    assert "mystery_all_skip_run" not in ids


def test_mystery_all_skip_run_unlocks_when_all_skipped() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_skipped=3))
    ids = [a["id"] for a in newly]
    assert "mystery_all_skip_run" in ids


def test_mystery_all_skip_run_not_unlocked_if_any_engaged() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(mystery_skipped=2, mystery_engaged=1))
    ids = [a["id"] for a in newly]
    assert "mystery_all_skip_run" not in ids


# ── 아티팩트 업적 (3종) ────────────────────────────────────────────────────────

def test_artifact_new_achievements_present() -> None:
    for aid in ("artifact_first_win", "artifact_hoarder", "artifact_zealot"):
        assert aid in ACHIEVEMENT_INDEX, f"{aid} 누락"


def test_artifact_first_win_unlocks_on_victory_with_artifact() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(is_victory=True, artifacts_held=1))
    assert "artifact_first_win" in [a["id"] for a in newly]


def test_artifact_first_win_not_unlocked_on_defeat() -> None:
    save = _clean_save()
    newly = evaluate_achievements(save, _run(is_victory=False, artifacts_held=2))
    assert "artifact_first_win" not in [a["id"] for a in newly]


def test_artifact_hoarder_requires_3_or_more() -> None:
    save2 = _clean_save()
    ids2 = [a["id"] for a in evaluate_achievements(save2, _run(is_victory=True, artifacts_held=2))]
    assert "artifact_hoarder" not in ids2

    save3 = _clean_save()
    ids3 = [a["id"] for a in evaluate_achievements(save3, _run(is_victory=True, artifacts_held=3))]
    assert "artifact_hoarder" in ids3


def test_artifact_zealot_requires_5_or_more() -> None:
    save4 = _clean_save()
    ids4 = [a["id"] for a in evaluate_achievements(save4, _run(is_victory=True, artifacts_held=4))]
    assert "artifact_zealot" not in ids4

    save5 = _clean_save()
    ids5 = [a["id"] for a in evaluate_achievements(save5, _run(is_victory=True, artifacts_held=5))]
    assert "artifact_zealot" in ids5
    assert "artifact_hoarder" in ids5  # 5종이면 3종 조건도 충족
    assert "artifact_first_win" in ids5  # 5종이면 1종 조건도 충족


# ── v9.1 퍼크 업적 ────────────────────────────────────────────────────────────

def test_perk_v91_achievements_present() -> None:
    """v9.1 신규 퍼크 업적 3종이 ACHIEVEMENTS 튜플에 존재하는지 검증."""
    ids = {a["id"] for a in ACHIEVEMENTS}
    assert "perk_hoarder_5" in ids
    assert "perk_hoarder_10" in ids
    assert "swift_first_win" in ids


def test_perk_hoarder_5_requires_5_perks() -> None:
    save4 = _clean_save(perks={"penalty_reduction": True, "time_extension": True,
                                "glitch_filter": True, "backtrack_protocol": True})
    ids4 = [a["id"] for a in evaluate_achievements(save4)]
    assert "perk_hoarder_5" not in ids4

    save5 = _clean_save(perks={"penalty_reduction": True, "time_extension": True,
                                "glitch_filter": True, "backtrack_protocol": True,
                                "lexical_assist": True})
    ids5 = [a["id"] for a in evaluate_achievements(save5)]
    assert "perk_hoarder_5" in ids5


def test_perk_hoarder_10_requires_10_perks() -> None:
    perks9 = {f"perk_{i}": True for i in range(9)}
    save9 = _clean_save(perks=perks9)
    ids9 = [a["id"] for a in evaluate_achievements(save9)]
    assert "perk_hoarder_10" not in ids9

    perks10 = {f"perk_{i}": True for i in range(10)}
    save10 = _clean_save(perks=perks10)
    ids10 = [a["id"] for a in evaluate_achievements(save10)]
    assert "perk_hoarder_10" in ids10
    assert "perk_hoarder_5" in ids10  # 10종이면 5종 조건도 충족


def test_swift_first_win_requires_perk_and_victory() -> None:
    # 퍼크 없이 승리 → 미해금
    save_no_perk = _clean_save(perks={"swift_analysis": False})
    ids_no = [a["id"] for a in evaluate_achievements(save_no_perk, _run(is_victory=True))]
    assert "swift_first_win" not in ids_no

    # 퍼크 있어도 패배 → 미해금
    save_perk = _clean_save(perks={"swift_analysis": True})
    ids_defeat = [a["id"] for a in evaluate_achievements(save_perk, _run(is_victory=False))]
    assert "swift_first_win" not in ids_defeat

    # 퍼크 + 승리 → 해금
    save_win = _clean_save(perks={"swift_analysis": True})
    ids_win = [a["id"] for a in evaluate_achievements(save_win, _run(is_victory=True))]
    assert "swift_first_win" in ids_win


# ── v9.4 특수 아티팩트 업적 ──────────────────────────────────────────────────

def test_v94_achievements_present() -> None:
    """v9.4 신규 업적 3종이 ACHIEVEMENTS 튜플에 존재하는지 검증."""
    ids = {a["id"] for a in ACHIEVEMENTS}
    assert "cascade_master" in ids
    assert "void_hunter" in ids
    assert "mystery_rich" in ids


def test_cascade_master_requires_cascade_triggered_and_victory() -> None:
    # 발동 없이 승리 → 미해금
    save = _clean_save()
    ids = [a["id"] for a in evaluate_achievements(save, _run(is_victory=True, cascade_triggered=False))]
    assert "cascade_master" not in ids

    # 발동 + 승리 → 해금
    save2 = _clean_save()
    ids2 = [a["id"] for a in evaluate_achievements(save2, _run(is_victory=True, cascade_triggered=True))]
    assert "cascade_master" in ids2


def test_void_hunter_requires_void_scanner_used_and_victory() -> None:
    # 미사용 → 미해금
    save = _clean_save()
    ids = [a["id"] for a in evaluate_achievements(save, _run(is_victory=True, void_scanner_used=False))]
    assert "void_hunter" not in ids

    # 사용 + 승리 → 해금
    save2 = _clean_save()
    ids2 = [a["id"] for a in evaluate_achievements(save2, _run(is_victory=True, void_scanner_used=True))]
    assert "void_hunter" in ids2


def test_mystery_rich_requires_300_frags_and_victory() -> None:
    # 299 → 미해금
    save = _clean_save()
    ids = [a["id"] for a in evaluate_achievements(save, _run(is_victory=True, mystery_frags_gained=299))]
    assert "mystery_rich" not in ids

    # 300 + 승리 → 해금
    save2 = _clean_save()
    ids2 = [a["id"] for a in evaluate_achievements(save2, _run(is_victory=True, mystery_frags_gained=300))]
    assert "mystery_rich" in ids2
