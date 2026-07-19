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
        assert w.platform == "qq"  # 默认平台
        assert w.message_type == "text"
        assert w.callback_url is None
        assert w.secret is None
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


def test_feishu_platform():
    """飞书平台配置（umo 不需要）"""
    data = {
        "webhooks": [
            {
                "name": "feishu_bot",
                "url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
                "platform": "feishu",
                "secret": "my_secret",
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        cfg = load_config(path)
        w = cfg.webhooks[0]
        assert w.platform == "feishu"
        assert w.secret == "my_secret"
        assert w.umo == ""
    finally:
        Path(path).unlink()


def test_unsupported_platform():
    """不支持的 platform 报错"""
    data = {"webhooks": [{"name": "x", "url": "http://x.com", "platform": "wechat"}]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        with pytest.raises(ValueError, match="不支持的平台"):
            load_config(path)
    finally:
        Path(path).unlink()
