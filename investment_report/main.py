"""
投資報告自動化系統 - 主程式 (Orchestrator)
Investment Report Automation System - Main Orchestrator

架構圖（Claude Team Agent）：
┌─────────────────────────────────────────────────┐
│              Orchestrator (main.py)              │
│                                                  │
│  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Market Data │  │     News Agent           │  │
│  │   Agent     │  │  (Claude + WebSearch)    │  │
│  │ (yfinance)  │  │                          │  │
│  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                     │                  │
│         └──────────┬──────────┘                  │
│                    ▼                              │
│         ┌─────────────────────┐                  │
│         │  Analysis Agent     │                  │
│         │  (Claude Opus +     │                  │
│         │  Adaptive Thinking) │                  │
│         └──────────┬──────────┘                  │
│                    ▼                              │
│         ┌─────────────────────┐                  │
│         │  Report Agent       │                  │
│         │  (Claude Opus)      │                  │
│         │  → Markdown Report  │                  │
│         └─────────────────────┘                  │
└─────────────────────────────────────────────────┘
"""

import anyio
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# 確保能找到 config 模組
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import ANTHROPIC_API_KEY
from agents.market_data_agent import get_market_data
from agents.news_agent import collect_news
from agents.analysis_agent import generate_analysis
from agents.report_agent import generate_report, save_report


def check_environment():
    """檢查環境設定"""
    if not ANTHROPIC_API_KEY:
        print("❌ 錯誤：請設定 ANTHROPIC_API_KEY 環境變數")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)

    required_packages = ["anthropic", "claude_agent_sdk", "yfinance", "pandas"]
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"❌ 缺少套件：{', '.join(missing)}")
        print(f"   請執行：pip install {' '.join(missing)}")
        sys.exit(1)

    print("✅ 環境檢查通過")


async def run_pipeline() -> str:
    """
    執行完整的投資報告生成流程
    Returns path to the generated report.
    """
    start_time = datetime.now()
    today = start_time.strftime("%Y%m%d")
    today_str = start_time.strftime("%Y年%m月%d日")

    print(f"\n{'='*60}")
    print(f"  投資報告自動化系統")
    print(f"  日期：{today_str}")
    print(f"  開始時間：{start_time.strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── Step 1：並行抓取市場資料和新聞 ──────────────────────
    print("📊 Step 1：收集市場資料與新聞（並行執行）...")

    async def fetch_news_async():
        print("  [新聞代理] 開始搜尋財經新聞...")
        news = await collect_news()
        print(f"  [新聞代理] ✅ 收集到 {len(news.get('news_items', []))} 則新聞")
        return news

    def fetch_market_sync():
        print("  [行情代理] 開始抓取股價資料...")
        data = get_market_data()
        tw_count = len(data.get("taiwan_market", []))
        us_count = len(data.get("us_market", []))
        print(f"  [行情代理] ✅ 台股 {tw_count} 檔，美股 {us_count} 檔")
        return data

    # 並行執行（新聞用 async，行情用 sync 在 executor）
    loop = asyncio.get_event_loop()
    news_task = asyncio.create_task(fetch_news_async())
    market_task = loop.run_in_executor(None, fetch_market_sync)

    news_data, market_data = await asyncio.gather(news_task, market_task)

    # ── Step 2：深度分析 ──────────────────────────────────
    print(f"\n🧠 Step 2：AI 深度分析（使用 Extended Thinking）...")
    analysis_data = await generate_analysis(news_data, market_data)
    print("  [分析代理] ✅ 分析完成")

    # ── Step 3：生成報告 ──────────────────────────────────
    print(f"\n📝 Step 3：生成專業投資報告...")
    report_content = await generate_report(news_data, market_data, analysis_data, today_str)
    print("  [報告代理] ✅ 報告生成完成")

    # ── Step 4：儲存報告 ──────────────────────────────────
    print(f"\n💾 Step 4：儲存報告...")
    report_path = save_report(report_content, today)

    # ── 完成 ──────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*60}")
    print(f"  ✅ 報告生成完成！")
    print(f"  📁 路徑：{report_path}")
    print(f"  ⏱️  耗時：{elapsed:.1f} 秒")
    print(f"{'='*60}\n")

    # 也儲存原始資料（供除錯用）
    debug_dir = Path(report_path).parent / "debug"
    debug_dir.mkdir(exist_ok=True)
    with open(debug_dir / f"raw_data_{today}.json", "w", encoding="utf-8") as f:
        json.dump({
            "news": news_data,
            "market": market_data,
            "analysis": analysis_data,
        }, f, ensure_ascii=False, indent=2, default=str)

    return report_path


def main():
    """同步入口點"""
    check_environment()
    report_path = anyio.run(run_pipeline)
    return report_path


if __name__ == "__main__":
    main()
