"""将变化事件渲染为 QQ 纯文本消息."""

from __future__ import annotations

from datetime import datetime, timezone

from src.detector import ChangeEvent

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

        sections.append(f"{event.title}: {event.details}")

    # 追加时间
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sections.append(f"更新时间：{now}")

    return "\n".join(sections)
