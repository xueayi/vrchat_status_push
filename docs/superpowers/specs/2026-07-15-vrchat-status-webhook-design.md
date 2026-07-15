# VRChat Status Webhook Push — 设计文档

## 概述

定时从 `status.vrchat.com` 获取 VRChat 服务状态，检测变化后推送到多个 QQ 机器人 webhook（兼容 `astrbot_plugin_push_lite` 格式），以 Docker 容器方式常驻运行，支持全局代理。

## 技术选型

| 维度 | 选择 |
|------|------|
| 语言 | Python 3.12+ |
| HTTP | aiohttp（异步） |
| 调度 | asyncio 事件循环 |
| 配置 | JSON（config.json） |
| 状态持久化 | JSON（data/state.json） |
| 部署 | Docker + docker-compose |

## 架构

```
┌─────────────────────────────────────────────────┐
│                  Docker Container                │
│                                                  │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐ │
│  │  Fetcher │────▶│ Detector │────▶│Formatter │ │
│  │ (定时拉取) │     │ (变化检测) │     │ (QQ文本)  │ │
│  └──────────┘     └──────────┘     └─────┬────┘ │
│                                          │       │
│                    ┌─────────────────────┘       │
│                    ▼                             │
│             ┌──────────────┐                     │
│             │  Dispatcher  │                     │
│             │ (并发推送N个    │                     │
│             │  webhook)     │                     │
│             └──────────────┘                     │
│                    │                             │
│            ┌───────┼───────┐                     │
│            ▼       ▼       ▼                     │
│         webhook1 webhook2 webhook3              │
│                                                  │
│  ┌──────────┐                                    │
│  │  State   │ ← JSON 文件，持久化上一次状态        │
│  │  Store   │                                    │
│  └──────────┘                                    │
└─────────────────────────────────────────────────┘
```

核心流程：定时拉取 → 和本地持久化的上一轮状态比较 → 有变化则渲染 QQ 文本 → 并发推送到所有 webhook → 保存新状态到文件。

## 项目文件结构

```
vrchat_status_push/
├── config.json              # 用户配置文件
├── Dockerfile               # Docker 构建
├── docker-compose.yml       # 可选
├── requirements.txt         # Python 依赖
├── main.py                  # 入口
├── src/
│   ├── __init__.py
│   ├── config.py            # 配置加载与校验
│   ├── fetcher.py           # 拉取 summary.json
│   ├── detector.py          # 对比新旧，检测变化
│   ├── formatter.py         # 变化 → QQ 纯文本
│   ├── dispatcher.py        # 并发推送到 webhook
│   └── state_store.py       # state.json 读写
└── data/
    └── state.json           # 持久化状态（自动生成）
```

## 配置文件

```json
{
  "poll_interval_seconds": 120,
  "proxy": "http://127.0.0.1:7890",
  "webhooks": [
    {
      "name": "我的QQ机器人",
      "url": "http://example.com/webhook",
      "umo": "user_group_xxx",
      "message_type": "text",
      "callback_url": null,
      "headers": {
        "Authorization": "Bearer xxx"
      }
    }
  ]
}
```

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `poll_interval_seconds` | ❌ | 120 | 轮询间隔，最小 30 秒 |
| `proxy` | ❌ | null | 全局代理，全部请求走此代理 |
| `webhooks[].name` | ✅ | — | 标识名称（日志用） |
| `webhooks[].url` | ✅ | — | webhook 接收地址 |
| `webhooks[].umo` | ✅ | — | 目标会话标识（QQ 群/用户） |
| `webhooks[].message_type` | ❌ | "text" | 消息类型 |
| `webhooks[].callback_url` | ❌ | null | 处理结果回调地址 |
| `webhooks[].headers` | ❌ | {} | 自定义请求头，如 Authorization |

### 实际发出的 POST 请求体

