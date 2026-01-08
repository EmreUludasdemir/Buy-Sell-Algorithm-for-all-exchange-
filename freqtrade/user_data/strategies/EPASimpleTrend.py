"""
EPA Simple Trend Strategy
===========================
Ultra-simple trend-following strategy using only native TA-Lib indicators.
No external dependencies. Designed to capture market trends aggressively.

Key Features:
- Entry: EMA crossover + ADX trend confirmation
- Exit: Trailing stop (enabled) + ROI
- No complex filters - just ride the trend

Author: Emre Uludaşdemir
Version: 1.0.0 - Maximum Simplicity
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

logger = logging.getLogger(__name__)


class EPASimpleTrend(IStrategy):
    """
    Ultra-Simple Trend Strategy
    
    Entry: EMA fast > EMA slow + ADX > 20 + DI+ > DI-
    Exit: EMA cross reverse + Trailing stop
    
    No Kivanc indicators, no SMC, no complex filters.
    Just pure trend following.
    """
    
    INTERFACE_VERSION = 3
    timeframe = '4h'  # 4h for cleaner signals
    can_short = False

    # AGGRESSIVE ROI
    minimal_roi = {
        "0": 0.25,      # 25% max
        "24": 0.12,     # 12% after 24h (6 candles)
        "72": 0.06,     # 6% after 3 days
        "168": 0.02     # 2% after 1 week
    }

    stoploss = -0.10  # 10% stoploss

    # TRAILING STOP - Key for capturing trends
    trailing_stop = True
    trailing_stop_positive = 0.04      # Trail at 4% profit
    trailing_stop_positive_offset = 0.06  # 6% offset
    trailing_only_offset_is_reached = True
    
    process_only_new_candles = True
    use_exit_signal = True  # Enable exit signals
    exit_profit_only = False
    startup_candle_count: int = 50
    
    # Simple parameters
    fast_ema = IntParameter(8, 20, default=12, space='buy', optimize=True)
    slow_ema = IntParameter(20, 50, default=26, space='buy', optimize=True)
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(15, 30, default=20, space='buy', optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Minimal indicators using only TA-Lib."""
        
        # EMAs
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        
        # ADX and DI
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        # EMA cross detection
        dataframe['ema_cross_up'] = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        dataframe['ema_cross_down'] = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Simple entry: EMA cross up + ADX trending + DI+ > DI-
        """
        
        dataframe.loc[
            (dataframe['ema_fast'] > dataframe['ema_slow']) &  # Bullish EMA
            (dataframe['adx'] > self.adx_threshold.value) &  # Trending
            (dataframe['plus_di'] > dataframe['minus_di']) &  # Bullish momentum
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on EMA cross down."""
        
        dataframe.loc[
            (dataframe['ema_fast'] < dataframe['ema_slow']),  # Bearish EMA cross
            'exit_long'
        ] = 1
        
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
