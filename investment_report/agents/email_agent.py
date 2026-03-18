"""
Gmail 通知代理 - 將每日投資報告透過 Gmail 寄送給指定收件人
Email Notification Agent - Sends daily investment report via Gmail SMTP

設定方式（Gmail App Password）：
1. 登入 Google 帳號 → 安全性 → 2 步驟驗證（必須開啟）
2. 安全性 → 應用程式密碼 → 產生 16 碼 App Password
3. 設定環境變數：
   export GMAIL_SENDER="your@gmail.com"
   export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
   export GMAIL_RECIPIENTS="recipient1@gmail.com,recipient2@gmail.com"
"""

import smtplib
import ssl
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    GMAIL_SENDER,
    GMAIL_APP_PASSWORD,
    GMAIL_RECIPIENTS,
)

logger = logging.getLogger(__name__)

# Gmail SMTP 設定
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465  # SSL port


def _markdown_to_html(md_text: str) -> str:
    """
    簡易 Markdown → HTML 轉換（不依賴外部套件）
    支援：標題 # ## ###、粗體 **、清單 - *、表格 |、分隔線 ---
    """
    lines = md_text.split("\n")
    html_lines = []
    in_table = False
    in_list = False

    for line in lines:
        # 表格處理
        if line.strip().startswith("|"):
            if not in_table:
                html_lines.append('<table style="border-collapse:collapse;width:100%;margin:10px 0;">')
                in_table = True
            cells = [c.strip() for c in line.split("|")[1:-1]]
            # 判斷是否為分隔行（|---|---|）
            if all(set(c.replace("-", "").replace(":", "")) == set() for c in cells if c):
                continue
            is_header = html_lines and "<thead>" not in "\n".join(html_lines[-3:]) and "<tbody>" not in "\n".join(html_lines[-3:])
            tag = "th" if is_header else "td"
            style = 'style="border:1px solid #ddd;padding:8px;text-align:left;' + (
                'background:#2c5f2e;color:white;"' if is_header else 'background:#f9f9f9;"'
            )
            row = "".join(f'<{tag} {style}>{c}</{tag}>' for c in cells)
            html_lines.append(f'<tr>{row}</tr>')
            continue
        elif in_table:
            html_lines.append("</table>")
            in_table = False

        # 清單項目
        if line.strip().startswith(("- ", "* ", "• ")):
            if not in_list:
                html_lines.append('<ul style="margin:5px 0;padding-left:20px;">')
                in_list = True
            content = line.strip()[2:]
            content = _inline_format(content)
            html_lines.append(f'<li style="margin:3px 0;">{content}</li>')
            continue
        elif in_list and line.strip():
            html_lines.append("</ul>")
            in_list = False
        elif in_list and not line.strip():
            html_lines.append("</ul>")
            in_list = False

        # 標題
        if line.startswith("#### "):
            html_lines.append(f'<h4 style="color:#1a5276;margin:10px 0 5px;">{_inline_format(line[5:])}</h4>')
        elif line.startswith("### "):
            html_lines.append(f'<h3 style="color:#2c5f2e;margin:15px 0 8px;border-bottom:1px solid #eee;padding-bottom:4px;">{_inline_format(line[4:])}</h3>')
        elif line.startswith("## "):
            html_lines.append(f'<h2 style="color:#1a5276;margin:20px 0 10px;border-bottom:2px solid #2c5f2e;padding-bottom:6px;">{_inline_format(line[3:])}</h2>')
        elif line.startswith("# "):
            html_lines.append(f'<h1 style="color:#1a5276;margin:0 0 15px;font-size:24px;">{_inline_format(line[2:])}</h1>')
        # 分隔線
        elif line.strip() in ("---", "***", "___"):
            html_lines.append('<hr style="border:none;border-top:2px solid #eee;margin:15px 0;">')
        # 引用塊 > (執行摘要)
        elif line.startswith("> "):
            content = _inline_format(line[2:])
            html_lines.append(f'<blockquote style="border-left:4px solid #2c5f2e;margin:5px 0;padding:8px 15px;background:#f0f8f0;color:#333;">{content}</blockquote>')
        # 空行
        elif not line.strip():
            html_lines.append('<br>')
        # 一般段落
        else:
            content = _inline_format(line)
            if content:
                html_lines.append(f'<p style="margin:5px 0;line-height:1.6;">{content}</p>')

    if in_table:
        html_lines.append("</table>")
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline_format(text: str) -> str:
    """處理行內格式：**粗體**、`程式碼`、表情符號直接保留"""
    import re
    # **粗體**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # *斜體*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # `程式碼`
    text = re.sub(r'`(.+?)`', r'<code style="background:#f4f4f4;padding:2px 4px;border-radius:3px;font-family:monospace;">\1</code>', text)
    return text


