"""Rich 기반 터미널 UI 렌더링 유틸리티 모듈."""

import random
import time
from typing import Any

from daily_challenge import get_performance_grade as _get_daily_grade

from achievement_progress import format_progress_bar, get_locked_progress_entries
from constants import BUILD_DATE, VERSION
from i18n import t
from theme_system import THEMES, get_theme_styles

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# 게임 전역에서 동일한 콘솔 인스턴스를 재사용한다.
console = Console()

# 아르고스 대사 저장소.
_ARGOS_TAUNTS: dict[str, list[str]] = {}
_FALLBACK_ARGOS_MESSAGE = "모든 저항 신호는 분석 완료. 다음 명령을 입력해라."

# 현재 활성 테마 스타일.  set_theme()으로 교체한다.
_THEME: dict[str, str] = THEMES["default"]


def set_theme(theme_name: str) -> None:
    """현재 세션의 색상 테마를 변경한다."""
    global _THEME
    _THEME = get_theme_styles(theme_name)


def get_current_theme_name() -> str:
    """현재 적용된 테마의 이름을 반환한다."""
    for name, styles in THEMES.items():
        if styles is _THEME:
            return name
    return "default"


def set_argos_taunts(taunts: dict[str, list[str]]) -> None:
    """아르고스 대사 테이블을 런타임에 등록한다."""
    global _ARGOS_TAUNTS
    _ARGOS_TAUNTS = taunts if isinstance(taunts, dict) else {}


def wait_for_enter(message: str = "계속하려면 Enter를 누르세요") -> None:
    """화면 전환 전 사용자의 확인 입력을 받는다."""
    from rich.prompt import Prompt
    Prompt.ask(f"[bold white]{message}[/bold white]", default="")


def render_logo() -> None:
    """게임 시작 또는 노드 진입 시 로고를 출력한다."""
    logo = r"""
 _____      _                      ___       _   _          _____                   _             _
| ____| ___| |__   ___   ___  ___|_ _|_ __ | |_| |__   ___|_   _|__ _ __ _ __ ___ (_)_ __   __ _| |
|  _|  / __| '_ \ / _ \ / _ \/ __|| || '_ \| __| '_ \ / _ \| |/ _ \ '__| '_ ` _ \| | '_ \ / _` | |
| |___| (__| | | | (_) |  __/\__ \| || | | | |_| | | |  __/| |  __/ |  | | | | | | | | | | (_| | |
|_____|\\___|_| |_|\___/ \___||___/___|_| |_|\__|_| |_|\___||_|\___|_|  |_| |_| |_|_|_| |_|\__,_|_|
"""
    console.print(logo, style="bold green")
    console.print(f"[bold white]{t('logo.subtitle')}[/bold white]")
    console.print(
        f"[dim]v{VERSION}  ({BUILD_DATE})[/dim]"
    )
    console.print()


def type_text(text: str, style: str = "white", delay: float = 0.02) -> None:
    """
    텍스트를 한 글자씩 출력하여 터미널 타이핑 효과를 만든다.

    Args:
        text: 출력할 원문 텍스트
        style: Rich 스타일 문자열
        delay: 글자당 지연 시간(초)
    """
    # 줄바꿈 문자는 별도 처리해 줄 구조를 깨지 않도록 하고,
    # 일반 문자는 end=""로 이어붙여 실제 타이핑처럼 보이게 만든다.
    for char in text:
        if char == "\n":
            console.print()
        else:
            # 로그 원문에는 '[' 같은 문자가 많아 Rich 마크업 파싱 충돌이 날 수 있으므로
            # 문자 단위 출력에서는 마크업/하이라이팅을 비활성화해 원문 그대로 출력한다.
            console.print(char, style=style, end="", markup=False, highlight=False)
        time.sleep(delay)

    # 한 블록 출력이 끝난 뒤 가독성을 위해 마지막 줄바꿈을 추가한다.
    console.print()


def render_save_slot_selection(slots_info: list[dict[str, Any]]) -> None:
    """세이브 슬롯 선택 화면을 표시한다."""
    table = Table(
        title=f"◀ {t('slot.title')} ▶",
        border_style="cyan",
        title_style="bold cyan",
        show_lines=True,
    )
    table.add_column(t("slot.col_slot"), style="bold white", width=6, justify="center")
    table.add_column("STATUS", width=12)
    table.add_column(t("slot.col_fragments"), justify="right", width=14)
    table.add_column(t("slot.col_victories"), justify="right", width=14)
    table.add_column(t("slot.col_saved"), width=14)

    dash = t("slot.never")
    for info in slots_info:
        slot_num = f"[{info['slot']}]"
        if info.get("empty"):
            table.add_row(slot_num, f"[dim]{t('slot.empty')}[/dim]", dash, dash, dash)
        elif info.get("corrupted"):
            table.add_row(slot_num, "[bold red]CORRUPTED[/bold red]", dash, dash, dash)
        else:
            frags = f"{info.get('data_fragments', 0):,}"
            victories = str(info.get("campaign_victories", 0))
            last_saved = info.get("last_saved", dash)
            table.add_row(
                slot_num,
                "[bold green]SAVED[/bold green]",
                frags,
                victories,
                last_saved,
            )

    console.print(table)
    console.print()


def _trace_style(trace_level: int) -> str:
    """현재 테마 기준으로 추적도 수치에 맞는 Rich 스타일을 반환한다."""
    if trace_level >= 80:
        return _THEME["trace_critical"]
    if trace_level >= 50:
        return _THEME["trace_danger"]
    if trace_level >= 30:
        return _THEME["trace_warn"]
    return _THEME["trace_safe"]


