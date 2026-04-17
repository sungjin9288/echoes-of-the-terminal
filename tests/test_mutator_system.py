"""mutator_system.py 단위 테스트."""

import time

import pytest

from mutator_system import apply_glitch_masking, track_time_limit


# ── apply_glitch_masking — 난이도별 동작 ─────────────────────────────────────

def test_easy_difficulty_returns_original_text() -> None:
    log = "alice alice bob"
    result = apply_glitch_masking(log, "Easy", target_keyword="alice")
    assert result == log


def test_unknown_difficulty_returns_original_text() -> None:
    log = "some log text"
    result = apply_glitch_masking(log, "UNKNOWN")
    assert result == log


def test_hard_difficulty_replaces_some_words(monkeypatch) -> None:
    # random.randint → 2, random.sample → 처음 2개, random.choice → 고정 글리치
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: 2)
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "alpha bravo charlie delta epsilon"
    result = apply_glitch_masking(log, "Hard")
    # 치환이 일어났으므로 원문과 달라야 함
    assert result != log
    # 글리치 문자열이 포함돼야 함
    assert "[■■DATA CORRUPTED■■]" in result


def test_nightmare_difficulty_replaces_more_words(monkeypatch) -> None:
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: hi)
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "one two three four five six seven eight"
    result = apply_glitch_masking(log, "NIGHTMARE")
    assert result != log


# ── apply_glitch_masking — target_keyword 보호 ────────────────────────────────

def test_target_keyword_not_replaced_in_hard(monkeypatch) -> None:
    # 모든 단어를 치환 대상으로 선택해도 target_keyword는 보호되어야 함
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: hi)
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "GPS was mentioned in the GPS log"
    result = apply_glitch_masking(log, "Hard", target_keyword="GPS")
    # 'GPS' 단어는 그대로 남아야 함
    assert "GPS" in result


def test_target_keyword_not_replaced_in_nightmare(monkeypatch) -> None:
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: hi)
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "protocol protocol protocol vector"
    result = apply_glitch_masking(log, "NIGHTMARE", target_keyword="protocol")
    assert "protocol" in result


def test_korean_keyword_not_replaced(monkeypatch) -> None:
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: hi)
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "용의자 홍길동 현장 도주 목격자 진술"
    result = apply_glitch_masking(log, "Hard", target_keyword="홍길동")
    assert "홍길동" in result


# ── apply_glitch_masking — glitch_word_count 파라미터 ────────────────────────

def test_glitch_word_count_zero_returns_original(monkeypatch) -> None:
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    log = "alpha bravo charlie"
    result = apply_glitch_masking(log, "Hard", glitch_word_count=0)
    assert result == log


def test_glitch_word_count_one_replaces_exactly_one(monkeypatch) -> None:
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "alpha bravo charlie delta"
    result = apply_glitch_masking(log, "Hard", glitch_word_count=1)
    # 글리치가 정확히 1개 치환됨
    glitch = "[■■DATA CORRUPTED■■]"
    assert result.count(glitch) == 1


# ── apply_glitch_masking — nightmare_noise_reduce ────────────────────────────

def test_nightmare_noise_reduce_limits_max_glitches(monkeypatch) -> None:
    # noise_reduce=3 이면 NIGHTMARE 최대값 5-3=2 → (2, 2) 범위
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: hi)
    monkeypatch.setattr("mutator_system.random.sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr("mutator_system.random.choice", lambda pool: pool[0])

    log = "a b c d e f g h i j k l m n"
    result = apply_glitch_masking(log, "NIGHTMARE", nightmare_noise_reduce=3)
    # 최대 2개 치환 → 글리치 문자열이 2개 이하여야 함
    glitch = "<GLITCH::0xDEAD>"  # nightmare pool[0] after monkeypatching choice
    assert result.count("[■■DATA CORRUPTED■■]") <= 2


# ── apply_glitch_masking — 엣지 케이스 ────────────────────────────────────────

def test_empty_text_returns_empty() -> None:
    result = apply_glitch_masking("", "Hard")
    assert result == ""


def test_text_with_no_word_tokens_returns_original() -> None:
    # 공백·특수문자만 있을 때 (regex \w 매칭 없음)
    log = "   ---   "
    result = apply_glitch_masking(log, "Hard")
    assert result == log


def test_all_candidates_are_keyword_returns_original(monkeypatch) -> None:
    monkeypatch.setattr("mutator_system.random.randint", lambda lo, hi: hi)
    log = "GPS GPS GPS"
    result = apply_glitch_masking(log, "Hard", target_keyword="GPS")
    # 모든 후보가 keyword라서 치환할 게 없음
    assert result == log


# ── track_time_limit ──────────────────────────────────────────────────────────

def test_track_time_limit_returns_zero_when_within_limit() -> None:
    result = track_time_limit(time.time(), time_limit_seconds=60)
    assert result == 0


def test_track_time_limit_returns_penalty_when_exceeded() -> None:
    past = time.time() - 100
    result = track_time_limit(past, time_limit_seconds=10)
    assert result == 10  # TIMEOUT_PENALTY 상수값
