"""MCP Server - 暴露游戏自动游玩工具"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from .core import GameController
from .config_manager import apply_api_keys, load_config as load_user_config, setup_file_logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 全局状态 ──
mcp = FastMCP("gai-mcp", instructions="AI 自动游玩游戏的 MCP 工具")
_ctrl = GameController()


# ── MCP Tools ──


@mcp.tool()
async def list_windows() -> list[dict]:
    """列出所有可见窗口，用于查找游戏窗口标题

    Returns:
        窗口列表，每个包含 hwnd 和 title
    """
    return _ctrl.list_windows()


@mcp.tool()
async def start_game(
    window_title: str,
    ai_provider: str = "local",
    ai_model: str | None = None,
    strategy_prompt: str = "",
    capture_interval: float = 2.0,
    action_delay: float = 0.5,
    use_virtual_desktop: bool = True,
) -> dict:
    """开始自动游玩游戏

    Args:
        window_title: 游戏窗口标题 (模糊匹配)
        ai_provider: AI 提供者 (claude/openai/local)
        ai_model: AI 模型名称 (可选，使用默认值)
        strategy_prompt: 游戏策略提示词，告诉 AI 怎么玩这个游戏
        capture_interval: 截图间隔秒数
        action_delay: 操作间延迟秒数
        use_virtual_desktop: 是否使用虚拟桌面隔离

    Returns:
        会话信息
    """
    return await _ctrl.start_game(
        window_title=window_title,
        ai_provider=ai_provider,
        ai_model=ai_model,
        strategy_prompt=strategy_prompt,
        capture_interval=capture_interval,
        action_delay=action_delay,
        use_virtual_desktop=use_virtual_desktop,
    )


@mcp.tool()
async def stop_game() -> dict:
    """停止自动游玩"""
    return await _ctrl.stop_game()


@mcp.tool()
async def pause_game() -> dict:
    """暂停自动游玩"""
    return _ctrl.pause_game()


@mcp.tool()
async def resume_game() -> dict:
    """恢复自动游玩"""
    return _ctrl.resume_game()


@mcp.tool()
async def get_status() -> dict:
    """获取当前游戏会话状态"""
    return _ctrl.get_status()


@mcp.tool()
async def set_strategy(prompt: str) -> dict:
    """更新游戏策略提示词

    Args:
        prompt: 新的策略提示词，告诉 AI 应该怎么玩
    """
    return _ctrl.set_strategy(prompt)


@mcp.tool()
async def screenshot() -> dict:
    """手动截取游戏窗口截图并返回分析

    Returns:
        截图的 base64 数据和窗口信息
    """
    return _ctrl.take_screenshot()


@mcp.tool()
async def execute_action(
    action_type: str,
    x: float | None = None,
    y: float | None = None,
    x2: float | None = None,
    y2: float | None = None,
    key: str | None = None,
    keys: list[str] | None = None,
    text: str | None = None,
    scroll_amount: int | None = None,
    duration: float | None = None,
) -> dict:
    """手动执行一个游戏操作

    Args:
        action_type: 操作类型 (click/right_click/double_click/key_press/key_combo/type_text/drag/scroll/wait)
        x: 鼠标 X 坐标 (0.0-1.0 归一化)
        y: 鼠标 Y 坐标 (0.0-1.0 归一化)
        x2: 拖拽终点 X
        y2: 拖拽终点 Y
        key: 按键名称
        keys: 组合键列表
        text: 输入文字
        scroll_amount: 滚轮量 (正上负下)
        duration: 持续时间/等待秒数
    """
    return await _ctrl.execute_action(
        action_type=action_type,
        x=x, y=y, x2=x2, y2=y2,
        key=key, keys=keys, text=text,
        scroll_amount=scroll_amount, duration=duration,
    )


def main() -> None:
    """启动 MCP Server"""
    setup_file_logging()
    user_cfg = load_user_config()
    apply_api_keys(user_cfg)
    _ctrl.load_config()
    logger.info("MCP Server 启动，已加载用户配置")
    mcp.run()


if __name__ == "__main__":
    main()
