"""전투 노드 타임아웃 타이머 관리 모듈."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class CombatTimer:
    """
    전투 노드 타임아웃을 관리하는 타이머 클래스.

    threading.Timer를 캡슐화하여 시작/연장/취소 인터페이스를 제공한다.
    기존 리스트-as-mutable-container 패턴을 대체한다.
    """

    timeout_seconds: float
    on_timeout: Callable[[], None]
    _fired: bool = field(default=False, init=False, repr=False)
    _deadline: float = field(default=0.0, init=False, repr=False)
    _timer: threading.Timer | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def start(self) -> None:
        """타이머를 시작한다."""
        self._deadline = time.monotonic() + self.timeout_seconds
        self._schedule(self.timeout_seconds)

    def extend(self, seconds: int) -> None:
        """남은 제한 시간을 연장한다. 이미 발동된 경우 무시."""
        if seconds <= 0:
            return
        with self._lock:
            if self._fired:
                return
            self._deadline += seconds
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                return
            if self._timer is not None:
                self._timer.cancel()
            self._schedule(remaining)

    def cancel(self) -> None:
        """타이머를 취소한다."""
        if self._timer is not None:
            self._timer.cancel()

    @property
    def has_fired(self) -> bool:
        """타임아웃이 발동됐는지 여부."""
        return self._fired

    @property
    def raw_timer(self) -> threading.Timer | None:
        """내부 threading.Timer 객체 (사망 체크 등에 전달용)."""
        return self._timer

    def _schedule(self, delay: float) -> None:
        self._timer = threading.Timer(max(0.05, delay), self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            if self._fired:
                return
            self._fired = True
        self.on_timeout()
