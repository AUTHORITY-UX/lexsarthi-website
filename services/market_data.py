# services/market_data.py - Market Data Service
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class MarketDataService:
    """Service for fetching market data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # seconds
    
    async def get_stock_data(self, symbol: str) -> Dict:
        """Get stock data with caching"""
        cache_key = f"stock_{symbol}"
        if cache_key in self.cache:
            cached_time, data = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return data
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            data = {
                "symbol": symbol,
                "price": info.get('currentPrice', 0),
                "change": info.get('regularMarketChange', 0),
                "change_percent": info.get('regularMarketChangePercent', 0),
                "volume": info.get('regularMarketVolume', 0),
                "market_cap": info.get('marketCap', 0)
            }
            self.cache[cache_key] = (datetime.now(), data)
            return data
        except:
            return {"symbol": symbol, "price": 0, "change": 0, "change_percent": 0, "volume": 0}
    
    async def get_multiple_stocks(self, symbols: List[str]) -> Dict:
        """Get data for multiple stocks"""
        results = {}
        for symbol in symbols:
            results[symbol] = await self.get_stock_data(symbol)
        return results

market_data = MarketDataService()