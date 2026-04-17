"""Echoes of the Terminal — 진입점.

모듈 구조:
  run_loops.py          런 루프 엔진 (run_game_session, run_daily_challenge)
  lobby.py              로비 UI (run_lobby_loop, run_shop, 클래스/어센션 선택)
  combat_orchestration  전투/미스터리/상점 노드 실행
  ui_renderer.py        Rich 터미널 렌더링

테스트 호환성을 위해 run_loops의 내부 헬퍼를 re-export한다.
"""

from progression_system import apply_ascension_reward_multiplier as _apply_ascension_reward_multiplier  # noqa: F401 (re-export)
from run_loops import (
    _apply_ascension_modifiers,       # noqa: F401 (re-export for tests)
    _build_run_stats,                 # noqa: F401 (re-export for tests)
    _calculate_analyze_penalty,       # noqa: F401 (re-export for tests)
    _get_boss_phase_runtime,          # noqa: F401 (re-export for tests)
    _initialize_run_state,            # noqa: F401 (re-export for tests)
    _mutate_route_choices_for_ascension,  # noqa: F401 (re-export for tests)
    run_daily_challenge,
    run_game_session,
)
from lobby import run_lobby_loop as _run_lobby_loop_impl


def run_lobby_loop() -> None:
    """게임 전체 상태 머신 (로비 → 런/상점 → 로비)을 실행한다."""
    _run_lobby_loop_impl(run_game_session, run_daily_challenge)


if __name__ == "__main__":
    run_lobby_loop()
