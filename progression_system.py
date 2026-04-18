"""메타 진행도(재화/특성) 저장 및 정산을 담당하는 모듈."""

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from achievement_system import normalize_achievement_state
from constants import (
    DEATH_MULTIPLIER,
    REWARD_PER_EASY,
    REWARD_PER_HARD,
    REWARD_PER_NIGHTMARE,
    VICTORY_BONUS,
)


# 앱 전용 데이터 폴더 이름.
APP_DATA_DIRNAME = "Echoes of the Terminal"

# 세이브 파일 최대 허용 크기 (1 MB).
_MAX_SAVE_FILE_SIZE: int = 1 * 1024 * 1024


def _save_warn(message: str) -> None:
    """세이브 데이터 복구 경고를 터미널에 가시적으로 출력한다.

    warnings.warn()은 기본적으로 터미널 플레이어에게 보이지 않으므로
    Rich console을 통해 노란색 경고를 직접 출력한다.
    """
    from ui_renderer import console
    console.print(f"[bold yellow][SAVE] {message}[/bold yellow]")


def _get_default_save_path() -> Path:
    """
    기본 세이브 파일 절대 경로를 계산한다.

    정책:
    - Windows APPDATA가 존재하면 AppData 하위에 저장 (배포 권장 경로)
    - 그 외에는 실행 위치 기반 로컬 폴더에 저장
      - PyInstaller 실행 파일: 실행 파일이 위치한 폴더
      - 개발 환경: 현재 작업 디렉터리

    주의:
    - 절대 경로 계산 시 sys._MEIPASS는 사용하지 않는다.
      _MEIPASS는 임시 압축 해제 영역이므로 세이브 영속성에 부적합하다.
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        return (Path(appdata) / APP_DATA_DIRNAME / "save_data.json").resolve()

    if getattr(sys, "frozen", False):
        return (Path(sys.executable).resolve().parent / "save_data.json").resolve()

    return (Path.cwd() / "save_data.json").resolve()


def _resolve_save_path(file_path: str) -> Path:
    """
    세이브 파일 입력 경로를 실제 절대 경로로 변환한다.

    - 절대 경로 입력: 그대로 사용
    - 기본 파일명(save_data.json): 플랫폼 정책 경로(AppData/실행 폴더)로 라우팅
    - 그 외 상대 경로: 현재 작업 디렉터리 기준
    """
    input_path = Path(file_path)
    if input_path.is_absolute():
        return input_path

    if input_path == Path("save_data.json"):
        return _get_default_save_path()

    return (Path.cwd() / input_path).resolve()


# ── 다중 세이브 슬롯 ───────────────────────────────────────────────────────────

#: 지원하는 세이브 슬롯 수.
SAVE_SLOT_COUNT: int = 3


def _get_slot_save_path(slot: int) -> Path:
    """슬롯 번호(1~SAVE_SLOT_COUNT)에 해당하는 세이브 파일 절대 경로를 반환한다."""
    safe_slot = max(1, min(SAVE_SLOT_COUNT, int(slot)))
    filename = f"save_slot_{safe_slot}.json"
    appdata = os.getenv("APPDATA")
    if appdata:
        return (Path(appdata) / APP_DATA_DIRNAME / filename).resolve()
    if getattr(sys, "frozen", False):
        return (Path(sys.executable).resolve().parent / filename).resolve()
    return (Path.cwd() / filename).resolve()


def migrate_legacy_save() -> None:
    """기존 save_data.json이 있으면 슬롯 1로 자동 마이그레이션한다.

    이미 슬롯 1 파일이 존재하면 아무 작업도 하지 않는다.
    실패해도 게임 진행에 영향을 주지 않는다.
    """
    import shutil

    legacy_path = _get_default_save_path()
    slot1_path = _get_slot_save_path(1)
    if legacy_path.exists() and not slot1_path.exists():
        try:
            slot1_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_path, slot1_path)
        except OSError:
            pass  # 마이그레이션 실패해도 게임 계속 가능


def get_slot_info(slot: int) -> dict[str, Any]:
    """단일 슬롯의 요약 정보를 반환한다.

    Returns:
        slot: 슬롯 번호 (1~SAVE_SLOT_COUNT)
        empty: True이면 파일 없음
        corrupted: True이면 파일이 손상됨
        data_fragments: 보유 데이터 조각
        campaign_victories: 캠페인 승리 횟수
        last_saved: 마지막 저장 날짜 (YYYY-MM-DD)
    """
    from datetime import datetime

    path = _get_slot_save_path(slot)
    if not path.exists():
        return {"slot": slot, "empty": True}
    try:
        file_size = path.stat().st_size
        if file_size > _MAX_SAVE_FILE_SIZE:
            return {"slot": slot, "empty": False, "corrupted": True}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        frags = int(data.get("data_fragments", 0))
        campaign = data.get("campaign", {})
        victories = int(campaign.get("victories", 0))
        mtime = path.stat().st_mtime
        last_saved = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        return {
            "slot": slot,
            "empty": False,
            "data_fragments": frags,
            "campaign_victories": victories,
            "last_saved": last_saved,
        }
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {"slot": slot, "empty": False, "corrupted": True}


def get_all_slots_info() -> list[dict[str, Any]]:
    """모든 슬롯의 요약 정보 리스트를 반환한다."""
    return [get_slot_info(s) for s in range(1, SAVE_SLOT_COUNT + 1)]


def load_save_slot(slot: int) -> dict[str, Any]:
    """슬롯 번호로 세이브 데이터를 로드한다."""
    return load_save(file_path=str(_get_slot_save_path(slot)))


def save_game_slot(data: dict[str, Any], slot: int) -> None:
    """슬롯 번호에 세이브 데이터를 저장한다."""
    save_game(data, file_path=str(_get_slot_save_path(slot)))


# ── 특성 메타데이터 (SSOT: 이 파일에서만 정의) ────────────────────────────────
# main.py와 ui_renderer.py 양쪽이 이 파일에서 임포트해 사용한다.

PERK_MENU_MAP: dict[str, str] = {
    "1": "penalty_reduction",
    "2": "time_extension",
    "3": "glitch_filter",
    "4": "backtrack_protocol",
    "5": "lexical_assist",
    "6": "node_scanner",
    "7": "trace_dampener",
    "8": "fragment_amplifier",
    "9": "elite_shield",
    "0": "keyword_echo",
    "a": "adaptive_shield",
    "b": "data_recovery",
    "c": "swift_analysis",
}

PERK_LABEL_MAP: dict[str, str] = {
    "penalty_reduction": "오류 허용 버퍼",
    "time_extension": "타임 익스텐션",
    "glitch_filter": "글리치 필터",
    "backtrack_protocol": "백트랙 프로토콜",
    "lexical_assist": "어휘 보조 모듈",
    "node_scanner": "노드 스캐너",
    "trace_dampener": "추적 완충기",
    "fragment_amplifier": "파편 증폭기",
    "elite_shield": "엘리트 실드",
    "keyword_echo": "키워드 에코",
    "adaptive_shield": "적응형 실드",
    "data_recovery": "데이터 복구",
    "swift_analysis": "신속 분석",
}

PERK_DESC_MAP: dict[str, str] = {
    "penalty_reduction": "오답 시 추적도 상승량 15% 감소",
    "time_extension": "입력 제한 시간 30초 → 40초",
    "glitch_filter": "Hard 글리치 마스킹 단어 수 1개로 완화",
    "backtrack_protocol": "사망 직전 추적도를 50%로 회복 (런당 1회)",
    "lexical_assist": "NIGHTMARE 노드 진입 시 키워드 첫 글자 힌트 공개",
    "node_scanner": "노드 진입 전 해당 노드 난이도 미리 공개",
    "trace_dampener": "타임아웃 추적도 패널티 추가 10% 감소",
    "fragment_amplifier": "런 완료 시 파편 보상 +20% 추가 지급",
    "elite_shield": "ELITE 노드 페널티 배율 상한 1.5× → 1.35×",
    "keyword_echo": "노드 정답 후 다음 노드 제한시간 +3초 보정",
    "adaptive_shield": "추적도 50% 이상 구간에서 오답 패널티 10% 추가 감소",
    "data_recovery": "런 시작 시 데이터 조각 +50 즉시 획득",
    "swift_analysis": "런당 첫 오답에 한해 패널티 50% 감소",
}

PERK_PRICES: dict[str, int] = {
    "penalty_reduction": 50,
    "time_extension": 30,
    "glitch_filter": 20,
    "backtrack_protocol": 80,
    "lexical_assist": 60,
    "node_scanner": 40,
    "trace_dampener": 45,
    "fragment_amplifier": 35,
    "elite_shield": 70,
    "keyword_echo": 65,
    "adaptive_shield": 55,
    "data_recovery": 25,
    "swift_analysis": 75,
}

# ── 장기 캠페인(100시간 목표) 메타 진행도 ───────────────────────────────────────
CAMPAIGN_TARGET_HOURS: int = 100
CAMPAIGN_CLEAR_POINTS: int = 60000
CAMPAIGN_CLEAR_TOTAL_VICTORIES: int = 450
CAMPAIGN_CLEAR_CLASS_VICTORIES: int = 120
CAMPAIGN_CLASS_KEYS: tuple[str, ...] = ("ANALYST", "GHOST", "CRACKER")
ASCENSION_MAX_LEVEL: int = 20

# 캠페인 수치 상한 — 저장 파일 조작이나 누적 오버플로로 인한 이상값을 방지한다.
_MAX_CAMPAIGN_POINTS: int = 10_000_000
_MAX_CAMPAIGN_RUNS: int = 100_000
_MAX_CAMPAIGN_VICTORIES: int = 100_000
_MAX_CAMPAIGN_CLASS_VICTORIES: int = 100_000

# ASCENSION 고정 밸런스 테이블 (0~20)
# 값 의미:
# - penalty_flat: 오답 기본 페널티 추가값
# - force_easy_glitch: Easy 노드 글리치 강제 여부
# - time_limit_delta: 제한시간 보정(초, 음수면 단축)
# - timeout_penalty_delta: 타임아웃 페널티 보정
# - start_trace: 런 시작 추적도
ASCENSION_TABLE: dict[int, dict[str, int | bool | float]] = {
    0: {"penalty_flat": 0, "force_easy_glitch": False, "time_limit_delta": 0, "timeout_penalty_delta": 0, "start_trace": 0},
    1: {"penalty_flat": 5, "force_easy_glitch": False, "time_limit_delta": 0, "timeout_penalty_delta": 0, "start_trace": 0},
    2: {"penalty_flat": 5, "force_easy_glitch": True, "time_limit_delta": 0, "timeout_penalty_delta": 0, "start_trace": 0},
    3: {"penalty_flat": 5, "force_easy_glitch": True, "time_limit_delta": -20, "timeout_penalty_delta": 0, "start_trace": 0},
    4: {"penalty_flat": 5, "force_easy_glitch": True, "time_limit_delta": -20, "timeout_penalty_delta": 4, "start_trace": 0},
    5: {"penalty_flat": 5, "force_easy_glitch": True, "time_limit_delta": -20, "timeout_penalty_delta": 4, "start_trace": 20},
    6: {"penalty_flat": 5, "force_easy_glitch": True, "time_limit_delta": -20, "timeout_penalty_delta": 4, "start_trace": 20},
    7: {"penalty_flat": 6, "force_easy_glitch": True, "time_limit_delta": -20, "timeout_penalty_delta": 4, "start_trace": 20},
    8: {"penalty_flat": 6, "force_easy_glitch": True, "time_limit_delta": -21, "timeout_penalty_delta": 4, "start_trace": 20},
    9: {"penalty_flat": 7, "force_easy_glitch": True, "time_limit_delta": -21, "timeout_penalty_delta": 5, "start_trace": 20},
    10: {"penalty_flat": 7, "force_easy_glitch": True, "time_limit_delta": -21, "timeout_penalty_delta": 5, "start_trace": 20},
    11: {"penalty_flat": 8, "force_easy_glitch": True, "time_limit_delta": -22, "timeout_penalty_delta": 5, "start_trace": 20},
    12: {"penalty_flat": 8, "force_easy_glitch": True, "time_limit_delta": -22, "timeout_penalty_delta": 5, "start_trace": 20},
    13: {"penalty_flat": 9, "force_easy_glitch": True, "time_limit_delta": -22, "timeout_penalty_delta": 6, "start_trace": 20},
    14: {"penalty_flat": 9, "force_easy_glitch": True, "time_limit_delta": -23, "timeout_penalty_delta": 6, "start_trace": 20},
    15: {"penalty_flat": 10, "force_easy_glitch": True, "time_limit_delta": -23, "timeout_penalty_delta": 6, "start_trace": 20},
    16: {"penalty_flat": 10, "force_easy_glitch": True, "time_limit_delta": -23, "timeout_penalty_delta": 6, "start_trace": 20},
    17: {"penalty_flat": 11, "force_easy_glitch": True, "time_limit_delta": -24, "timeout_penalty_delta": 7, "start_trace": 20},
    18: {"penalty_flat": 11, "force_easy_glitch": True, "time_limit_delta": -24, "timeout_penalty_delta": 7, "start_trace": 20},
    19: {"penalty_flat": 12, "force_easy_glitch": True, "time_limit_delta": -24, "timeout_penalty_delta": 7, "start_trace": 20},
    20: {"penalty_flat": 12, "force_easy_glitch": True, "time_limit_delta": -25, "timeout_penalty_delta": 7, "start_trace": 20},
}

# 세이브 파일 경로와 기본 구조를 상수로 관리해 전체 코드에서 일관성을 유지한다.
SAVE_FILE_PATH: str = str(_get_default_save_path())
DEFAULT_SAVE_DATA: dict[str, Any] = {
    "schema_version": 2,
    "tutorial_completed": False,
    "data_fragments": 0,
    "perks": {
        "penalty_reduction": False,
        "time_extension": False,
        "glitch_filter": False,
        "backtrack_protocol": False,
        "lexical_assist": False,
    },
    "campaign": {
        "points": 0,
        "runs": 0,
        "victories": 0,
        "ascension_unlocked": 0,
        "class_victories": {
            "ANALYST": 0,
            "GHOST": 0,
            "CRACKER": 0,
        },
        "cleared": False,
    },
    "achievements": {
        "unlocked": [],
    },
    "daily": {
        "last_played_date": "",
        "history": [],
        "best_score": 0,
        "streak": 0,
        "total_plays": 0,
    },
    "endings": {
        "unlocked": [],
    },
    "stats": {
        "total_runs": 0,
        "total_victories": 0,
        "total_trace_sum": 0,       # 승리 런 최종 trace 합산 (평균 계산용)
        "total_trace_counted": 0,   # 평균 계산에 포함된 런 수
        "best_ascension_cleared": 0,
        "most_seen_ending": "",
    },
    "theme": "default",
    "language": "ko",
    "run_history": [],
    "personal_records": {},
    "leaderboard": [],
}


def _normalize_campaign(raw_campaign: Any) -> dict[str, Any]:
    """캠페인 메타 진행도 구조를 정규화한다."""
    defaults = deepcopy(DEFAULT_SAVE_DATA["campaign"])
    if not isinstance(raw_campaign, dict):
        return defaults

    points = raw_campaign.get("points", 0)
    if isinstance(points, int) and 0 <= points <= _MAX_CAMPAIGN_POINTS:
        defaults["points"] = points

    runs = raw_campaign.get("runs", 0)
    if isinstance(runs, int) and 0 <= runs <= _MAX_CAMPAIGN_RUNS:
        defaults["runs"] = runs

    victories = raw_campaign.get("victories", 0)
    if isinstance(victories, int) and 0 <= victories <= _MAX_CAMPAIGN_VICTORIES:
        defaults["victories"] = victories

    ascension_unlocked = raw_campaign.get("ascension_unlocked", 0)
    if isinstance(ascension_unlocked, int):
        defaults["ascension_unlocked"] = max(0, min(ASCENSION_MAX_LEVEL, ascension_unlocked))

    class_victories = raw_campaign.get("class_victories", {})
    if isinstance(class_victories, dict):
        for class_key in CAMPAIGN_CLASS_KEYS:
            raw_value = class_victories.get(class_key, 0)
            if isinstance(raw_value, int) and 0 <= raw_value <= _MAX_CAMPAIGN_CLASS_VICTORIES:
                defaults["class_victories"][class_key] = raw_value

    defaults["cleared"] = bool(raw_campaign.get("cleared", False))
    return defaults


_CURRENT_SCHEMA_VERSION: int = 2


def _migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """schema_version 필드가 없는 구버전(v0) 세이브를 v1으로 마이그레이션한다."""
    migrated = deepcopy(data)
    migrated["schema_version"] = 1
    return migrated


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """v1 → v2: tutorial_completed 필드를 추가한다.

    기존 플레이어는 이미 게임에 익숙하므로 tutorial_completed = True로 설정해
    자동 튜토리얼 진입을 건너뛴다.
    """
    migrated = deepcopy(data)
    migrated["schema_version"] = 2
    migrated.setdefault("tutorial_completed", True)  # 기존 유저는 스킵
    return migrated


def _migrate_save(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    세이브 데이터의 schema_version을 확인하고 필요한 마이그레이션을 순차 적용한다.

    새 버전을 추가할 때는 _migrate_vN_to_vN+1() 함수를 구현하고
    이 함수의 디스패치 테이블에 등록한다.
    """
    data = deepcopy(raw_data)
    version = data.get("schema_version", 0)
    if not isinstance(version, int) or version < 0:
        version = 0

    migrations = {
        0: _migrate_v0_to_v1,
        1: _migrate_v1_to_v2,
    }

    while version < _CURRENT_SCHEMA_VERSION:
        migrate_fn = migrations.get(version)
        if migrate_fn is None:
            break
        data = migrate_fn(data)
        version = data.get("schema_version", version + 1)

    return data


