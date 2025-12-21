"""
Multi-Timeframe Analysis Module
===============================
Analyze multiple timeframes to confirm trading signals.
Based on EPA Strategy dashboard concept.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import yfinance as yf

from .indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class TimeframeBias(Enum):
    """Timeframe bias enumeration."""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe."""
    timeframe: str
    bias: TimeframeBias
    trend_direction: str
    trend_strength: float  # 0-100
    rsi: float
    macd_histogram: float
    above_ema: bool
    volume_trend: str
    key_levels: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeframe": self.timeframe,
            "bias": self.bias.value,
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
            "rsi": self.rsi,
            "macd_histogram": self.macd_histogram,
            "above_ema": self.above_ema,
            "volume_trend": self.volume_trend,
            "key_levels": self.key_levels,
        }


class MultiTimeframeAnalyzer:
    """
    Multi-timeframe analysis for trading signals.
    
    Analyzes multiple timeframes to find confluence:
    - Weekly (1W) - Major trend direction
    - Daily (1D) - Primary trend
    - 4 Hour (4H) - Short-term structure
    - 1 Hour (1H) - Entry timing
    - 15 Minute (15m) - Fine-tuned entries
    """
    
    # Timeframe configurations
    TIMEFRAMES = {
        "1W": {"period": "2y", "interval": "1wk", "weight": 0.25},
        "1D": {"period": "1y", "interval": "1d", "weight": 0.25},
        "4H": {"period": "60d", "interval": "1h", "weight": 0.20},  # Note: yfinance max is 1h
        "1H": {"period": "30d", "interval": "1h", "weight": 0.15},
        "15m": {"period": "7d", "interval": "15m", "weight": 0.15},
    }
    
    def __init__(
        self,
        ema_fast: int = 10,
        ema_slow: int = 30,
        ema_trend: int = 100,
        rsi_period: int = 14
    ):
        """
        Initialize the analyzer.
        
        Args:
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            ema_trend: Trend EMA period
            rsi_period: RSI period
        """
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.rsi_period = rsi_period
        self.indicators = TechnicalIndicators()
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def fetch_timeframe_data(
        self, 
        ticker: str, 
        timeframe: str
    ) -> pd.DataFrame:
        """
        Fetch data for a specific timeframe.
        
        Args:
            ticker: Stock/crypto symbol
            timeframe: Timeframe key (e.g., '1D', '4H')
            
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{ticker}_{timeframe}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        config = self.TIMEFRAMES.get(timeframe)
        if not config:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=config["period"], interval=config["interval"])
            
            if df.empty:
                logger.warning(f"No data for {ticker} {timeframe}")
                return pd.DataFrame()
            
            # Standardize columns
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df = df.reset_index()
            
            self._cache[cache_key] = df
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {timeframe} data for {ticker}: {e}")
            return pd.DataFrame()
    
    def analyze_timeframe(
        self, 
        ticker: str, 
        timeframe: str
    ) -> Optional[TimeframeAnalysis]:
        """
        Analyze a single timeframe.
        
        Args:
            ticker: Stock/crypto symbol
            timeframe: Timeframe to analyze
            
        Returns:
            TimeframeAnalysis or None if data unavailable
        """
        df = self.fetch_timeframe_data(ticker, timeframe)
        
        if df.empty or len(df) < self.ema_trend:
            return None
        
        close = df['close']
        
        # Calculate indicators
        ema_fast = self.indicators.ema(close, self.ema_fast)
        ema_slow = self.indicators.ema(close, self.ema_slow)
        ema_trend = self.indicators.ema(close, self.ema_trend)
        rsi = self.indicators.rsi(close, self.rsi_period)
        macd_line, signal_line, histogram = self.indicators.macd(close)
        obv = self.indicators.obv(df)
        
        # Get latest values
        latest = len(df) - 1
        current_close = close.iloc[latest]
        
        # Determine trend
        fast_above_slow = ema_fast.iloc[latest] > ema_slow.iloc[latest]
        above_trend_ema = current_close > ema_trend.iloc[latest]
        
        # Trend direction
        if fast_above_slow and above_trend_ema:
            trend_direction = "bullish"
        elif not fast_above_slow and not above_trend_ema:
            trend_direction = "bearish"
        else:
            trend_direction = "neutral"
        
        # Trend strength (based on EMA separation)
        ema_separation = abs(ema_fast.iloc[latest] - ema_slow.iloc[latest])
        avg_price = current_close
        trend_strength = min(100, (ema_separation / avg_price) * 1000)
        
        # Volume trend
        obv_current = obv.iloc[latest]
        obv_5_ago = obv.iloc[latest - 5] if latest >= 5 else obv.iloc[0]
        volume_trend = "up" if obv_current > obv_5_ago else "down"
        
        # RSI bias
        rsi_value = rsi.iloc[latest]
        
        # Determine overall bias
        bullish_signals = sum([
            fast_above_slow,
            above_trend_ema,
            histogram.iloc[latest] > 0,
            rsi_value > 50,
            volume_trend == "up" and trend_direction == "bullish"
        ])
        
        if bullish_signals >= 4:
            bias = TimeframeBias.STRONG_BULLISH
        elif bullish_signals >= 3:
            bias = TimeframeBias.BULLISH
        elif bullish_signals <= 1:
            bias = TimeframeBias.STRONG_BEARISH
        elif bullish_signals == 2:
            if trend_direction == "bearish":
                bias = TimeframeBias.BEARISH
            else:
                bias = TimeframeBias.NEUTRAL
        else:
            bias = TimeframeBias.NEUTRAL
        
        # Key levels
        bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(close)
        
        key_levels = {
            "ema_fast": round(ema_fast.iloc[latest], 2),
            "ema_slow": round(ema_slow.iloc[latest], 2),
            "ema_trend": round(ema_trend.iloc[latest], 2),
            "bb_upper": round(bb_upper.iloc[latest], 2),
            "bb_middle": round(bb_middle.iloc[latest], 2),
            "bb_lower": round(bb_lower.iloc[latest], 2),
            "recent_high": round(df['high'].tail(20).max(), 2),
            "recent_low": round(df['low'].tail(20).min(), 2),
        }
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            bias=bias,
            trend_direction=trend_direction,
            trend_strength=round(trend_strength, 1),
            rsi=round(rsi_value, 1),
            macd_histogram=round(histogram.iloc[latest], 4),
            above_ema=above_trend_ema,
            volume_trend=volume_trend,
            key_levels=key_levels,
        )
    
    def analyze_all_timeframes(self, ticker: str) -> Dict[str, TimeframeAnalysis]:
        """
        Analyze all configured timeframes.
        
        Args:
            ticker: Stock/crypto symbol
            
        Returns:
            Dictionary of timeframe -> analysis
        """
        results = {}
        
        for tf in self.TIMEFRAMES.keys():
            analysis = self.analyze_timeframe(ticker, tf)
            if analysis:
                results[tf] = analysis
            else:
                logger.warning(f"Could not analyze {tf} for {ticker}")
        
        return results
    
    def get_confluence_score(self, ticker: str) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculate overall confluence score across timeframes.
        
        Args:
            ticker: Stock/crypto symbol
            
        Returns:
            Tuple of (score -100 to +100, signal, detailed breakdown)
        """
        analyses = self.analyze_all_timeframes(ticker)
        
        if not analyses:
            return 0.0, "NO_DATA", {}
        
        total_weight = 0
        weighted_score = 0
        
        breakdown = {}
        
        for tf, analysis in analyses.items():
            weight = self.TIMEFRAMES[tf]["weight"]
            
            # Convert bias to score
            bias_scores = {
                TimeframeBias.STRONG_BULLISH: 100,
                TimeframeBias.BULLISH: 50,
                TimeframeBias.NEUTRAL: 0,
                TimeframeBias.BEARISH: -50,
                TimeframeBias.STRONG_BEARISH: -100,
            }
            
            tf_score = bias_scores.get(analysis.bias, 0)
            weighted_score += tf_score * weight
            total_weight += weight
            
            breakdown[tf] = {
                "bias": analysis.bias.value,
                "score": tf_score,
                "weight": weight,
                "contribution": round(tf_score * weight, 1),
            }
        
        # Normalize score
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        final_score = round(final_score, 1)
        
        # Determine signal
        if final_score >= 60:
            signal = "STRONG_BUY"
        elif final_score >= 30:
            signal = "BUY"
        elif final_score <= -60:
            signal = "STRONG_SELL"
        elif final_score <= -30:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return final_score, signal, breakdown
    
    def get_entry_timing(self, ticker: str) -> Dict[str, Any]:
        """
        Get entry timing based on lower timeframe alignment.
        
        Uses higher timeframes for direction and lower for entry.
        
        Args:
            ticker: Stock/crypto symbol
            
        Returns:
            Entry timing analysis
        """
        analyses = self.analyze_all_timeframes(ticker)
        
        if len(analyses) < 2:
            return {"status": "insufficient_data", "can_enter": False}
        
        # Check higher timeframe alignment
        htf_bullish = 0
        htf_bearish = 0
        
        for tf in ["1W", "1D"]:
            if tf in analyses:
                if analyses[tf].bias in [TimeframeBias.BULLISH, TimeframeBias.STRONG_BULLISH]:
                    htf_bullish += 1
                elif analyses[tf].bias in [TimeframeBias.BEARISH, TimeframeBias.STRONG_BEARISH]:
                    htf_bearish += 1
        
        # Determine HTF direction
        if htf_bullish > htf_bearish:
            htf_direction = "bullish"
        elif htf_bearish > htf_bullish:
            htf_direction = "bearish"
        else:
            htf_direction = "neutral"
        
        # Check LTF alignment
        ltf_aligned = False
        ltf_analysis = None
        
        for tf in ["1H", "15m"]:
            if tf in analyses:
                ltf_analysis = analyses[tf]
                
                if htf_direction == "bullish" and ltf_analysis.bias in [TimeframeBias.BULLISH, TimeframeBias.STRONG_BULLISH]:
                    ltf_aligned = True
                elif htf_direction == "bearish" and ltf_analysis.bias in [TimeframeBias.BEARISH, TimeframeBias.STRONG_BEARISH]:
                    ltf_aligned = True
                break
        
        # Entry decision
        can_enter = htf_direction != "neutral" and ltf_aligned
        
        return {
            "htf_direction": htf_direction,
            "ltf_aligned": ltf_aligned,
            "can_enter": can_enter,
            "recommended_direction": htf_direction if can_enter else "wait",
            "ltf_rsi": ltf_analysis.rsi if ltf_analysis else None,
            "entry_zone": self._get_entry_zone(analyses, htf_direction),
        }
    
    def _get_entry_zone(
        self, 
        analyses: Dict[str, TimeframeAnalysis], 
        direction: str
    ) -> Optional[Dict[str, float]]:
        """Calculate optimal entry zone based on key levels."""
        if "1H" not in analyses:
            return None
        
        levels = analyses["1H"].key_levels
        
        if direction == "bullish":
            # Entry near lower levels in uptrend
            return {
                "ideal_entry": levels.get("ema_fast", 0),
                "support_1": levels.get("ema_slow", 0),
                "support_2": levels.get("bb_lower", 0),
            }
        elif direction == "bearish":
            # Entry near upper levels in downtrend
            return {
                "ideal_entry": levels.get("ema_fast", 0),
                "resistance_1": levels.get("ema_slow", 0),
                "resistance_2": levels.get("bb_upper", 0),
            }
        
        return None
    
    def generate_dashboard(self, ticker: str) -> Dict[str, Any]:
        """
        Generate a complete MTF dashboard.
        
        Args:
            ticker: Stock/crypto symbol
            
        Returns:
            Complete dashboard data
        """
        analyses = self.analyze_all_timeframes(ticker)
        score, signal, breakdown = self.get_confluence_score(ticker)
        entry_timing = self.get_entry_timing(ticker)
        
        # Fetch current price
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get("currentPrice", info.get("regularMarketPrice", 0))
        except:
            current_price = 0
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "confluence_score": score,
            "signal": signal,
            "breakdown": breakdown,
            "entry_timing": entry_timing,
            "timeframes": {tf: a.to_dict() for tf, a in analyses.items()},
            "summary": self._generate_summary(analyses, score, signal),
        }
    
    def _generate_summary(
        self, 
        analyses: Dict[str, TimeframeAnalysis],
        score: float,
        signal: str
    ) -> str:
        """Generate human-readable summary."""
        if not analyses:
            return "Insufficient data for analysis."
        
        # Count biases
        bullish = sum(1 for a in analyses.values() if "bullish" in a.bias.value)
        bearish = sum(1 for a in analyses.values() if "bearish" in a.bias.value)
        
        summary_parts = []
        
        # Overall trend
        if score > 50:
            summary_parts.append(f"Strong bullish confluence ({bullish}/{len(analyses)} TFs aligned).")
        elif score > 20:
            summary_parts.append(f"Bullish bias across timeframes ({bullish}/{len(analyses)} TFs).")
        elif score < -50:
            summary_parts.append(f"Strong bearish confluence ({bearish}/{len(analyses)} TFs aligned).")
        elif score < -20:
            summary_parts.append(f"Bearish bias across timeframes ({bearish}/{len(analyses)} TFs).")
        else:
            summary_parts.append("Mixed signals - no clear direction.")
        
        # Key levels
        if "1D" in analyses:
            daily = analyses["1D"]
            if daily.rsi > 70:
                summary_parts.append("Daily RSI overbought - caution for longs.")
            elif daily.rsi < 30:
                summary_parts.append("Daily RSI oversold - potential reversal zone.")
        
        return " ".join(summary_parts)
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


if __name__ == "__main__":
    # Test MTF analyzer
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Multi-Timeframe Analyzer...")
    
    mtf = MultiTimeframeAnalyzer()
    ticker = "AAPL"
    
    print(f"\n=== MTF Analysis for {ticker} ===")
    
    # Get full dashboard
    dashboard = mtf.generate_dashboard(ticker)
    
    print(f"\nCurrent Price: ${dashboard['current_price']:.2f}")
    print(f"Confluence Score: {dashboard['confluence_score']}")
    print(f"Signal: {dashboard['signal']}")
    
    print("\n--- Timeframe Breakdown ---")
    for tf, data in dashboard['breakdown'].items():
        print(f"{tf}: {data['bias']} (score: {data['score']}, contribution: {data['contribution']})")
    
    print("\n--- Entry Timing ---")
    entry = dashboard['entry_timing']
    print(f"HTF Direction: {entry['htf_direction']}")
    print(f"LTF Aligned: {entry['ltf_aligned']}")
    print(f"Can Enter: {entry['can_enter']}")
    print(f"Recommended: {entry['recommended_direction']}")
    
    print(f"\n--- Summary ---")
    print(dashboard['summary'])
