"""
定時排程器 - 每天晚上自動生成投資報告並寄送 Gmail
Scheduler - Automatically generates investment report every evening and sends via Gmail

使用方法：
  python scheduler.py                  # 啟動排程器（每日固定時間執行）
  python scheduler.py --now            # 立即執行一次
  python scheduler.py --test-email     # 測試 Gmail 連線與寄信
  python scheduler.py --send <報告路徑> # 手動寄送指定報告

排程設定：
  修改 config/settings.py 中的 REPORT_SCHEDULE_HOUR / REPORT_SCHEDULE_MINUTE

Gmail 設定（必須先設定以下環境變數）：
  export GMAIL_SENDER="your@gmail.com"
  export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"   # 16碼 App Password
  export GMAIL_RECIPIENTS="you@gmail.com,partner@example.com"
"""

import argparse
import sys
import os
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# 確保報告目錄存在（放在 logging 之前）
Path(__file__).parent.joinpath("reports").mkdir(exist_ok=True)

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
from config.settings import REPORT_SCHEDULE_HOUR, REPORT_SCHEDULE_MINUTE, GMAIL_SEND_REPORT


def is_trading_day() -> bool:
    """判斷今天是否為交易日（週一到週五）"""
    return datetime.now().weekday() < 5


def run_report():
    """執行報告生成，完成後寄送 Gmail"""
    try:
        logger.info("開始生成今日投資報告...")
        from main import main
        report_path = main()
        logger.info(f"報告生成成功：{report_path}")

        # 寄送 Gmail 通知
        send_gmail_notification(report_path)

    except Exception as e:
        err = str(e)
        # 偵測 Anthropic 費用超限錯誤
        if any(k in err.lower() for k in ("credit", "billing", "quota", "402", "usage limit", "spend limit")):
            msg = (
                f"⛔ Anthropic API 月費已達上限，報告生成已停止。\n"
                f"   請前往 console.anthropic.com → Settings → Limits 查看用量。\n"
                f"   原始錯誤：{err}"
            )
            logger.error(msg)
            _send_error_notification(msg)
        else:
            logger.error(f"報告生成失敗：{e}", exc_info=True)
            _send_error_notification(err)


def send_gmail_notification(report_path: str):
    """讀取報告並寄送 Gmail"""
    if not GMAIL_SEND_REPORT:
        logger.info("Gmail 通知已停用（GMAIL_SEND_REPORT=false）")
        return

    try:
        from agents.email_agent import send_report_email

        report_file = Path(report_path)
        if not report_file.exists():
            logger.error(f"找不到報告檔案：{report_path}")
            return

        content = report_file.read_text(encoding="utf-8")
        today_str = datetime.now().strftime("%Y年%m月%d日")

        logger.info("準備寄送 Gmail 報告...")
        success = send_report_email(
            report_content=content,
            report_date=today_str,
            report_path=report_path,
        )

        if success:
            logger.info("✅ Gmail 報告寄送成功")
        else:
            logger.warning("⚠️ Gmail 報告寄送失敗（請檢查帳號設定）")

    except Exception as e:
        logger.error(f"Gmail 寄送過程發生錯誤：{e}", exc_info=True)


def _send_error_notification(error_msg: str):
    """報告生成失敗時，寄送錯誤通知郵件"""
    if not GMAIL_SEND_REPORT:
        return

    try:
        from agents.email_agent import send_report_email
        today_str = datetime.now().strftime("%Y年%m月%d日")
        error_report = f"""# ⚠️ 投資報告生成失敗 — {today_str}

今日投資報告在自動生成過程中發生錯誤，請手動檢查。

## 錯誤詳情

```
{error_msg}
```

## 處理建議

1. 確認 `ANTHROPIC_API_KEY` 環境變數已正確設定
2. 確認網路連線正常（yfinance 需要連接 Yahoo Finance）
3. 查看日誌檔案：`reports/scheduler.log`
4. 手動執行：`python scheduler.py --now`

---
*錯誤發生時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        send_report_email(
            report_content=error_report,
            report_date=today_str,
            subject=f"⚠️ [警告] 投資報告生成失敗 {today_str}",
        )
    except Exception:
        pass  # 避免通知本身也出錯


def start_scheduler():
    """啟動排程器"""
    target_hour = REPORT_SCHEDULE_HOUR
    target_minute = REPORT_SCHEDULE_MINUTE

    logger.info("投資報告排程器啟動")
    logger.info(f"執行時間：每日 {target_hour:02d}:{target_minute:02d}（週一至週五）")
    logger.info(f"Gmail 通知：{'✅ 啟用' if GMAIL_SEND_REPORT else '❌ 停用'}")
    logger.info("按 Ctrl+C 停止")

    def signal_handler(sig, frame):
        logger.info("接收到停止信號，排程器關閉")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    last_run_date = None

    while True:
        now = datetime.now()
        current_date = now.date()

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

        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(
        description="投資報告自動化排程器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python scheduler.py                   # 啟動每日排程
  python scheduler.py --now             # 立即生成報告並寄信
  python scheduler.py --test-email      # 測試 Gmail 連線
  python scheduler.py --send reports/investment_report_20260318.md
        """
    )
    parser.add_argument("--now", action="store_true",
                        help="立即執行一次（生成報告＋寄送 Gmail）")
    parser.add_argument("--test-email", action="store_true",
                        help="測試 Gmail 連線並寄送測試郵件")
    parser.add_argument("--send", type=str, metavar="REPORT_PATH",
                        help="手動寄送指定的報告檔案")
    args = parser.parse_args()

    if args.test_email:
        print("\n🧪 測試 Gmail 通知功能...")
        from agents.email_agent import test_email_connection, send_test_email
        if test_email_connection():
            print("\n📧 發送測試郵件...")
            send_test_email()
        return

    if args.send:
        report_path = Path(args.send)
        if not report_path.exists():
            print(f"❌ 找不到報告檔案：{report_path}")
            sys.exit(1)
        print(f"📧 手動寄送報告：{report_path.name}")
        send_gmail_notification(str(report_path))
        return

    if args.now:
        print("▶️  立即執行報告生成...")
        run_report()
        return

    start_scheduler()


if __name__ == "__main__":
    main()