```json
{
  "content": "【VRChat 状态变更】...（程序自动生成）",
  "umo": "user_group_xxx",
  "message_type": "text",
  "callback_url": null
}
```

`content` 由 formatter 模块渲染，其余字段从 webhook 配置透传。

## 模块职责

### config.py
- 加载 `config.json`，返回 `Config` dataclass
- 校验必填字段（name、url、umo）
- poll_interval_seconds 最小限制 30 秒
- proxy 为空字符串或 null 时视为不使用代理

### fetcher.py
- `async fetch(proxy: str | None) -> dict`
- 请求 `https://status.vrchat.com/api/v2/summary.json`
- 30 秒超时，异常时重试 3 次（间隔 5s/15s/30s）
- 3 次都失败则跳过本轮，记录错误日志

### detector.py
- `detect(old: dict | None, new: dict) -> list[ChangeEvent]`
- 对比四个维度：status、components、incidents、scheduled_maintenances
- 首次运行（old=None）返回空列表，不推送
- components 按 `id` 匹配，比较 `status` 字段
- incidents/maintenances 按 `id` 匹配，检测新增、状态变化、新增更新记录
- ChangeEvent dataclass：`type`（status/component/incident/maintenance）、`title`、`details`

### formatter.py
- `format(changes: list[ChangeEvent]) -> str`
- 按"整体状态 > 组件 > 事件 > 维护"顺序编排
- 中文展示，状态值映射为可读中文（如 major_outage → 重大故障）
- 同轮次多种变化合并为一条消息

### dispatcher.py
- `async dispatch(webhooks: list, content: str, proxy: str | None) -> None`
- `asyncio.gather` 并发 POST 到所有 webhook
- 每个请求：30 秒超时，失败仅记录日志，不抛异常阻断其他
- 请求体：`{"content": content, "umo": w.umo, "message_type": w.message_type, "callback_url": w.callback_url}`

### state_store.py
- `load() -> dict | None`：从 `data/state.json` 读取
- `save(data: dict) -> None`：写入 `data/state.json`
- 文件不存在或 JSON 解析失败返回 None（视为首次运行）

### main.py
- 加载配置 → 加载已有状态 → 进入 asyncio 事件循环
- 每轮：fetch → detect → 有变化时 format → dispatch → save state
- 捕获 SIGTERM/SIGINT 优雅退出
- 日志：使用标准库 logging，输出时间戳和级别

## 消息格式

### 整体状态变化
```
【VRChat 状态】
整体状态变更：All Systems Operational → Partial System Outage
更新时间：2026-07-15 21:30:00
```

### 组件状态变化
```
【VRChat 组件】
以下组件状态变更：
  · VRChat Web：Operational → Major Outage
  · Avatar System：Operational → Degraded Performance
更新时间：2026-07-15 21:30:00
```

### 新事件
```
【VRChat 事件】
新增事件：部分区域连接异常
状态：正在调查中
影响：critical
时间：2026-07-15 21:25:00
```

### 事件更新
```
【VRChat 事件】
事件更新：部分区域连接异常
状态：调查中 → 已确认
更新时间：2026-07-15 21:35:00
```

## Docker 部署

### Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY main.py .
CMD ["python", "main.py"]
```

### docker-compose.yml
```yaml
services:
  vrchat-status-push:
    build: .
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
    restart: unless-stopped
```

## 异常处理

| 场景 | 行为 |
|------|------|
| 配置文件缺失/格式错误 | 启动时打印错误并退出（exit code 1） |
| 配置必填字段缺失 | 启动时打印具体缺失字段并退出 |
| 网络超时 | 重试 3 次（5s/15s/30s），仍失败则跳过本轮 |
| webhook 发送失败 | 记录日志（含 webhook name），不影响其他目的地 |
| 状态文件损坏 | 打印警告，视为首次运行 |
| SIGTERM/SIGINT | 优雅退出，保存当前状态后关闭 |

## 待确认

- 无。所有设计点在对话中均已确认。
