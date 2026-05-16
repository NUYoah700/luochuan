@echo off
chcp 65001 >nul
echo ══════════════════════════════════
echo   洛川 - 创建定时任务
echo   每天 06:00 自动抓取+发邮件
echo ══════════════════════════════════
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 请右键此文件 → "以管理员身份运行"
    echo 否则无法创建计划任务
    pause
    exit /b 1
)

:: 获取当前用户名
set CURRENT_USER=%USERNAME%

:: 删除旧任务
schtasks /delete /tn "LuochuanScraper" /f >nul 2>&1

:: 创建新任务：每天 06:00 运行，错过则开机后立即补跑
schtasks /create ^
  /tn "LuochuanScraper" ^
  /tr "python %~dp0scraper.py" ^
  /sc daily ^
  /st 06:00 ^
  /ru %CURRENT_USER% ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo [成功] 定时任务已创建！
    echo   任务名称: LuochuanScraper
    echo   运行时间: 每天 06:00
    echo   脚本路径: %~dp0scraper.py
    echo.
    echo 关机错过也会在下次开机时补跑
) else (
    echo [失败] 任务创建失败，请检查权限
)

pause
