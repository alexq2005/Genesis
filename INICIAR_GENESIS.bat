@echo off
chcp 65001 >nul 2>&1
title GENESIS — IA Auto-Evolutiva
cd /d "%~dp0"
python genesis.py
pause