def _difficulty_style(difficulty: str) -> str:
    """현재 테마 기준으로 난이도 문자열에 맞는 Rich 스타일을 반환한다."""
    upper = difficulty.upper()
    if upper == "NIGHTMARE":
        return _THEME["difficulty_nightmare"]
    if upper == "HARD":
        return _THEME["difficulty_hard"]
    return _THEME["difficulty_easy"]


def _result_style(is_victory: bool) -> str:
    """현재 테마 기준으로 런 결과에 맞는 Rich 스타일을 반환한다."""
    return _THEME["result_victory"] if is_victory else _THEME["result_defeat"]


def render_info_panel(
    current_node: int,
    total_nodes: int,
    trace_level: int,
    time_limit_seconds: int = 30,
    is_boss: bool = False,
) -> None:
    """
    현재 진행 상태(노드, Trace)를 상단 패널에 표시한다.

    Args:
        current_node: 현재 진행 중인 노드 번호(1-based)
        total_nodes: 전체 노드 수
        trace_level: 현재 추적도(%)
        time_limit_seconds: 현재 적용 중인 제한 시간(초)
        is_boss: 보스 노드 여부 (True일 경우 경고 강조)
    """
    status = Text()
    node_label = f"[BOSS] NODE: {current_node}/{total_nodes}" if is_boss else f"NODE: {current_node}/{total_nodes}"
    node_style = "bold red" if is_boss else "bold green"
    status.append(f"{node_label}\n", style=node_style)
    status.append(f"TRACE LEVEL: {trace_level}%\n", style=_trace_style(trace_level))
    # 변주 시스템의 타임 프레셔 규칙을 항상 가시화해 플레이어가 리스크를 인지하게 한다.
    status.append(
        f"제한 시간: {time_limit_seconds}초 (초과 시 추적도 추가 상승)",
        style="bold #00FFFF",
    )

    border = "red" if is_boss else "green"
    title = "⚠ BOSS NODE — NIGHTMARE PROTOCOL" if is_boss else "SYSTEM STATUS"
    panel = Panel(
        status,
        title=title,
        title_align="left",
        border_style=border,
    )
    console.print(panel)


def render_alert(message: str) -> None:
    """붉은 경고 패널을 출력한다."""
    panel = Panel(message, style="bold white on red", border_style="red")
    console.print(panel)


def render_lobby(
    data_fragments: int,
    perks: dict[str, bool],
    campaign: dict[str, Any] | None = None,
    achievement_snapshot: dict[str, Any] | None = None,
    daily_available: bool = False,
) -> None:
    """
    게임 시작 전 로비 화면을 출력한다.

    로비는 현재 보유 재화와 주요 특성 보유 상태, 그리고 메뉴 입력 가이드를 제공한다.
    """
    render_logo()

    # 현재 보유한 특성 수를 요약해 성장 진행도를 직관적으로 보여준다.
    owned_count = sum(1 for is_owned in perks.values() if is_owned)
    total_perks = len(perks)
    lobby_status = Text()
    lobby_status.append(t("lobby.status.fragments", count=data_fragments) + "\n", style="bold green")
    lobby_status.append(t("lobby.status.perks", owned=owned_count, total=total_perks), style="bold white")
    console.print(Panel(lobby_status, title=t("lobby.status.title"), title_align="left", border_style="green"))

    if campaign:
        class_victories = campaign.get("class_victories", {})
        ascension_unlocked = int(campaign.get("ascension_unlocked", 0))
        campaign_text = Text()
        campaign_text.append(
            t("lobby.campaign.points", points=f"{campaign.get('points', 0):,}") + "\n",
            style="bold cyan",
        )
        campaign_text.append(
            t("lobby.campaign.victories", victories=campaign.get("victories", 0)) + "\n",
            style="bold white",
        )
        campaign_text.append(
            t(
                "lobby.campaign.class_victories",
                analyst=class_victories.get("ANALYST", 0),
                ghost=class_victories.get("GHOST", 0),
                cracker=class_victories.get("CRACKER", 0),
            ) + "\n",
            style="bold white",
        )
        campaign_text.append(
            t("lobby.campaign.ascension", level=ascension_unlocked) + "\n",
            style="bold white",
        )
        cleared = campaign.get("cleared", False)
        state_str = t("lobby.campaign.status_clear") if cleared else t("lobby.campaign.status_progress")
        state_style = "bold green" if cleared else "bold yellow"
        campaign_text.append(t("lobby.campaign.state_label", state=state_str), style=state_style)
        console.print(
            Panel(
                campaign_text,
                title=t("lobby.campaign.title"),
                title_align="left",
                border_style="cyan",
            )
        )

    if achievement_snapshot:
        achievement_text = Text()
        achievement_text.append(
            t(
                "lobby.achievement.unlocked",
                unlocked=achievement_snapshot.get("unlocked_count", 0),
                total=achievement_snapshot.get("total_count", 0),
            ) + "\n",
            style="bold yellow",
        )
        unlocked_entries = achievement_snapshot.get("unlocked_entries", [])
        if isinstance(unlocked_entries, list) and unlocked_entries:
            recent_titles = [str(item.get("title", "")) for item in unlocked_entries[-3:] if isinstance(item, dict)]
            achievement_text.append(
                t("lobby.achievement.recent", items=" | ".join(recent_titles)),
                style="bold white",
            )
        else:
            achievement_text.append(t("lobby.achievement.none"), style="bold white")
        console.print(
            Panel(
                achievement_text,
                title=t("lobby.achievement.title"),
                title_align="left",
                border_style="yellow",
            )
        )

    menu_text = Text()
    menu_text.append(t("lobby.menu.game_start") + "\n", style="bold green")
    menu_text.append(t("lobby.menu.shop") + "\n", style="bold white")
    menu_text.append(t("lobby.menu.exit") + "\n", style="bold white")
    daily_key = "lobby.menu.daily_available" if daily_available else "lobby.menu.daily_done"
    menu_text.append(t(daily_key) + "\n", style="bold cyan")
    menu_text.append(t("lobby.menu.records") + "\n", style="dim white")
    menu_text.append(t("lobby.menu.tutorial") + "\n", style="dim white")
    menu_text.append(t("lobby.menu.change_slot") + "\n", style="dim white")
    menu_text.append(t("lobby.menu.change_theme") + "\n", style="dim white")
    menu_text.append(t("lobby.menu.change_language") + "\n", style="dim white")
    menu_text.append(t("lobby.menu.lb_export") + "\n", style="dim white")
    menu_text.append(t("lobby.menu.lb_import"), style="dim white")
    console.print(
        Panel(
            menu_text,
            title=t("lobby.menu.title"),
            title_align="left",
            border_style="green",
        )
    )


