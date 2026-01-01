"""
EPASimpleTest - Debug Strategy without Kıvanç indicators
Tests if basic EPA logic works without the complex Kıvanç indicators.

Version: 1.0.0
Author: Emre Uludaşdemir
"""

import logging
import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class EPASimpleTest(IStrategy):
    """
    Simple test strategy to verify basic entries work.
    No Kıvanç indicators - just EMA + ADX.
    """
    
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False
    
    # ROI
    minimal_roi = {
        "0": 0.10,
        "480": 0.05,
        "960": 0.03,
    }
    
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 50
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Simple indicators only."""
        
        # EMAs
        dataframe['ema_10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema_30'] = ta.EMA(dataframe, timeperiod=30)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Debug: print some stats
        logger.info(f"[{metadata['pair']}] ADX range: {dataframe['adx'].min():.1f} - {dataframe['adx'].max():.1f}")
        logger.info(f"[{metadata['pair']}] EMA10 > EMA30 count: {(dataframe['ema_10'] > dataframe['ema_30']).sum()}")
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        SIMPLE entry: EMA cross + ADX trend + DI direction.
        No Kıvanç!
        """
        
        # Simple conditions
        ema_bullish = dataframe['ema_10'] > dataframe['ema_30']
        adx_trending = dataframe['adx'] > 20  # Low threshold
        di_bullish = dataframe['plus_di'] > dataframe['minus_di']
        rsi_ok = dataframe['rsi'] > 40  # Above oversold
        
        # Count how many candles match
        matches = (ema_bullish & adx_trending & di_bullish & rsi_ok).sum()
        logger.info(f"[{metadata['pair']}] Entry conditions matched: {matches} candles")
        
        dataframe.loc[
            (ema_bullish) &
            (adx_trending) &
            (di_bullish) &
            (rsi_ok) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        entries = dataframe['enter_long'].sum() if 'enter_long' in dataframe.columns else 0
        logger.info(f"[{metadata['pair']}] Total entries: {entries}")
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Simple exit: EMA cross down."""
        
        dataframe.loc[
            (dataframe['ema_10'] < dataframe['ema_30']) &
            (dataframe['volume'] > 0),
            'exit_long'
        ] = 1
        
        return dataframe
