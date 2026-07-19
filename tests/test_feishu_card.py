"""飞书卡片构建测试."""

from src.detector import ChangeEvent
from src.feishu_card import build_feishu_card


def test_card_has_correct_structure():
    """卡片包含正确的顶层结构"""
    changes = [
        ChangeEvent(
            type="status",
            title="整体状态变更",
            details="All Systems Operational → Partial System Outage",
        )
    ]
    result = build_feishu_card(changes, "major")

    assert result["msg_type"] == "interactive"
    assert "card" in result
    card = result["card"]
    assert card["schema"] == "2.0"
    assert "header" in card
    assert "body" in card


def test_header_color_by_indicator():
    """不同 indicator 对应不同 header 颜色"""
    tests = [
        ("none", "green"),
        ("minor", "yellow"),
        ("major", "orange"),
        ("critical", "red"),
    ]
    for indicator, expected_color in tests:
        result = build_feishu_card([], indicator)
        assert result["card"]["header"]["template"] == expected_color


def test_body_contains_markdown():
    """卡片 body 包含 markdown 元素"""
    changes = [
        ChangeEvent(
            type="component",
            title="组件状态变更: Web",
            details="operational → major_outage",
        )
    ]
    result = build_feishu_card(changes, "major")

    elements = result["card"]["body"]["elements"]
    markdown = elements[0]
    assert markdown["tag"] == "markdown"
    assert "组件状态变更" in markdown["content"]


def test_has_view_details_link():
    """卡片 markdown 包含查看详情链接"""
    result = build_feishu_card([], "none")

    elements = result["card"]["body"]["elements"]
    markdown = elements[0]
    assert markdown["tag"] == "markdown"
    assert "status.vrchat.com" in markdown["content"]


def test_empty_changes():
    """空变化列表仍可构建卡片"""
    result = build_feishu_card([], "none")
    assert result["msg_type"] == "interactive"
    assert "当前状态" in result["card"]["body"]["elements"][0]["content"]
