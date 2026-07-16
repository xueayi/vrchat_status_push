"""VRChat Status Webhook Push — 主入口.

定时从 status.vrchat.com 获取服务状态，检测变化后推送到配置的 webhook。
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from src.config import load_config
from src.fetcher import fetch
from src.detector import detect
from src.formatter import format_changes
from src.dispatcher import dispatch
from src.state_store import load as load_state, save as save_state

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("config.json")
STATE_PATH = Path("data/state.json")


def setup_logging() -> None:
    """配置日志格式."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run() -> None:
    """主循环."""
    setup_logging()

    # 加载配置
    logger.info("加载配置: %s", CONFIG_PATH)
    config = load_config(str(CONFIG_PATH))
    logger.info(
        "配置加载完成 — poll_interval=%ds, proxy=%s, webhooks=%d",
        config.poll_interval_seconds,
        config.proxy or "无",
        len(config.webhooks),
    )

    # 加载上次状态
    old_state = await load_state(str(STATE_PATH))
    if old_state is None:
        logger.info("首次运行，本轮仅保存状态不推送")

    # 事件循环
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("收到退出信号，正在关闭...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            pass

    round_count = 0
    while not stop_event.is_set():
        round_count += 1
        try:
            # 拉取
            logger.info("[第 %d 轮] 拉取 VRChat 状态...", round_count)
            new_state = await fetch(config.proxy)

            if new_state is None:
                logger.warning("[第 %d 轮] 拉取失败，跳过本轮，等待下次轮询", round_count)
            else:
                # 检测变化
                changes = detect(old_state, new_state)

                if changes:
                    logger.info("[第 %d 轮] 检测到 %d 项变化", round_count, len(changes))
                    # 渲染消息
                    content = format_changes(changes)
                    logger.info("[第 %d 轮] 推送内容:\n%s", round_count, content)
                    # 推送
                    await dispatch(config.webhooks, content, config.proxy)
                else:
                    logger.info("[第 %d 轮] 状态无变化", round_count)

                # 保存状态
                await save_state(str(STATE_PATH), new_state)
                old_state = new_state

        except Exception:
            logger.exception("[第 %d 轮] 出现未预期错误", round_count)

        # 等待下一轮（支持优雅退出）
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=config.poll_interval_seconds)
            break  # stop_event 被触发
        except asyncio.TimeoutError:
            pass  # 正常超时，继续下一轮

    logger.info("已退出")


def main() -> None:
    """入口."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("启动失败: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