def _normalize_save_data(raw_data: Any) -> dict[str, Any]:
    """
    외부에서 들어온 데이터를 세이브 스키마에 맞춰 정규화한다.

    잘못된 타입/누락 키가 있어도 기본값으로 보정하여
    게임 실행 중 KeyError가 발생하지 않도록 방어한다.
    """
    if isinstance(raw_data, dict):
        raw_data = _migrate_save(raw_data)

    data = deepcopy(DEFAULT_SAVE_DATA)
    if not isinstance(raw_data, dict):
        return data

    data["tutorial_completed"] = bool(raw_data.get("tutorial_completed", False))

    fragments = raw_data.get("data_fragments", 0)
    if isinstance(fragments, int) and fragments >= 0:
        data["data_fragments"] = fragments

    perks = raw_data.get("perks", {})
    if isinstance(perks, dict):
        for perk_name in data["perks"]:
            data["perks"][perk_name] = bool(perks.get(perk_name, False))

    data["campaign"] = _normalize_campaign(raw_data.get("campaign", {}))
    data["achievements"] = normalize_achievement_state(raw_data.get("achievements", {}))
    # daily/endings 상태는 각 모듈에서 자체 정규화하므로 raw 그대로 보존하되,
    # 호출부의 원본 dict 공유를 피하기 위해 deepcopy한다.
    raw_daily = raw_data.get("daily", {})
    if isinstance(raw_daily, dict):
        data["daily"] = deepcopy(raw_daily)
    raw_endings = raw_data.get("endings", {})
    if isinstance(raw_endings, dict):
        data["endings"] = deepcopy(raw_endings)
    raw_stats = raw_data.get("stats", {})
    if isinstance(raw_stats, dict):
        default_stats = data["stats"]
        for key in default_stats:
            raw_val = raw_stats.get(key, default_stats[key])
            if isinstance(raw_val, type(default_stats[key])):
                default_stats[key] = raw_val

    # theme: 알 수 없는 값은 기본 테마로 복원
    from theme_system import VALID_THEMES
    raw_theme = raw_data.get("theme", "default")
    data["theme"] = raw_theme if raw_theme in VALID_THEMES else "default"

    # language: 지원하지 않는 값은 기본 언어(ko)로 복원
    from i18n import SUPPORTED_LANGUAGES
    raw_lang = raw_data.get("language", "ko")
    data["language"] = raw_lang if raw_lang in SUPPORTED_LANGUAGES else "ko"

    # run_history: 리스트가 아니면 빈 리스트로 초기화
    raw_history = raw_data.get("run_history", [])
    data["run_history"] = raw_history if isinstance(raw_history, list) else []

    # personal_records: 딕셔너리가 아니면 빈 딕셔너리로 초기화
    raw_records = raw_data.get("personal_records", {})
    data["personal_records"] = raw_records if isinstance(raw_records, dict) else {}

    # leaderboard: 리스트가 아니면 빈 리스트로 초기화
    raw_board = raw_data.get("leaderboard", [])
    data["leaderboard"] = raw_board if isinstance(raw_board, list) else []

    return data


