"""PyInstaller 入口 - 独立命令行工具"""
import sys
import os

# Windows 控制台 UTF-8
if sys.platform == "win32":
    os.system("")  # 启用 ANSI
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 让打包后的 exe 能找到 skills 和 config.yaml
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from gai_play.cli import main
main()
