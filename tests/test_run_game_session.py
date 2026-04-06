"""Integration tests for run_game_session flow."""

from typing import Any

from artifact_system import apply_artifact_effect, get_artifact
from route_map import NodeType

import main


def _scenario(
    node_id: int,
    theme: str,
    difficulty: str = "Easy",
    penalty_rate: int = 10,
    is_boss: bool = False,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "theme": theme,
        "difficulty": difficulty,
        "text_log": f"log-{node_id}",
        "target_keyword": f"kw-{node_id}",
        "penalty_rate": penalty_rate,
        "is_boss": is_boss,
    }


def _combat_pool() -> list[dict[str, Any]]:
    return [
        _scenario(1, "T1", "Easy"),
        _scenario(2, "T2", "Hard"),
        _scenario(3, "T3", "Easy"),
        _scenario(4, "T4", "Hard"),
        _scenario(5, "T5", "Easy"),
        _scenario(6, "T6", "Hard"),
        _scenario(7, "T7", "Easy"),
    ]


def _boss() -> dict[str, Any]:
    return _scenario(999, "BOSS_THEME", "NIGHTMARE", penalty_rate=80, is_boss=True)


def _stub_common(monkeypatch, combat_pool: list[dict[str, Any]], boss: dict[str, Any]) -> None:
    monkeypatch.setattr(main, "load_scenarios", lambda _path: [{"stub": True}])
    monkeypatch.setattr(main, "_select_combat_scenarios", lambda _scenarios, _count: combat_pool)
    monkeypatch.setattr(main, "_select_boss_scenario", lambda _scenarios: boss)
    monkeypatch.setattr(main, "render_route_choice", lambda **_kwargs: None)
    monkeypatch.setattr(main, "_wait_for_enter", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main.Prompt, "ask", lambda *_args, **_kwargs: "A")


def test_run_game_session_victory_on_full_combat_path(monkeypatch) -> None:
    combat_pool = _combat_pool()
    boss = _boss()
    _stub_common(monkeypatch, combat_pool, boss)

    monkeypatch.setattr(
        main,
        "build_route_choices",
        lambda _num: [(NodeType.NORMAL, NodeType.NORMAL)] * 6,
    )
    monkeypatch.setattr(main, "_offer_artifact", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        main,
        "_run_combat_node",
        lambda scenario, position, total_positions, trace_level, node_type, perks, runtime, backtrack_used, run_state, acquired_artifacts, diver_class=None: (
            trace_level,
            backtrack_used,
            "cleared",
            scenario["difficulty"],
        ),
    )

    save_data = {"data_fragments": 0, "perks": {}}
    correct, victory, result, cleared, _stats = main.run_game_session({}, save_data)

    assert correct == 8
    assert victory is True
    assert result == "victory"
    assert cleared == [s["difficulty"] for s in combat_pool] + [boss["difficulty"]]


def test_run_game_session_returns_shutdown_when_combat_death_occurs(monkeypatch) -> None:
    combat_pool = _combat_pool()
    boss = _boss()
    _stub_common(monkeypatch, combat_pool, boss)

    monkeypatch.setattr(
        main,
        "build_route_choices",
        lambda _num: [(NodeType.NORMAL, NodeType.NORMAL)] * 6,
    )
    monkeypatch.setattr(main, "_offer_artifact", lambda *_args, **_kwargs: None)

    call_count = {"n": 0}

    def _fake_combat(
        scenario: dict[str, Any],
        position: int,
        total_positions: int,
        trace_level: int,
        node_type: NodeType,
        perks: dict[str, bool],
        runtime: dict[str, Any],
        backtrack_used: bool,
        run_state: dict[str, Any],
        acquired_artifacts: list[Any],
        diver_class=None,
    ) -> tuple[int, bool, str, str | None]:
        call_count["n"] += 1
        if call_count["n"] == 2:
            return trace_level, backtrack_used, "death", None
        return trace_level, backtrack_used, "cleared", scenario["difficulty"]

    monkeypatch.setattr(main, "_run_combat_node", _fake_combat)

    save_data = {"data_fragments": 0, "perks": {}}
    correct, victory, result, cleared, _stats = main.run_game_session({}, save_data)

    assert correct == 1
    assert victory is False
    assert result == "shutdown"
    assert cleared == [combat_pool[0]["difficulty"]]


