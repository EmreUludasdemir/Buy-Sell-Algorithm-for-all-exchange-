"""
WaveTrend Oscillator
Double-smoothed momentum oscillator for overbought/oversold detection.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class WaveTrendCalculator:
    """
    WaveTrend is a double-smoothed oscillator useful for:
    - Overbought/oversold detection (levels 60/-60)
    - Divergence analysis
    - Momentum crossovers
    """
    
    def __init__(self, channel_length: int = 10, average_length: int = 21):
        self.channel_length = channel_length
        self.average_length = average_length
    
    def calculate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate WaveTrend.
        
        Returns:
            Tuple of (wt1, wt2) where wt2 is signal line
        """
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        
        # First EMA
        esa = hlc3.ewm(span=self.channel_length, adjust=False).mean()
        
        # Difference from EMA
        d = abs(hlc3 - esa).ewm(span=self.channel_length, adjust=False).mean()
        
        # CI (Channel Index)
        ci = (hlc3 - esa) / (0.015 * d)
        ci = ci.replace([np.inf, -np.inf], 0).fillna(0)
        
        # WaveTrend lines
        wt1 = ci.ewm(span=self.average_length, adjust=False).mean()
        wt2 = wt1.rolling(window=4).mean()
        
        return wt1, wt2
    
    def get_signals(self, wt1: pd.Series, wt2: pd.Series, 
                    ob_level: int = 60, os_level: int = -60) -> Tuple[pd.Series, pd.Series]:
        """
        Generate buy/sell signals from WaveTrend.
        
        Returns:
            Tuple of (buy_signal, sell_signal)
        """
        # Bullish cross from oversold
        buy_signal = (
            (wt1 > wt2) & 
            (wt1.shift(1) <= wt2.shift(1)) & 
            (wt1 < os_level)
        )
        
        # Bearish cross from overbought
        sell_signal = (
            (wt1 < wt2) & 
            (wt1.shift(1) >= wt2.shift(1)) & 
            (wt1 > ob_level)
        )
        
        return buy_signal, sell_signal


def wavetrend(
    df: pd.DataFrame,
    channel_length: int = 10,
    average_length: int = 21
) -> Tuple[pd.Series, pd.Series]:
    """Convenience function for WaveTrend."""
    calc = WaveTrendCalculator(channel_length=channel_length, average_length=average_length)
    return calc.calculate(df)
