"""Fetcher 模块测试."""
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
    """三次都失败时返回 None"""
    with aioresponses() as m:
        m.get(STATUS_API_URL, exception=ClientError("timeout"))
        m.get(STATUS_API_URL, exception=ClientError("timeout"))
        m.get(STATUS_API_URL, exception=ClientError("timeout"))

        result = await fetch(proxy=None)
        assert result is None
