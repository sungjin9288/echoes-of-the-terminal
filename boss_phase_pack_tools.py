"""Utilities for building and syncing ASC20 boss phase pack templates."""

from __future__ import annotations

from typing import Any


def _boss_scenarios_sorted(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return boss scenarios sorted by node_id ascending."""
    bosses: list[dict[str, Any]] = []
    for scenario in scenarios:
        if not scenario.get("is_boss", False):
            continue
        try:
            node_id = int(scenario.get("node_id", -1))
        except (TypeError, ValueError):
            continue
        if node_id <= 0:
            continue
        copied = dict(scenario)
        copied["node_id"] = node_id
        bosses.append(copied)
    bosses.sort(key=lambda s: int(s["node_id"]))
    return bosses


def _placeholder_phase_entry(scenario: dict[str, Any], phase_index: int) -> dict[str, str]:
    """Build a placeholder phase entry from base boss scenario metadata."""
    node_id = int(scenario["node_id"])
    theme = str(scenario.get("theme", "BOSS"))
    keyword = str(scenario.get("target_keyword", "KEYWORD")).strip() or "KEYWORD"
    return {
        "text_log": (
            f"【ASC20 BOSS PHASE-{phase_index} // {theme}】\n"
            f"node_id {node_id} 페이즈 {phase_index} 텍스트를 여기에 작성하세요."
        ),
        "target_keyword": keyword,
        "logical_flaw_explanation": f"node_id {node_id} 페이즈 {phase_index} 모순 설명을 작성하세요.",
    }


def build_boss_phase_pack_template(
    scenarios: list[dict[str, Any]],
    phase_count: int = 3,
    existing_overrides: dict[int, list[dict[str, str]]] | None = None,
) -> dict[str, Any]:
    """
    Build a synced boss phase pack template for ASC20.

    Rules:
    - 대상으로는 scenarios 내 is_boss=true 항목만 사용
    - 기존 오버라이드가 있으면 우선 유지
    - phase_count보다 부족한 phase는 placeholder로 자동 채움
    - 기존 phase가 더 많으면 데이터 손실 방지를 위해 그대로 유지
    """
    safe_phase_count = max(1, int(phase_count))
    existing = existing_overrides or {}
    overrides: dict[str, list[dict[str, str]]] = {}

    for scenario in _boss_scenarios_sorted(scenarios):
        node_id = int(scenario["node_id"])
        existing_phases = existing.get(node_id, [])
        target_len = max(safe_phase_count, len(existing_phases))
        phase_entries: list[dict[str, str]] = []

        for idx in range(target_len):
            phase_index = idx + 1
            if idx < len(existing_phases):
                phase_data = existing_phases[idx]
                text_log = str(phase_data.get("text_log", "")).strip()
                target_keyword = str(phase_data.get("target_keyword", "")).strip()
                if text_log and target_keyword:
                    normalized = {
                        "text_log": text_log,
                        "target_keyword": target_keyword,
                    }
                    logical_flaw = str(phase_data.get("logical_flaw_explanation", "")).strip()
                    if logical_flaw:
                        normalized["logical_flaw_explanation"] = logical_flaw
                    phase_entries.append(normalized)
                    continue
            phase_entries.append(_placeholder_phase_entry(scenario, phase_index))

        overrides[str(node_id)] = phase_entries

    return {
        "version": 1,
        "ascension_20_boss_overrides": overrides,
    }
