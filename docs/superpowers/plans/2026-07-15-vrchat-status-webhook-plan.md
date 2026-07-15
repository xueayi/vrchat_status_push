# VRChat Status Webhook Push — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个从 status.vrchat.com 定时拉取状态、检测变化、推送到多个 QQ webhook 的 Docker 化后台服务。

**Architecture:** 采用 asyncio 异步架构，分为 config（配置）、fetcher（拉取）、detector（检测）、formatter（渲染）、dispatcher（推送）、state_store（状态持久化）六个模块，main.py 组装流程。所有 HTTP 请求走 aiohttp，支持全局代理。

**Tech Stack:** Python 3.12+, aiohttp, pytest, pytest-asyncio, pytest-aioresponses, Docker

## Global Constraints

- Python 3.12+
- 依赖仅限 aiohttp（运行时）+ pytest / pytest-asyncio / pytest-aioresponses（测试）
- 所有 HTTP 超时 30 秒
- 重试策略：3 次，间隔 5s / 15s / 30s
- poll_interval 最小 30 秒，默认 120 秒
- 使用标准库 logging，格式：`%(asctime)s [%(levelname)s] %(message)s`
- 所有用户可见文本使用中文
- 单文件不超过 200 行

---

### Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `config.json`
- Create: `data/.gitkeep`

**Interfaces:**
- Produces: 项目骨架、依赖声明、示例配置文件

- [ ] **Step 1: Write requirements.txt**

```txt
aiohttp>=3.9,<4
```

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p src data
touch src/__init__.py
touch data/.gitkeep
```

- [ ] **Step 3: Write example config.json**

```json
{
  "poll_interval_seconds": 120,
  "proxy": null,
  "webhooks": [
    {
      "name": "我的QQ机器人",
      "url": "http://example.com/webhook",
      "umo": "user_group_xxx",
      "message_type": "text",
      "callback_url": null,
      "headers": {}
    }
  ]
}
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-aioresponses
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt src/__init__.py config.json data/.gitkeep
git commit -m "feat: project scaffolding, dependencies and example config"
```

---

### Task 2: Config Module

**Files:**
- Create: `src/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `WebhookConfig` dataclass: `name: str`, `url: str`, `umo: str`, `message_type: str = "text"`, `callback_url: str | None = None`, `headers: dict[str, str] = field(default_factory=dict)`
  - `Config` dataclass: `poll_interval_seconds: int = 120`, `proxy: str | None = None`, `webhooks: list[WebhookConfig]`
  - `load_config(path: str) -> Config`

- [ ] **Step 1: Write failing tests for config loading**

Create `tests/test_config.py`:

