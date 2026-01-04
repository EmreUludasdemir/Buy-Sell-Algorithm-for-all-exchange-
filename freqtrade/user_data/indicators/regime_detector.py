"""
Regime Detector
Classifies market state: TRENDING, RANGING, VOLATILE, SQUEEZE
"""
import pandas as pd
import numpy as np
from enum import Enum
from typing import Tuple
import talib.abstract as ta


class MarketRegime(Enum):
    TRENDING = "trending"      # Strong directional movement
    RANGING = "ranging"        # Sideways consolidation
    VOLATILE = "volatile"      # High volatility, unclear direction
    SQUEEZE = "squeeze"        # Low volatility, breakout pending


class RegimeDetector:
    """
    Detects market regime using ADX, Choppiness, and BB Width.
    
    Regimes:
    - TRENDING: ADX > 25 and Choppiness < 50
    - RANGING: ADX < 20 and Choppiness > 55
    - SQUEEZE: BB Width at low percentile
    - VOLATILE: ADX > 20 and BB Width at high percentile
    """
    
    def __init__(
        self,
        adx_period: int = 14,
        chop_period: int = 14,
        bb_length: int = 20,
        bb_pct_lookback: int = 100
    ):
        self.adx_period = adx_period
        self.chop_period = chop_period
        self.bb_length = bb_length
        self.bb_pct_lookback = bb_pct_lookback
    
    def detect(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Detect market regime.
        
        Returns:
            Tuple of (regime_series, indicators_df)
            - regime_series: Series of regime strings
            - indicators_df: DataFrame with ADX, Choppiness, BB Width
        """
        # ADX
        adx = ta.ADX(df, timeperiod=self.adx_period)
        plus_di = ta.PLUS_DI(df, timeperiod=self.adx_period)
        minus_di = ta.MINUS_DI(df, timeperiod=self.adx_period)
        
        # Choppiness Index
        chop = self._choppiness_index(df)
        
        # BB Width Percentile
        bb_width_pct = self._bb_width_percentile(df)
        
        # Detect regime
        regime = pd.Series(index=df.index, dtype=str)
        
        # SQUEEZE: BB Width < 25th percentile
        squeeze_mask = bb_width_pct < 25
        regime[squeeze_mask] = MarketRegime.SQUEEZE.value
        
        # TRENDING: ADX > 25 and Chop < 50
        trending_mask = (adx > 25) & (chop < 50) & ~squeeze_mask
        regime[trending_mask] = MarketRegime.TRENDING.value
        
        # RANGING: ADX < 20 and Chop > 55
        ranging_mask = (adx < 20) & (chop > 55) & ~squeeze_mask
        regime[ranging_mask] = MarketRegime.RANGING.value
        
        # VOLATILE: High ADX with high BB width
        volatile_mask = (adx > 20) & (bb_width_pct > 75) & ~squeeze_mask
        regime[volatile_mask] = MarketRegime.VOLATILE.value
        
        # Default to RANGING for unclassified
        regime[regime == ''] = MarketRegime.RANGING.value
        
        # Create indicators DataFrame
        indicators = pd.DataFrame({
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di,
            'choppiness': chop,
            'bb_width_pct': bb_width_pct
        }, index=df.index)
        
        return regime, indicators
    
    def _choppiness_index(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Choppiness Index."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        
        atr_sum = tr.rolling(window=self.chop_period).sum()
        hl_range = high.rolling(self.chop_period).max() - low.rolling(self.chop_period).min()
        hl_range = hl_range.replace(0, np.nan)
        
        chop = 100 * np.log10(atr_sum / hl_range) / np.log10(self.chop_period)
        return chop.fillna(50)
    
    def _bb_width_percentile(self, df: pd.DataFrame) -> pd.Series:
        """Calculate BB Width as percentile of recent history."""
        close = df['close']
        
        bb_basis = close.rolling(window=self.bb_length).mean()
        bb_dev = close.rolling(window=self.bb_length).std() * 2
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        
        bb_width = (bb_upper - bb_lower) / bb_basis * 100
        
        def percentile_rank(x):
            if len(x) < 2:
                return 50
            return (x.rank().iloc[-1] - 1) / (len(x) - 1) * 100
        
        return bb_width.rolling(window=self.bb_pct_lookback).apply(percentile_rank, raw=False).fillna(50)
