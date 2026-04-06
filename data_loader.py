"""게임 데이터(JSON) 로딩 모듈.

이 모듈은 아래 리소스를 담당한다.
- scenarios.json: 스테이지 시나리오 데이터
- argos_taunts.json: 적대 AI 아르고스 대사 데이터
"""

import json
import sys
from pathlib import Path
from typing import Any


# JSON 파일 최대 허용 크기 (10 MB).
# 이 크기를 초과하는 파일은 파싱을 거부해 메모리 고갈을 방지한다.
_MAX_JSON_FILE_SIZE: int = 10 * 1024 * 1024

# 시나리오 1개가 최소한으로 가져야 하는 필드를 정의한다.
# 이 검증을 통과해야만 메인 루프에서 KeyError 없이 안전하게 접근할 수 있다.
REQUIRED_KEYS = {
    "node_id",
    "theme",
    "difficulty",
    "text_log",
    "target_keyword",
    "penalty_rate",
}

# ASC20 보스 페이즈 오버라이드 1개 항목의 필수 필드.
BOSS_PHASE_REQUIRED_KEYS = {
    "text_log",
    "target_keyword",
}


def _resolve_resource_path(file_path: str) -> Path:
    """
    리소스 파일의 실제 절대 경로를 계산한다.

    우선순위:
    1) 절대 경로 입력이면 그대로 사용
    2) 현재 작업 디렉터리(CWD) 기준 상대 경로
    3) PyInstaller 실행 시 sys._MEIPASS 내부 경로
    4) 소스 코드(data_loader.py) 위치 기준 상대 경로
    """
    input_path = Path(file_path)
    if input_path.is_absolute():
        return input_path

    cwd_path = (Path.cwd() / input_path).resolve()
    if cwd_path.exists():
        return cwd_path

    # PyInstaller(onefile/onedir) 환경에서는 리소스가 _MEIPASS에 풀릴 수 있다.
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        bundle_path = (Path(bundle_dir) / input_path).resolve()
        if bundle_path.exists():
            return bundle_path

    # 개발 환경 기본값: 현재 모듈 위치를 기준으로 리소스를 찾는다.
    module_path = (Path(__file__).resolve().parent / input_path).resolve()
    return module_path


def _load_json_file(file_path: str) -> Any:
    """리소스 JSON 파일을 경로 해석 후 로드한다."""
    resolved_path = _resolve_resource_path(file_path)
    file_size = resolved_path.stat().st_size
    if file_size > _MAX_JSON_FILE_SIZE:
        raise ValueError(
            f"JSON 파일 크기({file_size:,} bytes)가 허용 한도({_MAX_JSON_FILE_SIZE:,} bytes)를 초과합니다: {resolved_path}"
        )
    with open(resolved_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scenarios(file_path: str = "scenarios.json") -> list[dict[str, Any]]:
    """
    scenarios.json 파일을 읽어 시나리오 목록을 반환한다.

    Args:
        file_path: 시나리오 JSON 파일 경로

    Returns:
        list[dict[str, Any]]: 시나리오 데이터 리스트

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: JSON 구조가 예상과 다를 때
        json.JSONDecodeError: JSON 문법이 깨졌을 때
    """
    data = _load_json_file(file_path)

    # 최상위 구조는 반드시 리스트여야 루프 기반 진행이 가능하다.
    if not isinstance(data, list):
        raise ValueError("시나리오 데이터 최상위 구조는 리스트여야 합니다.")

    # 각 시나리오가 딕셔너리인지, 필수 키를 모두 포함하는지 검증한다.
    for idx, scenario in enumerate(data, start=1):
        if not isinstance(scenario, dict):
            raise ValueError(f"{idx}번째 시나리오가 딕셔너리 형식이 아닙니다.")

        missing = REQUIRED_KEYS - set(scenario.keys())
        if missing:
            raise ValueError(
                f"{idx}번째 시나리오에 필수 필드가 누락되었습니다: {sorted(missing)}"
            )

    return data


def load_argos_taunts(file_path: str = "argos_taunts.json") -> dict[str, list[str]]:
    """
    아르고스 대사 데이터를 로드한다.

    Returns:
        dict[str, list[str]]: 카테고리별 대사 배열

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: JSON 구조가 예상과 다를 때
        json.JSONDecodeError: JSON 문법이 깨졌을 때
    """
    data = _load_json_file(file_path)

    # 루트는 {카테고리: [문장, ...]} 형태여야 한다.
    if not isinstance(data, dict):
        raise ValueError("아르고스 대사 데이터 최상위 구조는 딕셔너리여야 합니다.")

    normalized: dict[str, list[str]] = {}
    for category, lines in data.items():
        if not isinstance(category, str):
            raise ValueError("아르고스 대사 카테고리 키는 문자열이어야 합니다.")
        if not isinstance(lines, list):
            raise ValueError(
                f"아르고스 대사 카테고리 '{category}'의 값은 리스트여야 합니다."
            )

        cleaned_lines: list[str] = []
        for idx, line in enumerate(lines, start=1):
            if not isinstance(line, str):
                raise ValueError(
                    f"카테고리 '{category}'의 {idx}번째 대사가 문자열이 아닙니다."
                )
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)

        normalized[category] = cleaned_lines

    return normalized


