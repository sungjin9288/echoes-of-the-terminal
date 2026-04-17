"""게임 색상 테마 시스템.

색각 이상(적록색맹 등) 플레이어를 위한 대체 테마를 제공한다.
모든 테마는 동일한 키 집합을 가지며 ui_renderer.py가 이를 참조한다.

테마 목록:
  default      — 기본 초록/노랑/빨강 팔레트
  colorblind   — 청색/황색 계열 (적록색맹 대응)
  high_contrast — 굵기·밑줄·반전으로만 구분 (완전 흑백 디스플레이 대응)
"""

from typing import Final

# ── 테마 정의 ─────────────────────────────────────────────────────────────────────

#: 테마별 Rich 스타일 딕셔너리.
#:
#: 키 목록:
#:   trace_safe      추적도 < 30% 구간
#:   trace_warn      추적도 30~49% 구간
#:   trace_danger    추적도 50~79% 구간
#:   trace_critical  추적도 >= 80% 구간
#:   difficulty_easy Easy 난이도
#:   difficulty_hard Hard 난이도
#:   difficulty_nightmare NIGHTMARE 난이도
#:   result_victory  승리 결과 강조
#:   result_defeat   패배 결과 강조
#:   node_boss       보스 노드 강조
#:   node_elite      ELITE 노드 강조
THEMES: Final[dict[str, dict[str, str]]] = {
    "default": {
        "trace_safe": "bold green",
        "trace_warn": "bold white",
        "trace_danger": "bold yellow",
        "trace_critical": "bold red",
        "difficulty_easy": "bold green",
        "difficulty_hard": "bold yellow",
        "difficulty_nightmare": "bold red",
        "result_victory": "bold green",
        "result_defeat": "bold red",
        "node_boss": "bold red",
        "node_elite": "bold yellow",
    },
    "colorblind": {
        # 적록색맹(deuteranopia/protanopia) 대응:
        # 초록 → 청색, 빨강 → 주황(#FF8C00), 노랑 유지
        "trace_safe": "bold blue",
        "trace_warn": "bold white",
        "trace_danger": "bold yellow",
        "trace_critical": "bold #FF8C00",
        "difficulty_easy": "bold blue",
        "difficulty_hard": "bold yellow",
        "difficulty_nightmare": "bold #FF8C00",
        "result_victory": "bold blue",
        "result_defeat": "bold #FF8C00",
        "node_boss": "bold #FF8C00",
        "node_elite": "bold yellow",
    },
    "high_contrast": {
        # 색상 없이 굵기·이탤릭·밑줄·반전으로만 구분 (단색/OLED 디스플레이 대응)
        "trace_safe": "bold white",
        "trace_warn": "bold white italic",
        "trace_danger": "bold white underline",
        "trace_critical": "reverse bold white",
        "difficulty_easy": "bold white",
        "difficulty_hard": "bold white italic",
        "difficulty_nightmare": "reverse bold white",
        "result_victory": "bold white",
        "result_defeat": "reverse bold white",
        "node_boss": "reverse bold white",
        "node_elite": "bold white underline",
    },
}

#: 로비 표시용 한글 테마명.
THEME_LABEL_MAP: Final[dict[str, str]] = {
    "default": "기본 (초록/노랑/빨강)",
    "colorblind": "색맹 보조 (청색/황색/주황)",
    "high_contrast": "고대비 (굵기·반전만 사용)",
}

#: 유효한 테마 이름 집합.
VALID_THEMES: Final[frozenset[str]] = frozenset(THEMES.keys())


def get_theme_styles(theme_name: str) -> dict[str, str]:
    """테마 이름으로 스타일 딕셔너리를 반환한다.

    알 수 없는 이름이면 기본 테마를 반환한다.
    """
    return THEMES.get(theme_name, THEMES["default"])