def render_achievement_unlocks(unlocked_achievements: list[dict[str, str]]) -> None:
    """Render newly unlocked achievements as a settlement panel."""
    if not unlocked_achievements:
        return

    content = Text()
    for entry in unlocked_achievements:
        title = str(entry.get("title", "")).strip()
        desc = str(entry.get("desc", "")).strip()
        if not title:
            continue
        content.append(f"- {title}\n", style="bold yellow")
        if desc:
            content.append(f"  {desc}\n", style="white")
    console.print(
        Panel(
            content,
            title="ACHIEVEMENT UNLOCKED",
            title_align="left",
            border_style="yellow",
        )
    )


def render_shop(
    data_fragments: int,
    perks: dict[str, bool],
    perk_prices: dict[str, int],
    perk_menu_map: dict[str, str] | None = None,
    perk_label_map: dict[str, str] | None = None,
    perk_desc_map: dict[str, str] | None = None,
) -> None:
    """
    상점 화면을 출력한다.

    각 특성의 효과, 비용, 현재 구매 상태를 한 번에 확인할 수 있도록 표 형태로 렌더링한다.
    perk_menu_map / perk_label_map / perk_desc_map을 전달하면 동적으로 행을 생성한다.
    """
    console.print(f"[bold green]>>> {t('shop.title')}[/bold green]")
    console.print(f"[bold white]{t('shop.fragments', count=data_fragments)}[/bold white]")
    console.print()

    table = Table(show_header=True, header_style="bold green")
    table.add_column(t("shop.col_num"), style="bold white", width=6)
    table.add_column(t("shop.col_name"), style="bold white")
    table.add_column(t("shop.col_desc"), style="white")
    table.add_column(t("shop.col_price"), style="bold white", width=10)
    table.add_column(t("shop.col_status"), style="bold white", width=10)

    owned_label = t("shop.owned")
    not_owned_label = t("shop.not_owned")

    if perk_menu_map and perk_label_map:
        # 동적 행 생성: PERK_MENU_MAP 순서대로 렌더링
        for menu_num, perk_key in sorted(perk_menu_map.items(), key=lambda x: x[0]):
            label = perk_label_map.get(perk_key, perk_key)
            desc = (perk_desc_map or {}).get(perk_key, "-")
            price = perk_prices.get(perk_key, 0)
            owned = perks.get(perk_key, False)
            status_str = f"[bold green]{owned_label}[/bold green]" if owned else not_owned_label
            table.add_row(menu_num, label, desc, str(price), status_str)
    else:
        # 폴백: 기존 3개 특성 하드코딩
        table.add_row(
            "1",
            "오류 허용 버퍼",
            "오답 시 추적도 상승량 15% 감소",
            str(perk_prices.get("penalty_reduction", 50)),
            owned_label if perks.get("penalty_reduction", False) else not_owned_label,
        )
        table.add_row(
            "2",
            "타임 익스텐션",
            "입력 제한 시간 30초 → 40초",
            str(perk_prices.get("time_extension", 30)),
            owned_label if perks.get("time_extension", False) else not_owned_label,
        )
        table.add_row(
            "3",
            "글리치 필터",
            "Hard 글리치 마스킹 단어 수 1개로 완화",
            str(perk_prices.get("glitch_filter", 20)),
            owned_label if perks.get("glitch_filter", False) else not_owned_label,
        )

    table.add_row("0", t("shop.back"), t("shop.back_desc"), "-", "-")
    console.print(table)


def render_settlement_log(
    correct_answers: int,
    base_reward: int,
    final_reward: int,
    is_victory: bool,
    trace_final: int = -1,
) -> None:
    """
    런 종료 후 보상 정산 로그를 상세 출력한다.

    명세에 따라 시스템 로그 형태 문구를 고정하며, 색상은 bold #00FFFF를 사용한다.
    """
    console.print(
        f"[bold #00FFFF]{t('settlement.nodes_cleared', count=correct_answers, base=base_reward)}[/bold #00FFFF]"
    )
    if trace_final >= 0:
        trace_style = _trace_style(trace_final)
        console.print(
            f"[{trace_style}]{t('settlement.final_trace', trace=trace_final)}[/{trace_style}]"
        )
    result_style = _result_style(is_victory)
    if not is_victory:
        console.print(
            f"[{result_style}]{t('settlement.death_penalty')}[/{result_style}]"
        )
    result_key = "settlement.result_victory" if is_victory else "settlement.result_defeat"
    console.print(
        f"[{result_style}]{t(result_key, reward=final_reward)}[/{result_style}]"
    )