def is_campaign_cleared(campaign: dict[str, Any]) -> bool:
    """캠페인 클리어 조건(100시간 목표)을 충족했는지 판정한다."""
    points = int(campaign.get("points", 0))
    victories = int(campaign.get("victories", 0))
    class_victories = campaign.get("class_victories", {})
    if not isinstance(class_victories, dict):
        class_victories = {}

    class_condition = all(
        int(class_victories.get(class_key, 0)) >= CAMPAIGN_CLEAR_CLASS_VICTORIES
        for class_key in CAMPAIGN_CLASS_KEYS
    )
    return (
        points >= CAMPAIGN_CLEAR_POINTS
        and victories >= CAMPAIGN_CLEAR_TOTAL_VICTORIES
        and class_condition
    )



def calculate_campaign_gain(reward: int, is_victory: bool) -> int:
    """
    단일 런 결과로 얻는 캠페인 포인트를 계산한다.

    캠페인 포인트는 데이터 조각 보상 1:1로 환산된다.
    사망 시에도 벌어들인 조각만큼 누적되어 장기 플레이가 보상받는다.
    승리 시 CAMPAIGN_VICTORY_BONUS(+20)만큼 추가 포인트가 가산된다.

    Args:
        reward: 최종 지급 데이터 조각 수 (ascension 배율 적용 후)
        is_victory: 런 승리 여부

    Returns:
        캠페인 포인트 증가량 (음수 없음)
    """
    from constants import CAMPAIGN_VICTORY_BONUS
    bonus = CAMPAIGN_VICTORY_BONUS if is_victory else 0
    return max(0, int(reward) + bonus)


