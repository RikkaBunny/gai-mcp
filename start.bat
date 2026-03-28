@echo off
chcp 65001 >nul 2>&1
title GAI Play - AI Game Player
cd /d "%~dp0"
python -m gai_play.cli
pause
