from src.detector import ChangeEvent
from src.formatter import format_changes


def test_format_empty():
    """空变化列表返回空字符串"""
    result = format_changes([])
    assert result == ""


def test_format_status_only():
    """仅整体状态变化"""
    changes = [
        ChangeEvent(
            type="status",
            title="整体状态变更",
            details="All Systems Operational → Partial System Outage",
        )
    ]
    result = format_changes(changes)
    assert "【VRChat 状态】" in result
    assert "整体状态变更" in result
    assert "所有系统正常" in result
    assert "部分系统中断" in result


def test_format_component_only():
    """仅组件变化"""
    changes = [
        ChangeEvent(
            type="component",
            title="组件状态变更: VRChat Web",
            details="operational → major_outage",
        )
    ]
    result = format_changes(changes)
    assert "【VRChat 组件】" in result
    assert "VRChat Web" in result
    assert "正常运行" in result
    assert "严重中断" in result


def test_format_incident_new():
    """新增事件"""
    changes = [
        ChangeEvent(
            type="incident",
            title="新增事件",
            details="事件: 连接异常\n状态: investigating\n影响: critical",
        )
    ]
    result = format_changes(changes)
    assert "【VRChat 事件】" in result
    assert "连接异常" in result
    assert "调查中" in result
    assert "严重故障" in result


def test_format_maintenance():
    """计划维护"""
    changes = [
        ChangeEvent(
            type="maintenance",
            title="新增计划维护",
            details="维护: 服务器升级\n状态: scheduled\n影响: maintenance",
        )
    ]
    result = format_changes(changes)
    assert "【VRChat 维护】" in result
    assert "服务器升级" in result
    assert "已计划" in result


def test_format_multiple_types_together():
    """多种变化合并为一条消息"""
    changes = [
        ChangeEvent(type="status", title="整体状态变更", details="A → B"),
        ChangeEvent(type="component", title="组件状态变更: Web", details="op → major"),
        ChangeEvent(type="incident", title="新增事件", details="事件: X\n状态: Y\n影响: Z"),
    ]
    result = format_changes(changes)
    # 顺序: 状态 > 组件 > 事件 > 维护
    status_pos = result.index("【VRChat 状态】")
    component_pos = result.index("【VRChat 组件】")
    incident_pos = result.index("【VRChat 事件】")
    assert status_pos < component_pos < incident_pos


def test_format_includes_update_time():
    """包含更新时间"""
    changes = [ChangeEvent(type="status", title="整体状态变更", details="A → B")]
    result = format_changes(changes)
    assert "更新时间" in result
