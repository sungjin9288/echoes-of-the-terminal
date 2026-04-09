"""아티팩트 시스템 — 런 내 랜덤 패시브 아이템 관리."""

import random
from dataclasses import dataclass
from typing import Any

# 아티팩트 추첨 전용 RNG 인스턴스.
# 전역 random 상태와 분리해 타이머 스레드 등 외부 시드 조작의 영향을 받지 않는다.
_rng: random.Random = random.Random()


@dataclass
class Artifact:
    """단일 아티팩트 메타데이터."""

    artifact_id: str
    name: str
    desc: str
    rarity: str  # "COMMON" | "RARE" | "EPIC"


# ── 아티팩트 풀 정의 (20종) ────────────────────────────────────────────────────
# 효과는 main.py의 _apply_artifact_effects()에서 런타임 설정에 반영된다.
ARTIFACT_POOL: list[Artifact] = [
    # COMMON (7종)
    Artifact(
        "static_dampener",
        "정전기 차폐기",
        "오답 시 기본 추적도 상승량 10% 감소",
        "COMMON",
    ),
    Artifact(
        "coolant_pack",
        "냉각 팩",
        "REST 노드에서 추적도 회복량 +10% 추가",
        "COMMON",
    ),
    Artifact(
        "data_shard_x",
        "데이터 샤드 X",
        "노드 클리어 시 데이터 조각 +3 즉시 획득",
        "COMMON",
    ),
    Artifact(
        "relay_booster",
        "릴레이 부스터",
        "타임아웃 추적도 패널티 10% → 7%",
        "COMMON",
    ),
    Artifact(
        "ghost_signal",
        "고스트 신호",
        "첫 오답 추적도 상승 무시 (1회, 런 시작 시 활성화)",
        "COMMON",
    ),
    Artifact(
        "echo_cache",
        "에코 캐시",
        "cat log 재출력 시 타이머 2초 정지",
        "COMMON",
    ),
    Artifact(
        "noise_filter",
        "노이즈 필터",
        "NIGHTMARE 노드 노이즈 헤더 1줄 제거",
        "COMMON",
    ),
    # RARE (5종)
    Artifact(
        "trace_siphon",
        "추적 시폰",
        "노드 클리어 시 추적도 5% 자동 감소",
        "RARE",
    ),
    Artifact(
        "dual_core",
        "듀얼 코어",
        "ELITE 노드 페널티 배율 1.5× → 1.2×",
        "RARE",
    ),
    Artifact(
        "quantum_key",
        "양자 키",
        "런당 1회 analyze 실패를 무조건 성공으로 전환 (힌트: '??' 출력)",
        "RARE",
    ),
    Artifact(
        "overclock",
        "오버클럭",
        "제한 시간 +5초 추가 연장",
        "RARE",
    ),
    Artifact(
        "memory_echo",
        "메모리 에코",
        "이미 클리어한 테마는 추적도 페널티 20% 감소",
        "RARE",
    ),
    # EPIC (3종)
    Artifact(
        "null_protocol",
        "널 프로토콜",
        "보스 노드 페널티 최대 40%로 제한",
        "EPIC",
    ),
    Artifact(
        "phantom_core",
        "팬텀 코어",
        "사망 시 추적도 75%로 1회 부활 (런 전체 1회)",
        "EPIC",
    ),
    Artifact(
        "argos_fragment",
        "아르고스 파편",
        "매 노드 진입 시 추적도 3% 자동 감소",
        "EPIC",
    ),
    # COMMON 추가 (2종) ──────────────────────────────────────────────────────────
    Artifact(
        "signal_buffer",
        "신호 버퍼",
        "타임아웃 발생 시 첫 추적도 상승 1회 면제",
        "COMMON",
    ),
    Artifact(
        "frag_scanner",
        "파편 스캐너",
        "SHOP 노드 아이템 구매 비용 10% 감소",
        "COMMON",
    ),
    # RARE 추가 (2종) ────────────────────────────────────────────────────────────
    Artifact(
        "chrono_anchor",
        "크로노 앵커",
        "오답 발생 시 제한시간 +3초 즉시 복구",
        "RARE",
    ),
    Artifact(
        "entropy_sink",
        "엔트로피 싱크",
        "ELITE 노드 오답 추적도 상한 30%로 제한",
        "RARE",
    ),
    # EPIC 추가 (1종) ────────────────────────────────────────────────────────────
    Artifact(
        "system_purge",
        "시스템 퍼지",
        "런 클리어 시 최종 추적도를 0으로 기록",
        "EPIC",
    ),
]

# ID → Artifact 빠른 조회용 맵
_ARTIFACT_MAP: dict[str, Artifact] = {a.artifact_id: a for a in ARTIFACT_POOL}

# 희귀도별 가중치
_RARITY_WEIGHTS: dict[str, int] = {
    "COMMON": 60,
    "RARE": 30,
    "EPIC": 10,
}


