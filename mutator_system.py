"""스테이지 변주 시스템(Mutators) 로직 모듈."""

import random
import re
import time

from constants import TIME_LIMIT_DEFAULT as TIME_LIMIT_SECONDS
from constants import TIMEOUT_PENALTY

# NIGHTMARE 전용 글리치 풀: 일반 Hard보다 더 공격적인 노이즈를 사용한다.
_NIGHTMARE_GLITCH_POOL = [
    "[■■DATA CORRUPTED■■]",
    "<GLITCH::0xDEAD>",
    "<SIGNAL_LOSS//####>",
    "[!!MEMORY_FAULT!!]",
    "<ERR::0xFF_OVERFLOW>",
]

_HARD_GLITCH_POOL = [
    "[■■DATA CORRUPTED■■]",
    "<GLITCH::0xDEAD>",
    "<SIGNAL_LOSS//####>",
]


def apply_glitch_masking(
    text_log: str,
    difficulty: str,
    target_keyword: str | None = None,
    glitch_word_count: int | None = None,
    nightmare_noise_reduce: int = 0,
) -> str:
    """
    텍스트 로그에 글리치 마스킹 변주를 적용한다.

    동작 규칙:
    - difficulty가 Hard가 아니고 NIGHTMARE가 아니면 원문을 그대로 반환한다.
    - Hard일 경우 무작위 단어 2~3개를 글리치 문자열로 치환한다.
    - NIGHTMARE일 경우 무작위 단어 4~5개를 더 강렬한 글리치 문자열로 치환한다.
    - nightmare_noise_reduce: 아티팩트 효과로 NIGHTMARE 글리치 수를 감소시킨다.
    - target_keyword와 동일한 단어는 치환 대상에서 제외한다.

    Args:
        text_log: 원문 텍스트 로그
        difficulty: 난이도 문자열(Easy/Hard/NIGHTMARE)
        target_keyword: 정답 키워드(치환 보호용, 선택)
        glitch_word_count: 강제 치환 단어 수(Perk로 강도 제어할 때 사용)
        nightmare_noise_reduce: NIGHTMARE 최대 글리치 수 감소량 (아티팩트 효과)

    Returns:
        글리치가 적용된 텍스트
    """
    difficulty_norm = str(difficulty).strip().upper()

    if difficulty_norm == "HARD":
        default_count_range = (2, 3)
        glitch_pool = _HARD_GLITCH_POOL
    elif difficulty_norm == "NIGHTMARE":
        # nightmare_noise_reduce만큼 최대 글리치 수를 줄인다 (최소 2)
        reduce = max(0, int(nightmare_noise_reduce))
        hi = max(2, 5 - reduce)
        lo = max(2, min(4, hi))
        default_count_range = (lo, hi)
        glitch_pool = _NIGHTMARE_GLITCH_POOL
    else:
        # Easy 및 기타 난이도는 글리치 없음
        return text_log

    # 공백 기준 토큰 대신 정규식으로 "단어" 경계를 찾아 치환 위치를 안정적으로 확보한다.
    # \w에는 한글도 포함되므로 한국어 키워드 보호가 가능하다.
    matches = list(re.finditer(r"\b[\w]+\b", text_log, flags=re.UNICODE))
    if not matches:
        return text_log

    target_norm = (target_keyword or "").strip().lower()
    candidate_indexes: list[int] = []

    # 정답 키워드와 일치하는 토큰은 후보에서 제외하여 정답 자체가 훼손되지 않게 한다.
    for idx, match in enumerate(matches):
        token_norm = match.group(0).strip().lower()
        if target_norm and token_norm == target_norm:
            continue
        candidate_indexes.append(idx)

    if not candidate_indexes:
        return text_log

    # 기본 규칙은 난이도별 범위이며, Perk가 켜지면 외부에서 치환 수를 고정할 수 있다.
    if glitch_word_count is not None:
        try:
            gw = max(0, int(glitch_word_count))
        except (TypeError, ValueError):
            gw = 0
        replace_count = min(len(candidate_indexes), gw)
    else:
        lo, hi = default_count_range
        replace_count = min(len(candidate_indexes), random.randint(lo, hi))

    if replace_count <= 0:
        return text_log

    chosen_indexes = set(random.sample(candidate_indexes, replace_count))

    # 원문 인덱스를 유지하기 위해 뒤에서부터 치환하면 슬라이싱 오프셋이 어긋나지 않는다.
    mutated = text_log
    for idx in sorted(chosen_indexes, reverse=True):
        match = matches[idx]
        glitch_word = random.choice(glitch_pool)
        mutated = mutated[: match.start()] + glitch_word + mutated[match.end() :]

    return mutated


def track_time_limit(start_time: float, time_limit_seconds: int = TIME_LIMIT_SECONDS) -> int:
    """
    입력 대기 시간을 계산해 타임아웃 페널티를 반환한다.

    Args:
        start_time: 입력 대기 시작 시각(time.time())
        time_limit_seconds: 제한 시간(초), 기본값은 30초

    Returns:
        int: 제한 시간 초과 시 TIMEOUT_PENALTY, 아니면 0
    """
    elapsed = time.time() - start_time
    if elapsed > time_limit_seconds:
        return TIMEOUT_PENALTY
    return 0
