"""Dispatcher 模块测试."""
import pytest
from aiohttp import ClientError
from aioresponses import aioresponses
from src.config import WebhookConfig
from src.detector import ChangeEvent
from src.dispatcher import dispatch

SAMPLE_CHANGE = ChangeEvent(type="status", title="整体状态变更", details="A → B")


@pytest.mark.asyncio
async def test_dispatch_single_qq_webhook():
    """单 QQ webhook 发送成功"""
    wh = WebhookConfig(name="test", url="http://example.com/wh", umo="group_1", platform="qq")
    with aioresponses() as m:
        m.post("http://example.com/wh", payload={"status": "ok"})
        await dispatch([wh], [SAMPLE_CHANGE], "minor", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_qq_sends_correct_body():
    """验证 QQ 发出的请求体格式"""
    wh = WebhookConfig(
        name="test", url="http://example.com/wh", umo="group_1",
        message_type="text", callback_url="http://example.com/cb",
        headers={"Authorization": "Bearer x"}, platform="qq",
    )
    sent_body = {}

    with aioresponses() as m:
        def callback(url, **kwargs):
            nonlocal sent_body
            sent_body = kwargs.get("json", {})

        m.post("http://example.com/wh", callback=callback)
        await dispatch([wh], [SAMPLE_CHANGE], "none", proxy=None)

    assert sent_body["umo"] == "group_1"
    assert sent_body["message_type"] == "text"
    assert sent_body["callback_url"] == "http://example.com/cb"


@pytest.mark.asyncio
async def test_dispatch_one_fails_others_succeed():
    """一个 webhook 失败不影响其他"""
    wh1 = WebhookConfig(name="good", url="http://example.com/good", umo="g1", platform="qq")
    wh2 = WebhookConfig(name="bad", url="http://example.com/bad", umo="g2", platform="qq")
    wh3 = WebhookConfig(name="also_good", url="http://example.com/also", umo="g3", platform="qq")

    with aioresponses() as m:
        m.post("http://example.com/good", payload={"status": "ok"})
        m.post("http://example.com/bad", exception=ClientError("timeout"))
        m.post("http://example.com/also", payload={"status": "ok"})
        await dispatch([wh1, wh2, wh3], [SAMPLE_CHANGE], "none", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_feishu_webhook():
    """飞书 webhook 发送成功"""
    wh = WebhookConfig(
        name="feishu", url="http://example.com/feishu",
        platform="feishu", secret="test_secret",
    )
    with aioresponses() as m:
        m.post("http://example.com/feishu", payload={"code": 0, "msg": "success"})
        await dispatch([wh], [SAMPLE_CHANGE], "major", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_feishu_without_secret():
    """飞书 webhook 无签名时发送"""
    wh = WebhookConfig(name="feishu", url="http://example.com/feishu2", platform="feishu")
    with aioresponses() as m:
        m.post("http://example.com/feishu2", payload={"code": 0, "msg": "success"})
        await dispatch([wh], [SAMPLE_CHANGE], "none", proxy=None)