def update_campaign_progress(
    save_data: dict[str, Any],
    gain: int,
    is_victory: bool,
    class_key: str = "",
    ascension_level: int = 0,
) -> dict[str, Any]:
    """
    세이브 데이터에 캠페인 진행도를 반영하고 결과 스냅샷을 반환한다.

    Returns:
        just_cleared: 이번 반영으로 처음 클리어했는지 여부
        campaign: 업데이트된 캠페인 dict
    """
    if "campaign" not in save_data or not isinstance(save_data["campaign"], dict):
        save_data["campaign"] = _normalize_campaign({})
    campaign = _normalize_campaign(save_data["campaign"])

    was_cleared = bool(campaign.get("cleared", False))
    campaign["runs"] = min(_MAX_CAMPAIGN_RUNS, int(campaign.get("runs", 0)) + 1)
    campaign["points"] = min(
        _MAX_CAMPAIGN_POINTS,
        int(campaign.get("points", 0)) + max(0, int(gain)),
    )

    if is_victory:
        campaign["victories"] = min(
            _MAX_CAMPAIGN_VICTORIES, int(campaign.get("victories", 0)) + 1
        )
        if class_key in CAMPAIGN_CLASS_KEYS:
            class_victories = campaign["class_victories"]
            class_victories[class_key] = min(
                _MAX_CAMPAIGN_CLASS_VICTORIES,
                int(class_victories.get(class_key, 0)) + 1,
            )
        unlocked = int(campaign.get("ascension_unlocked", 0))
        safe_asc = max(0, min(ASCENSION_MAX_LEVEL, int(ascension_level)))
        if safe_asc >= unlocked and unlocked < ASCENSION_MAX_LEVEL:
            campaign["ascension_unlocked"] = unlocked + 1

    campaign["cleared"] = is_campaign_cleared(campaign)
    save_data["campaign"] = campaign
    return {
        "just_cleared": bool(campaign["cleared"] and not was_cleared),
        "campaign": campaign,
    }


