"""
EPA DCA Strategy
================
Dollar Cost Averaging with multiple entries on dips.

Author: Emre Uludaşdemir
Version: 1.0.0
"""

import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade


class EPADCA(IStrategy):
    """DCA Strategy - Buy dips with position averaging"""
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # DCA requires position adjustment
    position_adjustment_enable = True
    max_entry_position_adjustment = 3  # Up to 4 total entries
    
    minimal_roi = {
        "0": 0.10,
        "120": 0.06,
        "240": 0.04,
        "480": 0.02,
    }
    
    stoploss = -0.15  # Wider stoploss for DCA
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 50
    
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {"method": "MaxDrawdown", "lookback_period_candles": 48, "trade_limit": 6,
             "stop_duration_candles": 8, "max_allowed_drawdown": 0.25},
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI for oversold detection
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        # Bollinger Bands for dip detection  
        bollinger = ta.BBANDS(dataframe['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_upper'] = bollinger['upperband']
        
        # EMA trend
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        DCA Initial Entry:
        1. RSI oversold (< 35)
        2. Price near lower Bollinger Band
        3. Price above EMA200 (still in uptrend)
        """
        dataframe.loc[
            (
                # Oversold
                (dataframe['rsi'] < 35) &
                
                # Near lower BB
                (dataframe['close'] < dataframe['bb_middle']) &
                
                # Still in uptrend
                (dataframe['ema_50'] > dataframe['ema_200']) &
                
                # Volume
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'dca_initial')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:
        """
        DCA Logic: Add to position when price drops
        - Add at -3%, -6%, -9% from entry
        """
        if current_profit > -0.03:  # Wait for 3% dip
            return None
        
        filled_entries = trade.nr_of_successful_entries
        
        # DCA levels: -3%, -6%, -9%
        dca_levels = [-0.03, -0.06, -0.09]
        
        if filled_entries <= len(dca_levels):
            target_level = dca_levels[filled_entries - 1]
            
            if current_profit <= target_level:
                # Add more to position (double down)
                return trade.stake_amount
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
