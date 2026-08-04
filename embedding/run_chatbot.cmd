@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
set HF_HUB_OFFLINE=1
set PYTHONIOENCODING=utf-8
"embedding\.venv-gpu\Scripts\python.exe" -m embedding.terminal_chatbot --mode hybrid %*
endlocal
