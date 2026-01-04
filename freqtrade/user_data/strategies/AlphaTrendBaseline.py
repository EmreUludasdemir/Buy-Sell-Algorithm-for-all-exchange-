"""
AlphaTrendBaseline Strategy
===========================
Simple baseline for comparison with AlphaTrendAdaptive.
Uses only AlphaTrend + EMA for entries.
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class AlphaTrendBaseline(IStrategy):
    """
    Simple AlphaTrend baseline strategy.
    Entry: AlphaTrend bullish + Close > EMA50
    Exit: AlphaTrend bearish
    """
    
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    
    use_exit_signal = True
    use_custom_stoploss = False
    
    process_only_new_candles = True
    startup_candle_count: int = 100
    
    minimal_roi = {
        "0": 0.10,
        "60": 0.05,
        "120": 0.03,
        "240": 0.02
    }
    
    stoploss = -0.05
    
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    # Parameters
    at_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    at_coeff = DecimalParameter(0.8, 1.5, default=1.0, decimals=1, space='buy', optimize=True)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Simple indicators."""
        # AlphaTrend
        dataframe = self._add_alphatrend(dataframe)
        
        # EMAs
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        # Volume
        dataframe['volume_sma'] = dataframe['volume'].rolling(20).mean()
        
        return dataframe
    
    def _add_alphatrend(self, df: DataFrame) -> DataFrame:
        """Add AlphaTrend."""
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        period = self.at_period.value
        coeff = self.at_coeff.value
        
        # ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # MFI
        tp = (high + low + close) / 3
        mf = tp * volume
        pos_flow = mf.where(tp > tp.shift(1), 0).rolling(period).sum()
        neg_flow = mf.where(tp < tp.shift(1), 0).rolling(period).sum()
        mfi = 100 - (100 / (1 + pos_flow / neg_flow.replace(0, np.nan))).fillna(50)
        
        # Bands
        upper = low - (atr * coeff)
        lower = high + (atr * coeff)
        
        # AlphaTrend
        at_line = pd.Series(index=df.index, dtype=float)
        at_line.iloc[:period] = close.iloc[:period]
        
        for i in range(period, len(df)):
            prev = at_line.iloc[i-1]
            if mfi.iloc[i] >= 50:
                at_line.iloc[i] = max(lower.iloc[i], prev)
            else:
                at_line.iloc[i] = min(upper.iloc[i], prev)
        
        df['alphatrend'] = at_line
        df['at_bullish'] = (at_line > at_line.shift(2)).astype(int)
        
        return df
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Simple entry: AlphaTrend bullish + Close > EMA50."""
        enter_long = (
            (dataframe['at_bullish'] == 1) &
            (dataframe['close'] > dataframe['ema_50']) &
            (dataframe['volume'] > dataframe['volume_sma'] * 0.5) &
            (dataframe['volume'] > 0)
        )
        
        dataframe.loc[enter_long.shift(1).fillna(False), 'enter_long'] = 1
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on AlphaTrend bearish."""
        exit_signal = (
            (dataframe['at_bullish'] == 0) &
            (dataframe['at_bullish'].shift(1) == 1)
        )
        
        dataframe.loc[exit_signal.shift(1).fillna(False), 'exit_long'] = 1
        return dataframe
