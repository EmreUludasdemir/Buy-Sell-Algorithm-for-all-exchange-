"""
Data Fetcher Module
====================
Multi-source financial data fetching using yfinance and other APIs.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import logging
import aiohttp
import asyncio
from functools import lru_cache
import time
import hashlib

try:
    from cachetools import TTLCache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

try:
    import anyio
    ANYIO_AVAILABLE = True
except ImportError:
    ANYIO_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global TTL cache for yfinance data (5 minute TTL)
_data_cache: Dict[str, Tuple[Any, float]] = {}
_CACHE_TTL = 300  # 5 minutes


class DataFetcher:
    """
    Multi-source financial data fetcher.
    
    Supports:
    - Yahoo Finance (stocks, crypto, forex)
    - Alpha Vantage (backup)
    - Finnhub (real-time quotes)
    """
    
    # Valid periods for yfinance
    VALID_PERIODS = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    
    # Valid intervals for yfinance
    VALID_INTERVALS = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']
    
    def __init__(self, alpha_vantage_key: Optional[str] = None, finnhub_key: Optional[str] = None):
        """
        Initialize the data fetcher.
        
        Args:
            alpha_vantage_key: Optional Alpha Vantage API key
            finnhub_key: Optional Finnhub API key
        """
        self.alpha_vantage_key = alpha_vantage_key
        self.finnhub_key = finnhub_key
        self._cache: Dict[str, Any] = {}
        
    def _get_cache_key(self, ticker: str, period: str, interval: str, start: Optional[str], end: Optional[str]) -> str:
        """Generate cache key for data request."""
        key_str = f"{ticker}_{period}_{interval}_{start}_{end}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if valid."""
        if cache_key in _data_cache:
            data, timestamp = _data_cache[cache_key]
            if time.time() - timestamp < _CACHE_TTL:
                logger.debug(f"Cache hit for {cache_key}")
                return data
            else:
                del _data_cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Store data in cache."""
        _data_cache[cache_key] = (data, time.time())
        # Limit cache size to 100 entries
        if len(_data_cache) > 100:
            oldest_key = min(_data_cache.keys(), key=lambda k: _data_cache[k][1])
            del _data_cache[oldest_key]
    
    def get_stock_data(
        self, 
        ticker: str, 
        period: str = "1y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
        max_retries: int = 3
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a ticker.
        
        Args:
            ticker: Stock/crypto symbol (e.g., 'AAPL', 'BTC-USD')
            period: Data period ('1d', '1mo', '1y', etc.)
            interval: Data interval ('1m', '1h', '1d', etc.)
            start: Optional start date (YYYY-MM-DD)
            end: Optional end date (YYYY-MM-DD)
            max_retries: Maximum retry attempts on failure
            
        Returns:
            DataFrame with OHLCV data
        """
        # Check cache first
        cache_key = self._get_cache_key(ticker, period, interval, start, end)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(ticker)
                
                if start and end:
                    df = stock.history(start=start, end=end, interval=interval)
                else:
                    df = stock.history(period=period, interval=interval)
                
                if df.empty:
                    logger.warning(f"No data found for {ticker}")
                    return pd.DataFrame()
                
                # Standardize column names
                df.columns = [col.lower().replace(' ', '_') for col in df.columns]
                
                # Ensure we have required columns
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in required_cols:
                    if col not in df.columns:
                        logger.warning(f"Missing column {col} for {ticker}")
                        
                # Reset index to have date as column
                df = df.reset_index()
                if 'Date' in df.columns:
                    df = df.rename(columns={'Date': 'date'})
                elif 'Datetime' in df.columns:
                    df = df.rename(columns={'Datetime': 'date'})
                    
                logger.info(f"Fetched {len(df)} rows for {ticker}")
                
                # Cache the result
                self._set_cache(cache_key, df)
                
                return df
                
            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {ticker}: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        logger.error(f"Error fetching data for {ticker} after {max_retries} attempts: {last_error}")
        return pd.DataFrame()
    
    def get_multi_stock_data(
        self, 
        tickers: List[str], 
        period: str = "1y",
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            period: Data period
            interval: Data interval
            
        Returns:
            Dictionary mapping ticker to DataFrame
        """
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_stock_data(ticker, period, interval)
        return result
    
    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive company information.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with company info
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract key metrics
            return {
                "symbol": ticker,
                "name": info.get("longName", info.get("shortName", ticker)),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "country": info.get("country", "N/A"),
                "website": info.get("website", "N/A"),
                "description": info.get("longBusinessSummary", "N/A"),
                
                # Price data
                "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
                "previous_close": info.get("previousClose"),
                "market_cap": info.get("marketCap"),
                "volume": info.get("volume"),
                "avg_volume": info.get("averageVolume"),
                
                # Valuation
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
                
                # Financials
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings": info.get("netIncomeToCommon"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                
                # Per share
                "eps": info.get("trailingEps"),
                "forward_eps": info.get("forwardEps"),
                "book_value": info.get("bookValue"),
                
                # Dividends
                "dividend_yield": info.get("dividendYield"),
                "dividend_rate": info.get("dividendRate"),
                
                # Analyst data
                "target_price": info.get("targetMeanPrice"),
                "target_high": info.get("targetHighPrice"),
                "target_low": info.get("targetLowPrice"),
                "recommendation": info.get("recommendationKey"),
                "analyst_count": info.get("numberOfAnalystOpinions"),
                
                # Technical
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "50_day_avg": info.get("fiftyDayAverage"),
                "200_day_avg": info.get("twoHundredDayAverage"),
                "beta": info.get("beta"),
                
                # Metadata
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange"),
                "quote_type": info.get("quoteType"),
            }
            
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return {"symbol": ticker, "error": str(e)}
    
    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed fundamental data including financials.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Dictionary with fundamental data
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get financial statements
            income_stmt = stock.income_stmt
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            # Get earnings
            earnings = stock.earnings_dates
            
            return {
                "symbol": ticker,
                "income_statement": income_stmt.to_dict() if income_stmt is not None and not income_stmt.empty else {},
                "balance_sheet": balance_sheet.to_dict() if balance_sheet is not None and not balance_sheet.empty else {},
                "cash_flow": cash_flow.to_dict() if cash_flow is not None and not cash_flow.empty else {},
                "earnings_dates": earnings.to_dict() if earnings is not None and not earnings.empty else {},
            }
            
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {e}")
            return {"symbol": ticker, "error": str(e)}
    
    def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Get news articles for a ticker from Yahoo Finance.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            List of news articles
        """
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            if not news:
                return []
            
            articles = []
            for item in news:
                articles.append({
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published": datetime.fromtimestamp(item.get("providerPublishTime", 0)).isoformat(),
                    "type": item.get("type", ""),
                    "thumbnail": item.get("thumbnail", {}).get("resolutions", [{}])[0].get("url", "") if item.get("thumbnail") else "",
                    "related_tickers": item.get("relatedTickers", []),
                })
            
            logger.info(f"Fetched {len(articles)} news articles for {ticker}")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []
    
    def get_options_chain(self, ticker: str, date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Get options chain for a ticker.
        
        Args:
            ticker: Stock symbol
            date: Optional expiration date
            
        Returns:
            Dictionary with 'calls' and 'puts' DataFrames
        """
        try:
            stock = yf.Ticker(ticker)
            
            if date:
                options = stock.option_chain(date)
            else:
                # Get nearest expiration
                expirations = stock.options
                if not expirations:
                    return {"calls": pd.DataFrame(), "puts": pd.DataFrame()}
                options = stock.option_chain(expirations[0])
            
            return {
                "calls": options.calls,
                "puts": options.puts,
                "expiration": date or expirations[0] if expirations else None
            }
            
        except Exception as e:
            logger.error(f"Error fetching options for {ticker}: {e}")
            return {"calls": pd.DataFrame(), "puts": pd.DataFrame()}
    
    def get_market_summary(self) -> Dict[str, Any]:
        """
        Get overall market summary with major indices.
        
        Returns:
            Dictionary with market indices data
        """
        indices = {
            "SP500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DOW": "^DJI",
            "VIX": "^VIX",
            "BITCOIN": "BTC-USD",
            "ETHEREUM": "ETH-USD",
            "GOLD": "GC=F",
            "OIL": "CL=F",
        }
        
        summary = {}
        for name, symbol in indices.items():
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                hist = stock.history(period="2d")
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2]
                    change = current - previous
                    change_pct = (change / previous) * 100
                else:
                    current = info.get("regularMarketPrice", 0)
                    change = info.get("regularMarketChange", 0)
                    change_pct = info.get("regularMarketChangePercent", 0)
                
                summary[name] = {
                    "symbol": symbol,
                    "price": round(current, 2) if current else None,
                    "change": round(change, 2) if change else None,
                    "change_percent": round(change_pct, 2) if change_pct else None,
                }
            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
                summary[name] = {"symbol": symbol, "error": str(e)}
        
        return summary


# Async version for concurrent fetching
class AsyncDataFetcher:
    """Async version of DataFetcher for concurrent operations."""
    
    def __init__(self, finnhub_key: Optional[str] = None):
        self.finnhub_key = finnhub_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_finnhub_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote from Finnhub."""
        if not self.finnhub_key or not self.session:
            return {}
            
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={self.finnhub_key}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "current": data.get("c"),
                        "change": data.get("d"),
                        "change_percent": data.get("dp"),
                        "high": data.get("h"),
                        "low": data.get("l"),
                        "open": data.get("o"),
                        "previous_close": data.get("pc"),
                        "timestamp": data.get("t"),
                    }
        except Exception as e:
            logger.error(f"Finnhub error for {ticker}: {e}")
        
        return {}
    
    async def get_finnhub_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """Get news from Finnhub."""
        if not self.finnhub_key or not self.session:
            return []
            
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start_date}&to={end_date}&token={self.finnhub_key}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Finnhub news error for {ticker}: {e}")
        
        return []


if __name__ == "__main__":
    # Test the data fetcher
    logging.basicConfig(level=logging.INFO)
    
    fetcher = DataFetcher()
    
    # Test stock data
    print("\n=== Stock Data Test (AAPL) ===")
    df = fetcher.get_stock_data("AAPL", period="1mo")
    print(df.head())
    
    # Test company info
    print("\n=== Company Info Test (AAPL) ===")
    info = fetcher.get_company_info("AAPL")
    print(f"Name: {info['name']}")
    print(f"Sector: {info['sector']}")
    print(f"P/E Ratio: {info['pe_ratio']}")
    print(f"Target Price: {info['target_price']}")
    
    # Test news
    print("\n=== News Test (AAPL) ===")
    news = fetcher.get_news("AAPL")
    for article in news[:3]:
        print(f"- {article['title']}")
    
    # Test market summary
    print("\n=== Market Summary ===")
    summary = fetcher.get_market_summary()
    for name, data in summary.items():
        if "error" not in data:
            print(f"{name}: ${data['price']} ({data['change_percent']:+.2f}%)")
