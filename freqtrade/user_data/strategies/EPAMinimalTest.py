"""
EPAMinimalTest - Absolute minimum strategy for debugging
Just EMA cross - no other filters.
"""

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class EPAMinimalTest(IStrategy):
    """Minimal test - just EMA cross."""
    
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False
    
    minimal_roi = {"0": 0.50}  # Very high ROI so trades don't exit early
    stoploss = -0.50  # Very wide stoploss
    trailing_stop = False
    
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 30
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=30)
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """MINIMAL: Just EMA golden cross."""
        dataframe.loc[
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1)) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """MINIMAL: Just EMA death cross."""
        dataframe.loc[
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1)) &
            (dataframe['volume'] > 0),
            'exit_long'
        ] = 1
        return dataframe
