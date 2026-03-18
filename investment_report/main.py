"""
投資報告自動化系統 - 主程式 (Team Lead)
Investment Report Automation System - Team Lead

架構圖（Claude Code Agent Teams 模式）：
┌──────────────────────────────────────────────────────────┐
│                   Team Lead (main.py)                     │
│                                                           │
│  建立共享任務清單 & Mailbox (AgentSharedState)             │
│                                                           │
│  同時啟動 4 位 Teammates（asyncio.gather 並行）：          │
│                                                           │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │  市場資料        │  │  新聞搜尋        │  ← 並行執行    │
│  │  Teammate       │  │  Teammate       │               │
│  └────────┬────────┘  └────────┬────────┘               │
│           │ 完成→Mailbox        │ 完成→Mailbox            │
│           └──────────┬─────────┘                         │
│                      ▼                                    │
│           ┌─────────────────────┐                        │
│           │  分析 Teammate       │  ← 等待兩者，讀 Mailbox │
│           │  (Extended Thinking) │                        │
│           └──────────┬──────────┘                        │
│                      ▼                                    │
│           ┌─────────────────────┐                        │
│           │  報告 Teammate       │  ← 等待分析，讀 Mailbox │
│           └─────────────────────┘                        │
└──────────────────────────────────────────────────────────┘

Agent Teams 核心概念：
  - Shared task list：Team Lead 建立任務，Teammates 自行認領
  - Mailbox：Teammates 之間直接傳遞訊息（非透過 Team Lead）
  - 並行執行：market_data 與 news 同時開始，無需等待彼此
  - 依賴由 Teammate 自行管理（wait_for 等待前置任務）
"""

import anyio
import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import ANTHROPIC_API_KEY
from team.shared_state import AgentSharedState
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


# ── Teammates 定義 ─────────────────────────────────────────────

async def market_data_teammate(state: AgentSharedState) -> None:
    """
    市場資料 Teammate
    認領 market_data 任務，完成後透過 Mailbox 通知分析代理
    """
    task = await state.claim_task("market_data_agent", "market_data")
    if not task:
        return

    print("  [行情代理] 認領任務：抓取股價資料...")
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, get_market_data)
        await state.complete_task("market_data", data)

        tw = len(data.get("taiwan_market", []))
        us = len(data.get("us_market", []))
        await state.send_message(
            "market_data_agent", "analysis_agent",
            f"市場資料就緒 ✅  台股 {tw} 檔 / 美股 {us} 檔"
        )
        print(f"  [行情代理] ✅ 完成，台股 {tw} 檔，美股 {us} 檔")
    except Exception as e:
        await state.fail_task("market_data", str(e))
        print(f"  [行情代理] ❌ 失敗：{e}")


async def news_teammate(state: AgentSharedState) -> None:
    """
    新聞搜尋 Teammate
    認領 news 任務，完成後透過 Mailbox 通知分析代理
    """
    task = await state.claim_task("news_agent", "news")
    if not task:
        return

    print("  [新聞代理] 認領任務：搜尋財經新聞...")
    try:
        data = await collect_news()
        await state.complete_task("news", data)

        count = len(data.get("news_items", []))
        themes = "、".join(data.get("key_themes", [])[:3])
        await state.send_message(
            "news_agent", "analysis_agent",
            f"新聞資料就緒 ✅  {count} 則新聞，主題：{themes}"
        )
        print(f"  [新聞代理] ✅ 完成，{count} 則新聞")
    except Exception as e:
        await state.fail_task("news", str(e))
        print(f"  [新聞代理] ❌ 失敗：{e}")


async def analysis_teammate(state: AgentSharedState) -> None:
    """
    分析 Teammate
    等待市場資料與新聞就緒，先讀取 Mailbox，再進行深度分析
    """
    task = await state.claim_task("analysis_agent", "analysis")
    if not task:
        return

    print("  [分析代理] 認領任務：等待市場資料與新聞...")

    # 等待兩個前置任務完成（market_data 和 news 並行執行中）
    market_data, news_data = await asyncio.gather(
        state.wait_for("market_data"),
        state.wait_for("news"),
    )

    # 查看 Mailbox：其他代理的最新通知
    messages = await state.check_messages("analysis_agent")
    if messages:
        print(f"  [分析代理] 收到 {len(messages)} 則訊息：")
        for msg in messages:
            print(f"    ← [{msg['from']}] {msg['message']}")

    print("  [分析代理] 開始 AI 深度分析（Extended Thinking）...")
    try:
        result = await generate_analysis(news_data, market_data)
        await state.complete_task("analysis", result)

        sentiment = result.get("market_overview", {}).get("overall_sentiment", "N/A")
        await state.send_message(
            "analysis_agent", "report_agent",
            f"分析完成 ✅  市場情緒評分：{sentiment}"
        )
        print("  [分析代理] ✅ 分析完成")
    except Exception as e:
        await state.fail_task("analysis", str(e))
        print(f"  [分析代理] ❌ 失敗：{e}")


