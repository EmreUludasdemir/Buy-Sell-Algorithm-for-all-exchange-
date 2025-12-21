"""
Pattern Recognition Module
==========================
Advanced price action pattern detection based on EPA Strategy.
Includes Smart Money Concepts patterns.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Pattern type enumeration."""
    SFP = "swing_failure_pattern"
    BREAKER_BLOCK = "breaker_block"
    MITIGATION_BLOCK = "mitigation_block"
    ORDER_BLOCK = "order_block"
    FAIR_VALUE_GAP = "fair_value_gap"
    EQUAL_HIGHS = "equal_highs"
    EQUAL_LOWS = "equal_lows"
    SUPPLY_ZONE = "supply_zone"
    DEMAND_ZONE = "demand_zone"
    ENGULFING = "engulfing"
    DOJI = "doji"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"


@dataclass
class Pattern:
    """Detected pattern information."""
    type: PatternType
    direction: str  # 'bullish' or 'bearish'
    index: int  # Bar index where pattern was detected
    price_level: float
    strength: float  # 0.0 to 1.0
    zone_high: Optional[float] = None
    zone_low: Optional[float] = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "direction": self.direction,
            "index": self.index,
            "price_level": self.price_level,
            "strength": self.strength,
            "zone_high": self.zone_high,
            "zone_low": self.zone_low,
            "description": self.description,
        }


