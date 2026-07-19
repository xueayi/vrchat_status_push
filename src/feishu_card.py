"""构建飞书交互式卡片消息."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.detector import ChangeEvent

# 状态严重程度 → 卡片 header 颜色
_INDICATOR_COLORS: dict[str, str] = {
    "none": "green",
    "minor": "yellow",
    "major": "orange",
    "critical": "red",
}

_STATUS_LABELS: dict[str, str] = {
    "none": "正常",
    "minor": "轻微故障",
    "major": "重大故障",
    "critical": "严重故障",
    "operational": "正常",
    "degraded_performance": "性能下降",
    "partial_outage": "部分中断",
    "major_outage": "严重中断",
    "under_maintenance": "维护中",
    "investigating": "调查中",
    "identified": "已确认",
    "monitoring": "监控中",
    "resolved": "已解决",
    "scheduled": "已计划",
    "in_progress": "进行中",
    "completed": "已完成",
    "All Systems Operational": "所有系统正常",
    "Partial System Outage": "部分系统中断",
    "Major Service Disruption": "重大服务中断",
    "Minor Service Disruption": "轻微服务中断",
}


def _label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


def _translate_details(details: str) -> str:
    """对详情中的英文状态值做中英对照替换."""
    for eng, cn in sorted(_STATUS_LABELS.items(), key=lambda x: -len(x[0])):
        details = details.replace(eng, cn)
    return details


def build_feishu_card(
    changes: list[ChangeEvent],
    status_indicator: str,
) -> dict:
    """构建飞书卡片消息的完整请求体."""
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    header_color = _INDICATOR_COLORS.get(status_indicator, "blue")
    current_status = _label(status_indicator)

    # 构建 markdown 内容
    lines: list[str] = [
        f"**当前状态：{current_status}**",
        "",
    ]

    for event in changes:
        details = _translate_details(event.details)
        lines.append(f"**{event.title}**")
        lines.append(details.replace("\n", "  \n"))
        lines.append("")

    lines.append(f"更新时间：{now} (UTC+8)")
    lines.append("")
    lines.append("[查看详情](https://status.vrchat.com)")

    markdown_content = "\n".join(lines)

    return {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"update_multi": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "VRChat 状态变更",
                },
                "template": header_color,
            },
            "body": {
                "direction": "vertical",
                "padding": "12px 12px 12px 12px",
                "elements": [
                    {
                        "tag": "markdown",
                        "content": markdown_content,
                        "text_align": "left",
                        "text_size": "normal_v2",
                    },
                ],
            },
        },
    }
