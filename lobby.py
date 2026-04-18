"""로비 루프, 상점, 클래스/어센션 선택 UI 모듈.

run_lobby_loop()가 게임의 최상위 상태 머신이며, run_game_session()과
run_daily_challenge()를 Callable 인자로 주입받아 순환 임포트를 피한다.
"""

from typing import Any, Callable

from rich.prompt import Prompt

from achievement_system import evaluate_achievements, get_achievement_snapshot
from daily_challenge import get_daily_state, get_today_str, has_played_today
from data_loader import load_argos_taunts
from diver_class import CLASS_MENU_MAP, CLASS_PROFILES, DiverClass, get_class_profile
from ending_system import evaluate_ending, get_endings_snapshot, record_ending_unlock
from progression_system import (
    ASCENSION_MAX_LEVEL,
    CAMPAIGN_CLEAR_CLASS_VICTORIES,
    CAMPAIGN_CLEAR_POINTS,
    CAMPAIGN_CLEAR_TOTAL_VICTORIES,
    PERK_DESC_MAP,
    PERK_LABEL_MAP,
    PERK_MENU_MAP,
    PERK_PRICES,
    SAVE_SLOT_COUNT,
    add_run_to_history,
    apply_ascension_reward_multiplier,
    calculate_base_reward,
    calculate_campaign_gain,
    calculate_reward,
    get_all_slots_info,
    get_campaign_progress_snapshot,
    get_personal_records,
    get_run_history,
    get_run_stats_snapshot,
    load_save,
    load_save_slot,
    migrate_legacy_save,
    save_game,
    save_game_slot,
    update_campaign_progress,
    update_personal_records,
    update_run_stats,
)
from i18n import LANGUAGE_LABEL_MAP, SUPPORTED_LANGUAGES, get_language, set_language as set_i18n_language, t
from theme_system import THEME_LABEL_MAP, VALID_THEMES
from ui_renderer import (
    console,
    get_current_theme_name,
    render_achievement_unlocks,
    render_alert,
    render_class_selection,
    render_ending,
    render_lobby,
    render_logo,
    render_personal_records,
    render_records_screen,
    render_run_history,
    render_save_slot_selection,
    render_settlement_log,
    render_shop,
    set_argos_taunts,
    set_theme,
    wait_for_enter,
)


# ── 초기화 ──────────────────────────────────────────────────────────────────────

def initialize_argos_taunts() -> None:
    """아르고스 대사 데이터를 로드해 UI 모듈에 주입한다."""
    try:
        taunts = load_argos_taunts("argos_taunts.json")
        set_argos_taunts(taunts)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold yellow]아르고스 대사 로드 실패: {exc}[/bold yellow]")
        set_argos_taunts({})


# ── 튜토리얼 ────────────────────────────────────────────────────────────────────

