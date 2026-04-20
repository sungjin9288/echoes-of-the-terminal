"""web/adapters.py — 게임 엔진 ↔ 웹 I/O 브리지.

ConsoleBridge:
    ui_renderer.console 를 thread-local 세션 콘솔로 프록시.
    게임 코드(run_loops, combat_orchestration 등)를 수정하지 않고
    세션별 Rich Console 캡처를 구현한다.

install_patches():
    builtins.input 과 rich.prompt.PromptBase.ask 를 패치해
    게임의 모든 입력 호출이 세션 큐로 라우팅되게 한다.
"""

from __future__ import annotations

import builtins
import queue
import re
import threading
import time
from typing import Any

from rich.console import Console

# ── 스레드-로컬 세션 레지스트리 ────────────────────────────────────────────────
_thread_local = threading.local()
_original_input = builtins.input


# ── 패치 함수 ──────────────────────────────────────────────────────────────────

def _web_input(prompt: str = "") -> str:
    """builtins.input 대체: 세션 스레드면 큐에서, 아니면 원본 호출."""
    session: WebGameSession | None = getattr(_thread_local, "session", None)
    if session is not None:
        return session.recv_command(prompt)
    return _original_input(prompt)


def install_patches() -> None:
    """builtins.input + PromptBase.ask 전역 패치를 설치한다.

    반드시 게임 모듈이 임포트되기 전 app.py 모듈 레벨에서 호출해야 한다.
    """
    builtins.input = _web_input

    # Rich Prompt.ask 도 세션 콘솔을 사용하도록 패치
    try:
        from rich.prompt import PromptBase

        _orig_ask = PromptBase.ask.__func__  # type: ignore[attr-defined]

        @classmethod  # type: ignore[misc]
        def _patched_ask(cls, prompt: str = "", *, console: Console | None = None, **kwargs: Any) -> Any:
            if console is None:
                s: WebGameSession | None = getattr(_thread_local, "session", None)
                if s is not None:
                    console = s.console
            return _orig_ask(cls, prompt, console=console, **kwargs)  # type: ignore[call-arg]

        PromptBase.ask = _patched_ask  # type: ignore[method-assign]
    except Exception:
        pass  # Prompt 패치 실패는 치명적이지 않음


# ── ConsoleBridge ──────────────────────────────────────────────────────────────

class ConsoleBridge:
    """thread-local 세션의 Console 로 모든 Rich 호출을 프록시한다.

    ui_renderer.console 를 이 인스턴스로 교체하면, 게임 모듈이
    ``from ui_renderer import console`` 으로 임포트해도 세션별 출력이 격리된다.
    (단, 교체는 게임 모듈 임포트 *이전* 에 이루어져야 한다.)
    """

    def __init__(self, fallback: Console) -> None:
        self._fallback = fallback

    @property
    def _active(self) -> Console:
        s: WebGameSession | None = getattr(_thread_local, "session", None)
        return s.console if s is not None else self._fallback

    # ── 자주 호출되는 메서드는 명시적으로 위임 ───────────────────────────────
    def print(self, *args: Any, **kwargs: Any) -> None:
        self._active.print(*args, **kwargs)

    def rule(self, *args: Any, **kwargs: Any) -> None:
        self._active.rule(*args, **kwargs)

    def input(self, prompt: str = "") -> str:
        # Rich Console.input() → builtins.input() → 패치된 _web_input()
        return builtins.input(prompt)

    def clear(self) -> None:
        self._active.clear()

    def log(self, *args: Any, **kwargs: Any) -> None:
        self._active.log(*args, **kwargs)

    # ── 나머지 속성·메서드는 동적 위임 ─────────────────────────────────────
    def __getattr__(self, name: str) -> Any:
        return getattr(self._active, name)


# ── WebGameSession ─────────────────────────────────────────────────────────────

def _extract_pre_html(raw_html: str) -> str:
    """Rich export_html 전체 문서에서 <pre> 콘텐츠만 추출한다."""
    match = re.search(r"<pre[^>]*>(.*?)</pre>", raw_html, re.DOTALL)
    if match:
        return f'<pre class="term-out">{match.group(1)}</pre>'
    # fallback: pre 없으면 raw 반환
    return f'<pre class="term-out">{raw_html}</pre>'