def update_run_stats(
    save_data: dict[str, Any],
    is_victory: bool,
    final_trace: int,
    ascension_level: int,
    ending_id: str = "",
) -> None:
    """
    런 종료 후 누적 통계(stats)를 갱신한다.

    save_data를 직접 수정한다.
    """
    # 기존 stats가 비어있거나 누락된 키가 있을 수 있으므로 기본값과 병합한다.
    defaults = deepcopy(DEFAULT_SAVE_DATA["stats"])
    raw = save_data.get("stats", {})
    if not isinstance(raw, dict):
        raw = {}
    defaults.update(raw)
    stats = defaults
    save_data["stats"] = stats

    stats["total_runs"] = int(stats.get("total_runs", 0)) + 1
    if is_victory:
        stats["total_victories"] = int(stats.get("total_victories", 0)) + 1

    # 최종 trace를 평균 계산에 포함
    safe_trace = max(0, min(100, int(final_trace)))
    stats["total_trace_sum"] = int(stats.get("total_trace_sum", 0)) + safe_trace
    stats["total_trace_counted"] = int(stats.get("total_trace_counted", 0)) + 1

    if is_victory:
        best = int(stats.get("best_ascension_cleared", 0))
        stats["best_ascension_cleared"] = max(best, max(0, int(ascension_level)))

    if ending_id:
        # 가장 많이 본 엔딩 업데이트 (endings 히스토리 기반)
        endings_unlocked: list[str] = save_data.get("endings", {}).get("unlocked", [])
        if endings_unlocked:
            from collections import Counter
            most_common = Counter(endings_unlocked).most_common(1)
            stats["most_seen_ending"] = most_common[0][0] if most_common else ""


def get_run_stats_snapshot(stats: dict[str, Any]) -> dict[str, Any]:
    """UI 표시용 누적 통계 스냅샷을 반환한다."""
    total_runs = int(stats.get("total_runs", 0))
    total_victories = int(stats.get("total_victories", 0))
    win_rate = (total_victories / total_runs * 100) if total_runs > 0 else 0.0
    counted = int(stats.get("total_trace_counted", 0))
    avg_trace = (int(stats.get("total_trace_sum", 0)) / counted) if counted > 0 else 0.0
    return {
        "total_runs": total_runs,
        "total_victories": total_victories,
        "win_rate": round(win_rate, 1),
        "avg_trace": round(avg_trace, 1),
        "best_ascension_cleared": int(stats.get("best_ascension_cleared", 0)),
        "most_seen_ending": str(stats.get("most_seen_ending", "")),
    }


# ── 런 기록 히스토리 ──────────────────────────────────────────────────────────

#: 저장할 최대 런 기록 수. 오래된 항목부터 삭제된다.
RUN_HISTORY_MAX: int = 20

#: run_record 딕셔너리의 필수 필드 집합.
_RUN_RECORD_REQUIRED: frozenset[str] = frozenset({
    "date", "class_key", "ascension", "result", "trace_final", "reward",
})


def _make_run_record(
    date: str,
    class_key: str,
    ascension: int,
    result: str,
    trace_final: int,
    reward: int,
    correct_answers: int = 0,
    ending_id: str = "",
) -> dict[str, Any]:
    """run_history 항목용 딕셔너리를 생성한다 (불변 값으로 구성)."""
    return {
        "date": str(date),
        "class_key": str(class_key),
        "ascension": max(0, int(ascension)),
        "result": str(result),
        "trace_final": max(0, min(100, int(trace_final))),
        "reward": max(0, int(reward)),
        "correct_answers": max(0, int(correct_answers)),
        "ending_id": str(ending_id),
    }


def add_run_to_history(
    save_data: dict[str, Any],
    *,
    date: str,
    class_key: str,
    ascension: int,
    result: str,
    trace_final: int,
    reward: int,
    correct_answers: int = 0,
    ending_id: str = "",
) -> None:
    """런 종료 후 save_data["run_history"]에 기록을 추가한다.

    기록이 RUN_HISTORY_MAX를 초과하면 가장 오래된 항목을 삭제한다.
    save_data를 직접 수정한다.

    Args:
        save_data:       현재 세이브 데이터
        date:            실행 날짜 (YYYY-MM-DD)
        class_key:       다이버 클래스 코드 ("ANALYST" / "GHOST" / "CRACKER")
        ascension:       사용한 어센션 레벨
        result:          런 결과 ("victory" / "shutdown" / "aborted")
        trace_final:     최종 추적도 (0~100)
        reward:          최종 획득 데이터 조각
        correct_answers: 정답 노드 수
        ending_id:       발동된 엔딩 ID (없으면 빈 문자열)
    """
    history = save_data.get("run_history")
    if not isinstance(history, list):
        history = []
    record = _make_run_record(
        date=date,
        class_key=class_key,
        ascension=ascension,
        result=result,
        trace_final=trace_final,
        reward=reward,
        correct_answers=correct_answers,
        ending_id=ending_id,
    )
    updated = list(history) + [record]
    # 최대 개수 초과 시 앞에서부터 잘라낸다
    if len(updated) > RUN_HISTORY_MAX:
        updated = updated[-RUN_HISTORY_MAX:]
    save_data["run_history"] = updated