def test_run_game_session_follows_rest_and_shop_route(monkeypatch) -> None:
    combat_pool = _combat_pool()
    boss = _boss()
    _stub_common(monkeypatch, combat_pool, boss)

    monkeypatch.setattr(
        main,
        "build_route_choices",
        lambda _num: [
            (NodeType.REST, NodeType.NORMAL),
            (NodeType.SHOP, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
        ],
    )
    monkeypatch.setattr(main, "_offer_artifact", lambda *_args, **_kwargs: None)

    node_types: list[NodeType] = []

    def _fake_combat(
        scenario: dict[str, Any],
        position: int,
        total_positions: int,
        trace_level: int,
        node_type: NodeType,
        perks: dict[str, bool],
        runtime: dict[str, Any],
        backtrack_used: bool,
        run_state: dict[str, Any],
        acquired_artifacts: list[Any],
        diver_class=None,
    ) -> tuple[int, bool, str, str | None]:
        node_types.append(node_type)
        return trace_level, backtrack_used, "cleared", scenario["difficulty"]

    shop_calls = {"n": 0}

    def _fake_mid_shop(
        save_data: dict[str, Any],
        trace_level: int,
        run_state: dict[str, Any],
        runtime: dict[str, Any],
    ) -> int:
        shop_calls["n"] += 1
        return trace_level

    monkeypatch.setattr(main, "_run_combat_node", _fake_combat)
    monkeypatch.setattr(main, "_run_mid_run_shop", _fake_mid_shop)

    save_data = {"data_fragments": 0, "perks": {}}
    correct, victory, result, cleared, _stats = main.run_game_session({}, save_data)

    assert correct == 6
    assert victory is True
    assert result == "victory"
    assert len(cleared) == 6
    assert shop_calls["n"] == 1
    assert node_types == [
        NodeType.NORMAL,
        NodeType.NORMAL,
        NodeType.NORMAL,
        NodeType.NORMAL,
        NodeType.NORMAL,
        NodeType.BOSS,
    ]


def test_run_game_session_applies_data_shard_bonus_after_elite_artifact(monkeypatch) -> None:
    combat_pool = _combat_pool()
    boss = _boss()
    _stub_common(monkeypatch, combat_pool, boss)

    monkeypatch.setattr(
        main,
        "build_route_choices",
        lambda _num: [
            (NodeType.ELITE, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
            (NodeType.NORMAL, NodeType.NORMAL),
        ],
    )
    monkeypatch.setattr(
        main,
        "_run_combat_node",
        lambda scenario, position, total_positions, trace_level, node_type, perks, runtime, backtrack_used, run_state, acquired_artifacts, diver_class=None: (
            trace_level,
            backtrack_used,
            "cleared",
            scenario["difficulty"],
        ),
    )

    data_shard = get_artifact("data_shard_x")
    assert data_shard is not None

    def _fake_offer_artifact(
        acquired_artifacts: list[Any],
        runtime: dict[str, Any],
        run_state: dict[str, Any],
        source: str = "ELITE",
        num_choices: int = 3,
    ) -> None:
        if source == "ELITE":
            apply_artifact_effect(data_shard, runtime, run_state)

    monkeypatch.setattr(main, "_offer_artifact", _fake_offer_artifact)

    save_data = {"data_fragments": 10, "perks": {}}
    correct, victory, result, _cleared, _stats = main.run_game_session({}, save_data)

    assert correct == 8
    assert victory is True
    assert result == "victory"
    # pos1 ELITE에서 획득 후 pos2~boss까지 6회 클리어에 대해 +3씩 획득
    assert save_data["data_fragments"] == 28


def test_run_game_session_uses_multi_phase_boss_on_high_ascension(monkeypatch) -> None:
    combat_pool = _combat_pool()
    boss = _boss()
    _stub_common(monkeypatch, combat_pool, boss)

    monkeypatch.setattr(
        main,
        "build_route_choices",
        lambda _num: [(NodeType.NORMAL, NodeType.NORMAL)] * 6,
    )
    monkeypatch.setattr(main, "_offer_artifact", lambda *_args, **_kwargs: None)

    call_count = {"n": 0}
    boss_phase_indexes: list[int] = []
    boss_phase_mults: list[float] = []
    boss_phase_cat_log_locks: list[int] = []
    boss_phase_skill_locks: list[int] = []
    boss_phase_violation_penalties: list[int] = []
    boss_phase_fake_keyword_counts: list[int] = []

    def _fake_combat(
        scenario: dict[str, Any],
        position: int,
        total_positions: int,
        trace_level: int,
        node_type: NodeType,
        perks: dict[str, bool],
        runtime: dict[str, Any],
        backtrack_used: bool,
        run_state: dict[str, Any],
        acquired_artifacts: list[Any],
        diver_class=None,
    ) -> tuple[int, bool, str, str | None]:
        call_count["n"] += 1
        if node_type == NodeType.BOSS:
            boss_phase_indexes.append(int(runtime.get("boss_phase_index", 0)))
            boss_phase_mults.append(float(runtime.get("ascension_boss_penalty_mult", 1.0)))
            boss_phase_cat_log_locks.append(int(runtime.get("ascension_boss_block_cat_log_from_phase", 0)))
            boss_phase_skill_locks.append(int(runtime.get("ascension_boss_block_skill_from_phase", 0)))
            boss_phase_violation_penalties.append(int(runtime.get("ascension_boss_command_violation_penalty", 0)))
            boss_phase_fake_keyword_counts.append(int(runtime.get("ascension_boss_fake_keyword_count", 0)))
        return trace_level, backtrack_used, "cleared", scenario["difficulty"]

    monkeypatch.setattr(main, "_run_combat_node", _fake_combat)

    save_data = {"data_fragments": 0, "perks": {}}
    correct, victory, result, cleared, _stats = main.run_game_session({}, save_data, ascension_level=20)

    assert correct == 8
    assert victory is True
    assert result == "victory"
    assert len(cleared) == 8
    assert call_count["n"] == 10  # 일반 7회 + 보스 3페이즈
    assert boss_phase_indexes == [1, 2, 3]
    assert boss_phase_mults[0] < boss_phase_mults[1] < boss_phase_mults[2]
    assert boss_phase_cat_log_locks == [2, 2, 2]
    assert boss_phase_skill_locks == [3, 3, 3]
    assert boss_phase_violation_penalties == [4, 4, 4]
    assert boss_phase_fake_keyword_counts == [4, 4, 4]


def test_run_game_session_applies_asc20_boss_phase_scenario_override(monkeypatch) -> None:
    combat_pool = _combat_pool()
    boss = _boss()
    _stub_common(monkeypatch, combat_pool, boss)

    monkeypatch.setattr(
        main,
        "build_route_choices",
        lambda _num: [(NodeType.NORMAL, NodeType.NORMAL)] * 6,
    )
    monkeypatch.setattr(main, "_offer_artifact", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        main,
        "load_boss_phase_pack",
        lambda _path: {
            999: [
                {"text_log": "phase-1-log", "target_keyword": "kw-p1"},
                {"text_log": "phase-2-log", "target_keyword": "kw-p2"},
                {"text_log": "phase-3-log", "target_keyword": "kw-p3"},
            ]
        },
    )

    boss_phase_keywords: list[str] = []

    def _fake_combat(
        scenario: dict[str, Any],
        position: int,
        total_positions: int,
        trace_level: int,
        node_type: NodeType,
        perks: dict[str, bool],
        runtime: dict[str, Any],
        backtrack_used: bool,
        run_state: dict[str, Any],
        acquired_artifacts: list[Any],
        diver_class=None,
    ) -> tuple[int, bool, str, str | None]:
        if node_type == NodeType.BOSS:
            boss_phase_keywords.append(str(scenario.get("target_keyword", "")))
        return trace_level, backtrack_used, "cleared", scenario["difficulty"]

    monkeypatch.setattr(main, "_run_combat_node", _fake_combat)

    save_data = {"data_fragments": 0, "perks": {}}
    correct, victory, result, _cleared, _stats = main.run_game_session({}, save_data, ascension_level=20)

    assert correct == 8
    assert victory is True
    assert result == "victory"
    assert boss_phase_keywords == ["kw-p1", "kw-p2", "kw-p3"]
