import json
import tempfile
from pathlib import Path
from src.state_store import load, save
import pytest


@pytest.mark.asyncio
async def test_save_and_load():
    """保存后能正确加载"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.json"
        data = {"status": {"indicator": "none"}, "components": []}

        await save(str(path), data)
        result = await load(str(path))

        assert result == data


@pytest.mark.asyncio
async def test_load_nonexistent_file():
    """文件不存在时返回 None"""
    result = await load("/nonexistent/path/state.json")
    assert result is None


@pytest.mark.asyncio
async def test_load_corrupted_file():
    """损坏的文件返回 None"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.json"
        path.write_text("not valid json {{{")

        result = await load(str(path))
        assert result is None


@pytest.mark.asyncio
async def test_save_creates_parent_dir():
    """保存时自动创建父目录"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sub" / "nested" / "state.json"
        data = {"key": "value"}

        await save(str(path), data)
        result = await load(str(path))

        assert result == data
