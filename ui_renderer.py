"""Rich 기반 터미널 UI 렌더링 유틸리티 모듈."""

import random
import time
from typing import Any

from constants import BUILD_DATE, VERSION

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# 게임 전역에서 동일한 콘솔 인스턴스를 재사용한다.
# 이렇게 하면 출력 스타일/동작이 일관되고, 테스트 시에도 접근 지점이 명확해진다.
console = Console()

# 아르고스 대사 저장소.
# 메인 루프에서 data_loader.load_argos_taunts() 결과를 주입받아 사용한다.
_ARGOS_TAUNTS: dict[str, list[str]] = {}
_FALLBACK_ARGOS_MESSAGE = "모든 저항 신호는 분석 완료. 다음 명령을 입력해라."


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
    console.print("[bold white]>>> ECHOES OF THE TERMINAL // 침투 세션 시작[/bold white]")
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
        title="◀ SAVE SLOT ▶",
        border_style="cyan",
        title_style="bold cyan",
        show_lines=True,
    )
    table.add_column("슬롯", style="bold white", width=6, justify="center")
    table.add_column("상태", width=12)
    table.add_column("데이터 조각", justify="right", width=14)
    table.add_column("캠페인 승리", justify="right", width=12)
    table.add_column("마지막 저장", width=14)

    for info in slots_info:
        slot_num = f"[{info['slot']}]"
        if info.get("empty"):
            table.add_row(slot_num, "[dim]비어있음[/dim]", "—", "—", "—")
        elif info.get("corrupted"):
            table.add_row(slot_num, "[bold red]손상됨[/bold red]", "—", "—", "—")
        else:
            frags = f"{info.get('data_fragments', 0):,}"
            victories = str(info.get("campaign_victories", 0))
            last_saved = info.get("last_saved", "—")
            table.add_row(
                slot_num,
                "[bold green]저장됨[/bold green]",
                frags,
                victories,
                last_saved,
            )

    console.print(table)
    console.print()


