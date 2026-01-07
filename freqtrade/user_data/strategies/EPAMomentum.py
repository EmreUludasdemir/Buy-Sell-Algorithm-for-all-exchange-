"""
EPA Momentum Strategy
=====================
RSI + MACD momentum-based strategy for catching strong moves.

Author: Emre Uludaşdemir
Version: 1.0.0
"""

import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy


class EPAMomentum(IStrategy):
    """Momentum Strategy - RSI + MACD confluence"""
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    minimal_roi = {
        "0": 0.12,
        "60": 0.08,
        "120": 0.05,
        "240": 0.03,
    }
    
    stoploss = -0.06
    
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 50
    
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {"method": "MaxDrawdown", "lookback_period_candles": 48, "trade_limit": 5,
             "stop_duration_candles": 10, "max_allowed_drawdown": 0.2},
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']
        
        # EMA for trend
        dataframe['ema_20'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        
        # Volume SMA
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Momentum Entry:
        1. RSI crosses above 50 (momentum shift)
        2. MACD histogram positive and increasing
        3. Price above EMA20
        4. Volume above average
        """
        dataframe.loc[
            (
                # RSI momentum
                (dataframe['rsi'] > 50) &
                (dataframe['rsi'].shift(1) <= 50) &
                
                # MACD bullish
                (dataframe['macd_hist'] > 0) &
                (dataframe['macd_hist'] > dataframe['macd_hist'].shift(1)) &
                
                # Trend filter
                (dataframe['close'] > dataframe['ema_20']) &
                
                # Volume confirmation
                (dataframe['volume'] > dataframe['volume_sma'])
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'momentum_entry')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