def get_run_history(save_data: dict[str, Any]) -> list[dict[str, Any]]:
    """save_data에서 런 기록 리스트를 반환한다 (최신순 — 역순).

    Returns:
        최신 런이 첫 번째인 리스트 복사본
    """
    history = save_data.get("run_history", [])
    if not isinstance(history, list):
        return []
    return list(reversed(history))

def get_campaign_progress_snapshot(campaign: dict[str, Any]) -> dict[str, Any]:
    """UI 표시에 사용할 캠페인 진행도 스냅샷을 생성한다."""
    normalized = _normalize_campaign(campaign)
    points = int(normalized["points"])
    victories = int(normalized["victories"])
    class_victories = normalized["class_victories"]

    return {
        "points": points,
        "points_target": CAMPAIGN_CLEAR_POINTS,
        "points_ratio": min(1.0, points / CAMPAIGN_CLEAR_POINTS),
        "victories": victories,
        "victories_target": CAMPAIGN_CLEAR_TOTAL_VICTORIES,
        "victories_ratio": min(1.0, victories / CAMPAIGN_CLEAR_TOTAL_VICTORIES),
        "class_victories": class_victories,
        "class_target": CAMPAIGN_CLEAR_CLASS_VICTORIES,
        "ascension_unlocked": int(normalized.get("ascension_unlocked", 0)),
        "cleared": bool(normalized["cleared"]),
        "target_hours": CAMPAIGN_TARGET_HOURS,
    }


def get_ascension_profile(level: int) -> dict[str, int | bool | float]:
    """
    각성 레벨 프로필을 반환한다.

    범위를 벗어난 입력은 0~ASCENSION_MAX_LEVEL로 클램프한다.
    """
    safe_level = max(0, min(ASCENSION_MAX_LEVEL, int(level)))
    raw = ASCENSION_TABLE.get(safe_level, ASCENSION_TABLE[0])
    shop_cost_mult = 1.0
    reward_mult = 1.0
    boss_penalty_mult = 1.0
    boss_phases = 1
    boss_phase_time_delta = 0
    boss_phase_penalty_step = 0.0
    boss_block_cat_log_from_phase = 99
    boss_block_skill_from_phase = 99
    boss_command_violation_penalty = 0
    boss_fake_keyword_count = 0
    route_elite_chance = 0.0
    route_relief_decay_chance = 0.0
    route_min_elite_choices = 0
    if safe_level >= 10:
        shop_cost_mult = 1.15
        reward_mult = 0.95
        boss_penalty_mult = 1.10
    if safe_level >= 12:
        route_elite_chance = 0.15
        route_relief_decay_chance = 0.10
        route_min_elite_choices = 1
    if safe_level >= 15:
        shop_cost_mult = 1.30
        reward_mult = 0.90
        boss_penalty_mult = 1.20
        route_elite_chance = 0.25
        route_relief_decay_chance = 0.20
        route_min_elite_choices = 2
    if safe_level >= 18:
        boss_phases = 2
        boss_phase_time_delta = -2
        boss_phase_penalty_step = 0.10
    if safe_level >= 20:
        shop_cost_mult = 1.50
        reward_mult = 0.85
        boss_penalty_mult = 1.35
        boss_phases = 3
        boss_phase_time_delta = -2
        boss_phase_penalty_step = 0.12
        boss_block_cat_log_from_phase = 2
        boss_block_skill_from_phase = 3
        boss_command_violation_penalty = 4
        boss_fake_keyword_count = 4
        route_elite_chance = 0.40
        route_relief_decay_chance = 0.30
        route_min_elite_choices = 3
    return {
        "level": safe_level,
        "penalty_flat": int(raw["penalty_flat"]),
        "force_easy_glitch": bool(raw["force_easy_glitch"]),
        "time_limit_delta": int(raw["time_limit_delta"]),
        "timeout_penalty_delta": int(raw["timeout_penalty_delta"]),
        "start_trace": int(raw["start_trace"]),
        "shop_cost_mult": shop_cost_mult,
        "reward_mult": reward_mult,
        "boss_penalty_mult": boss_penalty_mult,
        "boss_phases": boss_phases,
        "boss_phase_time_delta": boss_phase_time_delta,
        "boss_phase_penalty_step": boss_phase_penalty_step,
        "boss_block_cat_log_from_phase": boss_block_cat_log_from_phase,
        "boss_block_skill_from_phase": boss_block_skill_from_phase,
        "boss_command_violation_penalty": boss_command_violation_penalty,
        "boss_fake_keyword_count": boss_fake_keyword_count,
        "route_elite_chance": route_elite_chance,
        "route_relief_decay_chance": route_relief_decay_chance,
        "route_min_elite_choices": route_min_elite_choices,
    }


def save_game(data: dict[str, Any], file_path: str = SAVE_FILE_PATH) -> None:
    """
    현재 진행도 데이터를 JSON 파일에 저장한다.

    파일 쓰기 실패 시 상위 호출부에서 안내할 수 있도록 OSError를 래핑해 전달한다.
    """
    normalized = _normalize_save_data(data)
    resolved_path = _resolve_save_path(file_path)
    try:
        # 상위 폴더가 없으면 생성해 첫 실행에서도 저장이 실패하지 않게 한다.
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved_path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise OSError(f"세이브 파일 저장 실패: {resolved_path}") from exc


