"""
Data Providers - Veri Kaynakları

yfinance ile başlıyoruz, sonra borsapy eklenecek.
Interface pattern: Provider değişince motor bozulmasın.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Abstract base class for data providers"""
    
    @abstractmethod
    def fetch(self, ticker: str, period: str = "3y") -> pd.DataFrame:
        """
        OHLCV verisi çek.
        Returns: DataFrame with columns [Open, High, Low, Close, Volume]
        Index: DatetimeIndex
        """
        pass
    
    @abstractmethod
    def fetch_batch(self, tickers: List[str], period: str = "3y") -> Dict[str, pd.DataFrame]:
        """Birden fazla ticker için veri çek (rate limiting ile)"""
        pass


class YahooProvider(DataProvider):
    """
    yfinance ile ABD + BIST verisi.
    
    ABD: AAPL, NVDA, MSFT vb.
    BIST: ASELS.IS, THYAO.IS vb. (.IS suffix)
    """
    
    def __init__(self, delay_between_requests: float = 0.2):
        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            raise ImportError("yfinance yüklü değil: pip install yfinance")
        
        self.delay = delay_between_requests
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def fetch(self, ticker: str, period: str = "3y") -> pd.DataFrame:
        """
        Tek ticker için veri çek.
        
        Args:
            ticker: AAPL, NVDA, ASELS.IS vb.
            period: 1y, 2y, 3y, 5y, max
        
        Returns:
            DataFrame [Open, High, Low, Close, Volume] veya boş DataFrame
        """
        cache_key = f"{ticker}_{period}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            df = self.yf.download(
                ticker, 
                period=period, 
                interval="1d", 
                auto_adjust=False, 
                progress=False,
                timeout=10
            )
            
            if df is None or df.empty:
                logger.warning(f"Veri yok: {ticker}")
                return pd.DataFrame()
            
            # Normalize columns (yfinance bazen tuple döner multi-index için)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.rename(columns=str.title)
            df.index = pd.to_datetime(df.index)
            
            # Sadece OHLCV
            cols = ["Open", "High", "Low", "Close", "Volume"]
            available = [c for c in cols if c in df.columns]
            if len(available) < 5:
                logger.warning(f"Eksik kolonlar: {ticker}")
                return pd.DataFrame()
            
            df = df[cols].dropna()
            
            # Cache
            self._cache[cache_key] = df
            
            return df
            
        except Exception as e:
            logger.error(f"Veri çekme hatası ({ticker}): {e}")
            return pd.DataFrame()
    
    def fetch_batch(self, tickers: List[str], period: str = "3y") -> Dict[str, pd.DataFrame]:
        """
        Toplu veri çekme (rate limiting ile).
        """
        results = {}
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if i > 0 and self.delay > 0:
                time.sleep(self.delay)
            
            logger.info(f"Fetching {i+1}/{total}: {ticker}")
            df = self.fetch(ticker, period)
            
            if not df.empty:
                results[ticker] = df
        
        return results
    
    def clear_cache(self):
        """Cache'i temizle"""
        self._cache.clear()


class BorsaPyProvider(DataProvider):
    """
    borsapy entegrasyonu için placeholder.
    
    Not: borsapy gerçekten var (https://github.com/sinaatalay/borsapy)
    BIST verisi için daha sağlam olabilir.
    
    TODO: Kurulum sonrası implemente edilecek.
    """
    
    def __init__(self):
        self._borsapy = None
        try:
            # from borsapy import BorsaIstanbul
            # self._borsapy = BorsaIstanbul()
            pass
        except ImportError:
            logger.warning("borsapy yüklü değil. yfinance kullanılacak.")
    
    def fetch(self, ticker: str, period: str = "3y") -> pd.DataFrame:
        """
        borsapy ile BIST verisi.
        Şimdilik NotImplemented, yfinance fallback var.
        """
        raise NotImplementedError(
            "borsapy henüz entegre edilmedi. "
            "YahooProvider kullanın (BIST için .IS suffix ile)."
        )
    
    def fetch_batch(self, tickers: List[str], period: str = "3y") -> Dict[str, pd.DataFrame]:
        raise NotImplementedError("borsapy henüz entegre edilmedi.")


def get_provider(name: str = "yahoo") -> DataProvider:
    """Provider factory"""
    providers = {
        "yahoo": YahooProvider,
        "yfinance": YahooProvider,
        "borsapy": BorsaPyProvider,
    }
    
    if name.lower() not in providers:
        raise ValueError(f"Bilinmeyen provider: {name}. Seçenekler: {list(providers.keys())}")
    
    return providers[name.lower()]()
