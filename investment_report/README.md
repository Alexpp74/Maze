# 📊 投資報告自動化系統
### 使用 Claude Agent SDK (Multi-Agent 架構)

每日自動抓取台股/美股行情、財經新聞，透過 AI 深度分析，每晚生成專業投資報告。

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator (main.py)                 │
│                                                          │
│  ┌──────────────────┐    ┌───────────────────────────┐  │
│  │  Market Data     │    │     News Agent             │  │
│  │  Agent           │    │  (Claude + WebSearch       │  │
│  │  (yfinance)      │    │   + WebFetch)              │  │
│  │                  │    │                            │  │
│  │  台股/美股 行情   │    │  財經新聞自動搜尋           │  │
│  └────────┬─────────┘    └────────────┬───────────────┘  │
│           │                           │                   │
│           └─────────────┬─────────────┘                   │
│                         ▼                                 │
│              ┌──────────────────────┐                     │
│              │   Analysis Agent     │                     │
│              │  (Claude Opus 4.6    │                     │
│              │  + Adaptive Thinking)│                     │
│              │                      │                     │
│              │  深度投資分析         │                     │
│              └──────────┬───────────┘                     │
│                         ▼                                 │
│              ┌──────────────────────┐                     │
│              │   Report Agent       │                     │
│              │  (Claude Opus 4.6)   │                     │
│              │                      │                     │
│              │  → Markdown 投資日報  │                     │
│              └──────────────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速開始

### 1. 安裝依賴套件

```bash
cd investment_report
pip install -r requirements.txt
```

### 2. 設定 API 金鑰

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 3. 設定追蹤標的（可選）

編輯 `config/settings.py`：
- `TAIWAN_STOCKS`：台股追蹤清單
- `US_STOCKS`：美股追蹤清單
- `SEARCH_TOPICS`：新聞搜尋關鍵字

### 4. 執行

```bash
# 立即生成一份報告
python scheduler.py --now

# 啟動每日自動排程（預設晚上9點）
python scheduler.py

# 或使用系統 cron（更穩定）
# 在終端機輸入 crontab -e 加入：
# 0 21 * * 1-5 cd /path/to/investment_report && python main.py
```

---

## 📁 專案結構

```
investment_report/
├── main.py              # 主程式 / Orchestrator
├── scheduler.py         # 定時排程器
├── requirements.txt     # 套件依賴
├── README.md           # 說明文件
├── config/
│   └── settings.py      # 系統設定（追蹤標的、排程時間等）
├── agents/
│   ├── market_data_agent.py   # 市場資料代理（yfinance）
│   ├── news_agent.py          # 新聞代理（Claude + WebSearch）
│   ├── analysis_agent.py      # 分析代理（Claude Opus + Thinking）
│   └── report_agent.py        # 報告代理（Claude Opus）
└── reports/
    ├── investment_report_YYYYMMDD.md   # 每日投資報告
    └── debug/
        └── raw_data_YYYYMMDD.json      # 原始資料（除錯用）
```

---

## 📋 報告內容

每份報告包含：

| 章節 | 內容 |
|------|------|
| 執行摘要 | 30秒掌握今日重點（3-5條） |
| 市場概況 | 台股/美股整體分析、台美聯動 |
| 重點機會 | 具體個股、方向、目標價、停損 |
| 必看個股 | 值得關注的技術或基本面變化 |
| 產業趨勢 | 半導體、AI、科技等產業展望 |
| 總經觀察 | 聯準會、台灣央行、匯率、地緣政治 |
| 風險警示 | 重要下行風險 |
| 明日策略 | 具體操作建議、關鍵技術位 |
| ETF 分析 | 0050/0056/SPY/QQQ 分析 |

---

## ⚙️ 設定排程

### 方法一：內建排程器
```bash
python scheduler.py
# 預設每日 21:00 執行
# 修改 config/settings.py 中的 REPORT_SCHEDULE_HOUR
```

### 方法二：系統 Cron（推薦）
```bash
crontab -e
# 加入以下行（每日週一到週五 21:00 執行）：
0 21 * * 1-5 cd /path/to/investment_report && ANTHROPIC_API_KEY=xxx python main.py >> reports/cron.log 2>&1
```

### 方法三：macOS LaunchAgent
建立 `~/Library/LaunchAgents/com.investment.report.plist` 實現開機自動啟動。

---

## 🔔 加入通知功能

編輯 `scheduler.py` 的 `send_notification()` 函式：

### Line Notify
```python
import requests
token = os.environ.get("LINE_NOTIFY_TOKEN")
requests.post(
    "https://notify-api.line.me/api/notify",
    headers={"Authorization": f"Bearer {token}"},
    data={"message": f"\n今日投資報告已生成！"}
)
```

### Telegram Bot
```python
import telegram
bot = telegram.Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
bot.send_document(
    chat_id=os.environ["TELEGRAM_CHAT_ID"],
    document=open(report_path, 'rb')
)
```

---

## 💡 使用 Claude Agent SDK 的優勢

| 功能 | 說明 |
|------|------|
| **WebSearch 工具** | Claude 自動搜尋最新財經新聞，無需手動設定爬蟲 |
| **WebFetch 工具** | 自動抓取特定財經網頁內容 |
| **Adaptive Thinking** | 分析代理使用深度思考，提升分析品質 |
| **Multi-Agent** | 各代理專注單一任務，易於維護和擴充 |
| **並行執行** | 新聞收集與行情抓取同步進行，節省時間 |

---

## ⚠️ 免責聲明

本系統生成之報告**僅供參考**，不構成投資建議。
投資有風險，請依個人風險承受能力做出投資決策。