class WebGameSession:
    """단일 브라우저 게임 세션 상태.

    생명 주기: lobby → playing → ended
    """

    INPUT_TIMEOUT: int = 90  # 초

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.status: str = "lobby"  # lobby | playing | ended
        self.created_at: float = time.time()
        self.last_active: float = time.time()

        # 세션 전용 Rich Console (record=True → export_html 가능)
        self.console: Console = Console(
            record=True,
            highlight=False,
            markup=True,
            width=100,
            force_terminal=True,
        )

        self._input_q: queue.Queue[str] = queue.Queue()
        self._output_chunks: list[dict[str, Any]] = []
        self._chunk_lock = threading.Lock()
        self._thread: threading.Thread | None = None

        # 로비 선택 상태
        self.selected_class_name: str = "ANALYST"
        self.ascension_level: int = 0

    # ── 출력 관리 ──────────────────────────────────────────────────────────────

    def flush_console_html(self) -> str | None:
        """기록된 콘솔 출력을 HTML로 변환하고 버퍼를 초기화한다.

        Rich Console(record=True) 은 출력이 없어도 빈 <code> 태그를 반환하므로,
        실제 텍스트 콘텐츠 여부로 "유의미한 출력"을 판별한다.
        """
        raw = self.console.export_html(inline_styles=True, clear=True)
        inner = _extract_pre_html(raw)
        # <pre> 안에 가시적 문자가 없으면 None 반환
        import re as _re
        text_only = _re.sub(r"<[^>]+>", "", inner).strip()
        if not text_only:
            return None
        return inner

    def push_output(self, html: str, waiting: bool = False) -> None:
        with self._chunk_lock:
            self._output_chunks.append(
                {"html": html, "waiting": waiting, "ts": time.time()}
            )

    def pop_output_chunks(self) -> list[dict[str, Any]]:
        with self._chunk_lock:
            chunks = list(self._output_chunks)
            self._output_chunks.clear()
        return chunks

    # ── 입력 관리 ──────────────────────────────────────────────────────────────

    def send_command(self, cmd: str) -> None:
        """브라우저에서 받은 커맨드를 게임 스레드로 전달한다."""
        self.last_active = time.time()
        self._input_q.put(cmd)

    def recv_command(self, prompt: str = "") -> str:
        """게임 스레드 내부에서 호출: 콘솔 버퍼 플러시 후 명령 대기."""
        # 출력 플러시 → 브라우저가 폴링으로 가져갈 수 있게
        html = self.flush_console_html()
        if html:
            self.push_output(html, waiting=True)

        try:
            cmd = self._input_q.get(timeout=self.INPUT_TIMEOUT)
        except queue.Empty:
            cmd = ""  # 타임아웃 → 빈 입력 반환 (게임이 처리)
        return cmd

    # ── 게임 스레드 ────────────────────────────────────────────────────────────

    def start_game(self, save_data: dict[str, Any]) -> None:
        """백그라운드 스레드에서 게임 루프를 시작한다."""
        if self._thread and self._thread.is_alive():
            return
        self.status = "playing"
        self._thread = threading.Thread(
            target=self._game_worker,
            args=(save_data,),
            daemon=True,
            name=f"game-{self.session_id[:8]}",
        )
        self._thread.start()

    def _game_worker(self, save_data: dict[str, Any]) -> None:
        """게임 스레드 진입점: 스레드-로컬 세션 등록 → 게임 실행 → 정리."""
        _thread_local.session = self
        try:
            self._run_game(save_data)
        except Exception as exc:
            self.console.print(f"\n[bold red]SYSTEM ERROR: {exc}[/bold red]")
        finally:
            # 남은 출력 플러시
            html = self.flush_console_html()
            if html:
                self.push_output(html, waiting=False)
            self.status = "ended"
            _thread_local.session = None

    def _run_game(self, save_data: dict[str, Any]) -> None:
        """실제 게임 세션 실행 (게임 모듈 lazy 임포트)."""
        from diver_class import DiverClass
        from progression_system import (
            add_run_to_history,
            get_perks,
            save_game,
            update_leaderboard,
            update_personal_records,
        )
        from run_loops import run_game_session

        perks = get_perks(save_data)

        try:
            diver_class = DiverClass[self.selected_class_name]
        except KeyError:
            diver_class = None

        result = run_game_session(
            perks=perks,
            save_data=save_data,
            diver_class=diver_class,
            ascension_level=self.ascension_level,
        )

        correct, is_victory, result_label, difficulties, run_stats = result

        # 진행도 반영
        add_run_to_history(save_data, is_victory, correct, self.ascension_level, diver_class)
        update_personal_records(save_data, is_victory, correct, self.ascension_level)
        update_leaderboard(save_data, is_victory, correct, self.ascension_level, diver_class)
        save_game(save_data)
