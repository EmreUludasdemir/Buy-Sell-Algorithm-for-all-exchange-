"""
Structure Break Detection (BOS/CHoCH)
Identifies Break of Structure and Change of Character.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class StructureBreakDetector:
    """
    Detects market structure breaks for SMC analysis.
    
    BOS (Break of Structure): Continuation pattern
      - Bullish BOS: Price breaks above swing high in uptrend
      - Bearish BOS: Price breaks below swing low in downtrend
    
    CHoCH (Change of Character): Reversal pattern
      - Bullish CHoCH: Price breaks above swing high in downtrend
      - Bearish CHoCH: Price breaks below swing low in uptrend
    """
    
    def __init__(self, swing_length: int = 10):
        self.swing_length = swing_length
    
    def detect(self, df: pd.DataFrame, swings: pd.DataFrame = None) -> pd.DataFrame:
        """
        Detect BOS and CHoCH.
        
        Args:
            df: OHLCV DataFrame
            swings: Optional pre-calculated swing levels DataFrame
            
        Returns:
            DataFrame with BOS and CHOCH columns
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate swings if not provided
        if swings is None:
            swings = self._calculate_swings(df)
        
        # Get swing levels
        swing_high_price = swings.get('swing_high_price', pd.Series(index=df.index))
        swing_low_price = swings.get('swing_low_price', pd.Series(index=df.index))
        
        # Initialize results
        bos = pd.Series(0, index=df.index)
        choch = pd.Series(0, index=df.index)
        
        # Track trend direction
        trend = pd.Series(0, index=df.index)  # 1=up, -1=down
        
        for i in range(self.swing_length, len(df)):
            prev_trend = trend.iloc[i-1] if i > 0 else 0
            
            # Get recent swing levels (shifted to avoid lookahead)
            recent_sh = swing_high_price.iloc[:i].dropna().tail(1)
            recent_sl = swing_low_price.iloc[:i].dropna().tail(1)
            
            if len(recent_sh) == 0 or len(recent_sl) == 0:
                trend.iloc[i] = prev_trend
                continue
            
            last_sh = recent_sh.iloc[-1]
            last_sl = recent_sl.iloc[-1]
            
            # Check for breaks
            if close.iloc[i] > last_sh:
                if prev_trend >= 0:
                    bos.iloc[i] = 1  # Bullish BOS (continuation)
                else:
                    choch.iloc[i] = 1  # Bullish CHoCH (reversal)
                trend.iloc[i] = 1
            elif close.iloc[i] < last_sl:
                if prev_trend <= 0:
                    bos.iloc[i] = -1  # Bearish BOS (continuation)
                else:
                    choch.iloc[i] = -1  # Bearish CHoCH (reversal)
                trend.iloc[i] = -1
            else:
                trend.iloc[i] = prev_trend
        
        return pd.DataFrame({
            'BOS': bos,
            'CHOCH': choch,
            'trend': trend
        }, index=df.index)
    
    def _calculate_swings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate swing points internally."""
        high = df['high']
        low = df['low']
        
        rolling_high = high.rolling(
            window=2 * self.swing_length + 1, 
            center=True
        ).max()
        rolling_low = low.rolling(
            window=2 * self.swing_length + 1, 
            center=True
        ).min()
        
        swing_high = high == rolling_high
        swing_low = low == rolling_low
        
        return pd.DataFrame({
            'swing_high_price': high.where(swing_high).ffill(),
            'swing_low_price': low.where(swing_low).ffill()
        }, index=df.index)


def calculate_bos_choch(df: pd.DataFrame, swings: pd.DataFrame = None, swing_length: int = 10) -> pd.DataFrame:
    """Convenience function for structure break detection."""
    detector = StructureBreakDetector(swing_length=swing_length)
    return detector.detect(df, swings)
