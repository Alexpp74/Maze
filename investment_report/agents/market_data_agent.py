"""
市場資料代理 - 抓取股價、指數、ETF 行情
Market Data Agent - Fetches stock prices, indices, ETF data
"""

import json
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from config.settings import TAIWAN_STOCKS, US_STOCKS


def get_market_data() -> dict:
    """
    抓取台股與美股行情資料
    Returns structured market data for report generation.
    """
    today = datetime.now()
    # 抓取近5個交易日資料
    start_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    all_symbols = TAIWAN_STOCKS + US_STOCKS
    market_data = {
        "timestamp": today.isoformat(),
        "taiwan_market": [],
        "us_market": [],
        "errors": []
    }

    for symbol in all_symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            info = ticker.fast_info

            if hist.empty:
                market_data["errors"].append(f"{symbol}: 無法取得資料")
                continue

            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]

            price_change = latest["Close"] - prev["Close"]
            price_change_pct = (price_change / prev["Close"]) * 100

            stock_info = {
                "symbol": symbol,
                "name": getattr(info, "description", symbol),
                "close": round(float(latest["Close"]), 2),
                "change": round(float(price_change), 2),
                "change_pct": round(float(price_change_pct), 2),
                "volume": int(latest["Volume"]),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "week_52_high": round(float(getattr(info, "year_high", 0)), 2),
                "week_52_low": round(float(getattr(info, "year_low", 0)), 2),
                "market_cap": getattr(info, "market_cap", None),
                "date": hist.index[-1].strftime("%Y-%m-%d"),
            }

            # 加入5日、20日均線
            if len(hist) >= 5:
                stock_info["ma5"] = round(hist["Close"].tail(5).mean(), 2)
            if len(hist) >= 20:
                stock_info["ma20"] = round(hist["Close"].tail(20).mean(), 2)

            if symbol.endswith(".TW"):
                market_data["taiwan_market"].append(stock_info)
            else:
                market_data["us_market"].append(stock_info)

        except Exception as e:
            market_data["errors"].append(f"{symbol}: {str(e)}")

    # 計算市場摘要統計
    market_data["taiwan_summary"] = _calc_market_summary(market_data["taiwan_market"])
    market_data["us_summary"] = _calc_market_summary(market_data["us_market"])

    return market_data


def _calc_market_summary(stocks: list) -> dict:
    """計算市場整體統計"""
    if not stocks:
        return {}

    changes = [s["change_pct"] for s in stocks if "change_pct" in s]
    if not changes:
        return {}

    gainers = [s for s in stocks if s.get("change_pct", 0) > 0]
    losers = [s for s in stocks if s.get("change_pct", 0) < 0]

    return {
        "total_tracked": len(stocks),
        "gainers_count": len(gainers),
        "losers_count": len(losers),
        "avg_change_pct": round(sum(changes) / len(changes), 2),
        "top_gainer": max(stocks, key=lambda x: x.get("change_pct", 0)),
        "top_loser": min(stocks, key=lambda x: x.get("change_pct", 0)),
        "market_sentiment": (
            "偏多" if sum(changes) / len(changes) > 0.3 else
            "偏空" if sum(changes) / len(changes) < -0.3 else
            "盤整"
        )
    }


if __name__ == "__main__":
    data = get_market_data()
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
