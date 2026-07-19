"""并发推送消息到多个 webhook 目的地."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time

import aiohttp

from src.config import WebhookConfig
from src.detector import ChangeEvent
from src.formatter import format_changes
from src.feishu_card import build_feishu_card

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)


async def dispatch(
    webhooks: list[WebhookConfig],
    changes: list[ChangeEvent],
    status_indicator: str,
    proxy: str | None,
) -> None:
    """并发发送消息到所有 webhook。按平台构建不同请求体。"""
    if not webhooks:
        return

    qq_hooks = [w for w in webhooks if w.platform == "qq"]
    feishu_hooks = [w for w in webhooks if w.platform == "feishu"]

    tasks: list[asyncio.Task] = []
    for wh in qq_hooks:
        tasks.append(asyncio.ensure_future(_send_qq(wh, changes, proxy)))
    for wh in feishu_hooks:
        tasks.append(asyncio.ensure_future(_send_feishu(wh, changes, status_indicator, proxy)))

    if tasks:
        await asyncio.gather(*tasks)


async def _send_qq(wh: WebhookConfig, changes: list[ChangeEvent], proxy: str | None) -> None:
    """发送 QQ 文本消息."""
    content = format_changes(changes)
    payload = {
        "content": content,
        "umo": wh.umo,
        "message_type": wh.message_type,
        "callback_url": wh.callback_url,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    await _post(wh, payload, proxy)


async def _send_feishu(
    wh: WebhookConfig,
    changes: list[ChangeEvent],
    status_indicator: str,
    proxy: str | None,
) -> None:
    """发送飞书卡片消息."""
    payload = build_feishu_card(changes, status_indicator)

    # 签名校验
    if wh.secret:
        timestamp = str(int(time.time()))
        sign = _feishu_sign(timestamp, wh.secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign

    await _post(wh, payload, proxy)


def _feishu_sign(timestamp: str, secret: str) -> str:
    """飞书签名：HMAC-SHA256(timestamp + '\n' + secret)."""
    sign_str = f"{timestamp}\n{secret}"
    h = hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256)
    return h.hexdigest()


async def _post(wh: WebhookConfig, payload: dict, proxy: str | None) -> None:
    """通用 HTTP POST."""
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
