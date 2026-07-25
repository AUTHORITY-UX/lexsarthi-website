# routes/trading.py
import yfinance as yf
import pandas as pd
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/trading", tags=["Trading"])

# ─── STOCK DATA ──────────────────────────────────────────────────
@router.get("/stocks/{symbol}")
async def get_stock_data(symbol: str, period: str = "1d"):
    """Get real-time stock data"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        history = ticker.history(period=period)
        
        return {
            "symbol": symbol,
            "name": info.get('longName', symbol),
            "price": info.get('currentPrice', info.get('regularMarketPrice', 0)),
            "change": info.get('regularMarketChange', 0),
            "change_percent": info.get('regularMarketChangePercent', 0),
            "volume": info.get('regularMarketVolume', 0),
            "market_cap": info.get('marketCap', 0),
            "pe_ratio": info.get('trailingPE', 0),
            "dividend_yield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            "high": info.get('dayHigh', 0),
            "low": info.get('dayLow', 0),
            "open": info.get('regularMarketOpen', 0),
            "previous_close": info.get('regularMarketPreviousClose', 0),
            "history": history.reset_index().to_dict('records')[-30:],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(404, f"Stock {symbol} not found")

@router.get("/stocks/indices")
async def get_indices():
    """Get major indices"""
    indices = {
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ",
        "^FTSE": "FTSE 100",
        "^NSEI": "NIFTY 50",
        "^BSESN": "BSE SENSEX",
        "^HSI": "Hang Seng",
        "^N225": "Nikkei 225"
    }
    results = {}
    for symbol, name in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            results[symbol] = {
                "name": name,
                "price": info.get('regularMarketPrice', 0),
                "change": info.get('regularMarketChange', 0),
                "change_percent": info.get('regularMarketChangePercent', 0)
            }
        except:
            pass
    return results

@router.get("/stocks/screener/{category}")
async def stock_screener(category: str = "top_gainers"):
    """Stock screener for different categories"""
    categories = {
        "top_gainers": lambda: [],
        "top_losers": lambda: [],
        "most_active": lambda: [],
        "near_52wk_high": lambda: [],
        "near_52wk_low": lambda: []
    }
    if category not in categories:
        raise HTTPException(400, "Invalid category")
    # Implement screener logic
    return {"category": category, "stocks": []}