def load_boss_phase_pack(file_path: str = "boss_phase_pack.json") -> dict[int, list[dict[str, str]]]:
    """
    ASC20 전용 보스 페이즈 데이터팩을 로드한다.

    파일 구조:
        {
          "version": 1,
          "ascension_20_boss_overrides": {
            "17": [
              {"text_log": "...", "target_keyword": "..."},
              {"text_log": "...", "target_keyword": "..."},
              {"text_log": "...", "target_keyword": "..."}
            ]
          }
        }

    Returns:
        dict[int, list[dict[str, str]]]:
            node_id -> phase override list (1-based phase 순서)

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: JSON 구조가 예상과 다를 때
        json.JSONDecodeError: JSON 문법이 깨졌을 때
    """
    data = _load_json_file(file_path)
    if not isinstance(data, dict):
        raise ValueError("보스 페이즈 데이터팩 최상위 구조는 딕셔너리여야 합니다.")

    raw_overrides = data.get("ascension_20_boss_overrides")
    if not isinstance(raw_overrides, dict):
        raise ValueError("ascension_20_boss_overrides는 딕셔너리여야 합니다.")

    normalized: dict[int, list[dict[str, str]]] = {}
    for raw_node_id, raw_phases in raw_overrides.items():
        try:
            node_id = int(raw_node_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"보스 node_id가 정수가 아닙니다: {raw_node_id!r}") from exc

        if node_id <= 0:
            raise ValueError(f"보스 node_id는 양수여야 합니다: {node_id}")
        if not isinstance(raw_phases, list) or not raw_phases:
            raise ValueError(f"node_id {node_id}의 phase 목록은 비어있지 않은 리스트여야 합니다.")

        phase_list: list[dict[str, str]] = []
        for phase_idx, phase_data in enumerate(raw_phases, start=1):
            if not isinstance(phase_data, dict):
                raise ValueError(
                    f"node_id {node_id}의 {phase_idx}번째 phase 항목이 딕셔너리가 아닙니다."
                )

            missing = BOSS_PHASE_REQUIRED_KEYS - set(phase_data.keys())
            if missing:
                raise ValueError(
                    f"node_id {node_id}의 {phase_idx}번째 phase에 필수 필드가 누락되었습니다: {sorted(missing)}"
                )

            text_log = phase_data.get("text_log")
            target_keyword = phase_data.get("target_keyword")
            if not isinstance(text_log, str) or not text_log.strip():
                raise ValueError(f"node_id {node_id}의 {phase_idx}번째 text_log가 비어 있습니다.")
            if not isinstance(target_keyword, str) or not target_keyword.strip():
                raise ValueError(f"node_id {node_id}의 {phase_idx}번째 target_keyword가 비어 있습니다.")

            normalized_phase = {
                "text_log": text_log,
                "target_keyword": target_keyword,
            }
            logical_flaw = phase_data.get("logical_flaw_explanation", "")
            if isinstance(logical_flaw, str) and logical_flaw.strip():
                normalized_phase["logical_flaw_explanation"] = logical_flaw
            phase_list.append(normalized_phase)

        normalized[node_id] = phase_list

    return normalized
