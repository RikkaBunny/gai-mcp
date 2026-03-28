"""PyInstaller 入口 - Web 控制台"""
import sys
import os

if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from gai_mcp.web.run import main
main()
