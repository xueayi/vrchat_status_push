import pytest
from aiohttp import ClientError
from aioresponses import aioresponses
from src.config import WebhookConfig
from src.dispatcher import dispatch


@pytest.mark.asyncio
async def test_dispatch_single_webhook():
    """单 webhook 发送成功"""
    wh = WebhookConfig(name="test", url="http://example.com/wh", umo="group_1")
    with aioresponses() as m:
        m.post("http://example.com/wh", payload={"status": "ok"})

        # 应该不抛异常
        await dispatch([wh], "测试消息", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_sends_correct_body():
    """验证发出的请求体格式"""
    wh = WebhookConfig(
        name="test",
        url="http://example.com/wh",
        umo="group_1",
        message_type="text",
        callback_url="http://example.com/cb",
        headers={"Authorization": "Bearer x"},
    )
    sent_body = {}

    with aioresponses() as m:
        def callback(url, **kwargs):
            nonlocal sent_body
            sent_body = kwargs.get("json", {})

        m.post("http://example.com/wh", callback=callback)

        await dispatch([wh], "测试消息", proxy=None)

    assert sent_body["content"] == "测试消息"
    assert sent_body["umo"] == "group_1"
    assert sent_body["message_type"] == "text"
    assert sent_body["callback_url"] == "http://example.com/cb"


@pytest.mark.asyncio
async def test_dispatch_one_fails_others_succeed():
    """一个 webhook 失败不影响其他"""
    wh1 = WebhookConfig(name="good", url="http://example.com/good", umo="g1")
    wh2 = WebhookConfig(name="bad", url="http://example.com/bad", umo="g2")
    wh3 = WebhookConfig(name="also_good", url="http://example.com/also", umo="g3")

    with aioresponses() as m:
        m.post("http://example.com/good", payload={"status": "ok"})
        m.post("http://example.com/bad", exception=ClientError("timeout"))
        m.post("http://example.com/also", payload={"status": "ok"})

        # 应该不抛异常
        await dispatch([wh1, wh2, wh3], "测试", proxy=None)


@pytest.mark.asyncio
async def test_dispatch_with_headers():
    """自定义请求头被传递"""
    wh = WebhookConfig(
        name="test",
        url="http://example.com/wh",
        umo="g1",
        headers={"X-Custom": "value"},
    )
    captured_headers = {}

    with aioresponses() as m:
        def callback(url, **kwargs):
            nonlocal captured_headers
            captured_headers = kwargs.get("headers", {})

        m.post("http://example.com/wh", callback=callback)

        await dispatch([wh], "test", proxy=None)

    assert captured_headers.get("X-Custom") == "value"
