"""route_map.py 유닛 테스트.

NodeType 열거형, build_route_choices, 레이블/설명/스타일 헬퍼 함수 검증.
"""

from __future__ import annotations

import pytest

from route_map import (
    NodeType,
    build_route_choices,
    get_desc,
    get_label,
    get_style,
)


# ── NodeType 열거형 ──────────────────────────────────────────────────────────

class TestNodeType:
    def test_all_expected_types_exist(self) -> None:
        expected = {"NORMAL", "SHOP", "REST", "ELITE", "BOSS", "MYSTERY"}
        actual = {nt.value for nt in NodeType}
        assert expected == actual

    def test_node_type_is_str(self) -> None:
        assert isinstance(NodeType.NORMAL, str)
        assert NodeType.NORMAL == "NORMAL"

    def test_node_type_equality(self) -> None:
        assert NodeType.SHOP == NodeType.SHOP
        assert NodeType.SHOP != NodeType.REST


# ── build_route_choices ───────────────────────────────────────────────────────

class TestBuildRouteChoices:
    def test_returns_correct_length(self) -> None:
        result = build_route_choices(6)
        assert len(result) == 6

    def test_each_element_is_two_node_types(self) -> None:
        result = build_route_choices(3)
        for left, right in result:
            assert isinstance(left, NodeType)
            assert isinstance(right, NodeType)

    def test_zero_choices_returns_empty(self) -> None:
        result = build_route_choices(0)
        assert result == []

    def test_choices_do_not_include_boss(self) -> None:
        """BOSS는 가중치 테이블에 없으므로 build_route_choices에서 나와선 안 된다."""
        for _ in range(20):
            for left, right in build_route_choices(6):
                assert left != NodeType.BOSS
                assert right != NodeType.BOSS

    def test_variety_over_many_samples(self) -> None:
        """충분히 많이 샘플링하면 최소 3가지 이상 다른 타입이 등장해야 한다."""
        seen: set[NodeType] = set()
        for _ in range(50):
            for left, right in build_route_choices(6):
                seen.add(left)
                seen.add(right)
        assert len(seen) >= 3

    def test_choices_tend_to_differ(self) -> None:
        """각 쌍의 left/right가 항상 같지는 않아야 한다 (5회 재샘플링 덕분)."""
        same_count = 0
        total = 0
        for _ in range(30):
            for left, right in build_route_choices(6):
                total += 1
                if left == right:
                    same_count += 1
        # 최대 30% 이하여야 한다 (완전 랜덤 기대값은 1/5 = 20%)
        assert same_count / total < 0.30


# ── 레이블 / 설명 / 스타일 헬퍼 ──────────────────────────────────────────────

class TestHelpers:
    @pytest.mark.parametrize("node_type", list(NodeType))
    def test_get_label_returns_non_empty_string(self, node_type: NodeType) -> None:
        label = get_label(node_type)
        assert isinstance(label, str) and label

    @pytest.mark.parametrize("node_type", list(NodeType))
    def test_get_desc_returns_string(self, node_type: NodeType) -> None:
        desc = get_desc(node_type)
        assert isinstance(desc, str)

    @pytest.mark.parametrize("node_type", list(NodeType))
    def test_get_style_returns_non_empty_string(self, node_type: NodeType) -> None:
        style = get_style(node_type)
        assert isinstance(style, str) and style

    def test_boss_label_distinct(self) -> None:
        assert get_label(NodeType.BOSS) != get_label(NodeType.NORMAL)

    def test_unknown_node_type_get_label_falls_back(self) -> None:
        """존재하지 않는 키를 넣으면 str(node_type) 형태로 폴백된다."""
        # get_label은 dict.get(node_type, str(node_type)) 방식이므로 KeyError 없어야 함
        result = get_label(NodeType.MYSTERY)
        assert result  # 빈 문자열이면 안 됨
