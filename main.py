"""VRChat Status Webhook Push — 主入口.

定时从 status.vrchat.com 获取服务状态，检测变化后推送到配置的 webhook。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from src.config import load_config
from src.detector import ChangeEvent
from src.fetcher import fetch
from src.detector import detect
from src.dispatcher import dispatch
from src.state_store import load as load_state, save as save_state

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VRChat Status Webhook Push")
    parser.add_argument(
        "-c", "--config", default="config.json", help="配置文件路径 (默认: config.json)"
    )
    parser.add_argument(
        "-s", "--state", default="data/state.json", help="状态文件路径 (默认: data/state.json)"
    )
    parser.add_argument(
        "--once", action="store_true", help="手动测试推送：绕过变化检测，直接发送一条测试消息"
    )
    parser.add_argument(
        "--status", action="store_true", help="查看当前状态摘要"
    )
    return parser


def setup_logging() -> None:
    """配置日志格式."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run(config_path: str, state_path: str, once: bool = False) -> None:
    """主循环."""
    setup_logging()

    # 加载配置
    logger.info("加载配置: %s", config_path)
    config = load_config(config_path)
    logger.info(
        "配置加载完成 — poll_interval=%ds, proxy=%s, webhooks=%d",
        config.poll_interval_seconds,
        config.proxy or "无",
        len(config.webhooks),
    )

    # 加载上次状态
    old_state = await load_state(state_path)
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
            elif once:
                # --once 模式：绕过变化检测，直接推送测试消息
                status = new_state.get("status", {})
                indicator = status.get("indicator", "none")
                desc = status.get("description", "N/A")
                enabled_hooks = [w for w in config.webhooks if w.enabled]
                hook_names = ", ".join(w.name for w in enabled_hooks)

                test_change = ChangeEvent(
                    type="status",
                    title="手动测试推送",
                    details=(
                        f"当前状态: {desc}\n"
                        f"推送渠道: {len(enabled_hooks)} 个 ({hook_names})"
                    ),
                )
                logger.info("--once 测试推送，跳过变化检测")
                await dispatch(config.webhooks, [test_change], indicator, config.proxy)
                # 保存状态
                await save_state(state_path, new_state)
                old_state = new_state
                logger.info("--once 完成，退出")
                break
            else:
                # 正常模式：检测变化
                changes = detect(old_state, new_state)

                if changes:
                    logger.info("[第 %d 轮] 检测到 %d 项变化", round_count, len(changes))
                    indicator = new_state.get("status", {}).get("indicator", "none")
                    await dispatch(config.webhooks, changes, indicator, config.proxy)
                else:
                    logger.info("[第 %d 轮] 状态无变化", round_count)

                # 保存状态
                await save_state(state_path, new_state)
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


async def show_status(config_path: str, state_path: str) -> None:
    """打印当前状态摘要."""
    config = load_config(config_path)
    old_state = await load_state(state_path)

    status = old_state.get("status", {}) if old_state else {}
    page = old_state.get("page", {}) if old_state else {}
    components = old_state.get("components", []) if old_state else []
    incidents = old_state.get("incidents", []) if old_state else []
    maintenances = old_state.get("scheduled_maintenances", []) if old_state else []

    enabled = [w.name for w in config.webhooks if w.enabled]
    disabled = [w.name for w in config.webhooks if not w.enabled]

    print(f"VRChat 状态: {status.get('indicator', '未知')} — {status.get('description', '未知')}")
    print(f"数据更新时间: {page.get('updated_at', '无')}")
    print(f"组件数: {len(components)}  活跃事件: {len(incidents)}  计划维护: {len(maintenances)}")
    print(f"轮询间隔: {config.poll_interval_seconds}s  代理: {config.proxy or '无'}")
    print(f"已启用的 webhook ({len(enabled)}): {', '.join(enabled) if enabled else '无'}")
    if disabled:
        print(f"已禁用的 webhook ({len(disabled)}): {', '.join(disabled)}")


def main() -> None:
    """入口."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.status:
            asyncio.run(show_status(args.config, args.state))
        else:
            asyncio.run(run(args.config, args.state, args.once))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("启动失败: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