```python
import json
import tempfile
from pathlib import Path
import pytest
from src.config import load_config, Config, WebhookConfig


def test_load_minimal_config():
    """加载最小配置 — 仅有必填字段"""
    data = {
        "webhooks": [
            {"name": "test", "url": "http://example.com/webhook", "umo": "group_1"}
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        cfg = load_config(path)
        assert cfg.poll_interval_seconds == 120
        assert cfg.proxy is None
        assert len(cfg.webhooks) == 1
        w = cfg.webhooks[0]
        assert w.name == "test"
        assert w.url == "http://example.com/webhook"
        assert w.umo == "group_1"
        assert w.message_type == "text"
        assert w.callback_url is None
        assert w.headers == {}
    finally:
        Path(path).unlink()


def test_load_full_config():
    """加载完整配置"""
    data = {
        "poll_interval_seconds": 60,
        "proxy": "http://127.0.0.1:7890",
        "webhooks": [
            {
                "name": "bot1",
                "url": "http://example.com/wh1",
                "umo": "group_a",
                "message_type": "text",
                "callback_url": "http://example.com/cb",
                "headers": {"Authorization": "Bearer tok"},
            },
            {
                "name": "bot2",
                "url": "http://example.com/wh2",
                "umo": "group_b",
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        cfg = load_config(path)
        assert cfg.poll_interval_seconds == 60
        assert cfg.proxy == "http://127.0.0.1:7890"
        assert len(cfg.webhooks) == 2
        assert cfg.webhooks[0].headers == {"Authorization": "Bearer tok"}
        assert cfg.webhooks[1].message_type == "text"
    finally:
        Path(path).unlink()


def test_poll_interval_minimum():
    """poll_interval 小于 30 秒应被限制为 30"""
    data = {
        "poll_interval_seconds": 5,
        "webhooks": [{"name": "t", "url": "http://x.com", "umo": "g"}],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        cfg = load_config(path)
        assert cfg.poll_interval_seconds == 30
    finally:
        Path(path).unlink()


def test_proxy_empty_string_is_none():
    """proxy 为空字符串时视为 None"""
    data = {
        "proxy": "",
        "webhooks": [{"name": "t", "url": "http://x.com", "umo": "g"}],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        cfg = load_config(path)
        assert cfg.proxy is None
    finally:
        Path(path).unlink()


def test_missing_webhooks():
    """缺少 webhooks 字段时报错"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({}, f)
        path = f.name

    try:
        with pytest.raises(ValueError, match="webhooks"):
            load_config(path)
    finally:
        Path(path).unlink()


def test_missing_required_webhook_field():
    """webhook 缺少必填字段 name 时报错"""
    data = {"webhooks": [{"url": "http://x.com", "umo": "g"}]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        with pytest.raises(ValueError, match="name"):
            load_config(path)
    finally:
        Path(path).unlink()


def test_file_not_found():
    """配置文件不存在时报错"""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


def test_invalid_json():
    """非法 JSON 时报错"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        path = f.name

    try:
        with pytest.raises(ValueError, match="JSON"):
            load_config(path)
    finally:
        Path(path).unlink()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_config.py -v
```
Expected: all fail (ModuleNotFoundError or ImportError)

- [ ] **Step 3: Implement config.py**

Create `src/config.py`:

```python
"""配置加载与校验."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebhookConfig:
    """单个 webhook 目的地配置."""

    name: str
    url: str
    umo: str
    message_type: str = "text"
    callback_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    """应用全局配置."""

    poll_interval_seconds: int = 120
    proxy: str | None = None
    webhooks: list[WebhookConfig] = field(default_factory=list)


def load_config(path: str) -> Config:
    """从 JSON 文件加载配置，校验后返回 Config 实例."""

    try:
        with open(path, encoding="utf-8") as f:
            raw: dict[str, Any] = json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件 JSON 格式错误: {e}") from e

    if "webhooks" not in raw or not isinstance(raw["webhooks"], list):
        raise ValueError("配置缺少 webhooks 字段或格式不是数组")

    if len(raw["webhooks"]) == 0:
        raise ValueError("webhooks 数组不能为空")

    webhooks: list[WebhookConfig] = []
    for i, wh in enumerate(raw["webhooks"]):
        if not isinstance(wh, dict):
            raise ValueError(f"webhooks[{i}] 必须是对象")

        name = wh.get("name")
        url = wh.get("url")
        umo = wh.get("umo")

        if not name:
            raise ValueError(f"webhooks[{i}] 缺少必填字段: name")
        if not url:
            raise ValueError(f"webhooks[{i}] 缺少必填字段: url")
        if not umo:
            raise ValueError(f"webhooks[{i}] 缺少必填字段: umo")

        webhooks.append(
            WebhookConfig(
                name=str(name),
                url=str(url),
                umo=str(umo),
                message_type=str(wh.get("message_type", "text")),
                callback_url=wh.get("callback_url"),
                headers=wh.get("headers", {}),
            )
        )

    poll = raw.get("poll_interval_seconds", 120)
    if not isinstance(poll, (int, float)) or poll < 30:
        poll = 30

    proxy = raw.get("proxy")
    if proxy is not None and isinstance(proxy, str) and proxy.strip() == "":
        proxy = None

    return Config(
        poll_interval_seconds=int(poll),
        proxy=proxy if proxy else None,
        webhooks=webhooks,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_config.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: add config module with validation"
```

