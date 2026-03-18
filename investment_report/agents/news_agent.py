"""
新聞代理 - 使用 Claude Agent SDK 自動搜尋財經時事
News Agent - Uses Claude Agent SDK to search financial news
"""

import anyio
import json
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage
from config.settings import CLAUDE_MODEL_FAST, SEARCH_TOPICS


NEWS_SYSTEM_PROMPT = """你是一位專業的財經新聞分析師，專精於台灣與美國股票市場研究。

你的任務：
1. 搜尋並彙整今日最重要的財經時事
2. 重點關注：台股、美股、半導體、AI、ETF、總體經濟、地緣政治風險
3. 評估每則新聞對投資決策的影響程度（高/中/低）
4. 以投資人視角摘要重點

輸出格式（JSON）：
{
  "search_date": "YYYY-MM-DD",
  "news_items": [
    {
      "title": "新聞標題",
      "summary": "100字以內摘要",
      "source": "來源媒體",
      "category": "台股|美股|總經|地緣政治|產業",
      "impact": "高|中|低",
      "sentiment": "正面|負面|中性",
      "related_stocks": ["相關股票代號"],
      "key_insight": "對投資人的啟示（50字以內）"
    }
  ],
  "key_themes": ["今日最重要的3-5個主題"],
  "market_mood": "整體市場情緒（一句話）"
}"""


async def collect_news() -> dict:
    """
    使用 Claude Agent SDK 搜尋今日財經新聞
    Uses WebSearch tool to gather financial news automatically.
    """
    today = datetime.now().strftime("%Y年%m月%d日")

    # 建構搜尋提示
    search_prompt = f"""請搜尋 {today} 的以下財經時事，並整合成結構化報告：

搜尋主題：
{chr(10).join(f'- {topic}' for topic in SEARCH_TOPICS)}

請使用 WebSearch 工具搜尋每個主題，收集最新資訊後，
以指定的 JSON 格式輸出今日財經新聞摘要。

重點注意：
1. 優先搜尋今日（{today}）的最新消息
2. 台股相關：台積電、聯發科、鴻海、半導體供應鏈
3. 美股相關：Nvidia、Apple、S&P500、科技股
4. 總經：聯準會、台灣央行、匯率、油價、通膨
5. 地緣政治：美中關係、台海情勢、出口管制

只輸出有效的 JSON，不要有其他文字。"""

    result_text = ""

    async for message in query(
        prompt=search_prompt,
        options=ClaudeAgentOptions(
            model=CLAUDE_MODEL_FAST,
            system_prompt=NEWS_SYSTEM_PROMPT,
            allowed_tools=["WebSearch", "WebFetch"],
            max_turns=20,  # 允許多次搜尋
        )
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result
        elif isinstance(message, SystemMessage) and message.subtype == "init":
            print(f"  [新聞代理] Session: {message.data.get('session_id', 'N/A')}")

    # 解析 JSON 結果
    try:
        # 清理可能的 markdown code block
        clean_text = result_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            clean_text = "\n".join(lines[1:-1])
        return json.loads(clean_text)
    except json.JSONDecodeError:
        # 若解析失敗，返回原始文字
        return {
            "search_date": datetime.now().strftime("%Y-%m-%d"),
            "raw_content": result_text,
            "news_items": [],
            "key_themes": [],
            "market_mood": "資料解析失敗，請查看 raw_content"
        }


if __name__ == "__main__":
    async def main():
        print("開始收集財經新聞...")
        news = await collect_news()
        print(json.dumps(news, ensure_ascii=False, indent=2))

    anyio.run(main)
