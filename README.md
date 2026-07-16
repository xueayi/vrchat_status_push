# VRChat Status Webhook Push

定时从 [status.vrchat.com](https://status.vrchat.com) 获取 VRChat 服务状态，检测到变化时推送到 QQ 机器人（兼容 [astrbot_plugin_push_lite](https://github.com/Raven95676/astrbot_plugin_push_lite)）。

## 功能

- 每 15 分钟轮询 VRChat 官方状态 API
- 检测整体状态、组件、事件、计划维护四类变化
- 变化时通过 webhook 推送 QQ 纯文本消息（含中英文状态对照）
- 支持多个 webhook 目的地，并发推送
- 支持 HTTP 代理
- 首次运行不推送，避免刷屏
- Docker 一键部署

## 快速开始

### 1. 配置

参照 `config.example.json` 创建配置文件。实际配置文件 `config.json` 不会被 git 跟踪，避免凭据泄漏。

```bash
cp config.example.json config.json
# 编辑 config.json 填入你的 webhook 信息
```

```json
{
  "poll_interval_seconds": 900,
  "proxy": "http://127.0.0.1:7890",
  "webhooks": [
    {
      "name": "我的机器人",
      "url": "http://your-server:10010/send",
      "umo": "BotName:FriendMessage:QQ号",
      "message_type": "text",
      "callback_url": null,
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `poll_interval_seconds` | ❌ | 轮询间隔秒数，默认 900（15 分钟），最小 30 |
| `proxy` | ❌ | HTTP 代理地址，null 为直连 |
| `webhooks[].name` | ✅ | 标识名称（日志用） |
| `webhooks[].url` | ✅ | webhook 地址 |
| `webhooks[].umo` | ✅ | 会话标识，格式 `BotName:MessageType:ID` |
| `webhooks[].message_type` | ❌ | 默认 `"text"` |
| `webhooks[].callback_url` | ❌ | 回调地址 |
| `webhooks[].headers` | ❌ | 自定义请求头，如鉴权 |

### 2. 运行

**Docker（推荐）：**

```bash
docker compose up -d
```

**本地运行：**

```bash
pip install -r requirements.txt
python main.py
```

## 消息示例

推送消息自动附带中英文状态对照：

```
【VRChat 状态】
整体状态变更: 所有系统正常 → 部分系统中断 (Partial Outage)
更新时间：2026-07-16 17:30:00 (UTC+8)

【VRChat 组件】
组件状态变更: VRChat Web: 正常运行 (Operational) → 严重中断 (Major Outage)
更新时间：2026-07-16 17:30:00 (UTC+8)

【VRChat 事件】
新增事件: 部分区域连接异常
状态: 调查中 (Investigating)
影响: 严重故障 (Critical)
更新时间：2026-07-16 17:25:00 (UTC+8)
```

## 项目结构

```
vrchat_status_push/
├── main.py
├── config.example.json
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── config.py            # 配置加载校验
│   ├── fetcher.py           # API 拉取 + 重试
│   ├── detector.py          # 变化检测
│   ├── formatter.py         # QQ 文本渲染（含中英对照）
│   ├── dispatcher.py        # 并发推送
│   └── state_store.py       # 状态持久化
└── tests/
```

## 测试

```bash
pip install pytest pytest-asyncio pytest-aioresponses
python -m pytest tests/ -v
```
