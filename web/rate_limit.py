"""web/rate_limit.py — 인메모리 슬라이딩 윈도우 레이트 리미터.

신규 의존성 없음. 단일 프로세스(fly.io single worker) 환경에 최적화.
멀티 프로세스 배포 시 Redis 기반으로 교체 필요.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Final

# ── 상수 ───────────────────────────────────────────────────────────────────────
MAX_CONCURRENT_GAMES: Final[int] = 20      # 동시 실행 가능한 최대 게임 세션 수
GAME_START_PER_MINUTE: Final[int] = 5      # IP당 분당 최대 게임 시작 횟수
COMMAND_PER_MINUTE: Final[int] = 60        # 세션당 분당 최대 커맨드 입력 횟수
STREAM_PER_MINUTE: Final[int] = 30         # IP당 분당 최대 SSE 연결 개수

_WINDOW: Final[float] = 60.0              # 슬라이딩 윈도우 크기 (초)

# ── 내부 상태 (불변 컨테이너 참조, 내용만 변경) ────────────────────────────────
_lock: Lock = Lock()
_counters: dict[str, list[float]] = defaultdict(list)


def check_rate(key: str, limit: int, window: float = _WINDOW) -> bool:
    """슬라이딩 윈도우 체크.

    Args:
        key:    레이트 리밋 식별 키 (예: ``"start:127.0.0.1"``)
        limit:  ``window`` 내 허용 최대 요청 수
        window: 윈도우 크기 (초)

    Returns:
        True  → 허용
        False → 초과 (429 반환 필요)
    """
    now = time.time()
    cutoff = now - window
    with _lock:
        ts_list = _counters[key]
        # 만료된 타임스탬프 제거
        _counters[key] = [t for t in ts_list if t > cutoff]
        if len(_counters[key]) >= limit:
            return False
        _counters[key].append(now)
        return True


def cleanup() -> int:
    """5분 이상 비활성 키 제거. 주기적으로 호출해 메모리 누수를 방지한다."""
    cutoff = time.time() - 300
    with _lock:
        stale = [k for k, v in _counters.items() if not v or v[-1] < cutoff]
        for k in stale:
            del _counters[k]
    return len(stale)


def reset(key: str | None = None) -> None:
    """테스트용 — 특정 키(또는 전체) 리셋."""
    with _lock:
        if key is None:
            _counters.clear()
        else:
            _counters.pop(key, None)
