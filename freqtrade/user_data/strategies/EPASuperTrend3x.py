"""
EPA SuperTrend Futures 3x Leverage Strategy
============================================
Optimized SuperTrend with 3x leverage for higher returns.

Author: Emre Uludaşdemir  
Version: 2.0.0
"""

import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

from kivanc_indicators import supertrend


class EPASuperTrend3x(IStrategy):
    """SuperTrend with 3x Leverage - BTC/ETH only"""
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # Optimized parameters
    supertrend_period = 14
    supertrend_multiplier = 3.5
    
    # Tighter ROI for leveraged trading
    minimal_roi = {
        "0": 0.08,      # 8% / 3x = ~24% leveraged
        "60": 0.05,
        "120": 0.03,
        "240": 0.02,
    }
    
    # Tighter stoploss for leverage
    stoploss = -0.04  # 4% * 3x = 12% actual loss
    
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 50
    
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 3},
            {"method": "MaxDrawdown", "lookback_period_candles": 48, "trade_limit": 4, 
             "stop_duration_candles": 12, "max_allowed_drawdown": 0.15},
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        st_direction, st_line = supertrend(dataframe, period=self.supertrend_period, 
                                           multiplier=self.supertrend_multiplier)
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['supertrend_direction'] == 1) &
            (dataframe['supertrend_direction'].shift(1) == -1) &
            (dataframe['volume'] > 0),
            ['enter_long', 'enter_tag']
        ] = (1, 'st_3x')
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 3.0