class PatternRecognition:
    """
    Advanced pattern recognition for trading signals.
    
    Based on EPA Strategy patterns and Smart Money Concepts:
    - Swing Failure Pattern (SFP)
    - Breaker Block
    - Mitigation Block
    - Order Block
    - Fair Value Gap
    - Equal Highs/Lows
    - Supply/Demand Zones
    - Classic Candlestick Patterns
    """
    
    def __init__(
        self,
        pivot_lookback: int = 5,
        pivot_lookforward: int = 5,
        zone_atr_multiplier: float = 0.5,
        eq_threshold_pct: float = 0.1
    ):
        """
        Initialize pattern recognition.
        
        Args:
            pivot_lookback: Bars to look back for pivot detection
            pivot_lookforward: Bars to look forward for pivot confirmation
            zone_atr_multiplier: ATR multiplier for zone sizing
            eq_threshold_pct: Threshold percentage for equal highs/lows
        """
        self.pivot_lookback = pivot_lookback
        self.pivot_lookforward = pivot_lookforward
        self.zone_atr_multiplier = zone_atr_multiplier
        self.eq_threshold_pct = eq_threshold_pct
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                           PIVOT DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def find_pivot_highs(self, df: pd.DataFrame) -> pd.Series:
        """
        Find pivot high points.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Series with pivot high values (NaN where no pivot)
        """
        high = df['high']
        pivots = pd.Series(index=df.index, dtype=float)
        
        for i in range(self.pivot_lookback, len(df) - self.pivot_lookforward):
            # Check if this is the highest in the lookback and lookforward range
            left_high = high.iloc[i - self.pivot_lookback:i].max()
            right_high = high.iloc[i + 1:i + self.pivot_lookforward + 1].max()
            
            if high.iloc[i] >= left_high and high.iloc[i] >= right_high:
                pivots.iloc[i] = high.iloc[i]
        
        return pivots
    
    def find_pivot_lows(self, df: pd.DataFrame) -> pd.Series:
        """
        Find pivot low points.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Series with pivot low values (NaN where no pivot)
        """
        low = df['low']
        pivots = pd.Series(index=df.index, dtype=float)
        
        for i in range(self.pivot_lookback, len(df) - self.pivot_lookforward):
            left_low = low.iloc[i - self.pivot_lookback:i].min()
            right_low = low.iloc[i + 1:i + self.pivot_lookforward + 1].min()
            
            if low.iloc[i] <= left_low and low.iloc[i] <= right_low:
                pivots.iloc[i] = low.iloc[i]
        
        return pivots
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                    SWING FAILURE PATTERN (SFP)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_sfp(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect Swing Failure Patterns.
        
        SFP occurs when price wicks beyond a swing high/low but closes back 
        inside the range, trapping breakout traders.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of detected SFP patterns
        """
        patterns = []
        
        pivot_highs = self.find_pivot_highs(df)
        pivot_lows = self.find_pivot_lows(df)
        
        # Look for recent pivots that might be tested
        pivot_high_levels = pivot_highs.dropna().tail(10)
        pivot_low_levels = pivot_lows.dropna().tail(10)
        
        for i in range(self.pivot_lookback * 2, len(df)):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            open_price = df['open'].iloc[i]
            
            # Bearish SFP: Wick above pivot high, close below
            for pivot_idx, pivot_level in pivot_high_levels.items():
                if pivot_idx >= i - self.pivot_lookforward:
                    continue  # Skip too recent pivots
                    
                if high > pivot_level and close < pivot_level:
                    # Calculate wick ratio
                    body = abs(close - open_price)
                    upper_wick = high - max(open_price, close)
                    
                    if upper_wick > body * 0.5:  # Significant wick
                        strength = min(1.0, upper_wick / body if body > 0 else 0.5)
                        patterns.append(Pattern(
                            type=PatternType.SFP,
                            direction="bearish",
                            index=i,
                            price_level=pivot_level,
                            strength=strength,
                            zone_high=high,
                            zone_low=pivot_level,
                            description=f"Bearish SFP: Wick above {pivot_level:.2f}, closed below"
                        ))
            
            # Bullish SFP: Wick below pivot low, close above
            for pivot_idx, pivot_level in pivot_low_levels.items():
                if pivot_idx >= i - self.pivot_lookforward:
                    continue
                    
                if low < pivot_level and close > pivot_level:
                    body = abs(close - open_price)
                    lower_wick = min(open_price, close) - low
                    
                    if lower_wick > body * 0.5:
                        strength = min(1.0, lower_wick / body if body > 0 else 0.5)
                        patterns.append(Pattern(
                            type=PatternType.SFP,
                            direction="bullish",
                            index=i,
                            price_level=pivot_level,
                            strength=strength,
                            zone_high=pivot_level,
                            zone_low=low,
                            description=f"Bullish SFP: Wick below {pivot_level:.2f}, closed above"
                        ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                          ORDER BLOCK DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_order_blocks(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect Order Blocks.
        
        Order Block is the last opposing candle before an impulsive move.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of detected order blocks
        """
        patterns = []
        
        for i in range(3, len(df) - 1):
            # Check for impulsive move (large candle)
            current_range = df['high'].iloc[i] - df['low'].iloc[i]
            avg_range = (df['high'] - df['low']).iloc[i-5:i].mean()
            
            if current_range < avg_range * 1.5:
                continue  # Not impulsive enough
            
            # Bullish Order Block: Bearish candle before bullish impulsive move
            if df['close'].iloc[i] > df['open'].iloc[i]:  # Current is bullish
                if df['close'].iloc[i-1] < df['open'].iloc[i-1]:  # Previous is bearish
                    patterns.append(Pattern(
                        type=PatternType.ORDER_BLOCK,
                        direction="bullish",
                        index=i-1,
                        price_level=(df['high'].iloc[i-1] + df['low'].iloc[i-1]) / 2,
                        strength=min(1.0, current_range / avg_range / 2),
                        zone_high=df['high'].iloc[i-1],
                        zone_low=df['low'].iloc[i-1],
                        description="Bullish Order Block"
                    ))
            
            # Bearish Order Block: Bullish candle before bearish impulsive move
            elif df['close'].iloc[i] < df['open'].iloc[i]:  # Current is bearish
                if df['close'].iloc[i-1] > df['open'].iloc[i-1]:  # Previous is bullish
                    patterns.append(Pattern(
                        type=PatternType.ORDER_BLOCK,
                        direction="bearish",
                        index=i-1,
                        price_level=(df['high'].iloc[i-1] + df['low'].iloc[i-1]) / 2,
                        strength=min(1.0, current_range / avg_range / 2),
                        zone_high=df['high'].iloc[i-1],
                        zone_low=df['low'].iloc[i-1],
                        description="Bearish Order Block"
                    ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         FAIR VALUE GAP (FVG)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect Fair Value Gaps (Imbalances).
        
        FVG occurs when there's a gap between candle wicks, indicating
        an inefficiency that price may return to fill.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of detected FVGs
        """
        patterns = []
        
        for i in range(2, len(df)):
            # Bullish FVG: Gap between candle 1's high and candle 3's low
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                avg_range = (df['high'] - df['low']).iloc[i-5:i].mean()
                
                if gap_size > avg_range * 0.1:  # Significant gap
                    patterns.append(Pattern(
                        type=PatternType.FAIR_VALUE_GAP,
                        direction="bullish",
                        index=i-1,
                        price_level=(df['low'].iloc[i] + df['high'].iloc[i-2]) / 2,
                        strength=min(1.0, gap_size / avg_range),
                        zone_high=df['low'].iloc[i],
                        zone_low=df['high'].iloc[i-2],
                        description=f"Bullish FVG: Gap from {df['high'].iloc[i-2]:.2f} to {df['low'].iloc[i]:.2f}"
                    ))
            
            # Bearish FVG: Gap between candle 3's high and candle 1's low
            if df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                avg_range = (df['high'] - df['low']).iloc[i-5:i].mean()
                
                if gap_size > avg_range * 0.1:
                    patterns.append(Pattern(
                        type=PatternType.FAIR_VALUE_GAP,
                        direction="bearish",
                        index=i-1,
                        price_level=(df['high'].iloc[i] + df['low'].iloc[i-2]) / 2,
                        strength=min(1.0, gap_size / avg_range),
                        zone_high=df['low'].iloc[i-2],
                        zone_low=df['high'].iloc[i],
                        description=f"Bearish FVG: Gap from {df['high'].iloc[i]:.2f} to {df['low'].iloc[i-2]:.2f}"
                    ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                         EQUAL HIGHS/LOWS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_equal_highs_lows(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect Equal Highs and Equal Lows (liquidity pools).
        
        Multiple touches at similar levels indicate stop loss clusters.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of detected EQH/EQL patterns
        """
        patterns = []
        
        pivot_highs = self.find_pivot_highs(df).dropna()
        pivot_lows = self.find_pivot_lows(df).dropna()
        
        # Find equal highs
        for i, (idx1, level1) in enumerate(pivot_highs.items()):
            for idx2, level2 in list(pivot_highs.items())[i+1:]:
                if idx2 - idx1 < 5:  # Too close
                    continue
                    
                # Check if levels are within threshold
                threshold = level1 * (self.eq_threshold_pct / 100)
                if abs(level1 - level2) <= threshold:
                    patterns.append(Pattern(
                        type=PatternType.EQUAL_HIGHS,
                        direction="bearish",  # EQH suggests bearish bias (stop hunt potential)
                        index=idx2,
                        price_level=(level1 + level2) / 2,
                        strength=0.7,
                        zone_high=max(level1, level2),
                        zone_low=min(level1, level2),
                        description=f"Equal Highs at ~{(level1 + level2) / 2:.2f}"
                    ))
        
        # Find equal lows
        for i, (idx1, level1) in enumerate(pivot_lows.items()):
            for idx2, level2 in list(pivot_lows.items())[i+1:]:
                if idx2 - idx1 < 5:
                    continue
                    
                threshold = level1 * (self.eq_threshold_pct / 100)
                if abs(level1 - level2) <= threshold:
                    patterns.append(Pattern(
                        type=PatternType.EQUAL_LOWS,
                        direction="bullish",  # EQL suggests bullish bias (stop hunt potential)
                        index=idx2,
                        price_level=(level1 + level2) / 2,
                        strength=0.7,
                        zone_high=max(level1, level2),
                        zone_low=min(level1, level2),
                        description=f"Equal Lows at ~{(level1 + level2) / 2:.2f}"
                    ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                      SUPPLY/DEMAND ZONES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_supply_demand_zones(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect Supply and Demand Zones.
        
        Based on areas where price moved impulsively away,
        indicating strong institutional interest.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of detected supply/demand zones
        """
        patterns = []
        atr = self._calculate_atr(df, 14)
        
        for i in range(3, len(df) - 2):
            # Check for base (consolidation) followed by impulsive move
            range_i = df['high'].iloc[i] - df['low'].iloc[i]
            range_next = df['high'].iloc[i+1] - df['low'].iloc[i+1]
            
            # Small range followed by large range
            if range_i < atr.iloc[i] * 0.5 and range_next > atr.iloc[i] * 1.5:
                # Demand Zone: Impulsive move up
                if df['close'].iloc[i+1] > df['open'].iloc[i+1]:
                    patterns.append(Pattern(
                        type=PatternType.DEMAND_ZONE,
                        direction="bullish",
                        index=i,
                        price_level=(df['high'].iloc[i] + df['low'].iloc[i]) / 2,
                        strength=min(1.0, range_next / atr.iloc[i]),
                        zone_high=df['high'].iloc[i],
                        zone_low=df['low'].iloc[i],
                        description="Demand Zone (Support)"
                    ))
                
                # Supply Zone: Impulsive move down
                elif df['close'].iloc[i+1] < df['open'].iloc[i+1]:
                    patterns.append(Pattern(
                        type=PatternType.SUPPLY_ZONE,
                        direction="bearish",
                        index=i,
                        price_level=(df['high'].iloc[i] + df['low'].iloc[i]) / 2,
                        strength=min(1.0, range_next / atr.iloc[i]),
                        zone_high=df['high'].iloc[i],
                        zone_low=df['low'].iloc[i],
                        description="Supply Zone (Resistance)"
                    ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                    CLASSIC CANDLESTICK PATTERNS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_engulfing(self, df: pd.DataFrame) -> List[Pattern]:
        """Detect Bullish/Bearish Engulfing patterns."""
        patterns = []
        
        for i in range(1, len(df)):
            prev_open = df['open'].iloc[i-1]
            prev_close = df['close'].iloc[i-1]
            curr_open = df['open'].iloc[i]
            curr_close = df['close'].iloc[i]
            
            prev_body = abs(prev_close - prev_open)
            curr_body = abs(curr_close - curr_open)
            
            if curr_body < prev_body * 1.1:  # Current must be larger
                continue
            
            # Bullish Engulfing
            if (prev_close < prev_open and  # Previous bearish
                curr_close > curr_open and   # Current bullish
                curr_open <= prev_close and  # Opens at or below prev close
                curr_close >= prev_open):    # Closes at or above prev open
                
                patterns.append(Pattern(
                    type=PatternType.ENGULFING,
                    direction="bullish",
                    index=i,
                    price_level=curr_close,
                    strength=min(1.0, curr_body / prev_body / 2),
                    description="Bullish Engulfing"
                ))
            
            # Bearish Engulfing
            elif (prev_close > prev_open and  # Previous bullish
                  curr_close < curr_open and   # Current bearish
                  curr_open >= prev_close and  # Opens at or above prev close
                  curr_close <= prev_open):    # Closes at or below prev open
                
                patterns.append(Pattern(
                    type=PatternType.ENGULFING,
                    direction="bearish",
                    index=i,
                    price_level=curr_close,
                    strength=min(1.0, curr_body / prev_body / 2),
                    description="Bearish Engulfing"
                ))
        
        return patterns
    
    def detect_doji(self, df: pd.DataFrame, body_threshold: float = 0.1) -> List[Pattern]:
        """Detect Doji patterns (indecision)."""
        patterns = []
        
        for i in range(len(df)):
            open_price = df['open'].iloc[i]
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            body = abs(close - open_price)
            full_range = high - low
            
            if full_range > 0 and body / full_range < body_threshold:
                patterns.append(Pattern(
                    type=PatternType.DOJI,
                    direction="neutral",
                    index=i,
                    price_level=(open_price + close) / 2,
                    strength=1 - (body / full_range) if full_range > 0 else 0.5,
                    description="Doji (Indecision)"
                ))
        
        return patterns
    
    def detect_hammer_shooting_star(self, df: pd.DataFrame) -> List[Pattern]:
        """Detect Hammer and Shooting Star patterns."""
        patterns = []
        
        for i in range(len(df)):
            open_price = df['open'].iloc[i]
            close = df['close'].iloc[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            body = abs(close - open_price)
            upper_wick = high - max(open_price, close)
            lower_wick = min(open_price, close) - low
            
            if body == 0:
                continue
            
            # Hammer: Small body at top, long lower wick
            if lower_wick >= body * 2 and upper_wick <= body * 0.5:
                patterns.append(Pattern(
                    type=PatternType.HAMMER,
                    direction="bullish",
                    index=i,
                    price_level=close,
                    strength=min(1.0, lower_wick / body / 3),
                    description="Hammer (Bullish reversal)"
                ))
            
            # Shooting Star: Small body at bottom, long upper wick
            elif upper_wick >= body * 2 and lower_wick <= body * 0.5:
                patterns.append(Pattern(
                    type=PatternType.SHOOTING_STAR,
                    direction="bearish",
                    index=i,
                    price_level=close,
                    strength=min(1.0, upper_wick / body / 3),
                    description="Shooting Star (Bearish reversal)"
                ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                          HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    # ═══════════════════════════════════════════════════════════════════════════
    #                          MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_all(self, df: pd.DataFrame) -> Dict[str, List[Pattern]]:
        """
        Run all pattern detection.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Dictionary with all detected patterns by type
        """
        return {
            "sfp": self.detect_sfp(df),
            "order_blocks": self.detect_order_blocks(df),
            "fair_value_gaps": self.detect_fair_value_gaps(df),
            "equal_highs_lows": self.detect_equal_highs_lows(df),
            "supply_demand": self.detect_supply_demand_zones(df),
            "engulfing": self.detect_engulfing(df),
            "doji": self.detect_doji(df),
            "hammer_shooting_star": self.detect_hammer_shooting_star(df),
        }
    
    def get_recent_patterns(
        self, 
        df: pd.DataFrame, 
        lookback: int = 20
    ) -> List[Pattern]:
        """
        Get patterns detected in the last N bars.
        
        Args:
            df: DataFrame with OHLC data
            lookback: Number of bars to look back
            
        Returns:
            List of recent patterns sorted by index
        """
        all_patterns = self.analyze_all(df)
        min_index = len(df) - lookback
        
        recent = []
        for pattern_list in all_patterns.values():
            for pattern in pattern_list:
                if pattern.index >= min_index:
                    recent.append(pattern)
        
        return sorted(recent, key=lambda x: x.index, reverse=True)
    
    def get_pattern_score(self, df: pd.DataFrame, lookback: int = 10) -> Tuple[float, str]:
        """
        Calculate pattern-based trading score.
        
        Args:
            df: DataFrame with OHLC data
            lookback: Bars to consider for scoring
            
        Returns:
            Tuple of (score from -100 to +100, recommendation)
        """
        recent = self.get_recent_patterns(df, lookback)
        
        bullish_score = 0
        bearish_score = 0
        
        for pattern in recent:
            weight = pattern.strength * (1 - (len(df) - pattern.index) / lookback * 0.5)
            
            if pattern.direction == "bullish":
                bullish_score += weight * 20
            elif pattern.direction == "bearish":
                bearish_score += weight * 20
        
        score = bullish_score - bearish_score
        score = max(-100, min(100, score))
        
        if score > 40:
            signal = "STRONG_BUY"
        elif score > 15:
            signal = "BUY"
        elif score < -40:
            signal = "STRONG_SELL"
        elif score < -15:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        
        return score, signal


if __name__ == "__main__":
    # Test pattern recognition
    import yfinance as yf
    
    print("Testing Pattern Recognition...")
    
    # Fetch test data
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="3mo", interval="1d")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Run analysis
    pr = PatternRecognition()
    patterns = pr.analyze_all(df)
    
    print("\n=== Pattern Detection Results ===")
    for pattern_type, pattern_list in patterns.items():
        if pattern_list:
            print(f"\n{pattern_type.upper()}: {len(pattern_list)} found")
            for p in pattern_list[-3:]:  # Show last 3
                print(f"  - {p.description} at index {p.index} (strength: {p.strength:.2f})")
    
    print("\n=== Recent Patterns (Last 20 bars) ===")
    recent = pr.get_recent_patterns(df, 20)
    for p in recent[:10]:
        print(f"  [{p.type.value}] {p.direction}: {p.description}")
    
    print("\n=== Pattern Score ===")
    score, signal = pr.get_pattern_score(df)
    print(f"Score: {score:.1f} → {signal}")
