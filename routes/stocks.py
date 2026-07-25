# routes/stocks.py - Stock Market Routes
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import yfinance as yf

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])

@router.get("/market/status")
async def get_market_status():
    """Get global market status"""
    exchanges = {
        "NSE": "India",
        "BSE": "India",
        "NYSE": "USA",
        "NASDAQ": "USA",
        "LSE": "UK",
        "TSE": "Japan",
        "HKEX": "Hong Kong"
    }
    return {"exchanges": exchanges, "timestamp": datetime.now().isoformat()}

@router.get("/screener/{category}")
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
    
    # For now, return sample data
    return {
        "category": category,
        "stocks": [
            {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "price": 2856, "change": 45, "change_percent": 1.6},
            {"symbol": "TCS.NS", "name": "Tata Consultancy", "price": 3892, "change": 23, "change_percent": 0.6},
            {"symbol": "INFY.NS", "name": "Infosys", "price": 1523, "change": 12, "change_percent": 0.8}
        ],
        "timestamp": datetime.now().isoformat()
    }

@router.get("/historical/{symbol}")
async def get_historical_data(symbol: str, period: str = "1y"):
    """Get historical stock data"""
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period)
        return {
            "symbol": symbol,
            "period": period,
            "data": history.reset_index().to_dict('records'),
            "timestamp": datetime.now().isoformat()
        }
    except:
        raise HTTPException(404, f"Stock {symbol} not found")

@router.get("/sector/performance")
async def get_sector_performance():
    """Get sector performance data"""
    sectors = {
        "IT": {"change": 1.2},
        "Banking": {"change": 0.8},
        "Pharma": {"change": -0.3},
        "Auto": {"change": 1.5},
        "Energy": {"change": 0.5},
        "FMCG": {"change": 0.2},
        "Metal": {"change": -0.7},
        "Realty": {"change": 2.1}
    }
    return {"sectors": sectors, "timestamp": datetime.now().isoformat()}