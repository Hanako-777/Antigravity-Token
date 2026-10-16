@echo off
chcp 65001 >nul
title Antigravity Token 看板启动器
echo 正在启动 Antigravity Token 看板与后台托盘...
start "" "C:\Users\pc\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe" "%~dp0antigravity_tray.py" --open
echo 已成功拉起！本窗口将在 1 秒后自动关闭。
timeout /t 1 /nobreak >nul