_TUTORIAL_STEPS: list[tuple[str, str]] = [
    (
        "STEP 1 — 세계관 소개",
        "[bold white]당신은 [bold #00FFFF]데이터 다이버[/bold #00FFFF]입니다.[/bold white]\n\n"
        "ARGOS 시스템이 지배하는 디지털 네트워크에 침투해\n"
        "각 노드의 수사 조서에서 논리적 결함을 찾아내야 합니다.\n\n"
        "핵심 목표: [bold green]7개 노드 + 보스[/bold green]를 모두 클리어해\n"
        "[bold red]추적도(Trace)[/bold red]가 100%가 되기 전에 CORE를 뚫어라.",
    ),
    (
        "STEP 2 — cat log: 로그 읽기",
        "[bold white]cat log[/bold white] 명령으로 현재 노드의 수사 조서를 확인합니다.\n\n"
        "예시:\n"
        "[bold green]root@argos:~# cat log[/bold green]\n\n"
        "조서를 꼼꼼히 읽고 날짜·사실·논리 오류를 찾으세요.\n"
        "타이머가 작동 중이므로 빠르게 분석하는 것이 중요합니다.",
    ),
    (
        "STEP 3 — analyze: 정답 제출",
        "[bold white]analyze [키워드][/bold white] 명령으로 논리적 결함의 핵심 단어를 제출합니다.\n\n"
        "예시:\n"
        "[bold green]root@argos:~# analyze GPS[/bold green]\n\n"
        "• 정답: [bold green]추적도 변화 없음[/bold green] + 다음 노드 진입\n"
        "• 오답: [bold red]추적도 상승[/bold red] (penalty_rate%만큼)\n"
        "• 추적도 100% 도달 = [bold red]SYSTEM SHUTDOWN (사망)[/bold red]",
    ),
    (
        "STEP 4 — 보조 명령어",
        "[bold white]ls[/bold white]       현재 노드 테마/난이도 확인\n"
        "[bold white]help[/bold white]     사용 가능한 명령어 전체 목록\n"
        "[bold white]clear[/bold white]    화면 정리 (로그 재출력)\n"
        "[bold white]skill[/bold white]    [bold #00FFFF]액티브 스킬 발동[/bold #00FFFF] — 런당 1회, 클래스별 효과 상이\n\n"
        "  ANALYST : 첫 두 글자 힌트 공개\n"
        "  GHOST   : 추적도 즉시 -15%\n"
        "  CRACKER : 다음 오답 페널티 면제",
    ),
    (
        "STEP 5 — 루트 선택과 특수 노드",
        "각 노드 클리어 후 다음 경로(A/B)를 선택합니다.\n\n"
        "[bold yellow]ELITE[/bold yellow]   페널티 ×1.5, 클리어 시 [bold #00FFFF]아티팩트[/bold #00FFFF] 선택권\n"
        "[bold cyan]REST[/bold cyan]    추적도 20% 회복\n"
        "[bold white]SHOP[/bold white]    데이터 조각으로 아이템 구매\n"
        "[bold magenta]MYSTERY[/bold magenta] 선택지 이벤트 — 개입/무시 결정\n\n"
        "전략적으로 경로를 선택해 추적도를 관리하세요.",
    ),
    (
        "STEP 6 — 성장 시스템",
        "[bold #FFD700]데이터 조각[/bold #FFD700] — 노드 클리어마다 획득, 로비 상점에서 퍼크 구매\n"
        "[bold #00FFFF]퍼크[/bold #00FFFF]      — 영구 패시브 강화 (패널티 감소, 시간 연장 등) 13종\n"
        "[bold magenta]아티팩트[/bold magenta]  — 런 중 일시적 강화 효과 28종\n"
        "[bold white]어센션[/bold white]  — 클리어할수록 해금되는 고난이도 모드 (최대 20단계)\n\n"
        "캠페인 클리어 조건을 달성하면 진엔딩이 해금됩니다.",
    ),
    (
        "튜토리얼 완료",
        "[bold green]준비 완료.[/bold green]\n\n"
        "메인 메뉴에서 [bold white][1] 게임 시작[/bold white]을 선택하면\n"
        "클래스 선택 후 바로 첫 런이 시작됩니다.\n\n"
        "[dim]로비 메뉴 [bold white][6] 튜토리얼[/bold white] 에서 언제든 다시 볼 수 있습니다.[/dim]",
    ),
]


def run_tutorial(save_data: dict[str, Any], slot: int = 0) -> None:
    """
    튜토리얼 안내 화면을 순서대로 표시한다.

    각 스텝은 패널 + Enter로 진행하며, 마지막 스텝 완료 후
    save_data["tutorial_completed"] = True를 설정하고 저장한다.

    Args:
        save_data: 현재 세이브 데이터 (직접 수정됨)
        slot: 저장할 슬롯 번호 (0이면 기본 경로 save_game 사용)
    """
    from rich.panel import Panel

    console.clear()
    render_logo()
    console.print("[bold cyan]◀ TUTORIAL ▶[/bold cyan]  — 각 화면을 읽고 Enter를 누르세요\n")

    for title, body in _TUTORIAL_STEPS:
        console.print(Panel(body, title=title, title_align="left", border_style="cyan", padding=(1, 2)))
        wait_for_enter()
        console.print()

    save_data["tutorial_completed"] = True
    try:
        if slot > 0:
            save_game_slot(save_data, slot)
        else:
            save_game(save_data)
    except OSError:
        pass  # 저장 실패해도 플레이에 영향 없음


# ── 선택 UI ─────────────────────────────────────────────────────────────────────

def select_diver_class() -> DiverClass:
    """게임 시작 전 다이버 클래스를 선택하는 UI를 표시하고 선택된 클래스를 반환한다."""
    console.clear()
    render_logo()
    profiles = list(CLASS_PROFILES.values())
    render_class_selection(profiles)

    choice = Prompt.ask(
        "[bold white]클래스 번호를 선택하세요[/bold white]",
        choices=list(CLASS_MENU_MAP.keys()),
        default="1",
    )
    selected = CLASS_MENU_MAP[choice]
    profile = get_class_profile(selected)
    console.print(
        f"\n[bold white]클래스 선택: [{profile.diver_class.value}] {profile.name}[/bold white]"
    )
    wait_for_enter()
    return selected


