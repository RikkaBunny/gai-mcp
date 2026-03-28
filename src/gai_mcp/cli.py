"""独立命令行工具 - 不依赖 MCP 协议，直接运行"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from .core import GameController
from .config_manager import apply_api_keys, load_config, setup_file_logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gai-play",
        description="AI 自动游玩游戏 - 独立命令行工具",
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")

    # ── list ──
    sub.add_parser("list", help="列出所有可见窗口")

    # ── play ──
    p_play = sub.add_parser("play", help="开始自动游玩")
    p_play.add_argument("window_title", help="游戏窗口标题 (模糊匹配)")
    p_play.add_argument("--provider", "-p", default=None, help="AI 提供者 (claude/openai/local)")
    p_play.add_argument("--model", "-m", default=None, help="AI 模型名称")
    p_play.add_argument("--strategy", "-s", default="", help="游戏策略提示词")
    p_play.add_argument("--interval", "-i", type=float, default=None, help="截图间隔 (秒)")
    p_play.add_argument("--delay", "-d", type=float, default=None, help="操作间延迟 (秒)")
    p_play.add_argument("--no-vd", action="store_true", help="不使用虚拟桌面")

    # ── play-game ──
    p_game = sub.add_parser("play-game", help="按游戏名启动 (使用已保存的游戏配置)")
    p_game.add_argument("game_name", help="游戏配置名称")

    # ── screenshot ──
    p_shot = sub.add_parser("screenshot", help="截取窗口截图并保存")
    p_shot.add_argument("window_title", help="窗口标题")
    p_shot.add_argument("--output", "-o", default="screenshot.jpg", help="输出文件路径")

    return parser.parse_args()


async def _cmd_list() -> None:
    """列出窗口"""
    ctrl = GameController()
    windows = ctrl.list_windows()
    if not windows:
        print("未找到可见窗口")
        return
    print(f"{'HWND':<12} 标题")
    print("-" * 60)
    for w in windows:
        print(f"{w['hwnd']:<12} {w['title']}")
    print(f"\n共 {len(windows)} 个窗口")


async def _cmd_play(args: argparse.Namespace) -> None:
    """直接指定窗口标题游玩"""
    ctrl = GameController()
    cfg = ctrl.load_config()
    ai_cfg = cfg.get("ai", {})
    loop_cfg = cfg.get("game_loop", {})

    provider = args.provider or ai_cfg.get("provider", "local")
    interval = args.interval or loop_cfg.get("capture_interval", 2.0)
    delay = args.delay or loop_cfg.get("action_delay", 0.5)

    print(f"正在查找窗口: {args.window_title}")
    result = await ctrl.start_game(
        window_title=args.window_title,
        ai_provider=provider,
        ai_model=args.model,
        strategy_prompt=args.strategy,
        capture_interval=interval,
        action_delay=delay,
        use_virtual_desktop=not args.no_vd,
    )

    if "error" in result:
        print(f"启动失败: {result['error']}")
        return

    print(f"游戏已启动 (hwnd={result['hwnd']}, provider={result['ai_provider']})")
    print("按 Ctrl+C 停止")

    await _wait_for_stop(ctrl)


async def _cmd_play_game(args: argparse.Namespace) -> None:
    """按游戏配置名启动"""
    ctrl = GameController()
    cfg = ctrl.load_config()

    games = cfg.get("games", {})
    game = games.get(args.game_name)
    if not game:
        print(f"未找到游戏配置: {args.game_name}")
        print(f"可用游戏: {', '.join(games.keys()) or '无'}")
        return

    ai_cfg = cfg.get("ai", {})
    provider = game.get("ai_provider", ai_cfg.get("provider", "local"))

    print(f"正在启动: {args.game_name}")
    result = await ctrl.start_game(
        window_title=game.get("window_title", ""),
        ai_provider=provider,
        ai_model=None,
        strategy_prompt=game.get("strategy", ""),
        capture_interval=game.get("capture_interval", 2.0),
        action_delay=cfg.get("game_loop", {}).get("action_delay", 0.5),
        use_virtual_desktop=False,
    )

    if "error" in result:
        print(f"启动失败: {result['error']}")
        return

    print(f"游戏已启动 (hwnd={result['hwnd']}, provider={result['ai_provider']})")
    print("按 Ctrl+C 停止")

    await _wait_for_stop(ctrl)


async def _cmd_screenshot(args: argparse.Namespace) -> None:
    """截图并保存"""
    from .capturer import WindowCapturer

    capturer = WindowCapturer()
    hwnd = capturer.find_window(args.window_title)
    if not hwnd:
        print(f"未找到窗口: {args.window_title}")
        return

    img = capturer.capture(hwnd)
    if img is None:
        print("截图失败")
        return

    img.save(args.output)
    print(f"截图已保存: {args.output} ({img.width}x{img.height})")


async def _wait_for_stop(ctrl: GameController) -> None:
    """等待用户中断"""
    stop_event = asyncio.Event()

    def _on_signal():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler，用 fallback
            break

    try:
        if sys.platform == "win32":
            # Windows: 用轮询检测 KeyboardInterrupt
            while ctrl.game_loop and ctrl.game_loop.is_running:
                await asyncio.sleep(1)
                status = ctrl.get_status()
                if status.get("status") == "error":
                    print(f"游戏出错: {status.get('last_error')}")
        else:
            await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        print("\n正在停止...")
        result = await ctrl.stop_game()
        decisions = result.get("total_decisions", 0)
        actions = result.get("total_actions", 0)
        print(f"已停止。共 {decisions} 次决策，{actions} 次操作。")


def main() -> None:
    """CLI 入口"""
    setup_file_logging()
    args = _parse_args()

    if not args.command:
        print("用法: gai-play <command> [options]")
        print("命令: list, play, play-game, screenshot")
        print("使用 gai-play <command> --help 查看详细帮助")
        return

    match args.command:
        case "list":
            asyncio.run(_cmd_list())
        case "play":
            asyncio.run(_cmd_play(args))
        case "play-game":
            asyncio.run(_cmd_play_game(args))
        case "screenshot":
            asyncio.run(_cmd_screenshot(args))


if __name__ == "__main__":
    main()
