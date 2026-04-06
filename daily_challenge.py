"""데일리 챌린지 시스템 — 날짜 기반 고정 시드 런 + 결과 기록."""

from __future__ import annotations

import hashlib
import random
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any


# ── 데일리 챌린지 상수 ───────────────────────────────────────────────────────
DAILY_HISTORY_MAX: int = 30          # 최대 보관 히스토리 수
DAILY_SEED_SALT: str = "ARGOS_DAILY" # 시드 결정성 보장용 솔트
DAILY_BONUS_MULTIPLIER: float = 1.5  # 데일리 보상 배율


def get_today_str(tz: timezone = timezone.utc) -> str:
    """UTC 기준 오늘 날짜를 YYYY-MM-DD 형식으로 반환한다."""
    return datetime.now(tz).strftime("%Y-%m-%d")


def get_daily_seed(date_str: str) -> int:
    """
    날짜 문자열로부터 결정적인(deterministic) 정수 시드를 생성한다.

    동일한 날짜는 항상 동일한 시드를 반환하므로,
    모든 플레이어가 같은 시나리오 풀을 경험하게 된다.

    Args:
        date_str: "YYYY-MM-DD" 형식 날짜 문자열

    Returns:
        재현 가능한 양의 정수 시드
    """
    raw = f"{DAILY_SEED_SALT}:{date_str}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    # 첫 8바이트(16 hex chars)를 정수로 변환 → 충분한 엔트로피
    return int(digest[:16], 16)


def select_daily_scenarios(
    all_scenarios: list[dict[str, Any]],
    date_str: str,
    num_combat: int = 7,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    날짜 시드로 결정적으로 시나리오를 선택한다.

    Args:
        all_scenarios: 전체 시나리오 목록
        date_str: 오늘 날짜 문자열
        num_combat: 일반 노드 수 (기본 7)

    Returns:
        (combat_pool, boss_scenario)
        - combat_pool: 일반 전투 노드 시나리오 목록
        - boss_scenario: 보스 시나리오 (없으면 None)
    """
    seed = get_daily_seed(date_str)
    rng = random.Random(seed)

    normal = [s for s in all_scenarios if not s.get("is_boss", False)]
    bosses = [s for s in all_scenarios if s.get("is_boss", False)]

    # 난이도 비율: Easy 3, Hard 3, NIGHTMARE 1 (총 7)
    easy_pool = [s for s in normal if s.get("difficulty") == "Easy"]
    hard_pool = [s for s in normal if s.get("difficulty") == "Hard"]
    nightmare_pool = [s for s in normal if s.get("difficulty") == "NIGHTMARE"]

    # 각 풀에서 랜덤 샘플링 (시드 고정)
    n_easy = min(3, len(easy_pool))
    n_hard = min(3, len(hard_pool))
    n_nightmare = min(1, len(nightmare_pool))

    selected: list[dict[str, Any]] = []
    if easy_pool:
        selected.extend(rng.sample(easy_pool, n_easy))
    if hard_pool:
        selected.extend(rng.sample(hard_pool, n_hard))
    if nightmare_pool:
        selected.extend(rng.sample(nightmare_pool, n_nightmare))

    # 부족분은 Easy로 채움
    remaining_needed = num_combat - len(selected)
    if remaining_needed > 0:
        extra_pool = [s for s in easy_pool if s not in selected]
        extra = rng.sample(extra_pool, min(remaining_needed, len(extra_pool)))
        selected.extend(extra)

    rng.shuffle(selected)

    boss_scenario = rng.choice(bosses) if bosses else None

    return selected[:num_combat], boss_scenario


def has_played_today(daily_state: dict[str, Any], date_str: str | None = None) -> bool:
    """오늘 데일리 챌린지를 이미 플레이했는지 확인한다."""
    today = date_str or get_today_str()
    return daily_state.get("last_played_date") == today


def get_daily_state(save_data: dict[str, Any]) -> dict[str, Any]:
    """세이브 데이터에서 daily 상태를 추출하고 정규화한다."""
    raw = save_data.get("daily", {})
    if not isinstance(raw, dict):
        raw = {}
    return {
        "last_played_date": str(raw.get("last_played_date", "")),
        "history": _normalize_history(raw.get("history", [])),
        "best_score": max(0, int(raw.get("best_score", 0))),
        "streak": max(0, int(raw.get("streak", 0))),
        "total_plays": max(0, int(raw.get("total_plays", 0))),
    }


def _normalize_history(raw: Any) -> list[dict[str, Any]]:
    """히스토리 목록을 정규화한다."""
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        result.append({
            "date": str(entry.get("date", "")),
            "score": max(0, int(entry.get("score", 0))),
            "is_victory": bool(entry.get("is_victory", False)),
            "correct_answers": max(0, int(entry.get("correct_answers", 0))),
            "trace_final": max(0, int(entry.get("trace_final", 0))),
            "class_key": str(entry.get("class_key", "")),
            "wrong_analyzes": max(0, int(entry.get("wrong_analyzes", 0))),
        })
    return result[-DAILY_HISTORY_MAX:]


def calculate_daily_score(
    correct_answers: int,
    is_victory: bool,
    trace_final: int,
    wrong_analyzes: int,
    timeout_events: int,
    base_reward: int,
) -> int:
    """
    데일리 챌린지 점수를 계산한다.

    산출 공식:
    - 기본 점수 = base_reward × DAILY_BONUS_MULTIPLIER
    - 승리 보너스: +500
    - 최종 추적도 페널티: trace_final × 2 감소 (위험하게 플레이할수록 손해)
    - 오답 페널티: wrong_analyzes × 50 감소
    - 타임아웃 페널티: timeout_events × 30 감소
    - 최솟값 0 보장
    """
    score = int(base_reward * DAILY_BONUS_MULTIPLIER)
    if is_victory:
        score += 500
    score -= trace_final * 2
    score -= wrong_analyzes * 50
    score -= timeout_events * 30
    return max(0, score)


def record_daily_result(
    save_data: dict[str, Any],
    date_str: str,
    score: int,
    is_victory: bool,
    correct_answers: int,
    trace_final: int,
    class_key: str,
    wrong_analyzes: int,
) -> dict[str, Any]:
    """
    데일리 챌린지 결과를 세이브 데이터에 기록한다.

    Returns:
        업데이트된 daily_state dict
    """
    daily = get_daily_state(save_data)

    # 연속 플레이 스트릭 계산
    last = daily.get("last_played_date", "")
    if last:
        try:
            last_date = date.fromisoformat(last)
            today_date = date.fromisoformat(date_str)
            delta = (today_date - last_date).days
            if delta == 1:
                daily["streak"] = daily.get("streak", 0) + 1
            elif delta != 0:
                daily["streak"] = 1
        except ValueError:
            daily["streak"] = 1
    else:
        daily["streak"] = 1

    daily["last_played_date"] = date_str
    daily["total_plays"] = daily.get("total_plays", 0) + 1
    if score > daily.get("best_score", 0):
        daily["best_score"] = score

    # 히스토리 추가
    history = daily.get("history", [])
    history.append({
        "date": date_str,
        "score": score,
        "is_victory": is_victory,
        "correct_answers": correct_answers,
        "trace_final": trace_final,
        "class_key": class_key,
        "wrong_analyzes": wrong_analyzes,
    })
    daily["history"] = history[-DAILY_HISTORY_MAX:]

    save_data["daily"] = daily
    return daily