def select_ascension_level(save_data: dict[str, Any]) -> int:
    """시작 전 사용할 각성 레벨(Ascension)을 선택한다.

    해금된 최대 레벨까지만 선택 가능하다.
    """
    campaign = save_data.get("campaign", {})
    if not isinstance(campaign, dict):
        campaign = {}
    unlocked = int(campaign.get("ascension_unlocked", 0))
    unlocked = max(0, min(ASCENSION_MAX_LEVEL, unlocked))

    console.clear()
    render_logo()
    console.print("[bold white]━━━ ASCENSION SELECTION ━━━[/bold white]")
    console.print(
        f"[bold white]현재 해금: 0 ~ {unlocked}[/bold white] "
        "[dim](승리 시 현재 레벨 이상 클리어하면 다음 레벨 해금)[/dim]"
    )
    console.print(
        "[bold white]주요 규칙: ASC 1(+5 페널티), ASC 3(제한시간 단축), ASC 5(시작 TRACE 20), "
        "ASC 10+(상점가↑/보상↓/보스 강화), ASC 18+(보스 멀티 페이즈), "
        "ASC 20(보스 페이즈 명령 잠금/시나리오 변조)[/bold white]\n"
    )

    choices = [str(i) for i in range(unlocked + 1)]
    selected = int(
        Prompt.ask(
            "[bold white]각성 레벨을 선택하세요[/bold white]",
            choices=choices,
            default=str(unlocked),
        )
    )
    console.print(f"[bold cyan]ASCENSION {selected} 선택[/bold cyan]")
    wait_for_enter()
    return selected


# ── 상점 ─────────────────────────────────────────────────────────────────────────

def run_shop(save_data: dict[str, Any], slot: int = 0) -> None:
    """로비 상점 루프를 실행한다.

    Args:
        save_data: 현재 세이브 데이터 (직접 수정됨)
        slot: 저장할 슬롯 번호 (0이면 기본 경로 save_game 사용)
    """
    valid_choices = list(PERK_MENU_MAP.keys()) + ["0"]

    def _save() -> None:
        if slot > 0:
            save_game_slot(save_data, slot)
        else:
            save_game(save_data)

    while True:
        console.clear()
        render_shop(
            data_fragments=save_data["data_fragments"],
            perks=save_data["perks"],
            perk_prices=PERK_PRICES,
            perk_menu_map=PERK_MENU_MAP,
            perk_label_map=PERK_LABEL_MAP,
            perk_desc_map=PERK_DESC_MAP,
        )
        choice = Prompt.ask(
            "[bold green]구매할 특성 번호를 선택하세요 (0: 로비 복귀)[/bold green]",
            choices=valid_choices,
            default="0",
        )

        if choice == "0":
            return

        perk_key = PERK_MENU_MAP[choice]
        perk_label = PERK_LABEL_MAP.get(perk_key, perk_key)
        perk_price = PERK_PRICES.get(perk_key, 999999)

        if save_data["perks"].get(perk_key, False):
            console.print("[bold yellow]이미 구매한 특성입니다.[/bold yellow]")
            wait_for_enter()
            continue

        if save_data["data_fragments"] < perk_price:
            console.print(
                f"[bold red]데이터 조각이 부족합니다. (필요: {perk_price})[/bold red]"
            )
            wait_for_enter()
            continue

        prev_fragments = save_data["data_fragments"]
        prev_owned = save_data["perks"].get(perk_key, False)

        save_data["data_fragments"] -= perk_price
        save_data["perks"][perk_key] = True

        try:
            _save()
            console.print(f"[bold green]특성 구매 완료: {perk_label}[/bold green]")
        except OSError as exc:
            save_data["data_fragments"] = prev_fragments
            save_data["perks"][perk_key] = prev_owned
            console.print(f"[bold red]{exc}[/bold red]")

        wait_for_enter()


# ── 슬롯 선택 ────────────────────────────────────────────────────────────────────

def select_save_slot() -> int:
    """세이브 슬롯 선택 화면을 표시하고 선택된 슬롯 번호를 반환한다."""
    console.clear()
    render_logo()
    slots_info = get_all_slots_info()
    render_save_slot_selection(slots_info)
    choices = [str(s) for s in range(1, SAVE_SLOT_COUNT + 1)]
    choice = Prompt.ask(
        "[bold green]슬롯을 선택하세요[/bold green]",
        choices=choices,
        default="1",
    )
    return int(choice)