def render_class_selection(class_profiles: list[Any]) -> None:
    """
    다이버 클래스 선택 화면을 출력한다.

    Args:
        class_profiles: ClassProfile 인스턴스 목록 (최대 3개)
    """
    class_styles = {
        "ANALYST": "bold cyan",
        "GHOST": "bold green",
        "CRACKER": "bold magenta",
    }

    console.print(f"[bold white]{t('class.selection.header')}[/bold white]")
    console.print(f"[bold white]{t('class.selection.prompt')}[/bold white]\n")

    for idx, profile in enumerate(class_profiles, start=1):
        style = class_styles.get(profile.diver_class.value, "bold white")

        content = Text()
        content.append(f"{profile.name}  ({profile.diver_class.value})\n", style=style)
        content.append(f"{profile.tagline}\n\n", style="italic white")
        content.append("PASSIVE\n", style="bold yellow")
        for passive in profile.passives:
            content.append(f"  • {passive}\n", style="white")
        content.append(f"\nACTIVE: {profile.active_name}\n", style="bold #00FFFF")
        content.append(f"  {profile.active_desc}", style="white")

        panel = Panel(
            content,
            title=f"[{idx}] {profile.diver_class.value}",
            border_style=style.replace("bold ", ""),
        )
        console.print(panel)

    console.print()


def render_artifact_selection(
    artifacts: list[Any],
    source: str = "ELITE",
) -> None:
    """
    아티팩트 선택 UI를 출력한다.

    Args:
        artifacts: draw_artifacts()가 반환한 Artifact 리스트
        source: 획득 출처 레이블 ("ELITE" | "BOSS")
    """
    rarity_styles: dict[str, str] = {
        "COMMON": "bold white",
        "RARE": "bold cyan",
        "EPIC": "bold magenta",
    }

    console.print(
        f"\n[bold magenta]━━━ ARTIFACT REWARD [{source} CLEAR] ━━━[/bold magenta]"
    )
    console.print("[bold white]아티팩트를 하나 선택하세요.[/bold white]\n")

    for idx, art in enumerate(artifacts, start=1):
        style = rarity_styles.get(art.rarity, "bold white")
        content = Text()
        content.append(f"[{art.rarity}] ", style=style)
        content.append(art.name + "\n", style="bold white")
        content.append(art.desc, style="white")
        panel = Panel(
            content,
            title=f"[{idx}] {art.artifact_id}",
            border_style=style.replace("bold ", ""),
        )
        console.print(panel)

    console.print()


def render_artifact_hud(artifacts: list[Any]) -> None:
    """
    현재 보유 아티팩트 목록을 한 줄 요약으로 출력한다.

    노드 진입 화면 하단에 표시해 플레이어가 보유 효과를 항상 인지하게 한다.
    """
    if not artifacts:
        return
    rarity_styles: dict[str, str] = {
        "COMMON": "white",
        "RARE": "cyan",
        "EPIC": "magenta",
    }
    parts = []
    for art in artifacts:
        style = rarity_styles.get(art.rarity, "white")
        parts.append(f"[{style}]{art.name}[/{style}]")
    console.print("ARTIFACTS: " + "  │  ".join(parts))
    console.print()


def render_route_choice(
    current_depth: int,
    total_depth: int,
    left_type_name: str,
    right_type_name: str,
    left_label: str,
    right_label: str,
    left_desc: str,
    right_desc: str,
    left_style: str = "bold yellow",
    right_style: str = "bold cyan",
) -> None:
    """
    다음 노드 분기 선택 UI를 출력한다.

    Args:
        current_depth: 방금 완료된 노드의 0-based 인덱스
        total_depth: 일반 노드 전체 수 (보스 제외)
        left_type_name: 왼쪽 경로 NodeType 영문명
        right_type_name: 오른쪽 경로 NodeType 영문명
        left_label: 왼쪽 경로 한국어 레이블
        right_label: 오른쪽 경로 한국어 레이블
        left_desc: 왼쪽 경로 효과 설명
        right_desc: 오른쪽 경로 효과 설명
        left_style: 왼쪽 패널 Rich 스타일
        right_style: 오른쪽 패널 Rich 스타일
    """
    filled = "█" * (current_depth + 1)
    empty = "░" * (total_depth - current_depth - 1)
    progress_bar = filled + empty
    console.print(
        f"\n[bold white]━━━ ROUTE SELECTION  [{progress_bar}]  "
        f"{current_depth + 1}/{total_depth} ━━━[/bold white]"
    )

    left_content = Text()
    left_content.append(f"◈ {left_type_name}\n", style=left_style)
    left_content.append(left_label + "\n", style="bold white")
    left_content.append(left_desc, style="white")

    right_content = Text()
    right_content.append(f"◈ {right_type_name}\n", style=right_style)
    right_content.append(right_label + "\n", style="bold white")
    right_content.append(right_desc, style="white")

    left_panel = Panel(left_content, title="[A] 왼쪽 경로", border_style="yellow")
    right_panel = Panel(right_content, title="[B] 오른쪽 경로", border_style="cyan")
    console.print(Columns([left_panel, right_panel]))
    console.print()


def print_argos_message(category: str) -> None:
    """
    아르고스 개입 대사를 출력한다.

    Args:
        category: 상황 카테고리(wrong_analyze, game_over 등)
    """
    lines = _ARGOS_TAUNTS.get(category, [])
    if isinstance(lines, list):
        candidates = [line for line in lines if isinstance(line, str) and line.strip()]
    else:
        candidates = []

    line = random.choice(candidates) if candidates else _FALLBACK_ARGOS_MESSAGE
    # 위압감을 위해 기본 타이핑보다 느린 속도로 출력한다.
    type_text(f"[ARGOS] {line}", style="bold #FF073A", delay=0.035)


def render_daily_challenge_intro(date_str: str, already_played: bool) -> None:
    """데일리 챌린지 진입 화면을 렌더링한다."""
    title = f"DAILY CHALLENGE — {date_str}"
    if already_played:
        body = Text()
        body.append("오늘 챌린지는 이미 완료했습니다.\n", style="bold yellow")
        body.append("결과는 히스토리에서 확인할 수 있습니다.\n", style="white")
        body.append("내일 다시 도전하세요.", style="dim white")
    else:
        body = Text()
        body.append("오늘의 특수 임무가 발령되었습니다.\n", style="bold green")
        body.append("모든 플레이어 동일 시드 — 공정한 하루 한 번의 기회.\n", style="white")
        body.append("보상 배율 ×1.5 적용. 실패해도 데이터는 누적됩니다.", style="bold cyan")
    console.print(Panel(body, title=title, title_align="left", border_style="cyan"))


