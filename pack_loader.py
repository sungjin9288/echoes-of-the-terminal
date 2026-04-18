"""시나리오 팩(DLC) 로더 모듈.

기본 scenarios.json 외에 packs/ 디렉터리에 있는 추가 팩 파일을
자동으로 발견하고 시나리오 풀에 병합한다.

팩 파일 형식:
    {
        "pack_id":   "pack_23",
        "name":      "팩 이름",
        "version":   "1.0",
        "author":    "작성자",
        "scenarios": [ { ... }, ... ]
    }

팩 파일은 packs/ 디렉터리에 pack_*.json 패턴으로 저장한다.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── 내부 상수 ────────────────────────────────────────────────────────────────

_MAX_PACK_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

# 팩 메타데이터 필수 필드
_PACK_META_REQUIRED: frozenset[str] = frozenset({"pack_id", "name", "scenarios"})

# 팩 내 시나리오 필수 필드 (data_loader.REQUIRED_KEYS 와 동일)
_SCENARIO_REQUIRED: frozenset[str] = frozenset({
    "node_id",
    "theme",
    "difficulty",
    "text_log",
    "target_keyword",
    "penalty_rate",
})

# 유효한 difficulty 값
_VALID_DIFFICULTIES: frozenset[str] = frozenset({"Easy", "Hard", "NIGHTMARE"})


# ── 데이터 클래스 ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PackMetadata:
    """팩 파일의 메타데이터를 담는 불변 컨테이너."""

    pack_id: str
    name: str
    version: str = "1.0"
    author: str = "Unknown"
    scenario_count: int = 0


@dataclass(frozen=True)
class LoadedPack:
    """메타데이터 + 시나리오 리스트를 묶는 불변 컨테이너."""

    metadata: PackMetadata
    scenarios: tuple[dict[str, Any], ...]


# ── 경로 해석 ────────────────────────────────────────────────────────────────

def _resolve_packs_dir(packs_dir: str | Path | None = None) -> Path:
    """팩 디렉터리의 절대 경로를 계산한다.

    우선순위:
    1) 명시적으로 전달된 경로
    2) PyInstaller 번들 내 packs/
    3) 현재 작업 디렉터리 내 packs/
    4) 소스 파일 위치 기준 packs/
    """
    if packs_dir is not None:
        return Path(packs_dir).resolve()

    # PyInstaller 환경
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        candidate = (Path(bundle_dir) / "packs").resolve()
        if candidate.is_dir():
            return candidate

    # CWD 기준
    cwd_candidate = (Path.cwd() / "packs").resolve()
    if cwd_candidate.is_dir():
        return cwd_candidate

    # 소스 위치 기준
    return (Path(__file__).resolve().parent / "packs").resolve()


# ── 단일 팩 로딩 ─────────────────────────────────────────────────────────────

def load_scenario_pack(file_path: str | Path) -> LoadedPack:
    """단일 팩 파일을 로드해 검증 후 LoadedPack을 반환한다.

    Args:
        file_path: 팩 JSON 파일 경로

    Returns:
        LoadedPack: 메타데이터 + 시나리오 목록

    Raises:
        FileNotFoundError: 파일이 없을 때
        ValueError:        구조·필드 검증 실패
        json.JSONDecodeError: JSON 문법 오류
    """
    resolved = Path(file_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"팩 파일을 찾을 수 없습니다: {resolved}")

    file_size = resolved.stat().st_size
    if file_size > _MAX_PACK_FILE_SIZE:
        raise ValueError(
            f"팩 파일 크기({file_size:,} bytes)가 허용 한도를 초과합니다: {resolved}"
        )

    with open(resolved, "r", encoding="utf-8") as f:
        raw: Any = json.load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"팩 파일 최상위 구조는 딕셔너리여야 합니다: {resolved.name}")

    missing_meta = _PACK_META_REQUIRED - raw.keys()
    if missing_meta:
        raise ValueError(
            f"팩 메타데이터에 필수 필드가 누락되었습니다 {sorted(missing_meta)}: {resolved.name}"
        )

    pack_id: str = str(raw["pack_id"]).strip()
    name: str = str(raw["name"]).strip()
    version: str = str(raw.get("version", "1.0")).strip()
    author: str = str(raw.get("author", "Unknown")).strip()

    if not pack_id:
        raise ValueError(f"pack_id가 비어 있습니다: {resolved.name}")
    if not name:
        raise ValueError(f"name이 비어 있습니다: {resolved.name}")

    raw_scenarios = raw["scenarios"]
    if not isinstance(raw_scenarios, list):
        raise ValueError(f"scenarios는 리스트여야 합니다: {resolved.name}")

    validated: list[dict[str, Any]] = []
    for idx, scenario in enumerate(raw_scenarios, start=1):
        if not isinstance(scenario, dict):
            raise ValueError(
                f"{resolved.name}: {idx}번째 시나리오가 딕셔너리가 아닙니다."
            )
        missing_keys = _SCENARIO_REQUIRED - scenario.keys()
        if missing_keys:
            raise ValueError(
                f"{resolved.name}: {idx}번째 시나리오에 필수 필드가 누락되었습니다: "
                f"{sorted(missing_keys)}"
            )
        difficulty = scenario.get("difficulty", "")
        if difficulty not in _VALID_DIFFICULTIES:
            raise ValueError(
                f"{resolved.name}: {idx}번째 시나리오의 difficulty 값이 유효하지 않습니다: "
                f"'{difficulty}' (허용값: {sorted(_VALID_DIFFICULTIES)})"
            )
        validated.append(scenario)

    metadata = PackMetadata(
        pack_id=pack_id,
        name=name,
        version=version,
        author=author,
        scenario_count=len(validated),
    )
    return LoadedPack(metadata=metadata, scenarios=tuple(validated))


# ── 팩 디렉터리 탐색 ──────────────────────────────────────────────────────────

def discover_packs(packs_dir: str | Path | None = None) -> list[Path]:
    """팩 디렉터리에서 pack_*.json 파일 목록을 발견해 정렬 후 반환한다.

    디렉터리가 존재하지 않으면 빈 리스트를 반환한다 (선택적 기능이므로 오류 없음).

    Args:
        packs_dir: 탐색할 디렉터리 경로. None이면 기본 packs/ 디렉터리 사용.

    Returns:
        list[Path]: 발견된 팩 파일 경로 목록 (파일명 기준 정렬)
    """
    resolved_dir = _resolve_packs_dir(packs_dir)
    if not resolved_dir.is_dir():
        return []
    return sorted(resolved_dir.glob("pack_*.json"))


# ── 전체 팩 병합 ─────────────────────────────────────────────────────────────

def load_all_packs(
    packs_dir: str | Path | None = None,
    *,
    known_node_ids: set[int] | None = None,
) -> tuple[list[dict[str, Any]], list[PackMetadata]]:
    """팩 디렉터리의 모든 팩을 로드해 시나리오 목록과 메타데이터를 반환한다.

    node_id 중복 감지: known_node_ids와 팩 간 중복 모두 검사한다.
    중복 발견 시 ValueError를 발생시킨다.

    Args:
        packs_dir:       팩 디렉터리 경로. None이면 기본 경로 사용.
        known_node_ids:  기존 시나리오의 node_id 집합 (중복 방지용).

    Returns:
        (시나리오 목록, 메타데이터 목록)

    Raises:
        ValueError: node_id 중복 또는 팩 파일 구조 오류
    """
    pack_files = discover_packs(packs_dir)
    if not pack_files:
        return [], []

    seen_ids: set[int] = set(known_node_ids or set())
    all_scenarios: list[dict[str, Any]] = []
    all_metadata: list[PackMetadata] = []

    for pack_file in pack_files:
        loaded = load_scenario_pack(pack_file)
        for scenario in loaded.scenarios:
            node_id = int(scenario["node_id"])
            if node_id in seen_ids:
                raise ValueError(
                    f"node_id {node_id} 중복: 팩 '{loaded.metadata.pack_id}' "
                    f"({pack_file.name})"
                )
            seen_ids.add(node_id)
            all_scenarios.append(scenario)
        all_metadata.append(loaded.metadata)

    return all_scenarios, all_metadata