# ── 테마 선택 ────────────────────────────────────────────────────────────────────

def select_theme(save_data: dict[str, Any], slot: int = 0) -> None:
    """테마 선택 화면을 표시하고 선택된 테마를 세이브에 반영한다.

    Args:
        save_data: 현재 세이브 데이터 (직접 수정됨)
        slot: 저장할 슬롯 번호 (0이면 기본 경로 save_game 사용)
    """
    from rich.panel import Panel

    console.clear()
    render_logo()
    current = get_current_theme_name()
    current_label = THEME_LABEL_MAP.get(current, current)
    console.print(f"[bold cyan]현재 테마: {current_label}[/bold cyan]\n")
    theme_lines = "\n".join(
        f"  [bold white]{key}[/bold white] — {label}"
        for key, label in THEME_LABEL_MAP.items()
    )
    console.print(Panel(theme_lines, title="THEME SELECTION", title_align="left", border_style="cyan"))
    console.print()
    choices = list(THEME_LABEL_MAP.keys())
    choice = Prompt.ask(
        "[bold green]테마를 선택하세요[/bold green]",
        choices=choices,
        default=current,
    )
    save_data["theme"] = choice
    set_theme(choice)
    chosen_label = THEME_LABEL_MAP.get(choice, choice)
    console.print(f"[bold green]테마 변경 완료: {chosen_label}[/bold green]")
    try:
        if slot > 0:
            save_game_slot(save_data, slot)
        else:
            save_game(save_data)
    except OSError:
        pass
    wait_for_enter()


# ── 언어 선택 ────────────────────────────────────────────────────────────────────

def select_language(save_data: dict[str, Any], slot: int = 0) -> None:
    """언어 선택 화면을 표시하고 선택된 언어를 세이브에 반영한다.

    Args:
        save_data: 현재 세이브 데이터 (직접 수정됨)
        slot: 저장할 슬롯 번호 (0이면 기본 경로 save_game 사용)
    """
    from rich.panel import Panel

    console.clear()
    render_logo()
    current = get_language()
    current_label = LANGUAGE_LABEL_MAP.get(current, current)
    console.print(t("language.current", label=current_label) + "\n")

    lang_lines = "\n".join(
        f"  [bold white]{code}[/bold white] — {label}"
        for code, label in LANGUAGE_LABEL_MAP.items()
        if code in SUPPORTED_LANGUAGES
    )
    console.print(Panel(lang_lines, title=t("language.title"), title_align="left", border_style="blue"))
    console.print()

    choices = [c for c in LANGUAGE_LABEL_MAP if c in SUPPORTED_LANGUAGES]
    choice = Prompt.ask(
        t("lobby.prompt.language"),
        choices=choices,
        default=current,
    )
    set_i18n_language(choice)
    save_data["language"] = choice
    chosen_label = LANGUAGE_LABEL_MAP.get(choice, choice)
    console.print(t("language.changed", label=chosen_label))
    try:
        if slot > 0:
            save_game_slot(save_data, slot)
        else:
            save_game(save_data)
    except OSError:
        pass
    wait_for_enter()


# ── 로비 루프 ────────────────────────────────────────────────────────────────────

