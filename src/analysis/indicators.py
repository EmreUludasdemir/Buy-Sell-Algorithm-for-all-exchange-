"""
Technical Indicators Module
===========================
Comprehensive technical analysis indicators for trading signals.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Standardized indicator result."""
    name: str
    value: float
    signal: str  # 'bullish', 'bearish', 'neutral'
    strength: float  # 0.0 to 1.0
    
    
class TechnicalIndicators:
    """
    Comprehensive technical indicators library.
    
    Includes:
    - Trend Indicators (EMA, SMA, MACD)
    - Momentum Indicators (RSI, Stochastic, Williams %R)
    - Volatility Indicators (Bollinger Bands, ATR, Keltner)
    - Volume Indicators (OBV, VWAP, MFI)
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                          TREND INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def sma(data: pd.Series, period: int = 20) -> pd.Series:
        """
        Simple Moving Average.
        
        Args:
            data: Price series (typically close prices)
            period: Lookback period
            
        Returns:
            SMA series
        """
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int = 20) -> pd.Series:
        """
        Exponential Moving Average.
        
        Args:
            data: Price series
            period: Lookback period
            
        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def wma(data: pd.Series, period: int = 20) -> pd.Series:
        """
        Weighted Moving Average.
        
        Args:
            data: Price series
            period: Lookback period
            
        Returns:
            WMA series
        """
        weights = np.arange(1, period + 1)
        return data.rolling(period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
    
    @staticmethod
    def macd(
        data: pd.Series, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Moving Average Convergence Divergence.
        
        Args:
            data: Price series
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def supertrend(
        df: pd.DataFrame,
        period: int = 10,
        multiplier: float = 3.0
    ) -> Tuple[pd.Series, pd.Series]:
        """
        SuperTrend indicator.
        
        Args:
            df: DataFrame with OHLC data
            period: ATR period
            multiplier: ATR multiplier
            
        Returns:
            Tuple of (SuperTrend line, Direction: 1=up, -1=down)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Calculate basic upper and lower bands
        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        # Initialize
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(period, len(df)):
            if close.iloc[i] > upper_band.iloc[i-1]:
                direction.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i-1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i-1] if i > period else 1
            
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
        
        return supertrend, direction
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         MOMENTUM INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index.
        
        Args:
            data: Price series
            period: Lookback period
            
        Returns:
            RSI series (0-100 scale)
        """
        delta = data.diff()
        
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def stochastic(
        df: pd.DataFrame, 
        k_period: int = 14, 
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator.
        
        Args:
            df: DataFrame with high, low, close
            k_period: %K period
            d_period: %D smoothing period
            
        Returns:
            Tuple of (%K, %D)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Williams %R.
        
        Args:
            df: DataFrame with high, low, close
            period: Lookback period
            
        Returns:
            Williams %R series (-100 to 0 scale)
        """
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        
        wr = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        return wr
    
    @staticmethod
    def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Commodity Channel Index.
        
        Args:
            df: DataFrame with high, low, close
            period: Lookback period
            
        Returns:
            CCI series
        """
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        
        cci = (tp - sma) / (0.015 * mad)
        return cci
    
    @staticmethod
    def momentum(data: pd.Series, period: int = 10) -> pd.Series:
        """
        Price Momentum.
        
        Args:
            data: Price series
            period: Lookback period
            
        Returns:
            Momentum series
        """
        return data.diff(period)
    
    @staticmethod
    def roc(data: pd.Series, period: int = 10) -> pd.Series:
        """
        Rate of Change.
        
        Args:
            data: Price series
            period: Lookback period
            
        Returns:
            ROC series (percentage)
        """
        return ((data - data.shift(period)) / data.shift(period)) * 100
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                        VOLATILITY INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def bollinger_bands(
        data: pd.Series, 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands.
        
        Args:
            data: Price series
            period: SMA period
            std_dev: Standard deviation multiplier
            
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return upper, middle, lower
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Average True Range.
        
        Args:
            df: DataFrame with high, low, close
            period: Lookback period
            
        Returns:
            ATR series
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def keltner_channels(
        df: pd.DataFrame, 
        period: int = 20, 
        multiplier: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Keltner Channels.
        
        Args:
            df: DataFrame with OHLC data
            period: EMA period
            multiplier: ATR multiplier
            
        Returns:
            Tuple of (Upper channel, Middle (EMA), Lower channel)
        """
        close = df['close']
        
        middle = close.ewm(span=period, adjust=False).mean()
        atr = TechnicalIndicators.atr(df, period)
        
        upper = middle + (multiplier * atr)
        lower = middle - (multiplier * atr)
        
        return upper, middle, lower
    
    @staticmethod
    def donchian_channels(
        df: pd.DataFrame, 
        period: int = 20
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Donchian Channels.
        
        Args:
            df: DataFrame with high, low
            period: Lookback period
            
        Returns:
            Tuple of (Upper, Middle, Lower)
        """
        upper = df['high'].rolling(window=period).max()
        lower = df['low'].rolling(window=period).min()
        middle = (upper + lower) / 2
        
        return upper, middle, lower
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                          VOLUME INDICATORS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        """
        On-Balance Volume.
        
        Args:
            df: DataFrame with close and volume
            
        Returns:
            OBV series
        """
        close = df['close']
        volume = df['volume']
        
        direction = np.where(close > close.shift(1), 1,
                    np.where(close < close.shift(1), -1, 0))
        
        obv = (direction * volume).cumsum()
        return pd.Series(obv, index=df.index)
    
    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """
        Volume Weighted Average Price.
        
        Args:
            df: DataFrame with high, low, close, volume
            
        Returns:
            VWAP series
        """
        tp = (df['high'] + df['low'] + df['close']) / 3
        vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
        
        return vwap
    
    @staticmethod
    def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Money Flow Index.
        
        Args:
            df: DataFrame with OHLCV data
            period: Lookback period
            
        Returns:
            MFI series (0-100 scale)
        """
        tp = (df['high'] + df['low'] + df['close']) / 3
        raw_mf = tp * df['volume']
        
        positive_mf = raw_mf.where(tp > tp.shift(1), 0)
        negative_mf = raw_mf.where(tp < tp.shift(1), 0)
        
        positive_sum = positive_mf.rolling(window=period).sum()
        negative_sum = negative_mf.rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + positive_sum / negative_sum))
        return mfi
    
    @staticmethod
    def adl(df: pd.DataFrame) -> pd.Series:
        """
        Accumulation/Distribution Line.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            A/D Line series
        """
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.fillna(0)
        
        adl = (clv * volume).cumsum()
        return adl
    
    @staticmethod
    def chaikin_oscillator(
        df: pd.DataFrame, 
        fast: int = 3, 
        slow: int = 10
    ) -> pd.Series:
        """
        Chaikin Oscillator.
        
        Args:
            df: DataFrame with OHLCV data
            fast: Fast EMA period
            slow: Slow EMA period
            
        Returns:
            Chaikin Oscillator series
        """
        adl = TechnicalIndicators.adl(df)
        
        fast_ema = adl.ewm(span=fast, adjust=False).mean()
        slow_ema = adl.ewm(span=slow, adjust=False).mean()
        
        return fast_ema - slow_ema
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                          SIGNAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def analyze_all(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate all indicators and provide analysis.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with all indicators and signals
        """
        close = df['close']
        
        # Trend
        ema_10 = cls.ema(close, 10)
        ema_30 = cls.ema(close, 30)
        ema_100 = cls.ema(close, 100)
        macd_line, signal_line, histogram = cls.macd(close)
        
        # Momentum
        rsi = cls.rsi(close)
        stoch_k, stoch_d = cls.stochastic(df)
        williams = cls.williams_r(df)
        cci = cls.cci(df)
        
        # Volatility
        bb_upper, bb_middle, bb_lower = cls.bollinger_bands(close)
        atr = cls.atr(df)
        
        # Volume
        obv = cls.obv(df)
        mfi = cls.mfi(df)
        
        # Get latest values
        latest = len(df) - 1
        
        # Trend analysis
        uptrend = ema_10.iloc[latest] > ema_30.iloc[latest]
        strong_trend = close.iloc[latest] > ema_100.iloc[latest] if uptrend else close.iloc[latest] < ema_100.iloc[latest]
        
        # RSI analysis
        rsi_value = rsi.iloc[latest]
        rsi_signal = "oversold" if rsi_value < 30 else "overbought" if rsi_value > 70 else "neutral"
        
        # MACD analysis
        macd_bullish = histogram.iloc[latest] > 0 and histogram.iloc[latest] > histogram.iloc[latest-1]
        
        # Bollinger analysis
        bb_position = (close.iloc[latest] - bb_lower.iloc[latest]) / (bb_upper.iloc[latest] - bb_lower.iloc[latest])
        
        return {
            "trend": {
                "ema_10": ema_10.iloc[latest],
                "ema_30": ema_30.iloc[latest],
                "ema_100": ema_100.iloc[latest],
                "direction": "bullish" if uptrend else "bearish",
                "strength": "strong" if strong_trend else "weak",
            },
            "momentum": {
                "rsi": rsi_value,
                "rsi_signal": rsi_signal,
                "stoch_k": stoch_k.iloc[latest],
                "stoch_d": stoch_d.iloc[latest],
                "williams_r": williams.iloc[latest],
                "cci": cci.iloc[latest],
            },
            "volatility": {
                "bb_upper": bb_upper.iloc[latest],
                "bb_middle": bb_middle.iloc[latest],
                "bb_lower": bb_lower.iloc[latest],
                "bb_position": bb_position,
                "atr": atr.iloc[latest],
                "atr_percent": (atr.iloc[latest] / close.iloc[latest]) * 100,
            },
            "volume": {
                "obv": obv.iloc[latest],
                "obv_trend": "up" if obv.iloc[latest] > obv.iloc[latest-5] else "down",
                "mfi": mfi.iloc[latest],
            },
            "macd": {
                "line": macd_line.iloc[latest],
                "signal": signal_line.iloc[latest],
                "histogram": histogram.iloc[latest],
                "bullish": macd_bullish,
            },
            "signals": {
                "trend_signal": "buy" if uptrend and strong_trend else "sell" if not uptrend and strong_trend else "hold",
                "rsi_signal": "buy" if rsi_value < 30 else "sell" if rsi_value > 70 else "hold",
                "macd_signal": "buy" if macd_bullish else "sell",
            }
        }
    
    @classmethod
    def get_confluence_score(cls, df: pd.DataFrame) -> float:
        """
        Calculate confluence score based on multiple indicators.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Score from -100 (strong sell) to +100 (strong buy)
        """
        analysis = cls.analyze_all(df)
        
        score = 0.0
        
        # Trend contribution (weight: 30%)
        if analysis["trend"]["direction"] == "bullish":
            score += 15
            if analysis["trend"]["strength"] == "strong":
                score += 15
        else:
            score -= 15
            if analysis["trend"]["strength"] == "strong":
                score -= 15
        
        # RSI contribution (weight: 20%)
        rsi = analysis["momentum"]["rsi"]
        if rsi < 30:
            score += 20
        elif rsi > 70:
            score -= 20
        elif rsi < 45:
            score += 10
        elif rsi > 55:
            score -= 10
        
        # MACD contribution (weight: 20%)
        if analysis["macd"]["bullish"]:
            score += 20
        else:
            score -= 20
        
        # Bollinger position (weight: 15%)
        bb_pos = analysis["volatility"]["bb_position"]
        if bb_pos < 0.2:
            score += 15  # Near lower band - oversold
        elif bb_pos > 0.8:
            score -= 15  # Near upper band - overbought
        
        # Volume confirmation (weight: 15%)
        if analysis["volume"]["obv_trend"] == "up" and analysis["trend"]["direction"] == "bullish":
            score += 15
        elif analysis["volume"]["obv_trend"] == "down" and analysis["trend"]["direction"] == "bearish":
            score -= 15
        
        return max(-100, min(100, score))


if __name__ == "__main__":
    # Test indicators
    import yfinance as yf
    
    print("Testing Technical Indicators...")
    
    # Fetch test data
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="6mo", interval="1d")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Run analysis
    ti = TechnicalIndicators()
    analysis = ti.analyze_all(df)
    
    print("\n=== Trend Analysis ===")
    print(f"Direction: {analysis['trend']['direction']}")
    print(f"Strength: {analysis['trend']['strength']}")
    print(f"EMA 10/30/100: {analysis['trend']['ema_10']:.2f} / {analysis['trend']['ema_30']:.2f} / {analysis['trend']['ema_100']:.2f}")
    
    print("\n=== Momentum ===")
    print(f"RSI: {analysis['momentum']['rsi']:.2f} ({analysis['momentum']['rsi_signal']})")
    print(f"Stochastic K/D: {analysis['momentum']['stoch_k']:.2f} / {analysis['momentum']['stoch_d']:.2f}")
    
    print("\n=== Volatility ===")
    print(f"BB Position: {analysis['volatility']['bb_position']:.2%}")
    print(f"ATR: {analysis['volatility']['atr']:.2f} ({analysis['volatility']['atr_percent']:.2f}%)")
    
    print("\n=== Volume ===")
    print(f"OBV Trend: {analysis['volume']['obv_trend']}")
    print(f"MFI: {analysis['volume']['mfi']:.2f}")
    
    print("\n=== Confluence Score ===")
    score = ti.get_confluence_score(df)
    signal = "STRONG BUY" if score > 50 else "BUY" if score > 20 else "SELL" if score < -20 else "STRONG SELL" if score < -50 else "HOLD"
    print(f"Score: {score:.1f}/100 → {signal}")
