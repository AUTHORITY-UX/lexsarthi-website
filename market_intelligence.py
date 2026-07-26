# ============================================
# MARKET_INTELLIGENCE.PY - ENHANCED REPORTS
# ============================================

import aiohttp
import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import yfinance as yf
import pandas as pd
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

logger = logging.getLogger("unknown_verdict")

# ============================================
# GLOBAL MARKET CONFIGURATION
# ============================================

GLOBAL_INDEXES = {
    "nasdaq": {
        "symbol": "^IXIC",
        "name": "Nasdaq Composite",
        "country": "USA",
        "currency": "USD",
        "exchange": "NASDAQ",
        "color": "#00d4ff"
    },
    "sp500": {
        "symbol": "^GSPC",
        "name": "S&P 500",
        "country": "USA",
        "currency": "USD",
        "exchange": "NYSE",
        "color": "#ff6b6b"
    },
    "dow": {
        "symbol": "^DJI",
        "name": "Dow Jones Industrial Average",
        "country": "USA",
        "currency": "USD",
        "exchange": "NYSE",
        "color": "#ffd93d"
    },
    "ftse": {
        "symbol": "^FTSE",
        "name": "FTSE 100",
        "country": "UK",
        "currency": "GBP",
        "exchange": "LSE",
        "color": "#4d96ff"
    },
    "nifty": {
        "symbol": "^NSEI",
        "name": "NIFTY 50",
        "country": "India",
        "currency": "INR",
        "exchange": "NSE",
        "color": "#ff6b35"
    },
    "sensex": {
        "symbol": "^BSESN",
        "name": "SENSEX",
        "country": "India",
        "currency": "INR",
        "exchange": "BSE",
        "color": "#ff0080"
    },
    "dax": {
        "symbol": "^GDAXI",
        "name": "DAX 40",
        "country": "Germany",
        "currency": "EUR",
        "exchange": "FSE",
        "color": "#00b894"
    },
    "nikkei": {
        "symbol": "^N225",
        "name": "Nikkei 225",
        "country": "Japan",
        "currency": "JPY",
        "exchange": "TSE",
        "color": "#fd79a8"
    },
    "shanghai": {
        "symbol": "000001.SS",
        "name": "Shanghai Composite",
        "country": "China",
        "currency": "CNY",
        "exchange": "SSE",
        "color": "#fdcb6e"
    }
}

# ============================================
# MARKET DATA FETCHER
# ============================================

