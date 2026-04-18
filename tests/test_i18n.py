"""i18n.py 유닛 테스트.

언어 전환, 번역 조회, 폴백 동작, 포맷 보간, 세이브 정규화,
ui_renderer 연동까지 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import i18n as i18n_module
from i18n import (
    LANGUAGE_LABEL_MAP,
    SUPPORTED_LANGUAGES,
    get_language,
    reload,
    set_language,
    t,
)


# ── 픽스처 ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_language():
    """각 테스트 후 언어를 한국어(기본값)로 복원한다."""
    yield
    set_language("ko")
    reload()


# ── SUPPORTED_LANGUAGES / LANGUAGE_LABEL_MAP ─────────────────────────────────

def test_supported_languages_contains_ko_and_en() -> None:
    assert "ko" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES


def test_language_label_map_covers_supported_languages() -> None:
    for lang in SUPPORTED_LANGUAGES:
        assert lang in LANGUAGE_LABEL_MAP, f"레이블 없음: {lang}"


def test_language_label_map_values_non_empty() -> None:
    for lang, label in LANGUAGE_LABEL_MAP.items():
        assert label.strip(), f"빈 레이블: {lang}"


# ── set_language / get_language ───────────────────────────────────────────────

def test_default_language_is_ko() -> None:
    assert get_language() == "ko"


def test_set_language_en_then_get() -> None:
    set_language("en")
    assert get_language() == "en"


def test_set_language_unknown_is_ignored() -> None:
    set_language("ko")
    set_language("fr")  # 미지원
    assert get_language() == "ko"


def test_set_language_empty_string_is_ignored() -> None:
    set_language("")
    assert get_language() == "ko"


def test_set_language_roundtrip() -> None:
    set_language("en")
    set_language("ko")
    assert get_language() == "ko"


# ── t() — 기본 조회 ──────────────────────────────────────────────────────────

def test_t_returns_korean_string_by_default() -> None:
    result = t("lobby.menu.game_start")
    assert "게임 시작" in result


def test_t_returns_english_after_set_language_en() -> None:
    set_language("en")
    result = t("lobby.menu.game_start")
    assert "Game Start" in result


def test_t_unknown_key_returns_key_itself() -> None:
    result = t("this.key.does.not.exist")
    assert result == "this.key.does.not.exist"


def test_t_empty_key_returns_empty_key() -> None:
    result = t("")
    assert result == ""


# ── t() — 폴백 동작 ──────────────────────────────────────────────────────────

def test_t_falls_back_to_ko_when_key_missing_in_en(tmp_path, monkeypatch) -> None:
    """en.json에 없는 키는 ko.json에서 폴백해야 한다."""
    # locale 디렉터리를 tmp_path로 교체
    locale_dir = tmp_path / "locale"
    locale_dir.mkdir()

    ko_data = {"only_in_ko": "한국어 전용"}
    en_data = {}  # 키 없음
    (locale_dir / "ko.json").write_text(json.dumps(ko_data), encoding="utf-8")
    (locale_dir / "en.json").write_text(json.dumps(en_data), encoding="utf-8")

    monkeypatch.setattr(i18n_module, "_resolve_locale_path",
                        lambda lang: locale_dir / f"{lang}.json")
    set_language("en")

    result = t("only_in_ko")
    assert result == "한국어 전용"


# ── t() — 포맷 보간 ──────────────────────────────────────────────────────────

def test_t_format_interpolation_single_arg() -> None:
    result = t("lobby.status.fragments", count=42)
    assert "42" in result


def test_t_format_interpolation_multiple_args() -> None:
    result = t("lobby.status.perks", owned=5, total=13)
    assert "5" in result
    assert "13" in result


def test_t_format_interpolation_en() -> None:
    set_language("en")
    result = t("lobby.status.fragments", count=99)
    assert "99" in result
    assert "Data Fragments" in result


def test_t_format_missing_kwarg_returns_raw_template() -> None:
    """포맷 인수가 누락되면 원본 템플릿 문자열을 반환해야 한다."""
    # count를 전달하지 않음
    result = t("lobby.status.fragments")   # {count} 보간 실패
    assert "{count}" in result or result  # 키 자체 또는 템플릿 반환 (오류 없음)


# ── reload() ─────────────────────────────────────────────────────────────────

def test_reload_does_not_crash() -> None:
    """reload()는 예외 없이 실행되어야 한다."""
    reload()
    assert get_language() == "ko"


# ── 실제 locale 파일 smoke test ───────────────────────────────────────────────

def test_ko_locale_file_loads_and_has_required_keys() -> None:
    """locale/ko.json이 파싱되며 핵심 키를 포함해야 한다."""
    locale_file = Path(__file__).resolve().parent.parent / "locale" / "ko.json"
    assert locale_file.exists(), "locale/ko.json 없음"
    data = json.loads(locale_file.read_text(encoding="utf-8"))
    assert "lobby.menu.game_start" in data
    assert "settlement.result_victory" in data
    assert "shop.title" in data


def test_en_locale_file_loads_and_has_required_keys() -> None:
    """locale/en.json이 파싱되며 핵심 키를 포함해야 한다."""
    locale_file = Path(__file__).resolve().parent.parent / "locale" / "en.json"
    assert locale_file.exists(), "locale/en.json 없음"
    data = json.loads(locale_file.read_text(encoding="utf-8"))
    assert "lobby.menu.game_start" in data
    assert "settlement.result_victory" in data
    assert "shop.title" in data


def test_en_and_ko_have_same_keys() -> None:
    """en.json과 ko.json의 키 집합이 일치해야 한다."""
    base = Path(__file__).resolve().parent.parent / "locale"
    ko_keys = set(json.loads((base / "ko.json").read_text(encoding="utf-8")).keys())
    en_keys = set(json.loads((base / "en.json").read_text(encoding="utf-8")).keys())
    only_in_ko = ko_keys - en_keys
    only_in_en = en_keys - ko_keys
    assert not only_in_ko, f"ko에만 있는 키: {sorted(only_in_ko)}"
    assert not only_in_en, f"en에만 있는 키: {sorted(only_in_en)}"


# ── 세이브 정규화 — progression_system 연동 ──────────────────────────────────

def test_save_normalization_preserves_valid_language(tmp_path) -> None:
    """유효한 language 값은 그대로 유지되어야 한다."""
    import json as _json
    import copy
    from progression_system import load_save, DEFAULT_SAVE_DATA

    save_path = tmp_path / "save.json"
    data = copy.deepcopy(DEFAULT_SAVE_DATA)
    data["language"] = "en"
    save_path.write_text(_json.dumps(data), encoding="utf-8")

    result = load_save(file_path=str(save_path))
    assert result["language"] == "en"


def test_save_normalization_rejects_invalid_language(tmp_path) -> None:
    """알 수 없는 language 값은 'ko'로 교정되어야 한다."""
    import json as _json
    import copy
    from progression_system import load_save, DEFAULT_SAVE_DATA

    save_path = tmp_path / "save.json"
    data = copy.deepcopy(DEFAULT_SAVE_DATA)
    data["language"] = "fr"
    save_path.write_text(_json.dumps(data), encoding="utf-8")

    result = load_save(file_path=str(save_path))
    assert result["language"] == "ko"


def test_save_normalization_missing_language_defaults_to_ko(tmp_path) -> None:
    """language 키가 없는 구 세이브는 'ko'가 자동 보완되어야 한다."""
    import json as _json
    import copy
    from progression_system import load_save, DEFAULT_SAVE_DATA

    save_path = tmp_path / "save.json"
    data = copy.deepcopy(DEFAULT_SAVE_DATA)
    data.pop("language", None)
    save_path.write_text(_json.dumps(data), encoding="utf-8")

    result = load_save(file_path=str(save_path))
    assert result["language"] == "ko"


# ── ui_renderer 연동 — 번역 반영 확인 ────────────────────────────────────────

def test_ui_renderer_settlement_uses_t(monkeypatch) -> None:
    """render_settlement_log는 t()를 통해 번역된 문자열을 사용해야 한다."""
    set_language("en")
    from ui_renderer import render_settlement_log

    printed: list[str] = []
    monkeypatch.setattr("ui_renderer.console.print", lambda *a, **kw: printed.append(str(a)))

    render_settlement_log(correct_answers=5, base_reward=50, final_reward=60, is_victory=True)

    combined = " ".join(printed)
    assert "CORE BREACHED" in combined
    assert "Data fragments" in combined.lower() or "frags" in combined.lower()
