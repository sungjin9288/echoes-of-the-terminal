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
    apply_ascension_reward_multiplier,
    calculate_base_reward,
    calculate_campaign_gain,
    calculate_reward,
    get_campaign_progress_snapshot,
    load_save,
    save_game,
    update_campaign_progress,
)
from ui_renderer import (
    console,
    render_achievement_unlocks,
    render_alert,
    render_class_selection,
    render_ending,
    render_lobby,
    render_logo,
    render_records_screen,
    render_settlement_log,
    render_shop,
    set_argos_taunts,
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

def run_shop(save_data: dict[str, Any]) -> None:
    """로비 상점 루프를 실행한다."""
    valid_choices = list(PERK_MENU_MAP.keys()) + ["0"]

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
            save_game(save_data)
            console.print(f"[bold green]특성 구매 완료: {perk_label}[/bold green]")
        except OSError as exc:
            save_data["data_fragments"] = prev_fragments
            save_data["perks"][perk_key] = prev_owned
            console.print(f"[bold red]{exc}[/bold red]")

        wait_for_enter()


# ── 로비 루프 ────────────────────────────────────────────────────────────────────

def run_lobby_loop(
    game_session_fn: Callable[..., tuple[int, bool, str, list[str], dict[str, Any]]],
    daily_challenge_fn: Callable[[dict[str, Any]], None],
) -> None:
    """게임 전체 상태 머신 (로비 → 런/상점 → 로비)을 실행한다.

    Args:
        game_session_fn: run_game_session() 함수 (순환 임포트 방지를 위해 주입)
        daily_challenge_fn: run_daily_challenge() 함수 (동일 이유로 주입)
    """
    initialize_argos_taunts()

    while True:
        save_data = load_save()

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
            "[bold green]메뉴를 선택하세요[/bold green]",
            choices=["1", "2", "3", "4", "5"],
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

            try:
                save_game(save_data)
            except OSError as exc:
                console.print(f"[bold red]{exc}[/bold red]")

            if result == "shutdown":
                console.print("[bold red]세션 종료: SYSTEM SHUTDOWN[/bold red]")
            elif result == "victory":
                console.print("[bold green]세션 종료: CORE BREACHED[/bold green]")
            else:
                console.print("[bold yellow]세션이 비정상적으로 중단되었습니다.[/bold yellow]")

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
                    try:
                        save_game(save_data)
                    except OSError as exc:
                        console.print(f"[bold red]{exc}[/bold red]")

                newly_unlocked = evaluate_achievements(save_data, run_summary)
                if newly_unlocked:
                    render_achievement_unlocks(newly_unlocked)
                    try:
                        save_game(save_data)
                    except OSError as exc:
                        console.print(f"[bold red]{exc}[/bold red]")

            wait_for_enter("로비로 복귀하려면 Enter를 누르세요")
            continue

        if menu_choice == "2":
            run_shop(save_data)
            continue

        if menu_choice == "3":
            console.print("[bold white]세션을 종료합니다.[/bold white]")
            break

        if menu_choice == "4":
            daily_challenge_fn(save_data)
            continue

        if menu_choice == "5":
            ach_snap = get_achievement_snapshot(save_data.get("achievements", {}))
            end_snap = get_endings_snapshot(save_data)
            camp_snap = get_campaign_progress_snapshot(save_data.get("campaign", {}))
            daily_snap = get_daily_state(save_data)
            render_records_screen(ach_snap, end_snap, camp_snap, daily_snap)
            wait_for_enter("로비로 복귀하려면 Enter를 누르세요")
            continue
