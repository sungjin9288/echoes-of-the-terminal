"""E2E 스모크 테스트 — 로비 정산 파이프라인 전체 검증.

테스트 범위:
  1. 완전 승리 런 후 정산 (보상·캠페인·통계·엔딩·업적 순서)
  2. 완전 패배 런 후 정산 (shutdown 경로)
  3. run_lobby_loop 단일 턴 — 게임 시작 → 정산 → 종료 (Prompt 시퀀스 모킹)
"""

import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import lobby
import run_loops
from diver_class import DiverClass
from progression_system import (
    DEFAULT_SAVE_DATA,
    _normalize_save_data,
    calculate_reward,
    get_run_stats_snapshot,
    update_campaign_progress,
    update_run_stats,
)
from route_map import NodeType


# ── 공통 픽스처 ──────────────────────────────────────────────────────────────────

def _fresh_save() -> dict[str, Any]:
    """테스트용 초기 세이브 데이터를 반환한다."""
    save = deepcopy(DEFAULT_SAVE_DATA)
    save["tutorial_completed"] = True
    return save


def _combat_pool() -> list[dict[str, Any]]:
    return [
        {
            "node_id": i,
            "theme": f"T{i}",
            "difficulty": "Easy",
            "text_log": f"log-{i}",
            "target_keyword": f"kw{i}",
            "penalty_rate": 10,
            "is_boss": False,
        }
        for i in range(1, 8)
    ]


def _boss() -> dict[str, Any]:
    return {
        "node_id": 999,
        "theme": "BOSS_THEME",
        "difficulty": "NIGHTMARE",
        "text_log": "boss-log",
        "target_keyword": "boss_kw",
        "penalty_rate": 80,
        "is_boss": True,
    }


