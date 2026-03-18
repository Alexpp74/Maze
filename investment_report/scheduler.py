"""
定時排程器 - 每天晚上自動生成投資報告
Scheduler - Automatically generates investment report every evening

使用方法：
  python scheduler.py                  # 啟動排程器（每日固定時間執行）
  python scheduler.py --now            # 立即執行一次
  python scheduler.py --test           # 測試執行（不儲存完整報告）

排程設定：
  修改 config/settings.py 中的 REPORT_SCHEDULE_HOUR / REPORT_SCHEDULE_MINUTE
"""

import argparse
import sys
import os
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent / "reports" / "scheduler.log",
            encoding="utf-8"
        ),
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
from config.settings import REPORT_SCHEDULE_HOUR, REPORT_SCHEDULE_MINUTE


def is_trading_day() -> bool:
    """判斷今天是否為交易日（週一到週五）"""
    return datetime.now().weekday() < 5


def run_report():
    """執行報告生成"""
    try:
        logger.info("開始生成今日投資報告...")
        from main import main
        report_path = main()
        logger.info(f"報告生成成功：{report_path}")

        # 可選：發送通知（Email、Line Notify、Telegram 等）
        send_notification(report_path)

    except Exception as e:
        logger.error(f"報告生成失敗：{e}", exc_info=True)


def send_notification(report_path: str):
    """
    發送報告完成通知
    可自行擴充：Line Notify、Telegram Bot、Email 等

    Line Notify 範例：
    import requests
    token = os.environ.get("LINE_NOTIFY_TOKEN")
    if token:
        with open(report_path) as f:
            summary = f.read()[:1000]  # 只傳前1000字
        requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {token}"},
            data={"message": f"\n今日投資報告已生成\n{summary}..."}
        )
    """
    logger.info(f"報告已生成，路徑：{report_path}")
    # TODO: 在此加入你的通知邏輯


def start_scheduler():
    """啟動排程器"""
    target_hour = REPORT_SCHEDULE_HOUR
    target_minute = REPORT_SCHEDULE_MINUTE

    logger.info(f"投資報告排程器啟動")
    logger.info(f"執行時間：每日 {target_hour:02d}:{target_minute:02d}")
    logger.info(f"按 Ctrl+C 停止")

    # 優雅關閉
    def signal_handler(sig, frame):
        logger.info("接收到停止信號，排程器關閉")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    last_run_date = None

    while True:
        now = datetime.now()
        current_date = now.date()

        # 檢查是否達到執行時間
        should_run = (
            now.hour == target_hour and
            now.minute == target_minute and
            last_run_date != current_date and
            is_trading_day()
        )

        if should_run:
            last_run_date = current_date
            logger.info(f"觸發報告生成（{now.strftime('%Y-%m-%d %H:%M')}）")
            run_report()

        # 每分鐘檢查一次
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="投資報告自動化排程器")
    parser.add_argument("--now", action="store_true", help="立即執行一次")
    parser.add_argument("--test", action="store_true", help="測試模式")
    args = parser.parse_args()

    # 確保報告目錄存在
    Path(__file__).parent.joinpath("reports").mkdir(exist_ok=True)

    if args.now or args.test:
        print("▶️  立即執行報告生成...")
        run_report()
    else:
        start_scheduler()


if __name__ == "__main__":
    main()