---

### Task 3: State Store Module

**Files:**
- Create: `src/state_store.py`
- Create: `tests/test_state_store.py`

**Interfaces:**
- Produces:
  - `async load(path: str) -> dict | None`
  - `async save(path: str, data: dict) -> None`

- [ ] **Step 1: Write failing tests for state_store**

Create `tests/test_state_store.py`:

```python
import json
import tempfile
from pathlib import Path
from src.state_store import load, save
import pytest


@pytest.mark.asyncio
async def test_save_and_load():
    """保存后能正确加载"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.json"
        data = {"status": {"indicator": "none"}, "components": []}

        await save(str(path), data)
        result = await load(str(path))

        assert result == data


@pytest.mark.asyncio
async def test_load_nonexistent_file():
    """文件不存在时返回 None"""
    result = await load("/nonexistent/path/state.json")
    assert result is None


@pytest.mark.asyncio
async def test_load_corrupted_file():
    """损坏的文件返回 None"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.json"
        path.write_text("not valid json {{{")

        result = await load(str(path))
        assert result is None


@pytest.mark.asyncio
async def test_save_creates_parent_dir():
    """保存时自动创建父目录"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sub" / "nested" / "state.json"
        data = {"key": "value"}

        await save(str(path), data)
        result = await load(str(path))

        assert result == data
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_state_store.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement state_store.py**

Create `src/state_store.py`:

```python
"""状态文件读写."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def load(path: str) -> dict | None:
    """加载状态文件，返回解析后的 dict；文件不存在或损坏返回 None."""
    p = Path(path)
    if not p.exists():
        return None

    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("状态文件读取失败，视为首次运行: %s", e)
        return None


async def save(path: str, data: dict) -> None:
    """保存状态到文件，自动创建父目录."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_state_store.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/state_store.py tests/test_state_store.py
git commit -m "feat: add state_store module for JSON state persistence"
```

---

### Task 4: Fetcher Module

**Files:**
- Create: `src/fetcher.py`
- Create: `tests/test_fetcher.py`

**Interfaces:**
- Consumes: `Config.proxy` (str | None)
- Produces: `async fetch(proxy: str | None) -> dict`
- Note: fetcher 内部维护重试逻辑，不依赖外部模块（除 aiohttp）

- [ ] **Step 1: Write failing tests for fetcher**

Create `tests/test_fetcher.py`:

```python
import json
import pytest
from aiohttp import ClientError
from aioresponses import aioresponses
from src.fetcher import fetch, STATUS_API_URL


SAMPLE_RESPONSE = {
    "page": {"id": "x", "name": "VRChat", "updated_at": "2026-07-15T12:00:00Z"},
    "status": {"indicator": "none", "description": "All Systems Operational"},
    "components": [],
    "incidents": [],
    "scheduled_maintenances": [],
}


@pytest.mark.asyncio
async def test_fetch_success():
    """正常拉取返回 dict"""
    with aioresponses() as m:
        m.get(STATUS_API_URL, payload=SAMPLE_RESPONSE)

        result = await fetch(proxy=None)
        assert result == SAMPLE_RESPONSE


@pytest.mark.asyncio
async def test_fetch_with_proxy():
    """使用代理参数时请求正常"""
    with aioresponses() as m:
        m.get(STATUS_API_URL, payload=SAMPLE_RESPONSE)

        result = await fetch(proxy="http://127.0.0.1:7890")
        assert result == SAMPLE_RESPONSE


@pytest.mark.asyncio
async def test_fetch_retry_then_succeed():
    """前两次失败，第三次成功"""
    with aioresponses() as m:
        m.get(STATUS_API_URL, exception=ClientError("timeout"))
        m.get(STATUS_API_URL, exception=ClientError("timeout"))
        m.get(STATUS_API_URL, payload=SAMPLE_RESPONSE)

        result = await fetch(proxy=None)
        assert result == SAMPLE_RESPONSE