def render_daily_result(
    date_str: str,
    score: int,
    is_victory: bool,
    correct_answers: int,
    trace_final: int,
    class_key: str,
    streak: int,
    best_score: int,
) -> None:
    """데일리 챌린지 결과 패널을 렌더링한다."""
    content = Text()
    content.append("결과: ", style="white")
    content.append("CORE BREACHED\n" if is_victory else "SYSTEM SHUTDOWN\n",
                   style="bold green" if is_victory else "bold red")
    content.append(f"점수:        {score:,}\n", style="bold yellow")
    content.append(f"클리어 노드: {correct_answers}\n", style="white")
    content.append(f"최종 추적도: {trace_final}%\n", style="white")
    content.append(f"클래스:      {class_key}\n", style="white")
    content.append(f"연속 플레이: {streak}일\n", style="bold cyan")
    if score >= best_score:
        content.append("★ 베스트 기록 갱신!\n", style="bold yellow")
    console.print(Panel(
        content,
        title=f"DAILY RESULT — {date_str}",
        title_align="left",
        border_style="yellow" if is_victory else "red",
    ))


def render_daily_history(history: list[dict[str, Any]]) -> None:
    """데일리 챌린지 히스토리를 점수 바 차트 포함 테이블로 렌더링한다.

    최신 14개 항목을 최신순으로 표시하며, 각 행에 점수 분포를 시각 바로 표현한다.
    """
    if not history:
        console.print("[dim white]데일리 챌린지 히스토리가 없습니다.[/dim white]")
        return

    _GRADE_STYLE: dict[str, str] = {
        "S": "bold #FFD700",
        "A": "bold #00FFFF",
        "B": "bold green",
        "C": "bold white",
        "D": "dim white",
    }
    _BAR_WIDTH = 16

    recent = list(reversed(history[-14:]))  # 최신 14개, 최신→과거 순
    max_score = max((int(e.get("score", 0)) for e in recent), default=1) or 1

    table = Table(
        title="DAILY CHALLENGE HISTORY",
        border_style="cyan",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("날짜", style="white", width=12)
    table.add_column("결과", width=6)
    table.add_column("점수 분포", width=_BAR_WIDTH + 2)
    table.add_column("점수", style="bold yellow", justify="right", width=8)
    table.add_column("등급", justify="center", width=4)
    table.add_column("오답", justify="center", width=4)

    for entry in recent:
        score = int(entry.get("score", 0))
        victory = bool(entry.get("is_victory", False))
        date_str = str(entry.get("date", ""))
        wrong = int(entry.get("wrong_analyzes", 0))

        grade = _get_daily_grade(score)
        grade_text = Text(grade, style=_GRADE_STYLE.get(grade, "white"))

        bar_len = max(0, int(score / max_score * _BAR_WIDTH))
        bar_str = "█" * bar_len + "░" * (_BAR_WIDTH - bar_len)
        bar_text = Text(bar_str, style="green" if victory else "red")

        result_str = "[green]WIN[/green]" if victory else "[red]FAIL[/red]"

        table.add_row(
            date_str,
            result_str,
            bar_text,
            f"{score:,}",
            grade_text,
            str(wrong),
        )
    console.print(table)


def render_ending(ending: Any, is_new: bool = True) -> None:
    """
    엔딩 화면을 렌더링한다.

    Args:
        ending: Ending 데이터클래스 인스턴스
        is_new: True면 '첫 해금' 배너를 추가로 출력한다.
    """
    import time as _time

    console.print()
    if is_new:
        console.print(
            f"  [bold yellow]★ 새로운 엔딩 해금: {ending.ending_id} ★[/bold yellow]"
        )
        _time.sleep(0.5)

    content = Text(justify="center")
    content.append("\n")
    content.append(f"{ending.title}\n", style=ending.color)
    content.append(f"{ending.subtitle}\n\n", style="bold white")
    content.append(ending.flavor_text + "\n", style="italic white")

    console.print(
        Panel(
            content,
            border_style=ending.border_style,
            padding=(1, 4),
        )
    )
    console.print()


def render_endings_gallery(snapshot: dict[str, Any]) -> None:
    """해금된 엔딩 갤러리를 렌더링한다."""
    unlocked_ids: list[str] = snapshot.get("unlocked_ids", [])
    total: int = snapshot.get("total_count", 5)

    table = Table(
        title=f"ENDINGS  [{len(unlocked_ids)}/{total}]",
        border_style="white",
        header_style="bold white",
    )
    table.add_column("ID", style="dim white", width=16)
    table.add_column("제목", style="bold", width=20)
    table.add_column("조건", style="white", width=30)
    table.add_column("상태", justify="center", width=8)

    condition_map: dict[str, str] = {
        "TRUE_END": "캠페인 100% 클리어 후 승리",
        "ASCENSION_END": "Ascension 20 승리",
        "GHOST_END": "추적도 10% 이하로 승리",
        "ANALYST_END": "오답·타임아웃 0회 + 6노드 이상 클리어",
        "SURVIVOR_END": "추적도 90% 이상으로 승리",
    }

    # 미해금은 ??? 처리
    from ending_system import ENDINGS
    for ending_id, ending in ENDINGS.items():
        is_unlocked = ending_id in unlocked_ids
        title_str = ending.title if is_unlocked else "???"
        cond_str = condition_map.get(ending_id, "")  if is_unlocked else "???"
        status_str = "[bold green]해금[/bold green]" if is_unlocked else "[dim white]잠금[/dim white]"
        table.add_row(ending_id, title_str, cond_str, status_str)

    console.print(table)


def render_run_history(run_history: list[dict[str, Any]]) -> None:
    """최근 런 기록을 Rich 테이블로 출력한다 (최신순).

    Args:
        run_history: get_run_history() 반환값 (최신순 리스트)
    """
    table = Table(
        title="◀ RUN HISTORY ▶",
        border_style="magenta",
        title_style="bold magenta",
        show_lines=False,
        header_style="bold white",
    )
    table.add_column("#", style="dim white", width=4, justify="right")
    table.add_column("DATE", style="dim white", width=12)
    table.add_column("CLASS", style="bold white", width=9)
    table.add_column("ASC", justify="right", width=5)
    table.add_column("RESULT", width=10)
    table.add_column("TRACE", justify="right", width=7)
    table.add_column("REWARD", justify="right", width=8)
    table.add_column("CORRECT", justify="right", width=8)
    table.add_column("ENDING", style="dim white", width=20)

    if not run_history:
        table.add_row("-", "-", "-", "-", "[dim]기록 없음[/dim]", "-", "-", "-", "-")
    else:
        for idx, rec in enumerate(run_history, start=1):
            result = str(rec.get("result", ""))
            if result == "victory":
                result_cell = "[bold green]VICTORY[/bold green]"
                trace_style = _trace_style(int(rec.get("trace_final", 0)))
            elif result == "shutdown":
                result_cell = "[bold red]SHUTDOWN[/bold red]"
                trace_style = _THEME["trace_critical"]
            else:
                result_cell = "[dim]ABORTED[/dim]"
                trace_style = "dim white"

            trace_val = rec.get("trace_final", -1)
            trace_cell = (
                f"[{trace_style}]{trace_val}%[/{trace_style}]"
                if isinstance(trace_val, int) and trace_val >= 0
                else "-"
            )
            table.add_row(
                str(idx),
                str(rec.get("date", "-")),
                str(rec.get("class_key", "-")),
                str(rec.get("ascension", 0)),
                result_cell,
                trace_cell,
                str(rec.get("reward", 0)),
                str(rec.get("correct_answers", 0)),
                str(rec.get("ending_id", "")) or "-",
            )

    console.print(table)
    console.print()


def render_diver_profile(profile: dict[str, Any]) -> None:
    """다이버 프로필 카드를 Rich Panel로 출력한다.

    Args:
        profile: get_diver_profile() 반환값
    """
    title = str(profile.get("title", "데이터 다이버"))
    sig_class = str(profile.get("signature_class", "—"))
    total_runs = int(profile.get("total_runs", 0))
    win_rate = float(profile.get("win_rate", 0.0))
    avg_trace = float(profile.get("avg_trace", 0.0))
    best_asc = int(profile.get("best_ascension", 0))
    fav_ending = str(profile.get("favorite_ending", "—"))
    best_score = int(profile.get("best_lb_score", 0))
    ach_count = int(profile.get("achievements_count", 0))
    camp_cleared = bool(profile.get("campaign_cleared", False))

    content = Text()
    content.append(f"  {title}\n", style="bold #FFD700")
    content.append("\n")
    content.append(f"  주력 클래스:     ", style="dim white")
    content.append(f"{sig_class}\n", style="bold #00FFFF")
    content.append(f"  총 런 수:        ", style="dim white")
    content.append(f"{total_runs}회\n", style="white")
    content.append(f"  승률:            ", style="dim white")
    content.append(f"{win_rate:.1f}%\n", style="bold green" if win_rate >= 60 else "white")
    content.append(f"  평균 추적도:     ", style="dim white")
    content.append(f"{avg_trace:.1f}%\n", style="white")
    content.append(f"  최고 어센션:     ", style="dim white")
    content.append(f"Asc {best_asc}\n", style="bold magenta" if best_asc >= 10 else "white")
    content.append(f"  최다 엔딩:       ", style="dim white")
    content.append(f"{fav_ending}\n", style="dim white")
    content.append(f"  리더보드 최고점: ", style="dim white")
    content.append(f"{best_score:,}\n", style="bold yellow" if best_score > 0 else "dim white")
    content.append(f"  해금 업적:       ", style="dim white")
    content.append(f"{ach_count}개\n", style="white")
    if camp_cleared:
        content.append("\n  ★ 100H 캠페인 클리어 달성!", style="bold #FFD700")

    console.print(
        Panel(
            content,
            title="[bold white]◀ DIVER PROFILE ▶[/bold white]",
            title_align="center",
            border_style="#FFD700",
            padding=(0, 1),
        )
    )
    console.print()


def render_leaderboard(
    entries: list[dict[str, Any]],
    new_rank: int | None = None,
) -> None:
    """로컬 Top-10 리더보드를 Rich 테이블로 출력한다.

    Args:
        entries:  get_leaderboard() 반환값 (점수 내림차순)
        new_rank: 방금 달성한 순위 (1-based). 해당 행을 강조 표시한다.
    """
    table = Table(
        title="◀ LOCAL LEADERBOARD ▶",
        border_style="yellow",
        title_style="bold yellow",
        show_lines=False,
        header_style="bold white",
    )
    table.add_column("RANK", justify="center", width=6)
    table.add_column("SCORE", justify="right", width=8, style="bold yellow")
    table.add_column("DATE", style="dim white", width=12)
    table.add_column("CLASS", style="bold white", width=9)
    table.add_column("ASC", justify="right", width=5)
    table.add_column("RESULT", width=10)
    table.add_column("TRACE", justify="right", width=7)
    table.add_column("REWARD", justify="right", width=8)
    table.add_column("CORRECT", justify="right", width=8)

    if not entries:
        table.add_row("-", "-", "-", "-", "-", "[dim]기록 없음[/dim]", "-", "-", "-")
    else:
        for entry in entries:
            rank = int(entry.get("rank", 0))
            is_new = (new_rank is not None and rank == new_rank)
            result = str(entry.get("result", ""))
            if result == "victory":
                result_cell = "[bold green]VICTORY[/bold green]"
            elif result == "shutdown":
                result_cell = "[bold red]SHUTDOWN[/bold red]"
            else:
                result_cell = "[dim]ABORTED[/dim]"

            rank_cell = (
                f"[bold #FFD700]★ {rank}[/bold #FFD700]" if is_new else str(rank)
            )
            trace_val = entry.get("trace_final", -1)
            trace_cell = f"{trace_val}%" if isinstance(trace_val, int) and trace_val >= 0 else "-"

            table.add_row(
                rank_cell,
                str(entry.get("score", 0)),
                str(entry.get("date", "-")),
                str(entry.get("class_key", "-")),
                str(entry.get("ascension", 0)),
                result_cell,
                trace_cell,
                str(entry.get("reward", 0)),
                str(entry.get("correct_answers", 0)),
            )

    console.print(table)
    console.print()


def render_personal_records(records: list[dict[str, Any]]) -> None:
    """개인 최고 기록을 (클래스, 어센션) 기준으로 Rich 테이블로 출력한다.

    Args:
        records: get_personal_records() 반환값 — (class_key, ascension) 오름차순 정렬된 리스트
    """
    table = Table(
        title="◀ PERSONAL RECORDS ▶",
        border_style="cyan",
        title_style="bold cyan",
        show_lines=False,
        header_style="bold white",
    )
    table.add_column("CLASS", style="bold white", width=9)
    table.add_column("ASC", justify="right", width=5)
    table.add_column("RUNS", justify="right", width=6)
    table.add_column("WINS", justify="right", width=6)
    table.add_column("WIN%", justify="right", width=7)
    table.add_column("BEST TRACE", justify="right", width=12)
    table.add_column("BEST REWARD", justify="right", width=13)
    table.add_column("BEST CORRECT", justify="right", width=14)

    if not records:
        table.add_row("-", "-", "-", "-", "-", "[dim]기록 없음[/dim]", "-", "-")
    else:
        for rec in records:
            run_count = int(rec.get("run_count", 0))
            victory_count = int(rec.get("victory_count", 0))
            win_pct = (victory_count / run_count * 100) if run_count > 0 else 0.0
            best_trace = rec.get("best_trace")
            best_trace_cell = f"{best_trace}%" if best_trace is not None else "[dim]—[/dim]"
            table.add_row(
                str(rec.get("class_key", "-")),
                str(rec.get("ascension", 0)),
                str(run_count),
                f"[bold green]{victory_count}[/bold green]",
                f"[bold #00FFFF]{win_pct:.0f}%[/bold #00FFFF]",
                best_trace_cell,
                str(rec.get("best_reward", 0)),
                str(rec.get("best_correct", 0)),
            )

    console.print(table)
    console.print()


def render_run_timeline(entry: dict[str, Any]) -> None:
    """단일 런 기록의 타임라인 이벤트를 Rich Tree로 렌더링한다.

    Args:
        entry: get_run_history() 반환 리스트의 항목 1개 (timeline 필드 포함)
    """
    from rich.tree import Tree

    timeline: list[dict[str, Any]] = entry.get("timeline", [])
    date = str(entry.get("date", "-"))
    class_key = str(entry.get("class_key", "?"))
    ascension = int(entry.get("ascension", 0))
    result = str(entry.get("result", "-"))
    result_color = "green" if result == "victory" else ("red" if result == "shutdown" else "dim")

    tree_label = (
        f"[bold white]{date}[/bold white]  "
        f"[bold cyan]{class_key}[/bold cyan]  "
        f"[dim]ASC {ascension}[/dim]  "
        f"[bold {result_color}]{result.upper()}[/bold {result_color}]"
    )
    tree = Tree(tree_label)

    _EVENT_STYLE: dict[str, tuple[str, str]] = {
        "correct": ("✓", "bold green"),
        "wrong": ("✗", "bold red"),
        "timeout": ("⏱", "bold #FF8C00"),
        "artifact": ("◆", "bold magenta"),
        "mystery_engage": ("?", "bold #FFD700"),
        "mystery_skip": ("—", "dim"),
        "rest": ("♥", "bold cyan"),
        "shop": ("$", "bold white"),
    }

    if not timeline:
        tree.add("[dim]타임라인 데이터 없음[/dim]")
    else:
        for ev in timeline:
            event_type = str(ev.get("event", ""))
            node_num = int(ev.get("node", 0))
            detail = str(ev.get("detail", ""))
            icon, style = _EVENT_STYLE.get(event_type, ("·", "white"))
            tree.add(
                f"[{style}]{icon}[/{style}]  "
                f"[dim]N{node_num:02d}[/dim]  "
                f"[{style}]{detail}[/{style}]"
            )

    console.print(tree)
    console.print()


def render_records_screen(
    achievement_snapshot: dict[str, Any],
    endings_snapshot: dict[str, Any],
    campaign_snapshot: dict[str, Any],
    daily_state: dict[str, Any],
    stats_snapshot: dict[str, Any] | None = None,
    run_history: list[dict[str, Any]] | None = None,
    personal_records: list[dict[str, Any]] | None = None,
    leaderboard: list[dict[str, Any]] | None = None,
    diver_profile: dict[str, Any] | None = None,
    achievement_progress: list[dict[str, Any]] | None = None,
) -> None:
    """
    로비 '기록 보기' 통합 화면 — 캠페인·업적·엔딩·데일리 현황을 한 번에 표시한다.
    """
    console.print()
    console.rule("[bold white]RECORDS[/bold white]")

    # ── 다이버 프로필 카드 (최상단 표시) ────────────────────────────────────
    if diver_profile is not None:
        render_diver_profile(diver_profile)

    # ── 캠페인 진행도 ─────────────────────────────────────────────────────
    pts = campaign_snapshot.get("points", 0)
    pts_tgt = campaign_snapshot.get("points_target", 60000)
    vic = campaign_snapshot.get("victories", 0)
    vic_tgt = campaign_snapshot.get("victories_target", 450)
    asc_unlocked = campaign_snapshot.get("ascension_unlocked", 0)
    class_vic = campaign_snapshot.get("class_victories", {})
    class_tgt = campaign_snapshot.get("class_target", 120)

    cam_content = Text()
    cam_content.append(f"캠페인 포인트:  {pts:,} / {pts_tgt:,}\n", style="bold #00FFFF")
    cam_content.append(f"총 승리 수:     {vic} / {vic_tgt}\n", style="white")
    cam_content.append(
        f"클래스 숙련:   "
        f"ANALYST {class_vic.get('ANALYST',0)}/{class_tgt}  "
        f"GHOST {class_vic.get('GHOST',0)}/{class_tgt}  "
        f"CRACKER {class_vic.get('CRACKER',0)}/{class_tgt}\n",
        style="white",
    )
    cam_content.append(f"해금된 Ascension: {asc_unlocked}/20\n", style="dim white")
    if campaign_snapshot.get("cleared"):
        cam_content.append("★ 100H 캠페인 클리어 달성!\n", style="bold #FFD700")
    console.print(Panel(cam_content, title="CAMPAIGN", title_align="left", border_style="cyan"))

    # ── 업적 현황 ─────────────────────────────────────────────────────────
    ach_unlocked = achievement_snapshot.get("unlocked_count", 0)
    ach_total = achievement_snapshot.get("total_count", 11)
    ach_entries = achievement_snapshot.get("unlocked_entries", [])

    ach_content = Text()
    ach_content.append(f"해금: {ach_unlocked} / {ach_total}\n\n", style="bold yellow")
    for entry in ach_entries:
        ach_content.append(f"  v {entry.get('title','')}", style="bold green")
        ach_content.append(f"  --  {entry.get('desc','')}\n", style="dim white")
    if ach_unlocked == 0:
        ach_content.append("  아직 해금된 업적이 없습니다.\n", style="dim white")

    # ── 진행 중인 업적 (locked, 진행률 표시) ───────────────────────────────
    if achievement_progress:
        ach_content.append("\n진행 중:\n", style="bold #FFD700")
        for entry in achievement_progress:
            current = int(entry.get("current", 0))
            target = int(entry.get("target", 0))
            bar = format_progress_bar(current, target, width=10)
            title = str(entry.get("title", ""))
            ach_content.append(f"  {bar} ", style="#FFD700")
            ach_content.append(f"{current}/{target}  ", style="bold white")
            ach_content.append(f"{title}\n", style="dim white")

    console.print(Panel(ach_content, title="ACHIEVEMENTS", title_align="left", border_style="yellow"))

    # ── 엔딩 갤러리 ───────────────────────────────────────────────────────
    render_endings_gallery(endings_snapshot)

    # ── 데일리 통계 ───────────────────────────────────────────────────────
    streak = daily_state.get("streak", 0)
    best = daily_state.get("best_score", 0)
    total_plays = daily_state.get("total_plays", 0)
    last_date = daily_state.get("last_played_date", "—")

    daily_content = Text()
    daily_content.append(f"연속 플레이:    {streak}일\n", style="bold cyan")
    daily_content.append(f"최고 점수:     {best:,}\n", style="bold yellow")
    daily_content.append(f"총 플레이:     {total_plays}회\n", style="white")
    daily_content.append(f"마지막 플레이: {last_date}\n", style="dim white")
    console.print(Panel(daily_content, title="DAILY CHALLENGE", title_align="left", border_style="cyan"))

    # ── 데일리 히스토리 바 차트 ────────────────────────────────────────────────
    daily_history = daily_state.get("history", [])
    if daily_history:
        render_daily_history(daily_history)

    # ── 누적 통계 ─────────────────────────────────────────────────────────
    if stats_snapshot:
        total_runs = stats_snapshot.get("total_runs", 0)
        total_vic = stats_snapshot.get("total_victories", 0)
        win_rate = stats_snapshot.get("win_rate", 0.0)
        avg_trace = stats_snapshot.get("avg_trace", 0.0)
        best_asc = stats_snapshot.get("best_ascension_cleared", 0)
        most_ending = stats_snapshot.get("most_seen_ending", "") or "—"

        stat_content = Text()
        stat_content.append(f"총 런 수:          {total_runs}회\n", style="white")
        stat_content.append(f"클리어 수:         {total_vic}회\n", style="white")
        stat_content.append(f"승률:              {win_rate:.1f}%\n", style="bold #00FFFF")
        stat_content.append(f"평균 최종 Trace:   {avg_trace:.1f}%\n", style="white")
        stat_content.append(f"최고 어센션 클리어: Asc {best_asc}\n", style="bold yellow")
        stat_content.append(f"최다 엔딩:         {most_ending}\n", style="dim white")
        console.print(Panel(stat_content, title="CUMULATIVE STATS", title_align="left", border_style="magenta"))

    # ── 런 기록 히스토리 ────────────────────────────────────────────────────
    if run_history is not None:
        render_run_history(run_history)
        # 최근 1개 런의 타임라인을 표시
        if run_history:
            console.print("[bold white]◀ 최근 런 타임라인 ▶[/bold white]")
            render_run_timeline(run_history[0])

    # ── 개인 최고 기록 ──────────────────────────────────────────────────────
    if personal_records is not None:
        render_personal_records(personal_records)

    # ── 로컬 리더보드 ────────────────────────────────────────────────────────
    if leaderboard is not None:
        render_leaderboard(leaderboard)

    console.rule()
