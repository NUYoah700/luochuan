#!/usr/bin/env python3
"""
洛川 - 后台调度器
无需管理员权限，每天6:00自动运行抓取脚本
开机后放入后台，计算距离下次6:00的时间并等待
"""

import sys
import os
import time
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──
SCRIPT_DIR = Path(__file__).parent
SCRAPER_PATH = SCRIPT_DIR / "scraper.py"
LOG_PATH = SCRIPT_DIR / "data" / "scheduler.log"
PID_FILE = SCRIPT_DIR / "data" / "scheduler.pid"

# ── 日志 ──
SCRIPT_DIR.joinpath("data").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("luochuan-scheduler")

# ── 防止重复运行 ──
if PID_FILE.exists():
    try:
        old_pid = int(PID_FILE.read_text().strip())
        os.kill(old_pid, 0)  # 检查进程是否存在
        logger.info(f"调度器已在运行 (PID: {old_pid})，退出")
        sys.exit(0)
    except (OSError, ValueError):
        PID_FILE.unlink(missing_ok=True)

PID_FILE.write_text(str(os.getpid()))

def cleanup():
    PID_FILE.unlink(missing_ok=True)

import atexit
atexit.register(cleanup)


def seconds_until(target_hour=6, target_minute=0):
    """计算距离下一个目标时间的秒数"""
    now = datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_scraper():
    """执行抓取脚本"""
    logger.info("开始执行每日AI资讯抓取...")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRAPER_PATH)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(SCRIPT_DIR),
            timeout=300,
        )
        if result.returncode == 0:
            logger.info(f"抓取成功: {result.stdout[-200:] if result.stdout else 'ok'}")
        else:
            logger.error(f"抓取失败 (exit {result.returncode}): {result.stderr[:500]}")
    except Exception as e:
        logger.error(f"抓取异常: {e}")


def main():
    logger.info("═══════════════════════════════════════")
    logger.info("  洛川 AI 调度器启动")
    logger.info(f"  PID: {os.getpid()}")
    logger.info("  目标: 每日 06:00 自动抓取")
    logger.info("═══════════════════════════════════════")

    # 启动时先跑一次（如果今天还没数据）
    today_file = SCRIPT_DIR / "data" / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    if not today_file.exists():
        logger.info("今日数据尚未生成，立即执行首次抓取...")
        run_scraper()
    else:
        logger.info(f"今日数据已存在: {today_file}")

    # 主循环
    while True:
        wait_seconds = seconds_until(6, 0)
        next_run = datetime.now() + timedelta(seconds=wait_seconds)
        logger.info(f"下次运行: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (等待 {wait_seconds/3600:.1f} 小时)")

        # 长等待，但每10分钟检查一次以便优雅退出
        check_interval = 600  # 10分钟
        waited = 0
        while waited < wait_seconds:
            sleep_time = min(check_interval, wait_seconds - waited)
            time.sleep(sleep_time)
            waited += sleep_time

        logger.info("到达预定时间，开始抓取...")
        run_scraper()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("调度器收到中断信号，退出")
        cleanup()
    except Exception as e:
        logger.error(f"调度器异常退出: {e}")
        cleanup()
