"""
投資報告自動化系統 - 設定檔
Investment Report Automation System - Configuration
"""

import os

# ============================================================
# API 金鑰設定 (從環境變數讀取，勿寫死在程式碼中)
# ============================================================
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ============================================================
# 追蹤標的設定
# ============================================================
TAIWAN_STOCKS = [
    # 台股指數 / ETF
    "^TWII",      # 台灣加權指數
    "0050.TW",    # 元大台灣50
    "0056.TW",    # 元大高股息
    "00878.TW",   # 國泰永續高股息
    "00881.TW",   # 國泰台灣5G+

    # 台股個股 (依需求修改)
    "2330.TW",    # 台積電
    "2317.TW",    # 鴻海
    "2454.TW",    # 聯發科
    "2382.TW",    # 廣達
    "2308.TW",    # 台達電
]

US_STOCKS = [
    # 美股指數 / ETF
    "^GSPC",      # S&P 500
    "^IXIC",      # Nasdaq
    "^DJI",       # Dow Jones
    "SPY",        # SPDR S&P 500 ETF
    "QQQ",        # Invesco QQQ ETF
    "VTI",        # Vanguard Total Market ETF

    # 美股個股 (依需求修改)
    "NVDA",       # Nvidia
    "AAPL",       # Apple
    "MSFT",       # Microsoft
    "GOOGL",      # Alphabet
    "AMZN",       # Amazon
    "META",       # Meta
    "TSLA",       # Tesla
]

# ============================================================
# 報告設定
# ============================================================
REPORT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
REPORT_LANGUAGE = "zh-TW"  # 繁體中文

# 報告生成時間 (24小時制)
REPORT_SCHEDULE_HOUR = 21    # 晚上9點
REPORT_SCHEDULE_MINUTE = 0

# ============================================================
# 模型設定
# ============================================================
# Orchestrator / 報告生成使用最強模型
CLAUDE_MODEL_MAIN = "claude-opus-4-6"
# 資料收集子代理使用較快模型
CLAUDE_MODEL_FAST = "claude-sonnet-4-6"

# ============================================================
# 新聞搜尋關鍵字
# ============================================================
SEARCH_TOPICS = [
    # 台灣市場
    "台股 今日 盤勢 分析",
    "台積電 法說會 展望",
    "台灣 半導體 AI 供應鏈",
    "台灣央行 利率 政策",

    # 美國市場
    "US stock market today analysis",
    "Federal Reserve interest rate policy",
    "NVIDIA AI earnings outlook",
    "S&P 500 market outlook",

    # 總經 / 地緣政治
    "全球經濟 衰退 風險",
    "美中貿易 半導體 出口管制",
    "oil price commodity market",
    "USD TWD exchange rate",
]