def _stub_run_loops(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_loops의 I/O 의존성을 전부 무효화한다."""
    monkeypatch.setattr(run_loops, "load_scenarios", lambda _path: [{"stub": True}])
    monkeypatch.setattr(
        run_loops,
        "_select_combat_scenarios",
        lambda _scenarios, _count: _combat_pool(),
    )
    monkeypatch.setattr(
        run_loops,
        "_select_boss_scenario",
        lambda _scenarios: _boss(),
    )
    monkeypatch.setattr(
        run_loops,
        "build_route_choices",
        lambda _num: [(NodeType.NORMAL, NodeType.NORMAL)] * 6,
    )
    monkeypatch.setattr(run_loops, "render_route_choice", lambda **_kw: None)
    monkeypatch.setattr(run_loops, "_wait_for_enter", lambda *_a, **_kw: None)
    monkeypatch.setattr(run_loops.Prompt, "ask", lambda *_a, **_kw: "A")
    monkeypatch.setattr(run_loops, "_offer_artifact", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        run_loops,
        "_run_combat_node",
        lambda scenario, position, total_positions, trace_level, node_type,
               perks, runtime, backtrack_used, run_state, acquired_artifacts,
               diver_class=None: (
            trace_level, backtrack_used, "cleared", scenario["difficulty"]
        ),
    )


# ── P4.5-1: 승리 런 후 보상·캠페인·통계가 올바르게 갱신된다 ──────────────────────

def test_e2e_victory_updates_fragments_campaign_and_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """전체 승리 런 후 보상·캠페인 점수·누적 통계가 모두 반영된다."""
    _stub_run_loops(monkeypatch)
    save_data = _fresh_save()
    initial_frags = save_data["data_fragments"]

    correct, is_victory, result, difficulties, run_stats = run_loops.run_game_session(
        perks={},
        save_data=save_data,
        diver_class=None,
        ascension_level=0,
    )

    assert correct == 8
    assert is_victory is True
    assert result == "victory"

    # 보상 계산
    reward = calculate_reward(
        correct_answers=correct,
        is_victory=is_victory,
        node_difficulties=difficulties,
    )
    assert reward > 0

    # 캠페인 업데이트
    campaign_result = update_campaign_progress(
        save_data=save_data,
        gain=reward,
        is_victory=is_victory,
        class_key=DiverClass.ANALYST.value,
        ascension_level=0,
    )
    campaign = campaign_result["campaign"]
    assert campaign["runs"] == 1
    assert campaign["victories"] == 1
    assert campaign["points"] == reward
    assert campaign["ascension_unlocked"] == 1

    # 누적 통계 업데이트
    update_run_stats(
        save_data=save_data,
        is_victory=is_victory,
        final_trace=run_stats.get("trace_final", 0),
        ascension_level=0,
    )
    snap = get_run_stats_snapshot(save_data["stats"])
    assert snap["total_runs"] == 1
    assert snap["total_victories"] == 1
    assert snap["win_rate"] == 100.0


# ── P4.5-2: 패배 런 후 통계가 올바르게 갱신된다 ────────────────────────────────

def test_e2e_shutdown_updates_stats_no_ascension_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """패배 런(shutdown) 후 통계가 올바르게 갱신되고 어센션 기록은 바뀌지 않는다."""
    _stub_run_loops(monkeypatch)

    # 첫 전투에서 death 반환
    call_count: dict[str, int] = {"n": 0}

    def _fake_death_combat(
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
        return trace_level, backtrack_used, "death", None

    monkeypatch.setattr(run_loops, "_run_combat_node", _fake_death_combat)

    save_data = _fresh_save()
    correct, is_victory, result, _difficulties, run_stats = run_loops.run_game_session(
        perks={},
        save_data=save_data,
        ascension_level=5,
    )

    assert is_victory is False
    assert result == "shutdown"

    # 통계 갱신
    update_run_stats(
        save_data=save_data,
        is_victory=False,
        final_trace=run_stats.get("trace_final", 100),
        ascension_level=5,
    )
    snap = get_run_stats_snapshot(save_data["stats"])
    assert snap["total_runs"] == 1
    assert snap["total_victories"] == 0
    assert snap["win_rate"] == 0.0
    # 패배 시 best_ascension_cleared는 0 유지
    assert snap["best_ascension_cleared"] == 0


# ── P4.5-3: run_lobby_loop 단일 턴 — 게임 시작 → 정산 → 종료 ─────────────────

def test_e2e_lobby_single_run_then_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """로비 메뉴 [1] 게임 시작 → 런 승리 → 메뉴 [3] 종료 흐름을 시뮬레이션한다."""
    _stub_run_loops(monkeypatch)

    # 세이브 파일을 tmp 슬롯 파일로 격리
    save_file = tmp_path / "save_slot_1.json"
    fresh = _fresh_save()
    save_file.write_text(json.dumps(fresh), encoding="utf-8")

    # load_save_slot / save_game_slot을 tmp 파일로 리다이렉트
    def _mock_load_save_slot(slot: int) -> dict[str, Any]:
        try:
            raw = json.loads(save_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return deepcopy(DEFAULT_SAVE_DATA)
        return _normalize_save_data(raw)

    def _mock_save_game_slot(data: dict[str, Any], slot: int) -> None:
        save_file.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(lobby, "load_save_slot", _mock_load_save_slot)
    monkeypatch.setattr(lobby, "save_game_slot", _mock_save_game_slot)

    # 로비 I/O 무효화
    monkeypatch.setattr(lobby, "initialize_argos_taunts", lambda: None)
    monkeypatch.setattr(lobby, "migrate_legacy_save", lambda: None)
    monkeypatch.setattr(lobby, "select_save_slot", lambda: 1)
    monkeypatch.setattr(lobby, "render_lobby", lambda **_kw: None)
    monkeypatch.setattr(lobby, "render_settlement_log", lambda **_kw: None)
    monkeypatch.setattr(lobby, "render_ending", lambda *_a, **_kw: None)
    monkeypatch.setattr(lobby, "render_achievement_unlocks", lambda _x: None)
    monkeypatch.setattr(lobby, "wait_for_enter", lambda *_a, **_kw: None)
    monkeypatch.setattr(lobby, "select_diver_class", lambda: DiverClass.ANALYST)
    monkeypatch.setattr(lobby, "select_ascension_level", lambda _sd: 0)

    # Prompt 시퀀스: "1" (게임 시작) → "3" (종료)
    menu_sequence = iter(["1", "3"])
    monkeypatch.setattr(
        lobby.Prompt, "ask", lambda *_a, **_kw: next(menu_sequence)
    )

    # 가짜 run_game_session: 즉시 승리 반환
    def _fake_game_session(
        perks: dict[str, bool],
        save_data: dict[str, Any],
        diver_class: DiverClass | None = None,
        ascension_level: int = 0,
    ) -> tuple[int, bool, str, list[str], dict[str, Any]]:
        return (
            8,
            True,
            "victory",
            ["Easy"] * 7 + ["NIGHTMARE"],
            {
                "wrong_analyzes": 0,
                "timeout_events": 0,
                "trace_final": 10,
                "skill_used": False,
                "mystery_engaged": 0,
                "mystery_good": 0,
                "mystery_skipped": 0,
                "artifacts_held": 0,
                "max_trace_reached": 10,
                "cascade_triggered": False,
                "void_scanner_used": False,
                "mystery_frags_gained": 0,
            },
        )

    lobby.run_lobby_loop(
        game_session_fn=_fake_game_session,
        daily_challenge_fn=lambda _sd: None,
    )

    # 세이브 파일이 갱신되었는지 확인
    saved = json.loads(save_file.read_text(encoding="utf-8"))
    # 보상이 지급되어 data_fragments가 증가했어야 함
    assert saved["data_fragments"] > fresh["data_fragments"]
    # 캠페인 런 카운트 1 이상
    assert saved["campaign"]["runs"] >= 1
    assert saved["campaign"]["victories"] >= 1
    # 통계 총 런 1 이상
    assert saved["stats"]["total_runs"] >= 1


# ── P4.5-4: 정산 파이프라인 — 세이브 원본 불변성 ────────────────────────────────

def test_e2e_settlement_does_not_corrupt_existing_perks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """런 정산 시 기존 퍼크 상태가 손상되지 않는다."""
    _stub_run_loops(monkeypatch)

    save_data = _fresh_save()
    save_data["perks"]["penalty_reduction"] = True
    save_data["data_fragments"] = 500

    correct, is_victory, result, difficulties, run_stats = run_loops.run_game_session(
        perks=save_data["perks"],
        save_data=save_data,
        ascension_level=0,
    )

    reward = calculate_reward(
        correct_answers=correct,
        is_victory=is_victory,
        node_difficulties=difficulties,
    )
    save_data["data_fragments"] += reward
    update_run_stats(
        save_data=save_data,
        is_victory=is_victory,
        final_trace=run_stats.get("trace_final", 0),
        ascension_level=0,
    )

    # 퍼크가 여전히 유효해야 함
    assert save_data["perks"]["penalty_reduction"] is True
    assert save_data["data_fragments"] > 500


# ── P4.5-5: 연속 런 — 통계 누적 검증 ────────────────────────────────────────────

def test_e2e_two_runs_accumulate_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """두 번의 런(승리+패배) 후 통계가 올바르게 누적된다."""
    _stub_run_loops(monkeypatch)

    save_data = _fresh_save()

    # 런 1: 승리
    update_run_stats(
        save_data=save_data,
        is_victory=True,
        final_trace=20,
        ascension_level=3,
    )
    # 런 2: 패배
    update_run_stats(
        save_data=save_data,
        is_victory=False,
        final_trace=85,
        ascension_level=0,
    )

    snap = get_run_stats_snapshot(save_data["stats"])
    assert snap["total_runs"] == 2
    assert snap["total_victories"] == 1
    assert snap["win_rate"] == 50.0
    assert snap["avg_trace"] == pytest.approx((20 + 85) / 2, rel=1e-3)
    # 패배 런에서는 best_ascension_cleared가 갱신되지 않음
    assert snap["best_ascension_cleared"] == 3