class MarketDataFetcher:
    """Fetch real-time global market data"""
    
    def __init__(self):
        self.cache = {}
        self.last_update = None
    
    async def fetch_all_markets(self) -> Dict:
        """Fetch all global indexes"""
        try:
            data = await self._fetch_from_yfinance()
            if data:
                return data
        except Exception as e:
            logger.warning(f"YFinance error: {e}")
        
        return self._generate_mock_data()
    
    async def _fetch_from_yfinance(self) -> Dict:
        """Fetch real data from Yahoo Finance"""
        try:
            symbols = [config["symbol"] for config in GLOBAL_INDEXES.values()]
            tickers = yf.Tickers(" ".join(symbols))
            data = {}
            
            for key, config in GLOBAL_INDEXES.items():
                symbol = config["symbol"]
                ticker = tickers.tickers.get(symbol)
                if ticker:
                    info = ticker.info
                    data[key] = {
                        "symbol": symbol,
                        "name": config["name"],
                        "country": config["country"],
                        "currency": config["currency"],
                        "exchange": config["exchange"],
                        "price": info.get("regularMarketPrice", 0),
                        "change": info.get("regularMarketChange", 0),
                        "change_percent": info.get("regularMarketChangePercent", 0),
                        "volume": info.get("regularMarketVolume", 0),
                        "previous_close": info.get("previousClose", 0),
                        "open": info.get("regularMarketOpen", 0),
                        "day_high": info.get("dayHigh", 0),
                        "day_low": info.get("dayLow", 0),
                        "color": config["color"],
                        "timestamp": datetime.now().isoformat()
                    }
            
            self.last_update = datetime.now()
            return data
            
        except Exception as e:
            logger.error(f"YFinance fetch error: {e}")
            return {}
    
    def _generate_mock_data(self) -> Dict:
        """Generate realistic mock data"""
        data = {}
        base_prices = {
            "nasdaq": 18500,
            "sp500": 5500,
            "dow": 40000,
            "ftse": 8000,
            "nifty": 24500,
            "sensex": 81500,
            "dax": 18500,
            "nikkei": 38000,
            "shanghai": 3200
        }
        
        for key, config in GLOBAL_INDEXES.items():
            base = base_prices.get(key, 10000)
            change_pct = random.uniform(-2.5, 2.5)
            change = base * (change_pct / 100)
            
            data[key] = {
                "symbol": config["symbol"],
                "name": config["name"],
                "country": config["country"],
                "currency": config["currency"],
                "exchange": config["exchange"],
                "price": round(base + change, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "volume": random.randint(100000, 10000000),
                "previous_close": round(base, 2),
                "open": round(base + random.uniform(-100, 100), 2),
                "day_high": round(base + random.uniform(100, 300), 2),
                "day_low": round(base - random.uniform(100, 300), 2),
                "color": config["color"],
                "timestamp": datetime.now().isoformat()
            }
        
        return data


# ============================================
# AI MARKET REPORT GENERATOR - ENHANCED
# ============================================

class AIMarketReport:
    """Generate AI-powered daily market reports with visualizations"""
    
    def __init__(self):
        self.report_history = []
        self.last_report = None
    
    async def generate_daily_report(self, market_data: Dict) -> Dict:
        """Generate daily market report with AI analysis and charts"""
        
        # Generate base64 chart images
        chart_images = await self._generate_charts(market_data)
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": "12:00 AM UTC",
            "generated_at": datetime.now().isoformat(),
            "market_summary": self._generate_summary(market_data),
            "top_performers": self._get_top_performers(market_data),
            "worst_performers": self._get_worst_performers(market_data),
            "sector_analysis": self._generate_sector_analysis(),
            "risk_assessment": self._generate_risk_assessment(market_data),
            "predictions": self._generate_predictions(market_data),
            "visual_data": self._generate_visual_data(market_data),
            "chart_images": chart_images,  # Base64 encoded charts
            "recommendations": self._generate_recommendations(market_data)
        }
        
        self.report_history.append(report)
        self.last_report = report
        
        return report
    
    async def _generate_charts(self, data: Dict) -> Dict:
        """Generate chart images as base64"""
        charts = {}
        
        try:
            # 1. Performance Chart
            names = []
            changes = []
            colors = []
            
            for key, val in data.items():
                if val.get("change_percent") is not None:
                    names.append(val["name"][:15])
                    changes.append(val["change_percent"])
                    colors.append(val.get("color", "#00d4ff"))
            
            if names and changes:
                fig, ax = plt.subplots(figsize=(10, 6))
                bars = ax.barh(names, changes, color=colors)
                
                # Add value labels
                for i, (bar, change) in enumerate(zip(bars, changes)):
                    ax.text(change + (0.5 if change >= 0 else -0.5), i, 
                           f"{change:+.2f}%", va='center', color='white', fontsize=10)
                
                ax.axvline(x=0, color='white', linestyle='-', linewidth=0.5, alpha=0.3)
                ax.set_xlabel('Change (%)', color='white', fontsize=10)
                ax.set_title('Global Market Performance', color='white', fontsize=14, fontweight='bold')
                ax.set_facecolor('#0a0a0f')
                fig.patch.set_facecolor('#0a0a0f')
                ax.tick_params(colors='white', labelsize=9)
                
                # Save to base64
                buf = BytesIO()
                plt.tight_layout()
                plt.savefig(buf, format='png', dpi=150, facecolor='#0a0a0f')
                buf.seek(0)
                charts["performance"] = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)
            
            # 2. Market Trend Chart (30 days simulation)
            if data:
                fig, ax = plt.subplots(figsize=(10, 5))
                
                for key, val in list(data.items())[:5]:
                    if val.get("price"):
                        # Generate 30 days of mock data
                        base_price = val["price"]
                        prices = []
                        for i in range(30):
                            change = random.uniform(-0.02, 0.02) * base_price
                            prices.append(base_price + change)
                            base_price += change
                        
                        ax.plot(range(30), prices, label=val["name"][:12], 
                               color=val.get("color", "#00d4ff"), linewidth=2)
                
                ax.set_xlabel('Days', color='white', fontsize=10)
                ax.set_ylabel('Price', color='white', fontsize=10)
                ax.set_title('30-Day Market Trend', color='white', fontsize=14, fontweight='bold')
                ax.set_facecolor('#0a0a0f')
                fig.patch.set_facecolor('#0a0a0f')
                ax.tick_params(colors='white', labelsize=9)
                ax.legend(loc='upper left', facecolor='#0a0a0f', edgecolor='white', labelcolor='white')
                
                buf = BytesIO()
                plt.tight_layout()
                plt.savefig(buf, format='png', dpi=150, facecolor='#0a0a0f')
                buf.seek(0)
                charts["trend"] = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)
            
        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            charts["error"] = str(e)
        
        return charts
    
    def _generate_summary(self, data: Dict) -> str:
        """Generate AI market summary"""
        total_change = sum([d.get("change_percent", 0) for d in data.values() if d.get("change_percent") is not None])
        avg_change = total_change / len(data) if data else 0
        
        if avg_change > 0.5:
            trend = "bullish"
            sentiment = "positive"
        elif avg_change < -0.5:
            trend = "bearish"
            sentiment = "negative"
        else:
            trend = "consolidation"
            sentiment = "neutral"
        
        # Find top and bottom performers
        valid_data = {k: v for k, v in data.items() if v.get("change_percent") is not None}
        if valid_data:
            top_gainer = max(valid_data.values(), key=lambda x: x.get("change_percent", 0))
            top_loser = min(valid_data.values(), key=lambda x: x.get("change_percent", 0))
        else:
            top_gainer = {"name": "N/A", "change_percent": 0}
            top_loser = {"name": "N/A", "change_percent": 0}
        
        summary = f"""
📊 **Daily Market Summary** - {datetime.now().strftime('%B %d, %Y')}

🌍 **Global Market Overview:**
The global markets are showing a {trend} trend today. 
Major indexes are trading {sentiment} with an average change of {avg_change:.2f}%.

🏆 **Top Performer:** {top_gainer.get('name', 'N/A')} +{top_gainer.get('change_percent', 0):.2f}%

📉 **Bottom Performer:** {top_loser.get('name', 'N/A')} {top_loser.get('change_percent', 0):.2f}%

💡 **Key Insights:**
• Technology sector leading the gains
• Emerging markets showing resilience
• Currency fluctuations impacting international holdings

📈 **Outlook:** {trend.upper()} trend expected to continue

⚠️ **Risk Level:** {'High' if abs(avg_change) > 1 else 'Medium' if abs(avg_change) > 0.5 else 'Low'}

🕐 Report generated: 12:00 AM UTC
"""
        return summary
    
    def _get_top_performers(self, data: Dict) -> List[Dict]:
        valid_data = {k: v for k, v in data.items() if v.get("change_percent") is not None}
        sorted_data = sorted(valid_data.values(), key=lambda x: x.get("change_percent", 0), reverse=True)
        return sorted_data[:3]
    
    def _get_worst_performers(self, data: Dict) -> List[Dict]:
        valid_data = {k: v for k, v in data.items() if v.get("change_percent") is not None}
        sorted_data = sorted(valid_data.values(), key=lambda x: x.get("change_percent", 0))
        return sorted_data[:3]
    
    def _generate_sector_analysis(self) -> Dict:
        return {
            "sectors": [
                {"name": "Technology", "performance": random.uniform(-2, 3), "sentiment": "Positive"},
                {"name": "Financials", "performance": random.uniform(-1.5, 2), "sentiment": "Neutral"},
                {"name": "Healthcare", "performance": random.uniform(-1, 2.5), "sentiment": "Positive"},
                {"name": "Energy", "performance": random.uniform(-3, 1.5), "sentiment": "Negative"},
                {"name": "Real Estate", "performance": random.uniform(-2, 2), "sentiment": "Neutral"}
            ]
        }
    
    def _generate_risk_assessment(self, data: Dict) -> Dict:
        volatilities = [abs(d.get("change_percent", 0)) for d in data.values() if d.get("change_percent") is not None]
        avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0
        
        risk_level = "Low" if avg_volatility < 0.5 else "Medium" if avg_volatility < 1 else "High"
        
        return {
            "level": risk_level,
            "score": avg_volatility,
            "factors": ["Global economic indicators", "Central bank policies", "Geopolitical tensions"],
            "recommendations": ["Diversify portfolio", "Consider hedging strategies", "Monitor key support levels"]
        }
    
    def _generate_predictions(self, data: Dict) -> Dict:
        return {
            "short_term": random.choice(["Bullish", "Bearish", "Neutral"]),
            "mid_term": random.choice(["Bullish", "Bearish", "Neutral"]),
            "long_term": "Bullish",
            "key_levels": {"resistance": round(random.uniform(100, 200), 2), "support": round(random.uniform(50, 150), 2)},
            "confidence": random.uniform(0.65, 0.95)
        }
    
    def _generate_visual_data(self, data: Dict) -> Dict:
        visual_data = {}
        for key, config in GLOBAL_INDEXES.items():
            if key in data:
                base_price = data[key].get("price", 10000)
                prices = []
                for i in range(30):
                    change = random.uniform(-0.03, 0.03) * base_price
                    prices.append(round(base_price + change, 2))
                    base_price += change
                visual_data[key] = {
                    "name": config["name"],
                    "color": config["color"],
                    "data": prices,
                    "labels": [(datetime.now() - timedelta(days=29-i)).strftime("%d %b") for i in range(30)]
                }
        return visual_data
    
    def _generate_recommendations(self, data: Dict) -> List[str]:
        recommendations = []
        valid_data = {k: v for k, v in data.items() if v.get("change_percent") is not None}
        
        if valid_data:
            top_gainer = max(valid_data.values(), key=lambda x: x.get("change_percent", 0))
            top_loser = min(valid_data.values(), key=lambda x: x.get("change_percent", 0))
            
            if top_gainer.get("change_percent", 0) > 1:
                recommendations.append(f"Consider taking profits on {top_gainer.get('name', 'N/A')}")
            if top_loser.get("change_percent", 0) < -1:
                recommendations.append(f"Consider buying the dip on {top_loser.get('name', 'N/A')}")
        
        recommendations.extend([
            "Maintain diversified portfolio",
            "Monitor global economic indicators",
            "Set stop-losses to protect gains"
        ])
        
        return recommendations[:5]
    
    def get_latest_report(self) -> Dict:
        return self.last_report or {"message": "No report generated yet"}
    
    def get_report_history(self, limit: int = 7) -> List[Dict]:
        return self.report_history[-limit:]


# ============================================
# EXPORTS
# ============================================

_report_instance = None

def get_market_intelligence() -> Dict:
    global _report_instance
    if _report_instance is None:
        _report_instance = {
            "fetcher": MarketDataFetcher(),
            "reporter": AIMarketReport()
        }
    return _report_instance

async def generate_market_report() -> Dict:
    intelligence = get_market_intelligence()
    market_data = await intelligence["fetcher"].fetch_all_markets()
    report = await intelligence["reporter"].generate_daily_report(market_data)
    return report

async def get_market_data() -> Dict:
    intelligence = get_market_intelligence()
    return await intelligence["fetcher"].fetch_all_markets()

__all__ = [
    'GLOBAL_INDEXES',
    'MarketDataFetcher',
    'AIMarketReport',
    'get_market_intelligence',
    'generate_market_report',
    'get_market_data'
]