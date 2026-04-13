"""런 내 루트 맵 분기 시스템 — NORMAL/SHOP/REST/ELITE 노드 타입 관리."""

import random
from enum import Enum


class NodeType(str, Enum):
    """런 내 노드 타입."""

    NORMAL = "NORMAL"
    SHOP = "SHOP"
    REST = "REST"
    ELITE = "ELITE"
    BOSS = "BOSS"
    MYSTERY = "MYSTERY"


# 노드 타입별 출현 가중치
_WEIGHTS: dict[NodeType, int] = {
    NodeType.NORMAL: 45,
    NodeType.REST: 18,
    NodeType.SHOP: 14,
    NodeType.ELITE: 13,
    NodeType.MYSTERY: 10,
}

_TYPE_LABELS: dict[NodeType, str] = {
    NodeType.NORMAL: "일반 노드",
    NodeType.SHOP: "상점 노드",
    NodeType.REST: "휴식 노드",
    NodeType.ELITE: "엘리트 노드",
    NodeType.BOSS: "보스 노드",
    NodeType.MYSTERY: "미스터리 노드",
}

_TYPE_DESCS: dict[NodeType, str] = {
    NodeType.NORMAL: "표준 해킹 분석. 로그에서 모순을 찾아라.",
    NodeType.SHOP: "데이터 조각으로 임시 강화를 구매한다.",
    NodeType.REST: "추적도 20% 감소. 잠시 숨을 고른다.",
    NodeType.ELITE: "강화된 ARGOS 방벽. 페널티 ×1.5, 보상 ×1.5.",
    NodeType.BOSS: "최종 방벽 — NIGHTMARE 프로토콜 활성화.",
    NodeType.MYSTERY: "정체불명 시스템 이벤트. 개입 여부를 선택하라.",
}

_TYPE_STYLES: dict[NodeType, str] = {
    NodeType.NORMAL: "bold green",
    NodeType.SHOP: "bold yellow",
    NodeType.REST: "bold cyan",
    NodeType.ELITE: "bold magenta",
    NodeType.BOSS: "bold red",
    NodeType.MYSTERY: "bold #FF8C00",
}


def _sample_type() -> NodeType:
    """가중치에 따라 노드 타입 하나를 샘플링한다."""
    types = list(_WEIGHTS.keys())
    weights = list(_WEIGHTS.values())
    return random.choices(types, weights=weights, k=1)[0]


def build_route_choices(num_choices: int) -> list[tuple[NodeType, NodeType]]:
    """
    런 경로의 분기 선택지를 생성한다.

    반환값의 i번째 원소는 position i+1에서 선택 가능한 (왼쪽, 오른쪽) 타입 쌍이다.
    두 선택지가 같으면 최대 5회 재샘플링해 선택에 의미를 부여한다.

    Args:
        num_choices: 분기 선택 횟수 (= MAX_NODES_PER_RUN - 1)

    Returns:
        list of (left_type, right_type) tuples
    """
    choices: list[tuple[NodeType, NodeType]] = []
    for _ in range(num_choices):
        left = _sample_type()
        right = _sample_type()
        for _ in range(5):
            if left != right:
                break
            right = _sample_type()
        choices.append((left, right))
    return choices


def get_label(node_type: NodeType) -> str:
    """노드 타입의 한국어 레이블을 반환한다."""
    return _TYPE_LABELS.get(node_type, str(node_type))


def get_desc(node_type: NodeType) -> str:
    """노드 타입의 효과 설명을 반환한다."""
    return _TYPE_DESCS.get(node_type, "")


def get_style(node_type: NodeType) -> str:
    """노드 타입에 해당하는 Rich 스타일 문자열을 반환한다."""
    return _TYPE_STYLES.get(node_type, "white")
