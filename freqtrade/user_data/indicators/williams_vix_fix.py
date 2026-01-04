"""
Williams VixFix - Panic/Capitulation Detector
Identifies market bottoms using volatility spikes.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class WilliamsVixFix:
    """
    Williams VixFix identifies market panic/capitulation using
    the distance from highest close to current low.
    
    High VixFix = Market fear/panic = Potential bottom
    """
    
    def __init__(self, lookback: int = 22, bb_length: int = 20, bb_mult: float = 2.0):
        self.lookback = lookback
        self.bb_length = bb_length
        self.bb_mult = bb_mult
    
    def calculate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Williams VixFix.
        
        Returns:
            Tuple of (vixfix, upper_band, is_panic)
            - vixfix: The VixFix value
            - upper_band: BB upper band for threshold
            - is_panic: Boolean, True when VixFix > upper band
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # VixFix calculation
        highest_close = close.rolling(window=self.lookback).max()
        vixfix = (highest_close - low) / highest_close * 100
        
        # Bollinger Bands on VixFix for dynamic threshold
        vf_basis = vixfix.rolling(window=self.bb_length).mean()
        vf_std = vixfix.rolling(window=self.bb_length).std()
        upper_band = vf_basis + (vf_std * self.bb_mult)
        
        # Panic detection
        is_panic = vixfix > upper_band
        
        return vixfix, upper_band, is_panic
    
    def get_reversal_signal(
        self, 
        vixfix: pd.Series, 
        upper_band: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """
        Generate reversal signal from VixFix.
        
        Signal fires when:
        1. VixFix was above upper band (panic)
        2. VixFix drops below upper band (panic subsiding)
        3. Close is rising
        """
        was_panic = vixfix.shift(1) > upper_band.shift(1)
        panic_subsiding = vixfix <= upper_band
        price_rising = close > close.shift(1)
        
        return was_panic & panic_subsiding & price_rising


def williams_vix_fix(df: pd.DataFrame, lookback: int = 22) -> pd.Series:
    """Convenience function for Williams VixFix."""
    calc = WilliamsVixFix(lookback=lookback)
    vixfix, _, _ = calc.calculate(df)
    return vixfix
