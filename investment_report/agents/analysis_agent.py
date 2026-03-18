"""
投資分析代理 - 整合新聞與行情，生成深度分析
Investment Analysis Agent - Integrates news and market data for deep analysis
"""

import anyio
import json
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from config.settings import CLAUDE_MODEL_MAIN


ANALYSIS_SYSTEM_PROMPT = """你是一位具有20年經驗的台灣與美國股市投資分析師。

專業背景：
- 深度熟悉台股（台積電、半導體供應鏈、科技股、ETF）
- 精通美股（大型科技股、ETF、指數）
- 擅長技術分析、基本面分析、籌碼分析
- 熟悉總體經濟與地緣政治對股市的影響

分析原則：
1. 客觀中立，同時呈現多空論點
2. 以數據說話，避免情緒化預測
3. 區分短期（1-5天）、中期（1-3個月）觀點
4. 明確指出關鍵風險因素
5. 提供具體、可執行的投資建議

重要聲明：所有分析僅供參考，不構成投資建議。投資有風險，請自行評估風險承受能力。"""


async def generate_analysis(
    news_data: dict,
    market_data: dict
) -> dict:
    """
    整合新聞與行情資料，生成投資分析
    """
    today = datetime.now().strftime("%Y年%m月%d日")

    analysis_prompt = f"""請根據以下今日（{today}）的市場資料與新聞，生成專業投資分析報告。

=== 市場行情資料 ===
{json.dumps(market_data, ensure_ascii=False, indent=2, default=str)}

=== 今日財經新聞 ===
{json.dumps(news_data, ensure_ascii=False, indent=2)}

請生成以下分析（JSON 格式）：

{{
  "analysis_date": "{today}",

  "market_overview": {{
    "taiwan_market_analysis": "台股整體分析（200字）",
    "us_market_analysis": "美股整體分析（200字）",
    "cross_market_correlation": "台美股市聯動性分析（100字）",
    "overall_sentiment": "整體市場情緒評分（1-10分）及說明"
  }},

  "key_opportunities": [
    {{
      "symbol": "股票代號",
      "name": "股票名稱",
      "thesis": "投資論點（100字）",
      "entry_strategy": "進場策略",
      "target_price": "目標價",
      "stop_loss": "停損價",
      "timeframe": "短期|中期",
      "confidence": "高|中|低",
      "catalysts": ["正面催化劑1", "正面催化劑2"],
      "risks": ["風險1", "風險2"]
    }}
  ],

  "stocks_to_watch": [
    {{
      "symbol": "股票代號",
      "reason": "關注原因（50字）",
      "key_level": "關鍵技術關卡",
      "news_impact": "相關新聞影響"
    }}
  ],

  "sector_analysis": [
    {{
      "sector": "產業名稱",
      "outlook": "正面|中性|負面",
      "key_drivers": ["驅動因素"],
      "top_picks": ["推薦關注個股"]
    }}
  ],

  "macro_analysis": {{
    "fed_policy": "聯準會政策影響",
    "taiwan_cb": "台灣央行政策",
    "currency": "匯率影響分析",
    "geopolitics": "地緣政治風險評估",
    "key_economic_data": "近期重要經濟數據解讀"
  }},

  "etf_analysis": {{
    "taiwan_etf": "台灣ETF（0050、0056等）分析",
    "us_etf": "美國ETF（SPY、QQQ等）分析",
    "recommendation": "ETF配置建議"
  }},

  "risk_alerts": [
    {{
      "risk": "風險項目",
      "severity": "高|中|低",
      "description": "風險說明",
      "hedge_strategy": "對沖或防禦策略"
    }}
  ],

  "tomorrow_strategy": {{
    "pre_market_focus": "明日盤前重點觀察",
    "intraday_plan": "盤中操作策略",
    "key_resistance_support": "台股/美股重要支撐壓力",
    "events_to_watch": ["明日重要事件/數據"],
    "positioning": "整體部位建議（積極/中性/保守）"
  }},

  "disclaimer": "本報告僅供參考，不構成投資建議。"
}}

只輸出有效的 JSON，不要有其他文字。"""

    result_text = ""

    async for message in query(
        prompt=analysis_prompt,
        options=ClaudeAgentOptions(
            model=CLAUDE_MODEL_MAIN,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            allowed_tools=[],  # 分析代理不需要額外工具
            thinking={"type": "adaptive"},  # 使用深度思考模式
            max_turns=5,
        )
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result

    try:
        clean_text = result_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            clean_text = "\n".join(lines[1:-1])
        return json.loads(clean_text)
    except json.JSONDecodeError:
        return {
            "analysis_date": today,
            "raw_analysis": result_text,
            "error": "JSON 解析失敗"
        }


if __name__ == "__main__":
    async def main():
        # 測試用假資料
        test_news = {"news_items": [], "key_themes": ["測試"], "market_mood": "中性"}
        test_market = {"taiwan_market": [], "us_market": []}
        result = await generate_analysis(test_news, test_market)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    anyio.run(main)
