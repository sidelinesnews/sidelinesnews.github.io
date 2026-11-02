@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py aggregator.py) || (python aggregator.py)
start "" "docs\index.html"
pause
