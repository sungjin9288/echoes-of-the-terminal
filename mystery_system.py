"""MYSTERY 노드 시스템 — 랜덤 이벤트 분기 (개입/무시 선택형)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MysteryEvent:
    """단일 미스터리 이벤트 정의."""

    event_id: str
    title: str
    description: str
    engage_prompt: str  # 개입 선택지 설명
    good_desc: str      # 개입 성공 시 결과 메시지
    bad_desc: str       # 개입 실패 시 결과 메시지
    # 결과 수치 (trace_delta: 음수=감소, 양수=증가)
    good_trace_delta: int
    bad_trace_delta: int
    good_fragments_delta: int
    bad_fragments_delta: int


# ── 10종 미스터리 이벤트 풀 ───────────────────────────────────────────────────

MYSTERY_POOL: tuple[MysteryEvent, ...] = (
    MysteryEvent(
        event_id="corrupted_cache",
        title="부패한 데이터 캐시",
        description=(
            "시스템 어딘가에 방치된 암호화 캐시가 발견되었다.\n"
            "출처는 불분명하다. ARGOS의 함정일 수도 있고, 저항군의 잔재일 수도 있다."
        ),
        engage_prompt="캐시 복호화를 시도한다. (성공: 데이터 조각 +250 / 실패: 추적도 +25)",
        good_desc="[성공] 손상된 캐시에서 데이터 조각 250개를 복구했다.",
        bad_desc="[실패] ARGOS 추적 비콘이었다. 추적도 +25.",
        good_trace_delta=0,
        bad_trace_delta=25,
        good_fragments_delta=250,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="unlocked_backdoor",
        title="잠금 해제된 백도어",
        description=(
            "이전 침투자가 남긴 것으로 보이는 미인증 백도어가 발견되었다.\n"
            "경보 시스템이 아직 이것을 감지하지 못한 것 같다."
        ),
        engage_prompt="백도어를 통해 추적도를 우회한다. (성공: 추적도 -25 / 실패: 추적도 +35)",
        good_desc="[성공] 백도어 경유로 추적 레코드 일부가 삭제되었다. 추적도 -25.",
        bad_desc="[실패] 함정이었다. ARGOS가 이미 파악하고 있었다. 추적도 +35.",
        good_trace_delta=-25,
        bad_trace_delta=35,
        good_fragments_delta=0,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="argos_lure",
        title="ARGOS 미끼 신호",
        description=(
            "ARGOS 핵심 시스템에서 취약한 신호가 방사되고 있다.\n"
            "노출된 취약점처럼 보이지만, ARGOS가 일부러 만든 덫일 수도 있다."
        ),
        engage_prompt="신호에 접속해 취약점을 분석한다. (성공: 추적도 -30 / 실패: 추적도 +40)",
        good_desc="[성공] 실제 취약점이었다. ARGOS 방어 레이어 일부가 손상되었다. 추적도 -30.",
        bad_desc="[실패] ARGOS의 덫이었다. 역추적이 시작된다. 추적도 +40.",
        good_trace_delta=-30,
        bad_trace_delta=40,
        good_fragments_delta=0,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="emergency_signal",
        title="암호화된 긴급 신호",
        description=(
            "저항군 주파수에서 암호화된 짧은 신호가 감지되었다.\n"
            "복호화하면 중요한 정보를 얻을 수 있을 것 같다."
        ),
        engage_prompt="신호를 복호화한다. (성공: 데이터 조각 +300 / 실패: 추적도 +20)",
        good_desc="[성공] 복호화된 신호에는 저항군 캐시 좌표가 담겨 있었다. 데이터 조각 +300.",
        bad_desc="[실패] 신호 복호화 과정에서 ARGOS에게 위치가 노출되었다. 추적도 +20.",
        good_trace_delta=0,
        bad_trace_delta=20,
        good_fragments_delta=300,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="damaged_protocol",
        title="손상된 방어 프로토콜",
        description=(
            "ARGOS 방어 레이어 중 하나가 데이터 손상으로 불안정한 상태다.\n"
            "이것을 활용하면 다음 분석의 패널티를 줄일 수 있다."
        ),
        engage_prompt="손상된 프로토콜을 조작한다. (성공: 추적도 -20 + 데이터 조각 +150 / 실패: 추적도 +30)",
        good_desc="[성공] 프로토콜 손상을 역이용했다. 추적도 -20, 데이터 조각 +150.",
        bad_desc="[실패] 프로토콜이 복구 루틴을 실행했다. 추적도 +30.",
        good_trace_delta=-20,
        bad_trace_delta=30,
        good_fragments_delta=150,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="memory_dump",
        title="ARGOS 메모리 덤프",
        description=(
            "ARGOS의 단기 메모리 일부가 외부에 노출된 상태다.\n"
            "이 덤프를 처리하면 추적 기록을 대폭 지울 수 있다."
        ),
        engage_prompt="메모리 덤프를 처리한다. (성공: 추적도 -35 / 실패: 추적도 +45)",
        good_desc="[성공] 추적 기록 대량 삭제 완료. 추적도 -35.",
        bad_desc="[실패] 덤프에 바이러스가 숨어 있었다. 역추적 강화. 추적도 +45.",
        good_trace_delta=-35,
        bad_trace_delta=45,
        good_fragments_delta=0,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="unstable_connection",
        title="불안정한 연결",
        description=(
            "외부 서버와의 불안정한 연결이 감지되었다.\n"
            "데이터를 추출할 수 있지만, 연결이 끊기면 손실이 발생할 수 있다."
        ),
        engage_prompt="불안정한 연결로 데이터를 추출한다. (성공: 데이터 조각 +400 / 실패: 데이터 조각 -150 & 추적도 +15)",
        good_desc="[성공] 연결이 유지되었다. 대규모 데이터 추출 완료. 데이터 조각 +400.",
        bad_desc="[실패] 연결이 끊겼다. 부분 데이터 손실. 데이터 조각 -150, 추적도 +15.",
        good_trace_delta=0,
        bad_trace_delta=15,
        good_fragments_delta=400,
        bad_fragments_delta=-150,
    ),
    MysteryEvent(
        event_id="recovery_code",
        title="숨겨진 복구 코드",
        description=(
            "시스템 깊은 곳에 저항군이 숨겨둔 것으로 보이는 복구 코드가 있다.\n"
            "활성화하면 추적도를 크게 줄일 수 있다."
        ),
        engage_prompt="복구 코드를 활성화한다. (성공: 추적도 -40 / 실패: 추적도 +15)",
        good_desc="[성공] 복구 코드가 정상 작동했다. 추적도 대폭 감소. -40.",
        bad_desc="[실패] 코드가 만료되었다. 활성화 시도가 로그에 기록되었다. 추적도 +15.",
        good_trace_delta=-40,
        bad_trace_delta=15,
        good_fragments_delta=0,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="argos_vulnerability",
        title="ARGOS 취약점 분석",
        description=(
            "ARGOS 내부 감사 시스템에서 보안 취약점이 발견되었다.\n"
            "이를 즉시 활용할 수 있지만, 위험 부담이 있다."
        ),
        engage_prompt="취약점을 즉시 활용한다. (성공: 추적도 -10 + 데이터 조각 +200 / 실패: 추적도 +25)",
        good_desc="[성공] 취약점 활용 완료. 추적도 -10, 데이터 조각 +200.",
        bad_desc="[실패] 패치된 취약점이었다. 잘못된 접근이 경보를 울렸다. 추적도 +25.",
        good_trace_delta=-10,
        bad_trace_delta=25,
        good_fragments_delta=200,
        bad_fragments_delta=0,
    ),
    MysteryEvent(
        event_id="argos_broadcast",
        title="ARGOS 전송 가로채기",
        description=(
            "ARGOS가 하위 노드에게 전송 중인 명령 스트림이 포착되었다.\n"
            "이 스트림을 역이용하면 ARGOS 자신의 추적 시스템을 혼란시킬 수 있다."
        ),
        engage_prompt="전송 스트림을 역이용한다. (성공: 추적도 -20 + 데이터 조각 +100 / 실패: 추적도 +35)",
        good_desc="[성공] 역이용에 성공했다. ARGOS 추적 시스템 일시 혼란. 추적도 -20, 데이터 조각 +100.",
        bad_desc="[실패] ARGOS가 역탐지했다. 오히려 추적이 강화되었다. 추적도 +35.",
        good_trace_delta=-20,
        bad_trace_delta=35,
        good_fragments_delta=100,
        bad_fragments_delta=0,
    ),
)

# 빠른 조회를 위한 인덱스
MYSTERY_INDEX: dict[str, MysteryEvent] = {m.event_id: m for m in MYSTERY_POOL}


# ── 퍼블릭 API ────────────────────────────────────────────────────────────────

def pick_mystery(run_seed: int, node_position: int) -> MysteryEvent:
    """
    런 시드와 노드 포지션으로 결정론적 미스터리 이벤트를 선택한다.

    Args:
        run_seed: 런 고유 시드 (정수)
        node_position: 현재 노드 위치 (0~7)

    Returns:
        선택된 MysteryEvent
    """
    raw = f"{run_seed}-mystery-pick-{node_position}"
    digest = int(hashlib.md5(raw.encode()).hexdigest(), 16)
    idx = digest % len(MYSTERY_POOL)
    return MYSTERY_POOL[idx]


def resolve_mystery_outcome(run_seed: int, node_position: int) -> bool:
    """
    개입 선택 시 결과가 좋은지(True) 나쁜지(False)를 결정론적으로 판별한다.

    결과 판정은 50:50이며, 런 시드 + 포지션으로 고정된다.

    Args:
        run_seed: 런 고유 시드
        node_position: 현재 노드 위치

    Returns:
        True = 좋은 결과, False = 나쁜 결과
    """
    raw = f"{run_seed}-mystery-outcome-{node_position}"
    digest = int(hashlib.md5(raw.encode()).hexdigest(), 16)
    return digest % 2 == 0


def apply_mystery_outcome(
    event: MysteryEvent,
    is_good: bool,
    trace_level: int,
    save_data: dict[str, Any],
) -> tuple[int, dict[str, Any], str]:
    """
    미스터리 이벤트 결과를 적용하고 업데이트된 상태를 반환한다.

    세이브 데이터와 추적도를 직접 수정하지 않고 새 값으로 반환한다 (불변 패턴).

    Args:
        event: 발생한 MysteryEvent
        is_good: 좋은 결과 여부
        trace_level: 현재 추적도 (0~100)
        save_data: 현재 세이브 데이터

    Returns:
        tuple[int, dict, str]:
            - new_trace: 업데이트된 추적도
            - new_save_data: 업데이트된 세이브 데이터
            - result_message: 결과 설명 메시지
    """
    if is_good:
        trace_delta = event.good_trace_delta
        frag_delta = event.good_fragments_delta
        message = event.good_desc
    else:
        trace_delta = event.bad_trace_delta
        frag_delta = event.bad_fragments_delta
        message = event.bad_desc

    # 추적도 업데이트 (0~100 클램핑)
    new_trace = max(0, min(100, trace_level + trace_delta))

    # 데이터 조각 업데이트
    new_save_data = dict(save_data)
    current_frags = int(save_data.get("data_fragments", 0))
    new_frags = max(0, current_frags + frag_delta)
    new_save_data = {**save_data, "data_fragments": new_frags}

    return new_trace, new_save_data, message


def get_mystery_snapshot() -> dict[str, Any]:
    """미스터리 이벤트 풀 전체 요약 정보를 반환한다."""
    return {
        "total_events": len(MYSTERY_POOL),
        "event_ids": [m.event_id for m in MYSTERY_POOL],
    }