def run_lobby_loop(
    game_session_fn: Callable[..., tuple[int, bool, str, list[str], dict[str, Any]]],
    daily_challenge_fn: Callable[[dict[str, Any]], None],
) -> None:
    """게임 전체 상태 머신 (슬롯 선택 → 로비 → 런/상점 → 로비)을 실행한다.

    Args:
        game_session_fn: run_game_session() 함수 (순환 임포트 방지를 위해 주입)
        daily_challenge_fn: run_daily_challenge() 함수 (동일 이유로 주입)
    """
    initialize_argos_taunts()
    migrate_legacy_save()

    current_slot = select_save_slot()

    def _save(data: dict[str, Any]) -> None:
        """현재 슬롯에 저장한다. 실패 시 오류를 콘솔에 출력한다."""
        try:
            save_game_slot(data, current_slot)
        except OSError as exc:
            console.print(f"[bold red]{exc}[/bold red]")

    while True:
        save_data = load_save_slot(current_slot)

        # 세이브에 저장된 테마와 언어를 로드해 UI에 반영한다
        set_theme(save_data.get("theme", "default"))
        set_i18n_language(save_data.get("language", "ko"))

        # 첫 실행(tutorial_completed=False) 시 자동으로 튜토리얼 진입
        if not save_data.get("tutorial_completed", False):
            run_tutorial(save_data, slot=current_slot)
            continue

        console.clear()
        daily_state = get_daily_state(save_data)
        today_played = has_played_today(daily_state, get_today_str())
        ach_snap = get_achievement_snapshot(save_data.get("achievements", {}))
        render_lobby(
            data_fragments=save_data["data_fragments"],
            perks=save_data["perks"],
            campaign=save_data.get("campaign"),
            achievement_snapshot=ach_snap,
            daily_available=not today_played,
        )

        menu_choice = Prompt.ask(
            f"[bold green]{t('lobby.prompt.menu')}[/bold green]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            default="1",
        )

        if menu_choice == "1":
            selected_class = select_diver_class()
            selected_ascension = select_ascension_level(save_data)
            correct_answers, is_victory, result, node_difficulties_cleared, run_stats = game_session_fn(
                save_data["perks"],
                save_data,
                diver_class=selected_class,
                ascension_level=selected_ascension,
            )

            base_reward = calculate_base_reward(node_difficulties_cleared)
            reward = calculate_reward(
                correct_answers=correct_answers,
                is_victory=is_victory,
                node_difficulties=node_difficulties_cleared,
            )
            reward_before_asc = reward
            reward, reward_mult = apply_ascension_reward_multiplier(
                reward,
                selected_ascension,
            )
            save_data["data_fragments"] += reward

            campaign_gain = 0
            campaign_update = {"just_cleared": False, "campaign": save_data.get("campaign", {})}
            if result != "aborted":
                campaign_gain = calculate_campaign_gain(reward, is_victory)
                campaign_update = update_campaign_progress(
                    save_data=save_data,
                    gain=campaign_gain,
                    is_victory=is_victory,
                    class_key=selected_class.value,
                    ascension_level=selected_ascension,
                )

            # 누적 통계 + 런 히스토리 업데이트 (result != "aborted"인 경우만)
            if result != "aborted":
                update_run_stats(
                    save_data=save_data,
                    is_victory=is_victory,
                    final_trace=run_stats.get("trace_final", 100),
                    ascension_level=selected_ascension,
                )
                add_run_to_history(
                    save_data,
                    date=get_today_str(),
                    class_key=selected_class.value,
                    ascension=selected_ascension,
                    result=result,
                    trace_final=run_stats.get("trace_final", 100),
                    reward=reward,
                    correct_answers=correct_answers,
                )
                update_personal_records(
                    save_data,
                    class_key=selected_class.value,
                    ascension=selected_ascension,
                    result=result,
                    trace_final=run_stats.get("trace_final", 100),
                    reward=reward,
                    correct_answers=correct_answers,
                )

            _save(save_data)

            if result == "shutdown":
                console.print(f"[bold red]{t('lobby.shutdown_msg')}[/bold red]")
            elif result == "victory":
                console.print(f"[bold green]{t('lobby.victory_msg')}[/bold green]")
            else:
                console.print(f"[bold yellow]{t('lobby.abort_msg')}[/bold yellow]")

            render_settlement_log(
                correct_answers=correct_answers,
                base_reward=base_reward,
                final_reward=reward,
                is_victory=is_victory,
                trace_final=run_stats.get("trace_final", -1),
            )
            if reward_mult < 1.0 and reward_before_asc != reward:
                console.print(
                    f"[bold yellow][ASCENSION TAX] 보상 배율 ×{reward_mult:.2f} 적용: "
                    f"{reward_before_asc} -> {reward}[/bold yellow]"
                )

            campaign_snapshot = get_campaign_progress_snapshot(campaign_update["campaign"])
            class_victories = campaign_snapshot["class_victories"]
            console.print(
                f"[bold #00FFFF][SYSTEM LOG] 캠페인 점수 +{campaign_gain} "
                f"→ {campaign_snapshot['points']}/{CAMPAIGN_CLEAR_POINTS}[/bold #00FFFF]"
            )
            console.print(
                f"[bold #00FFFF][SYSTEM LOG] 캠페인 승리: "
                f"{campaign_snapshot['victories']}/{CAMPAIGN_CLEAR_TOTAL_VICTORIES}[/bold #00FFFF]"
            )
            console.print(
                "[bold #00FFFF][SYSTEM LOG] 클래스 숙련: "
                f"ANALYST {class_victories.get('ANALYST', 0)}/{CAMPAIGN_CLEAR_CLASS_VICTORIES} | "
                f"GHOST {class_victories.get('GHOST', 0)}/{CAMPAIGN_CLEAR_CLASS_VICTORIES} | "
                f"CRACKER {class_victories.get('CRACKER', 0)}/{CAMPAIGN_CLEAR_CLASS_VICTORIES}"
                "[/bold #00FFFF]"
            )
            if campaign_update["just_cleared"]:
                render_alert(
                    "TRUE ENDING UNLOCKED - 100H CAMPAIGN CLEAR\n"
                    "ARGOS CORE 완전 침묵. 장기 침투 작전 종료."
                )

            # ── 엔딩 / 업적 평가 및 표시 ─────────────────────────────────────
            if result != "aborted":
                run_summary = {
                    "result": result,
                    "is_victory": is_victory,
                    "class_key": selected_class.value,
                    "ascension_level": selected_ascension,
                    "wrong_analyzes": run_stats.get("wrong_analyzes", 0),
                    "timeout_events": run_stats.get("timeout_events", 0),
                    "trace_final": run_stats.get("trace_final", 100),
                    "correct_answers": correct_answers,
                    "cleared_difficulties": node_difficulties_cleared,
                    "skill_used": bool(run_stats.get("skill_used", False)),
                    "mystery_engaged": run_stats.get("mystery_engaged", 0),
                    "mystery_good": run_stats.get("mystery_good", 0),
                    "mystery_skipped": run_stats.get("mystery_skipped", 0),
                    "artifacts_held": run_stats.get("artifacts_held", 0),
                    "max_trace_reached": run_stats.get("max_trace_reached", 0),
                    "perks_count": sum(1 for v in save_data.get("perks", {}).values() if bool(v)),
                    "cascade_triggered": run_stats.get("cascade_triggered", False),
                    "void_scanner_used": run_stats.get("void_scanner_used", False),
                    "mystery_frags_gained": run_stats.get("mystery_frags_gained", 0),
                }
                # 엔딩 판정
                triggered_ending = evaluate_ending(run_summary, save_data)
                if triggered_ending:
                    is_new_ending = record_ending_unlock(save_data, triggered_ending.ending_id)
                    render_ending(triggered_ending, is_new=is_new_ending)
                    # 엔딩 해금 후 most_seen_ending 갱신
                    update_run_stats(
                        save_data=save_data,
                        is_victory=is_victory,
                        final_trace=run_stats.get("trace_final", 100),
                        ascension_level=selected_ascension,
                        ending_id=triggered_ending.ending_id,
                    )
                    _save(save_data)

                newly_unlocked = evaluate_achievements(save_data, run_summary)
                if newly_unlocked:
                    render_achievement_unlocks(newly_unlocked)
                    _save(save_data)

            wait_for_enter(t("records.press_enter"))
            continue

        if menu_choice == "2":
            run_shop(save_data, slot=current_slot)
            continue

        if menu_choice == "3":
            console.print(f"[bold white]{t('lobby.exit_msg')}[/bold white]")
            break

        if menu_choice == "4":
            daily_challenge_fn(save_data)
            continue

        if menu_choice == "5":
            ach_snap = get_achievement_snapshot(save_data.get("achievements", {}))
            end_snap = get_endings_snapshot(save_data)
            camp_snap = get_campaign_progress_snapshot(save_data.get("campaign", {}))
            daily_snap = get_daily_state(save_data)
            stats_snap = get_run_stats_snapshot(save_data.get("stats", {}))
            history = get_run_history(save_data)
            rec_snap = get_personal_records(save_data)
            render_records_screen(
                ach_snap, end_snap, camp_snap, daily_snap, stats_snap,
                run_history=history, personal_records=rec_snap,
            )
            wait_for_enter(t("records.press_enter"))
            continue

        if menu_choice == "6":
            # 튜토리얼 다시 보기 — 플래그 초기화 후 재진입
            save_data["tutorial_completed"] = False
            run_tutorial(save_data, slot=current_slot)
            continue

        if menu_choice == "7":
            # 슬롯 변경 — 슬롯 선택 화면으로 돌아감
            current_slot = select_save_slot()
            continue

        if menu_choice == "8":
            select_theme(save_data, slot=current_slot)
            continue

        if menu_choice == "9":
            select_language(save_data, slot=current_slot)
            continue
