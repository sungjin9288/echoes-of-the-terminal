"""다국어 지원(i18n) 모듈.

게임 프레임워크 UI 문자열을 언어별 JSON 파일로 관리한다.
시나리오 본문(text_log)은 게임 콘텐츠이므로 번역 대상에 포함되지 않는다.

사용법:
    from i18n import t, set_language, get_language

    set_language("en")
    print(t("lobby.menu.game_start"))   # "Game Start"
    print(t("lobby.status.fragments", count=42))  # "Data Fragments: 42"

지원 언어:
    ko — 한국어 (기본값)
    en — English
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final

# ── 상수 ─────────────────────────────────────────────────────────────────────

#: 지원 언어 목록.
SUPPORTED_LANGUAGES: Final[frozenset[str]] = frozenset({"ko", "en"})

#: 언어 이름 표시용 맵.
LANGUAGE_LABEL_MAP: Final[dict[str, str]] = {
    "ko": "한국어",
    "en": "English",
}

_DEFAULT_LANG: Final[str] = "ko"

# ── 모듈 상태 ────────────────────────────────────────────────────────────────

_current_lang: str = _DEFAULT_LANG
_catalog: dict[str, str] = {}   # 현재 언어의 번역 테이블


# ── 경로 해석 ────────────────────────────────────────────────────────────────

def _resolve_locale_path(lang: str) -> Path:
    """언어 코드에 해당하는 locale JSON 파일 경로를 계산한다."""
    filename = f"{lang}.json"

    # PyInstaller 번들 환경
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        candidate = (Path(bundle_dir) / "locale" / filename).resolve()
        if candidate.exists():
            return candidate

    # CWD 기준
    cwd_candidate = (Path.cwd() / "locale" / filename).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    # 소스 파일 위치 기준 (개발 환경)
    return (Path(__file__).resolve().parent / "locale" / filename).resolve()


# ── 카탈로그 로딩 ─────────────────────────────────────────────────────────────

def _load_catalog(lang: str) -> dict[str, str]:
    """lang에 해당하는 locale JSON을 로드해 반환한다.

    파일이 없거나 손상된 경우 빈 딕셔너리를 반환해 폴백 동작을 보장한다.
    """
    path = _resolve_locale_path(lang)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        # 값이 문자열인 키만 포함한다.
        return {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


# ── 공개 API ──────────────────────────────────────────────────────────────────

def set_language(lang: str) -> None:
    """현재 언어를 변경하고 카탈로그를 다시 로드한다.

    알 수 없는 언어 코드는 무시하고 현재 설정을 유지한다.
    """
    global _current_lang, _catalog
    normalized = lang.strip().lower() if isinstance(lang, str) else ""
    if normalized not in SUPPORTED_LANGUAGES:
        return
    _current_lang = normalized
    _catalog = _load_catalog(normalized)


def get_language() -> str:
    """현재 언어 코드를 반환한다."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """주어진 키에 해당하는 번역 문자열을 반환한다.

    키가 현재 언어 카탈로그에 없으면 한국어 카탈로그에서 재시도한다.
    그래도 없으면 키 자체를 반환한다.

    format kwargs가 있으면 str.format_map으로 보간한다.

    Args:
        key:    번역 키 (예: "lobby.menu.game_start")
        **kwargs: 포맷 인수 (예: count=42)

    Returns:
        번역된 문자열 (폴백 시 키 자체)
    """
    # 현재 언어 카탈로그에서 조회
    raw = _catalog.get(key)

    # 없으면 한국어 카탈로그에서 폴백
    if raw is None and _current_lang != _DEFAULT_LANG:
        ko_catalog = _load_catalog(_DEFAULT_LANG)
        raw = ko_catalog.get(key)

    # 그래도 없으면 키 자체 반환
    if raw is None:
        return key

    # 포맷 인수가 있으면 보간
    if kwargs:
        try:
            return raw.format_map(kwargs)
        except (KeyError, ValueError):
            return raw

    return raw


def reload() -> None:
    """현재 언어 카탈로그를 디스크에서 다시 로드한다. (핫 리로드 / 테스트용)"""
    global _catalog
    _catalog = _load_catalog(_current_lang)


# ── 모듈 초기화: 기본 언어(ko) 카탈로그 즉시 로드 ─────────────────────────────
reload()