@pytest.mark.asyncio
async def test_fetch_all_retries_exhausted():
    """三次都失败时抛出异常"""
    with aioresponses() as m:
        m.get(STATUS_API_URL, exception=ClientError("timeout"))
        m.get(STATUS_API_URL, exception=ClientError("timeout"))
        m.get(STATUS_API_URL, exception=ClientError("timeout"))

        with pytest.raises(ClientError):
            await fetch(proxy=None)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_fetcher.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement fetcher.py**

Create `src/fetcher.py`:

```python
"""从 status.vrchat.com 拉取服务状态."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)

STATUS_API_URL = "https://status.vrchat.com/api/v2/summary.json"
_RETRY_DELAYS = (5, 15, 30)
_TIMEOUT = aiohttp.ClientTimeout(total=30)


async def fetch(proxy: str | None) -> dict:
    """拉取 summary.json，自动重试。成功返回 dict，全部失败抛出异常."""
    last_error: Exception | None = None

    for attempt, delay in enumerate(_RETRY_DELAYS):
        try:
            return await _do_fetch(proxy)
        except Exception as e:
            last_error = e
            logger.warning(
                "拉取状态失败 (第 %d/%d 次): %s",
                attempt + 1,
                len(_RETRY_DELAYS),
                e,
            )
            if attempt < len(_RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)

    logger.error("拉取状态全部重试 (%d 次) 均失败", len(_RETRY_DELAYS))
    raise last_error  # type: ignore[misc]


async def _do_fetch(proxy: str | None) -> dict:
    """单次 HTTP GET 请求."""
    connector = None
    if proxy:
        connector = aiohttp.TCPConnector()
    else:
        connector = aiohttp.TCPConnector()

    async with aiohttp.ClientSession(
        connector=connector, timeout=_TIMEOUT
    ) as session:
        async with session.get(STATUS_API_URL, proxy=proxy) as resp:
            resp.raise_for_status()
            return await resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_fetcher.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/fetcher.py tests/test_fetcher.py
git commit -m "feat: add fetcher module with retry logic"
```

---

### Task 5: Detector Module

**Files:**
- Create: `src/detector.py`
- Create: `tests/test_detector.py`

**Interfaces:**
- Consumes: old state dict | None, new state dict
- Produces:
  - `ChangeEvent` dataclass: `type: str`, `title: str`, `details: str`
  - `detect(old: dict | None, new: dict) -> list[ChangeEvent]`

- [ ] **Step 1: Write failing tests for detector**

Create `tests/test_detector.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_detector.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement detector.py**

Create `src/detector.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_detector.py -v
```
Expected: all 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/detector.py tests/test_detector.py
git commit -m "feat: add detector module for state change detection"
```

---

### Task 6: Formatter Module

**Files:**
- Create: `src/formatter.py`
- Create: `tests/test_formatter.py`

**Interfaces:**
- Consumes: `list[ChangeEvent]`
- Produces: `format(changes: list[ChangeEvent]) -> str`

- [ ] **Step 1: Write failing tests for formatter**

Create `tests/test_formatter.py`:

```python
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
    assert "All Systems Operational → Partial System Outage" in result


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
    assert "operational → major_outage" in result


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
    assert "investigating" in result
    assert "critical" in result


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
    assert "scheduled" in result


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_formatter.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement formatter.py**

Create `src/formatter.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_formatter.py -v
```
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/formatter.py tests/test_formatter.py
git commit -m "feat: add formatter module for QQ plain text rendering"
```

---

### Task 7: Dispatcher Module

**Files:**
- Create: `src/dispatcher.py`
- Create: `tests/test_dispatcher.py`

**Interfaces:**
- Consumes: `Config.webhooks` (list[WebhookConfig]), content (str), proxy (str | None)
- Produces: `async dispatch(webhooks: list[WebhookConfig], content: str, proxy: str | None) -> None`

- [ ] **Step 1: Write failing tests for dispatcher**

Create `tests/test_dispatcher.py`:

