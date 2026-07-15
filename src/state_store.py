"""状态文件读写."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def load(path: str) -> dict | None:
    """加载状态文件，返回解析后的 dict；文件不存在或损坏返回 None."""
    p = Path(path)
    if not p.exists():
        return None

    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("状态文件读取失败，视为首次运行: %s", e)
        return None


async def save(path: str, data: dict) -> None:
    """保存状态到文件，自动创建父目录."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