def apply_artifact_effect(
    artifact: Artifact,
    runtime: dict[str, Any],
    run_state: dict[str, Any],
) -> None:
    """
    단일 아티팩트 효과를 런타임 설정과 런 상태에 즉시 적용한다.

    런 내에서 아티팩트를 획득할 때마다 한 번씩 호출한다.
    동일 아티팩트는 중복 획득되지 않으므로 중복 호출은 발생하지 않는다.

    runtime 수정 키:
        penalty_multiplier, time_limit_seconds, timeout_penalty,
        elite_penalty_cap, boss_penalty_cap, nightmare_noise_reduce

    run_state 수정 키:
        skip_next_penalty, ghost_signal_active, phantom_core_active,
        quantum_key_active, per_node_trace_reduction,
        on_clear_trace_reduction, on_clear_frag_bonus, rest_heal_bonus,
        memory_echo_active, echo_cache_active,
        on_timeout_skip_once, on_wrong_time_restore, clear_trace_to_zero

    runtime 추가 수정 키:
        shop_discount, elite_flat_penalty_cap
    """
    art_id = artifact.artifact_id

    if art_id == "static_dampener":
        runtime["penalty_multiplier"] = runtime.get("penalty_multiplier", 1.0) * 0.9

    elif art_id == "relay_booster":
        runtime["timeout_penalty"] = max(
            1, int(runtime.get("timeout_penalty", 10) * 0.7)
        )

    elif art_id == "overclock":
        runtime["time_limit_seconds"] = runtime.get("time_limit_seconds", 30) + 5

    elif art_id == "dual_core":
        runtime["elite_penalty_cap"] = min(
            runtime.get("elite_penalty_cap", 1.5), 1.2
        )

    elif art_id == "null_protocol":
        runtime["boss_penalty_cap"] = min(
            runtime.get("boss_penalty_cap", 999), 40
        )

    elif art_id == "noise_filter":
        runtime["nightmare_noise_reduce"] = (
            runtime.get("nightmare_noise_reduce", 0) + 1
        )

    elif art_id == "memory_echo":
        run_state["memory_echo_active"] = True

    elif art_id == "echo_cache":
        run_state["echo_cache_active"] = True

    elif art_id == "ghost_signal":
        # 런 시작 첫 오답 면역 — 중간 상점 skip_next_penalty와 동일 슬롯 사용
        if not run_state.get("skip_next_penalty"):
            run_state["ghost_signal_active"] = True
            run_state["skip_next_penalty"] = True

    elif art_id == "phantom_core":
        run_state.setdefault("phantom_core_active", True)

    elif art_id == "quantum_key":
        run_state.setdefault("quantum_key_active", True)

    elif art_id == "argos_fragment":
        run_state["per_node_trace_reduction"] = (
            run_state.get("per_node_trace_reduction", 0) + 3
        )

    elif art_id == "trace_siphon":
        run_state["on_clear_trace_reduction"] = (
            run_state.get("on_clear_trace_reduction", 0) + 5
        )

    elif art_id == "data_shard_x":
        run_state["on_clear_frag_bonus"] = run_state.get("on_clear_frag_bonus", 0) + 3

    elif art_id == "coolant_pack":
        run_state["rest_heal_bonus"] = run_state.get("rest_heal_bonus", 0) + 10

    elif art_id == "signal_buffer":
        run_state.setdefault("on_timeout_skip_once", True)

    elif art_id == "frag_scanner":
        runtime["shop_discount"] = runtime.get("shop_discount", 1.0) * 0.9

    elif art_id == "chrono_anchor":
        run_state["on_wrong_time_restore"] = (
            run_state.get("on_wrong_time_restore", 0) + 3
        )

    elif art_id == "entropy_sink":
        runtime["elite_flat_penalty_cap"] = min(
            runtime.get("elite_flat_penalty_cap", 999), 30
        )

    elif art_id == "system_purge":
        run_state.setdefault("clear_trace_to_zero", True)


def draw_artifacts(
    count: int,
    exclude_ids: list[str] | None = None,
) -> list[Artifact]:
    """
    아티팩트 풀에서 중복 없이 `count`개를 추첨해 반환한다.

    가중치는 희귀도에 따른다 (COMMON 60% / RARE 30% / EPIC 10%).
    exclude_ids에 포함된 아티팩트는 추첨에서 제외된다.

    Args:
        count: 반환할 아티팩트 수 (선택지 패널에 표시할 후보 수)
        exclude_ids: 이미 보유 중인 아티팩트 ID 목록

    Returns:
        최대 count개의 Artifact 리스트 (풀이 부족하면 그 이하)
    """
    excluded = set(exclude_ids or [])
    pool = [a for a in ARTIFACT_POOL if a.artifact_id not in excluded]

    if not pool:
        return []

    weights = [_RARITY_WEIGHTS.get(a.rarity, 10) for a in pool]
    k = min(count, len(pool))

    selected: list[Artifact] = []
    remaining = list(zip(pool, weights))

    for _ in range(k):
        if not remaining:
            break
        arts, wts = zip(*remaining)
        chosen = _rng.choices(list(arts), weights=list(wts), k=1)[0]
        selected.append(chosen)
        remaining = [(a, w) for a, w in remaining if a.artifact_id != chosen.artifact_id]

    return selected


def get_artifact(artifact_id: str) -> Artifact | None:
    """ID로 아티팩트를 조회한다. 없으면 None."""
    return _ARTIFACT_MAP.get(artifact_id)