def load_save(file_path: str = SAVE_FILE_PATH) -> dict[str, Any]:
    """
    세이브 파일을 로드한다.

    - 파일이 없으면 기본값 파일을 생성한다.
    - 파일이 손상되었거나 읽기 실패 시 기본값으로 복구를 시도한다.
    """
    resolved_path = _resolve_save_path(file_path)
    try:
        file_size = resolved_path.stat().st_size
        if file_size > _MAX_SAVE_FILE_SIZE:
            raise ValueError(
                f"세이브 파일 크기({file_size:,} bytes)가 허용 한도를 초과합니다."
            )
        with open(resolved_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        normalized = _normalize_save_data(raw_data)
        # 구조가 손상된 파일을 읽은 경우 즉시 정규화된 형태로 덮어써 복구한다.
        if normalized != raw_data:
            save_game(normalized, file_path=str(resolved_path))
        return normalized
    except FileNotFoundError:
        # 첫 실행인 경우 기본 세이브를 생성한다.
        default_data = deepcopy(DEFAULT_SAVE_DATA)
        try:
            save_game(default_data, file_path=str(resolved_path))
        except OSError as exc:
            # 저장 실패하더라도 런타임은 기본값으로 계속 진행 가능해야 한다.
            _save_warn(f"세이브 파일 초기 생성 실패 (진행은 가능): {exc}")
        return default_data
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        # 파일이 깨졌거나 접근 불가능한 경우 기본값으로 복구를 시도한다.
        _save_warn(f"세이브 파일 손상 — 기본값으로 복구합니다: {exc}")
        default_data = deepcopy(DEFAULT_SAVE_DATA)
        try:
            save_game(default_data, file_path=str(resolved_path))
        except OSError as save_exc:
            _save_warn(f"세이브 파일 복구 저장 실패: {save_exc}")
        return default_data


def _reward_for_difficulty(difficulty: str) -> int:
    """단일 난이도 문자열에 대한 정답 보상액을 반환한다."""
    diff_norm = str(difficulty).strip().upper()
    if diff_norm == "HARD":
        return REWARD_PER_HARD
    if diff_norm == "NIGHTMARE":
        return REWARD_PER_NIGHTMARE
    return REWARD_PER_EASY


def calculate_base_reward(node_difficulties: list[str]) -> int:
    """
    클리어한 노드 난이도 목록으로 기본 보상(승리 보너스 제외)을 계산한다.

    정산 화면 표시용으로 main.py에서 호출한다.
    """
    return sum(_reward_for_difficulty(d) for d in node_difficulties)


def calculate_reward(
    correct_answers: int,
    is_victory: bool,
    node_difficulties: list[str] | None = None,
) -> int:
    """
    정답 횟수와 종료 상태를 기반으로 최종 보상을 계산한다.

    규칙:
    - 난이도별 정답 보상: Easy=10, Hard=15, NIGHTMARE=30
    - node_difficulties 미제공 시 Easy 기준으로 폴백
    - 승리 시 VICTORY_BONUS 추가 지급
    - 사망 시 기본 보상의 DEATH_MULTIPLIER(60%)만 지급 (int 반내림, 승리 보너스 없음)
    """
    safe_correct = max(0, min(_MAX_CAMPAIGN_RUNS, int(correct_answers)))
    difficulties = list(node_difficulties or [])

    # 정답 수와 난이도 목록 길이가 다를 경우 Easy로 채워 폴백한다.
    while len(difficulties) < safe_correct:
        difficulties.append("Easy")

    base_reward = sum(_reward_for_difficulty(d) for d in difficulties[:safe_correct])

    if is_victory:
        return base_reward + VICTORY_BONUS
    return int(base_reward * DEATH_MULTIPLIER)


def apply_ascension_reward_multiplier(
    reward: int,
    ascension_level: int,
) -> tuple[int, float]:
    """Ascension 레벨에 따른 런 보상 배율을 적용한다."""
    safe_reward = max(0, int(reward))
    profile = get_ascension_profile(ascension_level)
    multiplier = max(0.0, float(profile.get("reward_mult", 1.0)))
    return max(0, int(safe_reward * multiplier)), multiplier


# ── 개인 최고 기록 (Personal Records) ────────────────────────────────────────

def _record_key(class_key: str, ascension: int) -> str:
    """(클래스, 어센션) 조합의 딕셔너리 키를 생성한다."""
    return f"{class_key.upper()}_{max(0, int(ascension))}"


def update_personal_records(
    save_data: dict[str, Any],
    *,
    class_key: str,
    ascension: int,
    result: str,
    trace_final: int,
    reward: int,
    correct_answers: int,
) -> None:
    """런 종료 후 개인 최고 기록을 갱신한다.

    승리 런에서만 best_trace / best_reward / best_correct를 경신 대상으로 삼는다.
    모든 런에서 run_count를 증가시킨다.

    Args:
        save_data:       현재 세이브 데이터 (직접 수정)
        class_key:       클래스 코드 ("ANALYST" / "GHOST" / "CRACKER")
        ascension:       어센션 레벨
        result:          런 결과 ("victory" / "shutdown" / "aborted")
        trace_final:     최종 추적도
        reward:          최종 보상
        correct_answers: 정답 노드 수
    """
    records: dict[str, Any] = save_data.get("personal_records")
    if not isinstance(records, dict):
        records = {}
        save_data["personal_records"] = records

    key = _record_key(class_key, ascension)
    entry: dict[str, Any] = records.get(key)
    if not isinstance(entry, dict):
        entry = {
            "class_key": str(class_key).upper(),
            "ascension": max(0, int(ascension)),
            "run_count": 0,
            "victory_count": 0,
            "best_trace": None,     # 승리 런 중 최저 추적도 (낮을수록 좋음)
            "best_reward": 0,       # 승리 런 중 최고 보상
            "best_correct": 0,      # 승리 런 중 최고 정답 수
        }

    entry["run_count"] = int(entry.get("run_count", 0)) + 1
    is_victory = result == "victory"
    if is_victory:
        entry["victory_count"] = int(entry.get("victory_count", 0)) + 1
        safe_trace = max(0, min(100, int(trace_final)))
        prev_trace = entry.get("best_trace")
        if prev_trace is None or safe_trace < int(prev_trace):
            entry["best_trace"] = safe_trace
        safe_reward = max(0, int(reward))
        if safe_reward > int(entry.get("best_reward", 0)):
            entry["best_reward"] = safe_reward
        safe_correct = max(0, int(correct_answers))
        if safe_correct > int(entry.get("best_correct", 0)):
            entry["best_correct"] = safe_correct

    records[key] = entry


def get_personal_records(
    save_data: dict[str, Any],
    class_key: str | None = None,
) -> list[dict[str, Any]]:
    """개인 기록을 클래스 → 어센션 순으로 정렬해 반환한다.

    Args:
        save_data:  현재 세이브 데이터
        class_key:  None이면 전체 반환; 지정하면 해당 클래스만 필터링

    Returns:
        (class_key, ascension) 오름차순 정렬된 기록 리스트
    """
    raw: dict[str, Any] = save_data.get("personal_records", {})
    if not isinstance(raw, dict):
        return []
    entries = [v for v in raw.values() if isinstance(v, dict)]
    if class_key is not None:
        normalized = str(class_key).upper()
        entries = [e for e in entries if e.get("class_key", "").upper() == normalized]
    return sorted(entries, key=lambda e: (e.get("class_key", ""), e.get("ascension", 0)))


# ── 로컬 리더보드 (Local Score Leaderboard) ──────────────────────────────────

#: 리더보드에 보관할 최대 항목 수.
LEADERBOARD_MAX: int = 10

#: 승리 런에 추가되는 리더보드 점수 보너스.
_LB_VICTORY_BONUS: int = 200

#: 어센션 레벨당 추가되는 리더보드 점수.
_LB_ASCENSION_BONUS: int = 30

#: 추적도 절감(100 - trace_final)당 리더보드 점수 배율.
_LB_TRACE_MULT: int = 2

#: 정답 노드 1개당 리더보드 점수.
_LB_CORRECT_BONUS: int = 10


def calculate_run_score(
    result: str,
    trace_final: int,
    reward: int,
    correct_answers: int,
    ascension: int,
) -> int:
    """런 종료 후 리더보드 점수를 계산한다.

    점수 공식:
        reward
        + (100 - trace_final) × 2   ← 추적도를 낮게 유지할수록 보너스
        + correct_answers × 10
        + ascension × 30            ← 높은 어센션일수록 가중치
        + 200 (승리 시 추가)

    Args:
        result:          런 결과 ("victory" / "shutdown" / "aborted")
        trace_final:     최종 추적도 (0~100)
        reward:          최종 보상 (데이터 조각)
        correct_answers: 정답 노드 수
        ascension:       어센션 레벨

    Returns:
        정수 점수 (0 이상)
    """
    safe_trace = max(0, min(100, int(trace_final)))
    safe_reward = max(0, int(reward))
    safe_correct = max(0, int(correct_answers))
    safe_asc = max(0, int(ascension))

    score = (
        safe_reward
        + (100 - safe_trace) * _LB_TRACE_MULT
        + safe_correct * _LB_CORRECT_BONUS
        + safe_asc * _LB_ASCENSION_BONUS
    )
    if result == "victory":
        score += _LB_VICTORY_BONUS
    return max(0, score)


def _make_leaderboard_entry(
    rank: int,
    score: int,
    date: str,
    class_key: str,
    ascension: int,
    result: str,
    trace_final: int,
    reward: int,
    correct_answers: int,
) -> dict[str, Any]:
    """리더보드 항목 딕셔너리를 생성한다 (불변 값으로 구성)."""
    return {
        "rank": int(rank),
        "score": max(0, int(score)),
        "date": str(date),
        "class_key": str(class_key).upper(),
        "ascension": max(0, int(ascension)),
        "result": str(result),
        "trace_final": max(0, min(100, int(trace_final))),
        "reward": max(0, int(reward)),
        "correct_answers": max(0, int(correct_answers)),
    }


def update_leaderboard(
    save_data: dict[str, Any],
    *,
    date: str,
    class_key: str,
    ascension: int,
    result: str,
    trace_final: int,
    reward: int,
    correct_answers: int,
) -> int | None:
    """런 종료 후 로컬 리더보드를 갱신한다.

    점수를 계산해 현재 리더보드와 비교하고, 순위권이면 삽입한다.
    LEADERBOARD_MAX 초과 시 최하위 항목을 삭제한다.

    Args:
        save_data:       현재 세이브 데이터 (직접 수정)
        date:            런 날짜 (YYYY-MM-DD)
        class_key:       클래스 코드
        ascension:       어센션 레벨
        result:          런 결과 ("victory" / "shutdown" / "aborted")
        trace_final:     최종 추적도
        reward:          최종 보상
        correct_answers: 정답 노드 수

    Returns:
        순위권 진입 시 1-based 순위 (int), 진입 실패 시 None
    """
    board: list[dict[str, Any]] = save_data.get("leaderboard")
    if not isinstance(board, list):
        board = []

    score = calculate_run_score(result, trace_final, reward, correct_answers, ascension)

    # 현재 최하위 점수보다 낮으면 리더보드가 꽉 찬 경우 삽입하지 않는다.
    if len(board) >= LEADERBOARD_MAX and score <= int(board[-1].get("score", 0)):
        return None

    # 임시 rank 0으로 새 항목 생성 후 삽입 위치를 결정한다.
    new_entry: dict[str, Any] = _make_leaderboard_entry(
        rank=0,
        score=score,
        date=date,
        class_key=class_key,
        ascension=ascension,
        result=result,
        trace_final=trace_final,
        reward=reward,
        correct_answers=correct_answers,
    )

    updated = list(board) + [new_entry]
    updated.sort(key=lambda e: int(e.get("score", 0)), reverse=True)
    if len(updated) > LEADERBOARD_MAX:
        updated = updated[:LEADERBOARD_MAX]

    # 순위(1-based) 재계산
    for i, entry in enumerate(updated):
        entry["rank"] = i + 1

    save_data["leaderboard"] = updated

    # 새 항목의 순위 반환
    for entry in updated:
        if (
            entry.get("score") == score
            and entry.get("date") == date
            and entry.get("class_key") == str(class_key).upper()
        ):
            return int(entry["rank"])
    return None


def get_leaderboard(save_data: dict[str, Any]) -> list[dict[str, Any]]:
    """로컬 리더보드를 점수 내림차순으로 반환한다.

    Returns:
        점수 내림차순 정렬된 리더보드 복사본
    """
    board = save_data.get("leaderboard", [])
    if not isinstance(board, list):
        return []
    return list(board)
