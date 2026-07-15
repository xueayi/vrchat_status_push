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
