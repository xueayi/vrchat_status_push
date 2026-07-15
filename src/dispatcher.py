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
