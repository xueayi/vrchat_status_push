"""对比新旧状态，检测变化."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChangeEvent:
    """状态变化事件."""

    type: str  # "status" | "component" | "incident" | "maintenance"
    title: str
    details: str


def detect(old: dict | None, new: dict) -> list[ChangeEvent]:
    """比较新旧 summary.json 数据，返回变化事件列表。首次运行时 old 为 None，返回空列表。"""
    if old is None:
        return []

    changes: list[ChangeEvent] = []

    changes.extend(_detect_status(old.get("status", {}), new.get("status", {})))
    changes.extend(_detect_components(old.get("components", []), new.get("components", [])))
    changes.extend(_detect_incidents(old.get("incidents", []), new.get("incidents", [])))
    changes.extend(
        _detect_maintenances(
            old.get("scheduled_maintenances", []),
            new.get("scheduled_maintenances", []),
        )
    )

    return changes


def _detect_status(old_status: dict, new_status: dict) -> list[ChangeEvent]:
    old_ind = old_status.get("indicator", "")
    new_ind = new_status.get("indicator", "")
    old_desc = old_status.get("description", "")
    new_desc = new_status.get("description", "")

    if old_ind != new_ind or old_desc != new_desc:
        return [
            ChangeEvent(
                type="status",
                title="整体状态变更",
                details=f"{old_desc} → {new_desc}",
            )
        ]
    return []


def _detect_components(old_comps: list, new_comps: list) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    old_by_id = {c["id"]: c for c in old_comps if isinstance(c, dict) and "id" in c}

    for comp in new_comps:
        if not isinstance(comp, dict) or "id" not in comp:
            continue
        cid = comp["id"]
        old_comp = old_by_id.get(cid)
        if old_comp and old_comp.get("status") != comp.get("status"):
            events.append(
                ChangeEvent(
                    type="component",
                    title=f"组件状态变更: {comp.get('name', cid)}",
                    details=f"{old_comp.get('status', '?')} → {comp.get('status', '?')}",
                )
            )

    return events


def _detect_incidents(old_list: list, new_list: list) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    old_by_id = {i["id"]: i for i in old_list if isinstance(i, dict) and "id" in i}

    for inc in new_list:
        if not isinstance(inc, dict) or "id" not in inc:
            continue
        iid = inc["id"]
        old_inc = old_by_id.get(iid)

        if old_inc is None:
            events.append(
                ChangeEvent(
                    type="incident",
                    title="新增事件",
                    details=(
                        f"事件: {inc.get('name', iid)}\n"
                        f"状态: {inc.get('status', '?')}\n"
                        f"影响: {inc.get('impact', '?')}"
                    ),
                )
            )
        else:
            if old_inc.get("status") != inc.get("status"):
                events.append(
                    ChangeEvent(
                        type="incident",
                        title=f"事件状态变更: {inc.get('name', iid)}",
                        details=f"状态: {old_inc.get('status', '?')} → {inc.get('status', '?')}",
                    )
                )

            old_updates = len(old_inc.get("incident_updates", []))
            new_updates = len(inc.get("incident_updates", []))
            if new_updates > old_updates:
                latest = inc["incident_updates"][-1]
                events.append(
                    ChangeEvent(
                        type="incident",
                        title=f"事件更新: {inc.get('name', iid)}",
                        details=(
                            f"更新: {latest.get('body', '')}\n"
                            f"状态: {latest.get('status', '?')}"
                        ),
                    )
                )

    return events


def _detect_maintenances(old_list: list, new_list: list) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    old_by_id = {m["id"]: m for m in old_list if isinstance(m, dict) and "id" in m}

    for mt in new_list:
        if not isinstance(mt, dict) or "id" not in mt:
            continue
        mid = mt["id"]
        if mid not in old_by_id:
            events.append(
                ChangeEvent(
                    type="maintenance",
                    title="新增计划维护",
                    details=(
                        f"维护: {mt.get('name', mid)}\n"
                        f"状态: {mt.get('status', '?')}\n"
                        f"影响: {mt.get('impact', '?')}"
                    ),
                )
            )
        else:
            old_mt = old_by_id[mid]
            if old_mt.get("status") != mt.get("status"):
                events.append(
                    ChangeEvent(
                        type="maintenance",
                        title=f"维护状态变更: {mt.get('name', mid)}",
                        details=f"状态: {old_mt.get('status', '?')} → {mt.get('status', '?')}",
                    )
                )

    return events