```python
import json
import pytest
from aiohttp import ClientError
from aioresponses import aioresponses
from src.config import WebhookConfig
from src.dispatcher import dispatch


@pytest.mark.asyncio
async def test_dispatch_single_webhook():
    """单 webhook 发送成功"""
    wh = WebhookConfig(name="test", url="http://example.com/wh", umo="group_1")
    with aioresponses() as m:
        m.post("http://example.com/wh", payload={"status": "ok"})

        # 应该不抛异常
        await dispatch([wh], "测试消息", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_sends_correct_body():
    """验证发出的请求体格式"""
    wh = WebhookConfig(
        name="test",
        url="http://example.com/wh",
        umo="group_1",
        message_type="text",
        callback_url="http://example.com/cb",
        headers={"Authorization": "Bearer x"},
    )
    sent_body = {}

    with aioresponses() as m:
        def callback(url, **kwargs):
            nonlocal sent_body
            sent_body = json.loads(kwargs.get("data", "{}"))
            return {"status": "ok"}

        m.post("http://example.com/wh", callback=callback)

        await dispatch([wh], "测试消息", proxy=None)

    assert sent_body["content"] == "测试消息"
    assert sent_body["umo"] == "group_1"
    assert sent_body["message_type"] == "text"
    assert sent_body["callback_url"] == "http://example.com/cb"


@pytest.mark.asyncio
async def test_dispatch_one_fails_others_succeed():
    """一个 webhook 失败不影响其他"""
    wh1 = WebhookConfig(name="good", url="http://example.com/good", umo="g1")
    wh2 = WebhookConfig(name="bad", url="http://example.com/bad", umo="g2")
    wh3 = WebhookConfig(name="also_good", url="http://example.com/also", umo="g3")

    with aioresponses() as m:
        m.post("http://example.com/good", payload={"status": "ok"})
        m.post("http://example.com/bad", exception=ClientError("timeout"))
        m.post("http://example.com/also", payload={"status": "ok"})

        # 应该不抛异常
        await dispatch([wh1, wh2, wh3], "测试", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_with_headers():
    """自定义请求头被传递"""
    wh = WebhookConfig(
        name="test",
        url="http://example.com/wh",
        umo="g1",
        headers={"X-Custom": "value"},
    )
    captured_headers = {}

    with aioresponses() as m:
        def callback(url, **kwargs):
            nonlocal captured_headers
            captured_headers = kwargs.get("headers", {})
            return {"status": "ok"}

        m.post("http://example.com/wh", callback=callback)

        await dispatch([wh], "test", proxy=None)

    assert captured_headers.get("X-Custom") == "value"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_dispatcher.py -v
```
Expected: ImportError

- [ ] **Step 3: Implement dispatcher.py**

Create `src/dispatcher.py`:

```python
"""并发推送消息到多个 webhook 目的地."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from src.config import WebhookConfig

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)


async def dispatch(
    webhooks: list[WebhookConfig],
    content: str,
    proxy: str | None,
) -> None:
    """并发发送消息到所有 webhook。单个失败仅记录日志，不影响其他。"""
    if not webhooks:
        return

    async def _send_one(wh: WebhookConfig) -> None:
        payload = {
            "content": content,
            "umo": wh.umo,
            "message_type": wh.message_type,
            "callback_url": wh.callback_url,
        }
        # 移除值为 None 的字段
        payload = {k: v for k, v in payload.items() if v is not None}

        connector = aiohttp.TCPConnector()
        try:
            async with aiohttp.ClientSession(
                connector=connector, timeout=_TIMEOUT
            ) as session:
                async with session.post(
                    wh.url,
                    json=payload,
                    headers=wh.headers,
                    proxy=proxy,
                ) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        logger.error(
                            "webhook [%s] 返回错误 %d: %s",
                            wh.name,
                            resp.status,
                            body[:200],
                        )
                    else:
                        logger.info("webhook [%s] 发送成功", wh.name)
        except Exception as e:
            logger.error("webhook [%s] 发送失败: %s", wh.name, e)

    # 并发发送
    await asyncio.gather(*[_send_one(wh) for wh in webhooks])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_dispatcher.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/dispatcher.py tests/test_dispatcher.py
git commit -m "feat: add dispatcher module for concurrent webhook delivery"
```

