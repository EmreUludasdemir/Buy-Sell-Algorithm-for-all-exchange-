"""
EPA Simple EMA Cross Strategy
==============================
The simplest possible trend strategy - just EMA crossover.
No complex indicators, no SMC, no regime detection.

Author: Emre Uludaşdemir
Version: 1.0.0
"""

import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy


class EPASimpleEMA(IStrategy):
    """
    Simplest EMA Crossover Strategy
    
    Entry: EMA 12 crosses above EMA 26
    Exit: ROI or Stoploss only
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # Conservative ROI - take profits early
    minimal_roi = {
        "0": 0.12,
        "120": 0.08,
        "240": 0.05,
        "480": 0.03,
    }
    
    stoploss = -0.08  # Tight 8% stoploss
    
    # NO trailing stop
    trailing_stop = False
    
    use_exit_signal = False  # Only ROI/stoploss
    process_only_new_candles = True
    startup_candle_count = 50
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Simple EMAs
        dataframe['ema_12'] = ta.EMA(dataframe['close'], timeperiod=12)
        dataframe['ema_26'] = ta.EMA(dataframe['close'], timeperiod=26)
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry: EMA 12 crosses above EMA 26 + price above EMA 50"""
        dataframe.loc[
            (
                (dataframe['ema_12'].shift(1) > dataframe['ema_26'].shift(1)) &
                (dataframe['ema_12'].shift(2) <= dataframe['ema_26'].shift(2)) &
                (dataframe['close'].shift(1) > dataframe['ema_50'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals - only ROI and stoploss"""
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