def build_html_email(report_content: str, report_date: str, report_path: str = None) -> str:
    """將 Markdown 報告轉換為精美 HTML 郵件"""
    body_html = _markdown_to_html(report_content)

    # 擷取執行摘要（前500字）作為郵件預覽
    preview_text = report_content[:200].replace("\n", " ").replace("#", "").strip()

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>投資日報 {report_date}</title>
  <style>
    body {{ font-family: -apple-system, 'Microsoft JhengHei', Arial, sans-serif; margin:0; padding:0; background:#f5f5f5; color:#333; }}
    .container {{ max-width:800px; margin:20px auto; background:#fff; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1); overflow:hidden; }}
    .header {{ background:linear-gradient(135deg, #1a5276, #2c5f2e); color:#fff; padding:30px; text-align:center; }}
    .header h1 {{ margin:0; font-size:26px; letter-spacing:1px; }}
    .header .subtitle {{ margin:8px 0 0; opacity:0.85; font-size:14px; }}
    .badge {{ display:inline-block; background:rgba(255,255,255,0.2); border-radius:20px; padding:4px 12px; margin-top:10px; font-size:12px; }}
    .content {{ padding:30px; }}
    .footer {{ background:#f8f8f8; border-top:1px solid #eee; padding:15px 30px; font-size:11px; color:#888; text-align:center; }}
    .disclaimer {{ background:#fff8e1; border:1px solid #ffe082; border-radius:6px; padding:12px 15px; margin:20px 0 0; font-size:12px; color:#7d5200; }}
    .meta-bar {{ display:flex; justify-content:space-between; align-items:center; background:#f0f8f0; padding:10px 15px; border-radius:6px; margin-bottom:20px; font-size:13px; color:#2c5f2e; font-weight:bold; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📊 投資日報</h1>
      <div class="subtitle">Investment Daily Report</div>
      <div class="badge">🗓️ {report_date}</div>
    </div>
    <div class="content">
      <div class="meta-bar">
        <span>⏱️ 自動生成於 {datetime.now().strftime('%H:%M')}</span>
        <span>🤖 Powered by Claude AI Agent</span>
      </div>
      {body_html}
      <div class="disclaimer">
        ⚠️ <strong>免責聲明：</strong>本報告由 AI 自動生成，僅供參考，不構成任何投資建議。
        投資有風險，請依個人風險承受能力做出獨立判斷。
      </div>
    </div>
    <div class="footer">
      本郵件由投資報告自動化系統發送 &nbsp;|&nbsp; 請勿直接回覆
      {f'<br>報告檔案：{Path(report_path).name}' if report_path else ''}
    </div>
  </div>
</body>
</html>"""
    return html


def send_report_email(
    report_content: str,
    report_date: str,
    report_path: str = None,
    subject: str = None,
) -> bool:
    """
    透過 Gmail SMTP 寄送投資報告

    Args:
        report_content: Markdown 格式的報告內容
        report_date:    報告日期字串（顯示用）
        report_path:    報告檔案路徑（選填，作為附件）
        subject:        郵件主旨（選填）

    Returns:
        True 表示發送成功，False 表示失敗
    """
    # 讀取設定
    sender = GMAIL_SENDER
    app_password = GMAIL_APP_PASSWORD
    recipients_str = GMAIL_RECIPIENTS

    if not sender or not app_password:
        logger.warning("❌ 未設定 GMAIL_SENDER 或 GMAIL_APP_PASSWORD，跳過郵件發送")
        logger.warning("   請設定環境變數或在 config/settings.py 中填入帳號資訊")
        return False

    if not recipients_str:
        logger.warning("❌ 未設定 GMAIL_RECIPIENTS，跳過郵件發送")
        return False

    # 解析收件人清單
    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    if not recipients:
        logger.warning("❌ GMAIL_RECIPIENTS 格式錯誤")
        return False

    # 郵件主旨
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekdays[datetime.now().weekday()]
    if not subject:
        subject = f"📊 投資日報 {report_date}（星期{weekday}）— AI 自動分析"

    # 建立郵件
    msg = MIMEMultipart("alternative")
    msg["From"] = f"投資報告系統 <{sender}>"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # 純文字版本（給不支援 HTML 的郵件客戶端）
    plain_text = f"投資日報 {report_date}\n\n{report_content}"
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))

    # HTML 版本
    html_content = build_html_email(report_content, report_date, report_path)
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # 附上 Markdown 原始報告（選填）
    if report_path and Path(report_path).exists():
        with open(report_path, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        filename = Path(report_path).name
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=filename
        )
        msg.attach(attachment)
        logger.info(f"  [郵件] 已附上報告檔案：{filename}")

    # 發送（SSL 加密）
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, context=context) as server:
            server.login(sender, app_password)
            server.sendmail(sender, recipients, msg.as_string())

        logger.info(f"✅ 投資報告已寄送至：{', '.join(recipients)}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail 認證失敗！請確認：")
        logger.error("   1. GMAIL_SENDER 是正確的 Gmail 帳號")
        logger.error("   2. GMAIL_APP_PASSWORD 是 16 碼應用程式密碼（非 Gmail 登入密碼）")
        logger.error("   3. Gmail 帳號已開啟「2步驟驗證」")
        return False

    except smtplib.SMTPException as e:
        logger.error(f"❌ Gmail SMTP 錯誤：{e}")
        return False

    except Exception as e:
        logger.error(f"❌ 郵件發送失敗：{e}")
        return False


def test_email_connection() -> bool:
    """
    測試 Gmail 連線（不寄送實際報告，只驗證帳號密碼）
    執行方式：python agents/email_agent.py --test
    """
    sender = GMAIL_SENDER
    app_password = GMAIL_APP_PASSWORD

    if not sender or not app_password:
        print("❌ 請先設定 GMAIL_SENDER 和 GMAIL_APP_PASSWORD 環境變數")
        return False

    print(f"🔍 測試 Gmail 連線...")
    print(f"   寄件帳號：{sender}")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, context=context) as server:
            server.login(sender, app_password)
        print("✅ Gmail 連線測試成功！帳號密碼正確。")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ 認證失敗！請確認 App Password 是否正確（16碼，不含空格）")
        return False
    except Exception as e:
        print(f"❌ 連線失敗：{e}")
        return False


def send_test_email() -> bool:
    """發送一封測試郵件"""
    today_str = datetime.now().strftime("%Y年%m月%d日")
    test_report = f"""# 📊 投資日報測試 — {today_str}

> **這是一封測試郵件**，用來確認 Gmail 通知功能正常運作。

---

## 🌏 市場概況

### 台灣股市
- 台灣加權指數：**測試資料**
- 台積電 (2330)：正常運作中

### 美國股市
- S&P 500：測試正常
- Nasdaq：運作中

---

## ✅ 系統狀態

| 項目 | 狀態 |
|------|------|
| Market Data Agent | ✅ 正常 |
| News Agent | ✅ 正常 |
| Analysis Agent | ✅ 正常 |
| Email Notification | ✅ 正常 |

---

## ⚠️ 風險警示

- 本郵件為系統測試，非真實投資分析

---

*系統測試時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    return send_report_email(
        report_content=test_report,
        report_date=today_str,
        subject=f"[測試] 投資報告系統 - Gmail 通知功能驗證 {today_str}",
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gmail 郵件通知代理")
    parser.add_argument("--test-connection", action="store_true", help="測試 Gmail 連線")
    parser.add_argument("--send-test", action="store_true", help="發送測試郵件")
    parser.add_argument("--report", type=str, help="指定報告檔案路徑寄送")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.test_connection:
        test_email_connection()
    elif args.send_test:
        send_test_email()
    elif args.report:
        report_path = Path(args.report)
        if not report_path.exists():
            print(f"❌ 找不到報告檔案：{report_path}")
        else:
            content = report_path.read_text(encoding="utf-8")
            today_str = datetime.now().strftime("%Y年%m月%d日")
            result = send_report_email(content, today_str, str(report_path))
            print("✅ 發送成功" if result else "❌ 發送失敗")
    else:
        parser.print_help()
