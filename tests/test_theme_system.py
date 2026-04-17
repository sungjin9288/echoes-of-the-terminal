"""theme_system.py 유닛 테스트.

테마 정의 완결성, get_theme_styles 반환 값, 세이브 정규화 흐름,
ui_renderer의 set_theme / get_current_theme_name 연동까지 검증한다.
"""

from __future__ import annotations

import pytest

import theme_system as ts
from theme_system import THEMES, THEME_LABEL_MAP, VALID_THEMES, get_theme_styles


# ──────────────────────────────────────────────────────────────────────────────
# 1. 테마 목록 / 구조 검증
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_KEYS = {
    "trace_safe",
    "trace_warn",
    "trace_danger",
    "trace_critical",
    "difficulty_easy",
    "difficulty_hard",
    "difficulty_nightmare",
    "result_victory",
    "result_defeat",
    "node_boss",
    "node_elite",
}


def test_all_themes_present() -> None:
    """default / colorblind / high_contrast 세 테마가 정의되어야 한다."""
    assert "default" in THEMES
    assert "colorblind" in THEMES
    assert "high_contrast" in THEMES


def test_each_theme_has_all_required_keys() -> None:
    """모든 테마는 동일한 필수 키 집합을 가져야 한다."""
    for theme_name, styles in THEMES.items():
        missing = REQUIRED_KEYS - styles.keys()
        assert not missing, f"테마 '{theme_name}' 에 누락된 키: {missing}"


def test_valid_themes_matches_themes_dict() -> None:
    """VALID_THEMES는 THEMES의 키 집합과 정확히 일치해야 한다."""
    assert VALID_THEMES == frozenset(THEMES.keys())


def test_theme_label_map_covers_all_themes() -> None:
    """THEME_LABEL_MAP은 모든 테마에 대한 레이블을 가져야 한다."""
    for name in THEMES:
        assert name in THEME_LABEL_MAP, f"'{name}' 레이블 없음"


# ──────────────────────────────────────────────────────────────────────────────
# 2. get_theme_styles
# ──────────────────────────────────────────────────────────────────────────────

def test_get_theme_styles_known_theme() -> None:
    """알려진 테마 이름은 해당 스타일 딕셔너리를 반환해야 한다."""
    result = get_theme_styles("colorblind")
    assert result is THEMES["colorblind"]


def test_get_theme_styles_unknown_falls_back_to_default() -> None:
    """알 수 없는 테마 이름은 default 스타일 딕셔너리를 반환해야 한다."""
    result = get_theme_styles("does_not_exist")
    assert result is THEMES["default"]


def test_get_theme_styles_empty_string_falls_back_to_default() -> None:
    """빈 문자열도 default 테마를 반환해야 한다."""
    result = get_theme_styles("")
    assert result is THEMES["default"]