async def report_teammate(state: AgentSharedState, today_str: str) -> None:
    """
    報告 Teammate
    等待分析完成，讀取 Mailbox，生成最終投資報告
    """
    task = await state.claim_task("report_agent", "report")
    if not task:
        return

    print("  [報告代理] 認領任務：等待分析結果...")

    analysis_data = await state.wait_for("analysis")
    market_data = await state.get_result("market_data")
    news_data = await state.get_result("news")

    # 查看 Mailbox
    messages = await state.check_messages("report_agent")
    if messages:
        for msg in messages:
            print(f"  [報告代理] ← [{msg['from']}] {msg['message']}")

    print("  [報告代理] 開始撰寫投資報告...")
    try:
        content = await generate_report(news_data, market_data, analysis_data, today_str)
        await state.complete_task("report", content)
        print("  [報告代理] ✅ 報告撰寫完成")
    except Exception as e:
        await state.fail_task("report", str(e))
        print(f"  [報告代理] ❌ 失敗：{e}")


# ── Team Lead ──────────────────────────────────────────────────

async def run_team() -> str:
    """
    Team Lead：
    1. 建立共享任務清單
    2. 並行啟動所有 Teammates
    3. 等待全部完成，儲存報告
    4. 輸出 Team 執行摘要
    """
    start_time = datetime.now()
    today = start_time.strftime("%Y%m%d")
    today_str = start_time.strftime("%Y年%m月%d日")

    print(f"\n{'='*60}")
    print(f"  投資報告自動化系統  ── Agent Team 模式")
    print(f"  日期：{today_str}")
    print(f"  開始時間：{start_time.strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── 初始化共享狀態（Task List + Mailbox）──────────────────
    state = AgentSharedState()

    # ── Team Lead：建立任務清單 ───────────────────────────────
    print("📋 Team Lead：建立任務清單...")
    await state.add_task("market_data")
    await state.add_task("news")
    await state.add_task("analysis")
    await state.add_task("report")

    print("🚀 啟動所有 Teammates（並行執行）...\n")

    # ── 並行啟動全部 Teammates ─────────────────────────────────
    # market_data 與 news 完全並行
    # analysis 自行等待兩者，report 自行等待 analysis
    # 依賴關係由 Teammate 透過 wait_for() 自行管理
    await asyncio.gather(
        market_data_teammate(state),
        news_teammate(state),
        analysis_teammate(state),
        report_teammate(state, today_str),
    )

    # ── 儲存報告 ──────────────────────────────────────────────
    report_content = await state.get_result("report") or ""
    if not report_content:
        print("❌ 報告生成失敗")
        return ""

    report_path = save_report(report_content, today)

    # ── 儲存 debug 原始資料 ────────────────────────────────────
    debug_dir = Path(report_path).parent / "debug"
    debug_dir.mkdir(exist_ok=True)
    with open(debug_dir / f"raw_data_{today}.json", "w", encoding="utf-8") as f:
        json.dump({
            "news": await state.get_result("news"),
            "market": await state.get_result("market_data"),
            "analysis": await state.get_result("analysis"),
        }, f, ensure_ascii=False, indent=2, default=str)

    # ── Team 執行摘要 ─────────────────────────────────────────
    elapsed = (datetime.now() - start_time).total_seconds()
    team_status = state.get_team_status()

    print(f"\n{'='*60}")
    print(f"  ✅ 報告生成完成！")
    print(f"  📁 路徑：{report_path}")
    print(f"  ⏱️  總耗時：{elapsed:.1f} 秒")
    print(f"\n  📊 Teammate 執行摘要：")
    for name, info in team_status.items():
        icon = "✅" if info["status"] == "completed" else "❌"
        elapsed_str = f" ({info['elapsed_s']}s)" if info["elapsed_s"] else ""
        print(f"    {icon} {name:<20} {info['status']}{elapsed_str}")
    print(f"{'='*60}\n")

    return report_path


def main():
    """同步入口點"""
    check_environment()
    report_path = anyio.run(run_team)
    return report_path


if __name__ == "__main__":
    main()
