"""
AlphaTrend Indicator - MFI-gated ATR-based Trend Detection
Non-repainting, lookahead-free implementation.
"""
import pandas as pd
import numpy as np
from typing import Tuple


class AlphaTrendCalculator:
    """
    AlphaTrend calculates dynamic support/resistance using MFI as a momentum gate.
    
    When MFI >= 50 (bullish): line follows lower ATR band (support)
    When MFI < 50 (bearish): line follows upper ATR band (resistance)
    """
    
    def __init__(self, period: int = 14, coeff: float = 1.0, src: str = 'mfi'):
        self.period = period
        self.coeff = coeff
        self.src = src
    
    def calculate(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate AlphaTrend.
        
        Returns:
            Tuple of (alphatrend_line, alphatrend_signal, alphatrend_direction)
            - alphatrend_line: The main AlphaTrend line
            - alphatrend_signal: Shifted line for crossover detection (shift 2)
            - alphatrend_direction: 1 for bullish, -1 for bearish
        """
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        # ATR calculation (SMA-based for consistency)
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=self.period).mean()
        
        # Momentum source
        if self.src == 'mfi':
            momentum = self._calculate_mfi(high, low, close, volume)
        else:
            momentum = self._calculate_rsi(close)
        
        # ATR bands
        upper_band = low - (atr * self.coeff)  # Support
        lower_band = high + (atr * self.coeff)  # Resistance
        
        # Initialize AlphaTrend line
        at_line = pd.Series(index=df.index, dtype=float)
        at_line.iloc[:self.period] = close.iloc[:self.period]
        
        # Calculate AlphaTrend (self-referencing loop required)
        for i in range(self.period, len(df)):
            prev_at = at_line.iloc[i-1]
            
            if momentum.iloc[i] >= 50:
                # Bullish: use lower band, don't go below previous
                at_line.iloc[i] = max(lower_band.iloc[i], prev_at)
            else:
                # Bearish: use upper band, don't go above previous
                at_line.iloc[i] = min(upper_band.iloc[i], prev_at)
        
        # Signal line (shifted for crossover detection)
        at_signal = at_line.shift(2)
        
        # Direction: 1 bullish, -1 bearish
        at_direction = pd.Series(
            np.where(at_line > at_signal, 1, -1),
            index=df.index
        )
        
        return at_line, at_signal, at_direction
    
    def _calculate_mfi(self, high, low, close, volume) -> pd.Series:
        """Calculate Money Flow Index."""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        pos_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        neg_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        pos_sum = pos_flow.rolling(window=self.period).sum()
        neg_sum = neg_flow.rolling(window=self.period).sum()
        
        mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, np.nan)))
        return mfi.fillna(50)
    
    def _calculate_rsi(self, close) -> pd.Series:
        """Calculate RSI as fallback."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)


def alphatrend(df: pd.DataFrame, period: int = 14, coeff: float = 1.0) -> Tuple[pd.Series, pd.Series]:
    """Convenience function for AlphaTrend calculation."""
    calc = AlphaTrendCalculator(period=period, coeff=coeff)
    line, signal, _ = calc.calculate(df)
    return line, signal
