"""将变化事件渲染为 QQ 纯文本消息."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.detector import ChangeEvent

# 状态值中英文对照
_STATUS_LABELS: dict[str, str] = {
    "none": "正常",
    "minor": "轻微故障 (Minor)",
    "major": "重大故障 (Major)",
    "critical": "严重故障 (Critical)",
    "operational": "正常运行 (Operational)",
    "degraded_performance": "性能下降 (Degraded)",
    "partial_outage": "部分中断 (Partial Outage)",
    "major_outage": "严重中断 (Major Outage)",
    "under_maintenance": "维护中 (Maintenance)",
    "investigating": "调查中 (Investigating)",
    "identified": "已确认 (Identified)",
    "monitoring": "监控中 (Monitoring)",
    "resolved": "已解决 (Resolved)",
    "scheduled": "已计划 (Scheduled)",
    "in_progress": "进行中 (In Progress)",
    "completed": "已完成 (Completed)",
    "All Systems Operational": "所有系统正常",
    "Partial System Outage": "部分系统中断 (Partial Outage)",
    "Major Service Disruption": "重大服务中断 (Major Disruption)",
    "Minor Service Disruption": "轻微服务中断 (Minor Disruption)",
}


def _label(status: str) -> str:
    """返回状态的中英文对照标签."""
    return _STATUS_LABELS.get(status, status)


# 消息中各组件的排序优先级
_TYPE_ORDER = {"status": 0, "component": 1, "incident": 2, "maintenance": 3}

_TYPE_SECTION_TITLE = {
    "status": "【VRChat 状态】",
    "component": "【VRChat 组件】",
    "incident": "【VRChat 事件】",
    "maintenance": "【VRChat 维护】",
}


def format_changes(changes: list[ChangeEvent]) -> str:
    """将变化列表渲染为一条 QQ 纯文本消息。空列表返回空字符串。"""
    if not changes:
        return ""

    # 按类型排序
    sorted_changes = sorted(changes, key=lambda e: _TYPE_ORDER.get(e.type, 99))

    # 按类型分组
    sections: list[str] = []
    current_type: str | None = None

    for event in sorted_changes:
        if event.type != current_type:
            current_type = event.type
            sections.append(_TYPE_SECTION_TITLE.get(event.type, f"【{event.type}】"))

        # 对 details 中的英文状态值做中英文对照替换（长键优先，避免 major 误替 major_outage）
        details_with_labels = event.details
        for eng, cn in sorted(_STATUS_LABELS.items(), key=lambda x: -len(x[0])):
            details_with_labels = details_with_labels.replace(eng, cn)
        sections.append(f"{event.title}: {details_with_labels}")

    # 追加时间
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    sections.append(f"更新时间：{now} (UTC+8)")

    return "\n".join(sections)
