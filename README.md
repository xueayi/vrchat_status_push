# VRChat Status Webhook Push

定时从 [status.vrchat.com](https://status.vrchat.com) 获取 VRChat 服务状态，检测到变化时推送到 QQ / 飞书 webhook。

## 功能

- 每 15 分钟轮询 VRChat 官方状态 API
- 检测整体状态、组件、事件、计划维护四类变化
- **QQ**：纯文本消息（含中英文状态对照），兼容 [astrbot_plugin_push_lite](https://github.com/Raven95676/astrbot_plugin_push_lite)
- **飞书**：交互式卡片消息，header 颜色随状态严重程度变化，底部带跳转按钮
- 支持多个 webhook 目的地混合推送，并发发送
- 支持 HTTP 代理
- 首次运行不推送，避免刷屏
- CLI 参数启动，支持 systemd 开机自启
- Docker 一键部署

## 快速开始

### 1. 配置

```bash
cp config.example.json config.json
# 编辑 config.json
```

```json
{
  "poll_interval_seconds": 900,
  "proxy": "http://127.0.0.1:7890",
  "webhooks": [
    {
      "name": "QQ机器人",
      "url": "http://your-server:10010/send",
      "platform": "qq",
      "umo": "BotName:FriendMessage:QQ号",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    },
    {
      "name": "飞书通知",
      "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
      "platform": "feishu",
      "secret": "签名密钥（可选）"
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `poll_interval_seconds` | ❌ | 轮询间隔，默认 900（15 分钟），最小 30 |
| `proxy` | ❌ | HTTP 代理地址，null 为直连 |
| `webhooks[].name` | ✅ | 标识名称（日志用） |
| `webhooks[].url` | ✅ | webhook 地址 |
| `webhooks[].platform` | ❌ | `"qq"`（默认）或 `"feishu"` |
| `webhooks[].umo` | ❌ | QQ 会话标识，飞书不需要 |
| `webhooks[].secret` | ❌ | 飞书签名密钥 |
| `webhooks[].headers` | ❌ | 自定义请求头 |

### 2. 运行

**本地：**

```bash
pip install -r requirements.txt
python main.py -c config.json -s data/state.json
```

**Docker：**

```bash
docker compose up -d
```

**Linux systemd：**

```bash
sudo cp vrchat-status-push.service /etc/systemd/system/
sudo systemctl enable --now vrchat-status-push

# 查看运行状态
systemctl status vrchat-status-push
journalctl -u vrchat-status-push -f
```

## 消息示例

**QQ 文本：**

```
【VRChat 状态】
整体状态变更: 所有系统正常 → 部分系统中断
更新时间：2026-07-19 19:00:00 (UTC+8)
```

**飞书卡片：**

卡片 header 颜色根据状态自动切换：正常→绿、轻微→黄、重大→橙、严重→红。body 以 markdown 展示详情，底部按钮可跳转 status.vrchat.com。

## 项目结构

```
vrchat_status_push/
├── main.py                     # 入口（-c -s --once CLI 参数）
├── config.example.json
├── vrchat-status-push.service  # systemd 服务文件
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── config.py               # 配置加载校验
│   ├── fetcher.py              # API 拉取 + 重试
│   ├── detector.py             # 变化检测
│   ├── formatter.py            # QQ 文本渲染
│   ├── feishu_card.py          # 飞书卡片构建
│   ├── dispatcher.py           # 并发推送（按平台分发）
│   └── state_store.py          # 状态持久化
└── tests/
```

## CLI 参数

```
python main.py -h
  -c, --config  配置文件路径 (默认: config.json)
  -s, --state   状态文件路径 (默认: data/state.json)
  --once        手动测试推送：绕过变化检测，直接发送测试消息
  --status      查看当前状态摘要
```

```bash
# 查看状态
python main.py --status

# 手动测试推送
python main.py --once
```

## 测试

```bash
pip install pytest pytest-asyncio pytest-aioresponses
python -m pytest tests/ -v
```
