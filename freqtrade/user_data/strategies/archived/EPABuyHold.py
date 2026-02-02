"""
EPA Buy & Hold Strategy
========================
Simple buy-and-hold baseline to compare against active strategies.
Buys at start and holds until end of backtest period.

Author: Emre Uludaşdemir
Version: 1.0.0 - Baseline Comparison
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class EPABuyHold(IStrategy):
    """
    Buy and Hold Strategy - Baseline Comparison
    
    Simply buys at the first opportunity and holds.
    Used to compare against active trading strategies.
    """
    
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False

    # Never take profit early - hold forever
    minimal_roi = {
        "0": 100  # 10000% - effectively never hit
    }

    # Very wide stoploss - don't get stopped out
    stoploss = -0.99  # 99% - effectively never hit

    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = False
    startup_candle_count: int = 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Just need a simple indicator to trigger entry
        dataframe['sma_5'] = ta.SMA(dataframe, timeperiod=5)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Buy on first candle after startup
        dataframe.loc[
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Never exit - hold forever
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
