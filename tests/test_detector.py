from src.detector import detect, ChangeEvent


def test_first_run_returns_empty():
    """首次运行（old=None）返回空列表"""
    new = {"status": {"indicator": "none"}}
    result = detect(None, new)
    assert result == []


def test_status_indicator_change():
    """整体状态 indicator 变化"""
    old = {"status": {"indicator": "none", "description": "All Systems Operational"}}
    new = {"status": {"indicator": "major", "description": "Partial System Outage"}}

    result = detect(old, new)
    assert len(result) == 1
    assert result[0].type == "status"
    assert "All Systems Operational" in result[0].details
    assert "Partial System Outage" in result[0].details


def test_status_description_change():
    """整体状态 description 变化"""
    old = {"status": {"indicator": "none", "description": "All Systems Operational"}}
    new = {"status": {"indicator": "none", "description": "All Systems Running"}}

    result = detect(old, new)
    assert len(result) == 1
    assert result[0].type == "status"


def test_no_status_change():
    """整体状态无变化"""
    s = {"status": {"indicator": "none", "description": "All Systems Operational"}}
    result = detect(s, s)
    assert len([e for e in result if e.type == "status"]) == 0


def test_component_status_change():
    """组件 status 变化"""
    old = {
        "components": [
            {"id": "c1", "name": "VRChat Web", "status": "operational"},
            {"id": "c2", "name": "Avatar System", "status": "operational"},
        ]
    }
    new = {
        "components": [
            {"id": "c1", "name": "VRChat Web", "status": "major_outage"},
            {"id": "c2", "name": "Avatar System", "status": "operational"},
        ]
    }

    result = detect(old, new)
    comp_events = [e for e in result if e.type == "component"]
    assert len(comp_events) == 1
    assert "VRChat Web" in comp_events[0].title
    assert "operational" in comp_events[0].details
    assert "major_outage" in comp_events[0].details


def test_new_incident():
    """新增 incident"""
    old = {"incidents": []}
    new = {
        "incidents": [
            {
                "id": "inc1",
                "name": "连接异常",
                "status": "investigating",
                "impact": "critical",
            }
        ]
    }

    result = detect(old, new)
    inc_events = [e for e in result if e.type == "incident"]
    assert len(inc_events) == 1
    assert "新增" in inc_events[0].title
    assert "连接异常" in inc_events[0].details


def test_incident_status_change():
    """incident 状态变化"""
    old = {
        "incidents": [
            {"id": "inc1", "name": "连接异常", "status": "investigating", "impact": "critical"}
        ]
    }
    new = {
        "incidents": [
            {"id": "inc1", "name": "连接异常", "status": "identified", "impact": "critical"}
        ]
    }

    result = detect(old, new)
    inc_events = [e for e in result if e.type == "incident"]
    assert len(inc_events) == 1
    assert "连接异常" in inc_events[0].title


def test_incident_new_update():
    """incident 有新的更新记录"""
    old = {
        "incidents": [
            {
                "id": "inc1",
                "name": "连接异常",
                "status": "investigating",
                "impact": "critical",
                "incident_updates": [
                    {"status": "investigating", "body": "正在调查", "display_at": "2026-07-15T10:00:00Z"}
                ],
            }
        ]
    }
    new = {
        "incidents": [
            {
                "id": "inc1",
                "name": "连接异常",
                "status": "investigating",
                "impact": "critical",
                "incident_updates": [
                    {"status": "investigating", "body": "正在调查", "display_at": "2026-07-15T10:00:00Z"},
                    {"status": "investigating", "body": "仍在排查", "display_at": "2026-07-15T11:00:00Z"},
                ],
            }
        ]
    }

    result = detect(old, new)
    inc_events = [e for e in result if e.type == "incident"]
    assert len(inc_events) == 1
    assert "更新" in inc_events[0].title


def test_new_scheduled_maintenance():
    """新增计划维护"""
    old = {"scheduled_maintenances": []}
    new = {
        "scheduled_maintenances": [
            {
                "id": "m1",
                "name": "服务器升级",
                "status": "scheduled",
                "impact": "maintenance",
            }
        ]
    }

    result = detect(old, new)
    m_events = [e for e in result if e.type == "maintenance"]
    assert len(m_events) == 1
    assert "新增" in m_events[0].title
    assert "服务器升级" in m_events[0].details


def test_multiple_changes_in_one_poll():
    """同一轮次多种变化"""
    old = {
        "status": {"indicator": "none", "description": "All Systems Operational"},
        "components": [{"id": "c1", "name": "Web", "status": "operational"}],
        "incidents": [],
        "scheduled_maintenances": [],
    }
    new = {
        "status": {"indicator": "major", "description": "Partial Outage"},
        "components": [{"id": "c1", "name": "Web", "status": "major_outage"}],
        "incidents": [
            {"id": "i1", "name": "故障", "status": "investigating", "impact": "critical"}
        ],
        "scheduled_maintenances": [],
    }

    result = detect(old, new)
    types = {e.type for e in result}
    assert types == {"status", "component", "incident"}