---

### Task 8: Main Entry Point

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: all modules from src/
- Produces: runnable app entry point

- [ ] **Step 1: Write main.py**

Create `main.py`:

```python
"""VRChat Status Webhook Push — 主入口.

定时从 status.vrchat.com 获取服务状态，检测变化后推送到配置的 webhook。
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from src.config import load_config
from src.fetcher import fetch
from src.detector import detect
from src.formatter import format_changes
from src.dispatcher import dispatch
from src.state_store import load as load_state, save as save_state

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("config.json")
STATE_PATH = Path("data/state.json")


def setup_logging() -> None:
    """配置日志格式."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run() -> None:
    """主循环."""
    setup_logging()

    # 加载配置
    logger.info("加载配置: %s", CONFIG_PATH)
    config = load_config(str(CONFIG_PATH))
    logger.info(
        "配置加载完成 — poll_interval=%ds, proxy=%s, webhooks=%d",
        config.poll_interval_seconds,
        config.proxy or "无",
        len(config.webhooks),
    )

    # 加载上次状态
    old_state = await load_state(str(STATE_PATH))
    if old_state is None:
        logger.info("首次运行，本轮仅保存状态不推送")

    # 事件循环
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("收到退出信号，正在关闭...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            pass

    while not stop_event.is_set():
        try:
            # 拉取
            logger.info("拉取 VRChat 状态...")
            new_state = await fetch(config.proxy)

            # 检测变化
            changes = detect(old_state, new_state)

            if changes:
                # 渲染消息
                content = format_changes(changes)
                logger.info("检测到 %d 项变化，准备推送", len(changes))

                # 推送
                await dispatch(config.webhooks, content, config.proxy)
            else:
                logger.debug("本轮无变化")

            # 保存状态
            await save_state(str(STATE_PATH), new_state)
            old_state = new_state

        except Exception:
            logger.exception("本轮轮询出现未预期错误")

        # 等待下一轮（支持优雅退出）
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=config.poll_interval_seconds)
            break  # stop_event 被触发
        except asyncio.TimeoutError:
            pass  # 正常超时，继续下一轮

    logger.info("已退出")


def main() -> None:
    """入口."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("启动失败: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax**

```bash
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"
```
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main entry point with graceful shutdown"
```

---

### Task 9: Docker Deployment

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 1: Write Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY src/ ./src/
COPY main.py .

# 创建数据目录
RUN mkdir -p /app/data

CMD ["python", "main.py"]
```

- [ ] **Step 2: Write docker-compose.yml**

Create `docker-compose.yml`:

```yaml
services:
  vrchat-status-push:
    build: .
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
    restart: unless-stopped
```

- [ ] **Step 3: Write .dockerignore**

Create `.dockerignore`:

```
__pycache__
*.pyc
.venv
venv
.git
tests
docs
data/state.json
*.egg-info
.pytest_cache
```

- [ ] **Step 4: Verify Docker build**

```bash
docker build -t vrchat-status-push .
```
Expected: build succeeds

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker deployment files"
```

---

### Task 10: Integration Verification

**Files:**
- Create: `tests/test_integration.py`（可选，端到端冒烟测试）

- [ ] **Step 1: Full test suite pass**

```bash
python -m pytest tests/ -v
```
Expected: all tests pass (23 tests across 6 test files)

- [ ] **Step 2: Verify config.json is valid**

```bash
python -c "from src.config import load_config; c = load_config('config.json'); print(f'Loaded: {len(c.webhooks)} webhooks, poll={c.poll_interval_seconds}s, proxy={c.proxy}')"
```
Expected: 成功加载配置

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py 2>/dev/null || true
git commit -m "verification: all tests pass, config loads correctly"
```
