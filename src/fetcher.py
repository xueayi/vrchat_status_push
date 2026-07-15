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
