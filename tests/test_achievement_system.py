"""Achievement system unit tests."""

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
    }


# ── 기본 구조 검증 ─────────────────────────────────────────────────────────────

def test_achievements_tuple_has_55_entries() -> None:
    assert len(ACHIEVEMENTS) == 55


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
    assert snap["total_count"] == 55
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
        (100, "runs_100"), (200, "runs_200"),
    ]:
        save = _clean_save(runs=run_count)
        newly = evaluate_achievements(save)
        ids = [a["id"] for a in newly]
        assert expected_id in ids, f"{expected_id} not unlocked at {run_count} runs"


def test_victory_milestones() -> None:
    for v_count, expected_id in [
        (5, "victories_5"), (25, "victories_25"),
        (50, "victories_50"), (100, "victories_100"),
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
    save = _clean_save(endings_unlocked=["ending_a", "ending_b", "ending_c"])
    newly = evaluate_achievements(save)
    assert "endings_3" in [a["id"] for a in newly]
    assert "all_endings" not in [a["id"] for a in newly]

    save2 = _clean_save(
        endings_unlocked=["ending_a", "ending_b", "ending_c", "ending_d", "ending_e"]
    )
    newly2 = evaluate_achievements(save2)
    ids2 = [a["id"] for a in newly2]
    assert "endings_3" in ids2
    assert "all_endings" in ids2


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
