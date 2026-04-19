"""다중 세이브 슬롯 시스템 테스트."""

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from progression_system import (
    DEFAULT_SAVE_DATA,
    SAVE_SLOT_COUNT,
    _get_slot_save_path,
    _normalize_save_data,
    get_all_slots_info,
    get_slot_info,
    load_save_slot,
    migrate_legacy_save,
    save_game_slot,
)


# ── 슬롯 경로 ─────────────────────────────────────────────────────────────────────

def test_slot_paths_are_distinct() -> None:
    """슬롯별 경로가 서로 달라야 한다."""
    paths = [str(_get_slot_save_path(s)) for s in range(1, SAVE_SLOT_COUNT + 1)]
    assert len(set(paths)) == SAVE_SLOT_COUNT


def test_slot_path_contains_slot_number() -> None:
    """슬롯 경로 파일명에 슬롯 번호가 포함돼야 한다."""
    for slot in range(1, SAVE_SLOT_COUNT + 1):
        assert f"save_slot_{slot}" in str(_get_slot_save_path(slot))


def test_slot_path_clamps_below_min(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """슬롯 번호 0 이하는 1로 클램핑된다."""
    monkeypatch.chdir(tmp_path)
    path_neg = _get_slot_save_path(0)
    path_one = _get_slot_save_path(1)
    assert path_neg == path_one


def test_slot_path_clamps_above_max(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """슬롯 번호 SAVE_SLOT_COUNT 초과는 최댓값으로 클램핑된다."""
    monkeypatch.chdir(tmp_path)
    path_over = _get_slot_save_path(SAVE_SLOT_COUNT + 10)
    path_max = _get_slot_save_path(SAVE_SLOT_COUNT)
    assert path_over == path_max


# ── get_slot_info ────────────────────────────────────────────────────────────────

def test_get_slot_info_empty_when_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """파일이 없으면 empty=True를 반환한다."""
    monkeypatch.chdir(tmp_path)
    info = get_slot_info(1)
    assert info["slot"] == 1
    assert info["empty"] is True


def test_get_slot_info_returns_fragments_and_victories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """슬롯 파일이 있으면 data_fragments와 campaign_victories를 반환한다."""
    monkeypatch.chdir(tmp_path)
    save = deepcopy(DEFAULT_SAVE_DATA)
    save["data_fragments"] = 500
    save["campaign"]["victories"] = 7
    slot_path = _get_slot_save_path(1)
    slot_path.write_text(json.dumps(save), encoding="utf-8")

    info = get_slot_info(1)
    assert info["empty"] is False
    assert info.get("corrupted") is not True
    assert info["data_fragments"] == 500
    assert info["campaign_victories"] == 7
    assert "last_saved" in info


def test_get_slot_info_corrupted_on_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JSON이 깨진 파일은 corrupted=True를 반환한다."""
    monkeypatch.chdir(tmp_path)
    slot_path = _get_slot_save_path(2)
    slot_path.write_text("NOT_JSON{{{", encoding="utf-8")

    info = get_slot_info(2)
    assert info["corrupted"] is True


# ── get_all_slots_info ───────────────────────────────────────────────────────────

def test_get_all_slots_info_returns_correct_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 슬롯 정보 리스트 길이가 SAVE_SLOT_COUNT와 같아야 한다."""
    monkeypatch.chdir(tmp_path)
    infos = get_all_slots_info()
    assert len(infos) == SAVE_SLOT_COUNT


def test_get_all_slots_info_slot_numbers_are_sequential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """슬롯 번호가 1~SAVE_SLOT_COUNT 순서로 반환돼야 한다."""
    monkeypatch.chdir(tmp_path)
    infos = get_all_slots_info()
    assert [i["slot"] for i in infos] == list(range(1, SAVE_SLOT_COUNT + 1))


# ── load_save_slot / save_game_slot ─────────────────────────────────────────────

def test_save_and_load_slot_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """저장 후 로드하면 동일한 데이터가 반환돼야 한다."""
    monkeypatch.chdir(tmp_path)
    save = deepcopy(DEFAULT_SAVE_DATA)
    save["data_fragments"] = 999
    save_game_slot(save, 2)

    loaded = load_save_slot(2)
    assert loaded["data_fragments"] == 999


def test_save_game_slot_writes_to_correct_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """save_game_slot은 지정 슬롯 파일에만 쓴다."""
    monkeypatch.chdir(tmp_path)
    save = deepcopy(DEFAULT_SAVE_DATA)

    save_game_slot(save, 1)
    save_game_slot(save, 3)

    assert _get_slot_save_path(1).exists()
    assert not _get_slot_save_path(2).exists()
    assert _get_slot_save_path(3).exists()


def test_load_save_slot_creates_default_on_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """파일이 없으면 기본값 세이브가 반환된다."""
    monkeypatch.chdir(tmp_path)
    loaded = load_save_slot(2)
    assert loaded["data_fragments"] == 0
    assert loaded["schema_version"] == 3


def test_slots_are_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """슬롯 1과 슬롯 2는 서로 독립된 데이터를 가진다."""
    monkeypatch.chdir(tmp_path)
    save1 = deepcopy(DEFAULT_SAVE_DATA)
    save1["data_fragments"] = 100
    save2 = deepcopy(DEFAULT_SAVE_DATA)
    save2["data_fragments"] = 200

    save_game_slot(save1, 1)
    save_game_slot(save2, 2)

    loaded1 = load_save_slot(1)
    loaded2 = load_save_slot(2)
    assert loaded1["data_fragments"] == 100
    assert loaded2["data_fragments"] == 200


# ── migrate_legacy_save ───────────────────────────────────────────────────────────

def test_migrate_legacy_save_copies_to_slot1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """save_data.json이 있고 슬롯 1이 없을 때 슬롯 1로 복사된다."""
    monkeypatch.chdir(tmp_path)
    save = deepcopy(DEFAULT_SAVE_DATA)
    save["data_fragments"] = 42
    # 레거시 파일 생성 (CWD 기준 save_data.json)
    (tmp_path / "save_data.json").write_text(json.dumps(save), encoding="utf-8")

    migrate_legacy_save()

    slot1_path = _get_slot_save_path(1)
    assert slot1_path.exists()
    migrated = json.loads(slot1_path.read_text(encoding="utf-8"))
    assert migrated["data_fragments"] == 42


def test_migrate_legacy_save_skips_if_slot1_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """슬롯 1 파일이 이미 존재하면 레거시 파일을 덮어쓰지 않는다."""
    monkeypatch.chdir(tmp_path)
    legacy = deepcopy(DEFAULT_SAVE_DATA)
    legacy["data_fragments"] = 100
    (tmp_path / "save_data.json").write_text(json.dumps(legacy), encoding="utf-8")

    existing_slot1 = deepcopy(DEFAULT_SAVE_DATA)
    existing_slot1["data_fragments"] = 999
    slot1_path = _get_slot_save_path(1)
    slot1_path.write_text(json.dumps(existing_slot1), encoding="utf-8")

    migrate_legacy_save()

    kept = json.loads(slot1_path.read_text(encoding="utf-8"))
    assert kept["data_fragments"] == 999  # 기존 슬롯 1 데이터 유지


def test_migrate_legacy_save_noop_if_no_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """레거시 파일이 없으면 슬롯 1 파일을 생성하지 않는다."""
    monkeypatch.chdir(tmp_path)
    migrate_legacy_save()
    assert not _get_slot_save_path(1).exists()
