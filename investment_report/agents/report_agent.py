"""
報告生成代理 - 將分析結果轉為專業投資報告
Report Generation Agent - Converts analysis into professional investment report
"""

import anyio
import json
import os
from datetime import datetime
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from config.settings import CLAUDE_MODEL_MAIN, REPORT_OUTPUT_DIR


REPORT_SYSTEM_PROMPT = """你是一位專業的投資報告撰寫師，負責將分析師的研究成果
整理成清晰、專業、易讀的投資日報。

撰寫風格：
- 使用繁體中文
- 專業但易於理解（避免過度術語）
- 結構清晰，重點突出
- 加入表格、清單等視覺化元素（Markdown 格式）
- 每份報告不超過 3000 字（確保可讀性）

報告必須包含：
1. 執行摘要（最重要，讓投資人30秒了解今日重點）
2. 市場概況
3. 重點機會
4. 風險警示
5. 明日策略"""


async def generate_report(
    news_data: dict,
    market_data: dict,
    analysis_data: dict,
    report_date: str = None
) -> str:
    """
    生成最終 Markdown 格式投資報告
    """
    if not report_date:
        report_date = datetime.now().strftime("%Y年%m月%d日")

    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekdays[datetime.now().weekday()]

    report_prompt = f"""請根據以下分析資料，撰寫 {report_date}（星期{weekday}）的專業投資日報。

=== 分析資料 ===
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

=== 市場行情摘要 ===
台股追蹤標的數：{len(market_data.get('taiwan_market', []))}
美股追蹤標的數：{len(market_data.get('us_market', []))}
台股市場情緒：{market_data.get('taiwan_summary', {}).get('market_sentiment', 'N/A')}
美股市場情緒：{market_data.get('us_summary', {}).get('market_sentiment', 'N/A')}

=== 新聞主題 ===
{json.dumps(news_data.get('key_themes', []), ensure_ascii=False)}
整體市場氛圍：{news_data.get('market_mood', 'N/A')}

請以 Markdown 格式撰寫報告，結構如下：

# 📊 投資日報 — {report_date}（星期{weekday}）

> **執行摘要**（30秒重點）
> [3-5點最重要的投資重點]

---

## 🌏 市場概況

### 台灣股市
[台股分析]

### 美國股市
[美股分析]

### 台美聯動
[跨市場分析]

---

## 🎯 今日重點機會

[以表格呈現重點機會]
| 股票 | 方向 | 理由 | 目標價 | 停損 | 信心度 |
|------|------|------|--------|------|--------|

### 詳細分析
[各標的詳細說明]

---

## 📌 必看個股

[以簡潔方式列出值得關注的標的]

---

## 🏭 產業趨勢

[各產業展望]

---

## 🌐 總經觀察

[聯準會、央行、匯率、地緣政治]

---

## ⚠️ 風險警示

[重要風險因素，用紅色警示感]

---

## 📅 明日操作策略

### 盤前重點
[盤前需要關注的事項]

### 關鍵技術位
[重要支撐/壓力]

### 重要行事曆
[明日重要事件/數據發布]

### 部位建議
[整體倉位建議：積極/中性/保守]

---

## 📊 ETF 配置參考

[台股ETF與美股ETF分析]

---

*⚠️ 免責聲明：本報告僅供參考，不構成投資建議。投資有風險，請依個人風險承受能力做決策。*

*📅 報告生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*"""

    result_text = ""

    async for message in query(
        prompt=report_prompt,
        options=ClaudeAgentOptions(
            model=CLAUDE_MODEL_MAIN,
            system_prompt=REPORT_SYSTEM_PROMPT,
            allowed_tools=[],
            max_turns=3,
        )
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result

    return result_text


def save_report(content: str, report_date: str = None) -> str:
    """
    儲存報告至檔案
    Returns the file path of saved report.
    """
    if not report_date:
        report_date = datetime.now().strftime("%Y%m%d")

    output_dir = Path(REPORT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 儲存 Markdown
    md_path = output_dir / f"investment_report_{report_date}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 報告已儲存：{md_path}")
    return str(md_path)


if __name__ == "__main__":
    async def main():
        test_analysis = {"analysis_date": "2024-01-01", "market_overview": {"taiwan_market_analysis": "測試"}}
        test_market = {"taiwan_market": [], "us_market": []}
        test_news = {"key_themes": ["測試主題"], "market_mood": "中性"}

        report = await generate_report(test_news, test_market, test_analysis)
        save_report(report)
        print(report[:500])

    anyio.run(main)