def test_get_theme_styles_returns_correct_trace_styles() -> None:
    """high_contrast 테마는 색상 없이 bold/italic/underline/reverse만 사용한다."""
    styles = get_theme_styles("high_contrast")
    for key, style in styles.items():
        # 색상 이름(green, red, blue, yellow, #…)이 포함되지 않아야 함
        for colour_word in ("green", "red", "blue", "yellow", "#"):
            assert colour_word not in style, (
                f"high_contrast 테마의 '{key}'에 색상 '{colour_word}'이 포함됨: {style}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# 3. ui_renderer set_theme / get_current_theme_name 연동
# ──────────────────────────────────────────────────────────────────────────────

def test_set_and_get_theme_roundtrip() -> None:
    """set_theme() → get_current_theme_name() 왕복이 일치해야 한다."""
    import ui_renderer

    for name in THEMES:
        ui_renderer.set_theme(name)
        assert ui_renderer.get_current_theme_name() == name


def test_set_theme_unknown_falls_back_to_default() -> None:
    """알 수 없는 테마를 set_theme에 넘기면 default로 되돌아와야 한다."""
    import ui_renderer

    ui_renderer.set_theme("nonexistent_theme")
    # get_theme_styles("nonexistent") → default 스타일 dict가 적용됨
    assert ui_renderer.get_current_theme_name() == "default"


def test_set_theme_default_restores_default() -> None:
    """colorblind로 바꾼 뒤 default로 복원하면 get_current_theme_name이 'default'."""
    import ui_renderer

    ui_renderer.set_theme("colorblind")
    ui_renderer.set_theme("default")
    assert ui_renderer.get_current_theme_name() == "default"


# ──────────────────────────────────────────────────────────────────────────────
# 4. 세이브 정규화 — progression_system과 연동
# ──────────────────────────────────────────────────────────────────────────────

def test_save_normalization_preserves_valid_theme(tmp_path, monkeypatch) -> None:
    """세이브 로딩 시 유효한 theme 값은 그대로 유지되어야 한다."""
    import json
    from progression_system import load_save

    save_path = tmp_path / "save.json"
    # colorblind 테마가 저장된 세이브 데이터 준비
    import progression_system as ps
    import copy
    data = copy.deepcopy(ps.DEFAULT_SAVE_DATA)
    data["theme"] = "colorblind"
    save_path.write_text(json.dumps(data), encoding="utf-8")

    result = load_save(file_path=str(save_path))
    assert result["theme"] == "colorblind"


def test_save_normalization_rejects_invalid_theme(tmp_path, monkeypatch) -> None:
    """세이브 로딩 시 알 수 없는 theme 값은 'default'로 교정되어야 한다."""
    import json
    from progression_system import load_save
    import progression_system as ps
    import copy

    save_path = tmp_path / "save.json"
    data = copy.deepcopy(ps.DEFAULT_SAVE_DATA)
    data["theme"] = "solarized"  # 존재하지 않는 테마
    save_path.write_text(json.dumps(data), encoding="utf-8")

    result = load_save(file_path=str(save_path))
    assert result["theme"] == "default"


def test_save_normalization_missing_theme_defaults(tmp_path) -> None:
    """theme 키가 없는 구 세이브 데이터는 'default'가 자동 보완되어야 한다."""
    import json
    from progression_system import load_save
    import progression_system as ps
    import copy

    save_path = tmp_path / "save.json"
    data = copy.deepcopy(ps.DEFAULT_SAVE_DATA)
    data.pop("theme", None)  # theme 키 제거
    save_path.write_text(json.dumps(data), encoding="utf-8")

    result = load_save(file_path=str(save_path))
    assert result["theme"] == "default"


# ──────────────────────────────────────────────────────────────────────────────
# 5. 테마 스타일 값 품질 검사
# ──────────────────────────────────────────────────────────────────────────────

def test_default_theme_trace_styles_use_standard_colors() -> None:
    """default 테마는 green / white / yellow / red 계열 색상을 순서대로 사용해야 한다."""
    styles = THEMES["default"]
    assert "green" in styles["trace_safe"]
    assert "yellow" in styles["trace_danger"]
    assert "red" in styles["trace_critical"]


def test_colorblind_theme_avoids_red_green_confusion() -> None:
    """colorblind 테마는 red / green 색상을 trace_safe / trace_critical에 사용하지 않아야 한다."""
    styles = THEMES["colorblind"]
    assert "red" not in styles["trace_safe"]
    assert "green" not in styles["trace_safe"]
    assert "red" not in styles["trace_critical"]
    assert "green" not in styles["trace_critical"]


def test_all_style_values_are_non_empty_strings() -> None:
    """모든 테마의 모든 스타일 값이 비어 있지 않은 문자열이어야 한다."""
    for theme_name, styles in THEMES.items():
        for key, value in styles.items():
            assert isinstance(value, str) and value.strip(), (
                f"테마 '{theme_name}'의 '{key}' 스타일 값이 비어 있음"
            )