def _trace_style(trace_level: int) -> str:
    """추적도 수치에 따른 Rich 스타일을 반환한다."""
    if trace_level >= 80:
        return "bold red"
    if trace_level >= 50:
        return "bold yellow"
    if trace_level >= 30:
        return "bold white"
    return "bold green"


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
    lobby_status.append(f"보유 데이터 조각: {data_fragments}\n", style="bold green")
    lobby_status.append(f"해금 특성: {owned_count}/{total_perks}", style="bold white")
    console.print(Panel(lobby_status, title="LOBBY STATUS", title_align="left", border_style="green"))

    if campaign:
        class_victories = campaign.get("class_victories", {})
        ascension_unlocked = int(campaign.get("ascension_unlocked", 0))
        campaign_text = Text()
        campaign_text.append(
            f"캠페인 포인트: {campaign.get('points', 0):,}\n",
            style="bold cyan",
        )
        campaign_text.append(
            f"캠페인 승리: {campaign.get('victories', 0)} / 450\n",
            style="bold white",
        )
        campaign_text.append(
            "클래스 승리: "
            f"A {class_victories.get('ANALYST', 0)}  "
            f"G {class_victories.get('GHOST', 0)}  "
            f"C {class_victories.get('CRACKER', 0)}\n",
            style="bold white",
        )
        campaign_text.append(
            f"ASCENSION 해금: {ascension_unlocked}/20\n",
            style="bold white",
        )
        state_str = "CLEAR" if campaign.get("cleared", False) else "IN PROGRESS (100h target)"
        state_style = "bold green" if campaign.get("cleared", False) else "bold yellow"
        campaign_text.append(f"상태: {state_str}", style=state_style)
        console.print(
            Panel(
                campaign_text,
                title="LONG CAMPAIGN",
                title_align="left",
                border_style="cyan",
            )
        )

    if achievement_snapshot:
        achievement_text = Text()
        achievement_text.append(
            f"해금 업적: {achievement_snapshot.get('unlocked_count', 0)} / "
            f"{achievement_snapshot.get('total_count', 0)}\n",
            style="bold yellow",
        )
        unlocked_entries = achievement_snapshot.get("unlocked_entries", [])
        if isinstance(unlocked_entries, list) and unlocked_entries:
            recent_titles = [str(item.get("title", "")) for item in unlocked_entries[-3:] if isinstance(item, dict)]
            achievement_text.append(
                "최근 해금: " + " | ".join(recent_titles),
                style="bold white",
            )
        else:
            achievement_text.append("최근 해금: 없음", style="bold white")
        console.print(
            Panel(
                achievement_text,
                title="ACHIEVEMENTS",
                title_align="left",
                border_style="yellow",
            )
        )

    menu_text = Text()
    menu_text.append("[1] 게임 시작\n", style="bold green")
    menu_text.append("[2] 상점 진입\n", style="bold white")
    menu_text.append("[3] 종료\n", style="bold white")
    daily_tag = " [도전 가능!]" if daily_available else " [완료]"
    menu_text.append(f"[4] DAILY CHALLENGE{daily_tag}\n", style="bold cyan")
    menu_text.append("[5] 기록 보기\n", style="dim white")
    menu_text.append("[6] 튜토리얼\n", style="dim white")
    menu_text.append("[7] 슬롯 변경", style="dim white")
    console.print(
        Panel(
            menu_text,
            title="MAIN MENU",
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
    console.print("[bold green]>>> HACKER PERK SHOP[/bold green]")
    console.print(f"[bold white]보유 데이터 조각: {data_fragments}[/bold white]")
    console.print()

    table = Table(show_header=True, header_style="bold green")
    table.add_column("번호", style="bold white", width=6)
    table.add_column("특성명", style="bold white")
    table.add_column("효과", style="white")
    table.add_column("비용", style="bold white", width=8)
    table.add_column("상태", style="bold white", width=8)

    if perk_menu_map and perk_label_map:
        # 동적 행 생성: PERK_MENU_MAP 순서대로 렌더링
        for menu_num, perk_key in sorted(perk_menu_map.items(), key=lambda x: x[0]):
            label = perk_label_map.get(perk_key, perk_key)
            desc = (perk_desc_map or {}).get(perk_key, "-")
            price = perk_prices.get(perk_key, 0)
            owned = perks.get(perk_key, False)
            status_str = "[bold green]보유[/bold green]" if owned else "미보유"
            table.add_row(menu_num, label, desc, str(price), status_str)
    else:
        # 폴백: 기존 3개 특성 하드코딩
        table.add_row(
            "1",
            "오류 허용 버퍼",
            "오답 시 추적도 상승량 15% 감소",
            str(perk_prices.get("penalty_reduction", 50)),
            "보유" if perks.get("penalty_reduction", False) else "미보유",
        )
        table.add_row(
            "2",
            "타임 익스텐션",
            "입력 제한 시간 30초 → 40초",
            str(perk_prices.get("time_extension", 30)),
            "보유" if perks.get("time_extension", False) else "미보유",
        )
        table.add_row(
            "3",
            "글리치 필터",
            "Hard 글리치 마스킹 단어 수 1개로 완화",
            str(perk_prices.get("glitch_filter", 20)),
            "보유" if perks.get("glitch_filter", False) else "미보유",
        )

    table.add_row("0", "돌아가기", "로비 메뉴로 복귀", "-", "-")
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
        f"[bold #00FFFF][SYSTEM LOG] 정답 노드: {correct_answers}개 "
        f"(기본 보상: {base_reward} 조각)[/bold #00FFFF]"
    )
    if trace_final >= 0:
        trace_style = _trace_style(trace_final)
        console.print(
            f"[{trace_style}][SYSTEM LOG] 최종 추적도: {trace_final}%[/{trace_style}]"
        )
    if not is_victory:
        console.print(
            "[bold #00FFFF][WARNING] 비정상 종료(사망) 감지... "
            "보상 40% 데이터 유실 페널티 적용됨.[/bold #00FFFF]"
        )
    console.print(
        f"[bold #00FFFF][RESULT] 최종 획득 데이터 조각: {final_reward} 조각[/bold #00FFFF]"
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

    console.print("[bold white]━━━ DIVER CLASS SELECTION ━━━[/bold white]")
    console.print("[bold white]클래스를 선택하세요. 런 전체에 적용됩니다.[/bold white]\n")

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
    """데일리 챌린지 히스토리 테이블을 렌더링한다."""
    if not history:
        console.print("[dim white]데일리 챌린지 히스토리가 없습니다.[/dim white]")
        return

    table = Table(title="DAILY CHALLENGE HISTORY", border_style="cyan", header_style="bold cyan")
    table.add_column("날짜", style="white", width=12)
    table.add_column("결과", width=8)
    table.add_column("점수", style="bold yellow", justify="right", width=8)
    table.add_column("클리어", justify="center", width=6)
    table.add_column("TRACE", justify="center", width=6)
    table.add_column("클래스", width=8)

    for entry in reversed(history[-10:]):  # 최신 10개
        victory = entry.get("is_victory", False)
        result_str = "[green]WIN[/green]" if victory else "[red]FAIL[/red]"
        table.add_row(
            str(entry.get("date", "")),
            result_str,
            f"{entry.get('score', 0):,}",
            str(entry.get("correct_answers", 0)),
            f"{entry.get('trace_final', 0)}%",
            str(entry.get("class_key", "")),
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


def render_records_screen(
    achievement_snapshot: dict[str, Any],
    endings_snapshot: dict[str, Any],
    campaign_snapshot: dict[str, Any],
    daily_state: dict[str, Any],
    stats_snapshot: dict[str, Any] | None = None,
) -> None:
    """
    로비 '기록 보기' 통합 화면 — 캠페인·업적·엔딩·데일리 현황을 한 번에 표시한다.
    """
    console.print()
    console.rule("[bold white]RECORDS[/bold white]")

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

    console.rule()
