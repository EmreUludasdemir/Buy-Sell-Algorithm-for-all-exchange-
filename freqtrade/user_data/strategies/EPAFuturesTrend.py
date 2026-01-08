"""
EPA Futures Trend Strategy (3x Leverage)
==========================================
Aggressive trend-following strategy using 3x leverage on futures.
Designed to capture 100%+ of market moves.

Key Features:
- 3x leverage for amplified gains
- Tight trailing stop to protect profits
- EMA cross + ADX for clean signals
- Both long and short capability

Author: Emre Uludaşdemir
Version: 1.0.0 - Futures Aggressive
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

logger = logging.getLogger(__name__)


class EPAFuturesTrend(IStrategy):
    """
    Futures Trend Strategy with 3x Leverage
    
    Entry: EMA cross + ADX + DI direction
    Exit: Trailing stop + EMA reversal
    Leverage: 3x (configurable)
    
    Target: 100%+ profit to match/beat buy-hold
    """
    
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False  # Disabled for spot $1000 test

    # Moderate ROI - let leverage do the work
    minimal_roi = {
        "0": 0.20,      # 20% (60% with 3x leverage)
        "48": 0.10,     # 10% (30% with 3x)
        "96": 0.05,     # 5% (15% with 3x)
        "192": 0.02     # 2% (6% with 3x)
    }

    # Tighter stoploss for leveraged trading
    stoploss = -0.05  # 5% base = 15% with 3x leverage

    # Trailing stop - critical for locking in gains
    trailing_stop = True
    trailing_stop_positive = 0.03      # Trail at 3% profit (9% with 3x)
    trailing_stop_positive_offset = 0.05  # 5% offset (15% with 3x)
    trailing_only_offset_is_reached = True
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    startup_candle_count: int = 50
    
    # Parameters
    fast_ema = IntParameter(8, 15, default=10, space='buy', optimize=True)
    slow_ema = IntParameter(20, 40, default=25, space='buy', optimize=True)
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(20, 35, default=25, space='buy', optimize=True)
    
    # Leverage setting
    leverage_value = 3.0  # 3x leverage

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate trend indicators."""
        
        # EMAs
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        
        # ADX and DI
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        # RSI for overbought/oversold
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Long: EMA cross up + ADX trending + DI+ > DI-
        Short: EMA cross down + ADX trending + DI- > DI+
        """
        
        # LONG entry
        dataframe.loc[
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['adx'] > self.adx_threshold.value) &
            (dataframe['plus_di'] > dataframe['minus_di']) &
            (dataframe['rsi'] < 70) &  # Not overbought
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        # SHORT entry
        dataframe.loc[
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['adx'] > self.adx_threshold.value) &
            (dataframe['minus_di'] > dataframe['plus_di']) &
            (dataframe['rsi'] > 30) &  # Not oversold
            (dataframe['volume'] > 0),
            'enter_short'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on trend reversal."""
        
        # Exit long on bearish cross
        dataframe.loc[
            (dataframe['ema_fast'] < dataframe['ema_slow']),
            'exit_long'
        ] = 1
        
        # Exit short on bullish cross
        dataframe.loc[
            (dataframe['ema_fast'] > dataframe['ema_slow']),
            'exit_short'
        ] = 1
        
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Use 3x leverage for all trades."""
        return min(self.leverage_value, max_leverage)
