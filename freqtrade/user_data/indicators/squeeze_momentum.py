"""
Squeeze Momentum Indicator (LazyBear style)
Detects volatility squeezes and measures momentum direction.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class SqueezeMomentumCalculator:
    """
    Squeeze Momentum detects when Bollinger Bands are inside Keltner Channels.
    This indicates low volatility (squeeze) that often precedes breakouts.
    """
    
    def __init__(
        self, 
        bb_length: int = 20,
        bb_mult: float = 2.0,
        kc_length: int = 20,
        kc_mult: float = 1.5,
        mom_length: int = 12
    ):
        self.bb_length = bb_length
        self.bb_mult = bb_mult
        self.kc_length = kc_length
        self.kc_mult = kc_mult
        self.mom_length = mom_length
    
    def calculate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Squeeze Momentum.
        
        Returns:
            Tuple of (momentum, squeeze_on, squeeze_off)
            - momentum: Momentum value (positive = bullish, negative = bearish)
            - squeeze_on: Boolean, True when in squeeze (low volatility)
            - squeeze_off: Boolean, True when squeeze fires (breakout)
        """
        close = df['close']
        high = df['high']
        low = df['low']
        
        # Bollinger Bands
        bb_basis = close.rolling(window=self.bb_length).mean()
        bb_dev = close.rolling(window=self.bb_length).std() * self.bb_mult
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        
        # Keltner Channels (ATR-based)
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=self.kc_length).mean()
        
        kc_basis = close.rolling(window=self.kc_length).mean()
        kc_upper = kc_basis + atr * self.kc_mult
        kc_lower = kc_basis - atr * self.kc_mult
        
        # Squeeze detection
        squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        squeeze_off = ~squeeze_on & squeeze_on.shift(1).fillna(False)
        
        # Momentum calculation
        highest = high.rolling(window=self.kc_length).max()
        lowest = low.rolling(window=self.kc_length).min()
        avg_hl = (highest + lowest) / 2
        avg_close = close.rolling(window=self.kc_length).mean()
        
        momentum = close - (avg_hl + avg_close) / 2
        momentum = momentum.rolling(window=self.mom_length).mean()
        
        return momentum, squeeze_on, squeeze_off
    
    def get_momentum_direction(self, momentum: pd.Series) -> pd.Series:
        """Get momentum direction: 1 for increasing, -1 for decreasing."""
        return pd.Series(
            np.where(momentum > momentum.shift(1), 1, -1),
            index=momentum.index
        )


def squeeze_momentum(
    df: pd.DataFrame, 
    bb_length: int = 20, 
    kc_length: int = 20
) -> Tuple[pd.Series, pd.Series]:
    """Convenience function for squeeze momentum."""
    calc = SqueezeMomentumCalculator(bb_length=bb_length, kc_length=kc_length)
    momentum, squeeze_on, _ = calc.calculate(df)
    return momentum, squeeze_on
