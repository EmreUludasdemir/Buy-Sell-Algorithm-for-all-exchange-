"""
Swing Point Detection
Identifies significant swing highs and lows for structure analysis.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class SwingPointDetector:
    """
    Detects swing highs and lows using a lookback window.
    
    Swing High: Highest high in window, with lower highs on both sides
    Swing Low: Lowest low in window, with higher lows on both sides
    """
    
    def __init__(self, swing_length: int = 10):
        self.swing_length = swing_length
    
    def detect(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.DataFrame]:
        """
        Detect swing points.
        
        Returns:
            Tuple of (swing_high, swing_low, levels_df)
            - swing_high: Boolean series, True at swing high
            - swing_low: Boolean series, True at swing low
            - levels_df: DataFrame with swing point price levels
        """
        high = df['high']
        low = df['low']
        
        # Rolling max/min
        rolling_high = high.rolling(window=2 * self.swing_length + 1, center=True).max()
        rolling_low = low.rolling(window=2 * self.swing_length + 1, center=True).min()
        
        # Swing points
        swing_high = high == rolling_high
        swing_low = low == rolling_low
        
        # Get price levels
        levels = pd.DataFrame({
            'swing_high_price': high.where(swing_high),
            'swing_low_price': low.where(swing_low)
        }, index=df.index)
        
        # Forward fill levels
        levels['swing_high_price'] = levels['swing_high_price'].ffill()
        levels['swing_low_price'] = levels['swing_low_price'].ffill()
        
        return swing_high, swing_low, levels
    
    def get_last_swing_levels(
        self, 
        df: pd.DataFrame, 
        n_levels: int = 3
    ) -> Tuple[list, list]:
        """
        Get the last N swing high/low levels.
        
        Returns:
            Tuple of (swing_highs, swing_lows) lists
        """
        swing_high, swing_low, _ = self.detect(df)
        
        # Get last N swing highs
        sh_idx = swing_high[swing_high].tail(n_levels).index
        sh_prices = df['high'].loc[sh_idx].tolist()
        
        # Get last N swing lows
        sl_idx = swing_low[swing_low].tail(n_levels).index
        sl_prices = df['low'].loc[sl_idx].tolist()
        
        return sh_prices, sl_prices


def calculate_swing_highs_lows(df: pd.DataFrame, swing_length: int = 10) -> pd.DataFrame:
    """Convenience function for swing detection."""
    detector = SwingPointDetector(swing_length=swing_length)
    swing_high, swing_low, levels = detector.detect(df)
    
    result = levels.copy()
    result['swing_high'] = swing_high
    result['swing_low'] = swing_low
    
    return result
