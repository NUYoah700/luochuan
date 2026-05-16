@echo off
chcp 65001 >nul
cd /d "%~dp0"
python scraper.py >> "data\scraper.log" 2>&1
