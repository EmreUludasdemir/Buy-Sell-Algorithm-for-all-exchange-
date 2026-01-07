"""
EPA Buy & Hold DCA Hybrid Strategy
===================================
Combination of Buy & Hold with Dollar Cost Averaging.
Designed to capture market uptrends while managing entries.

Logic:
- Initial entry when above EMA 200 (bull market)
- DCA on dips: buy more when price drops 5% below average
- Hold for long term with very wide stoploss

Author: Emre Uludaşdemir
Version: 1.0.0
"""

import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade


class EPAHoldDCA(IStrategy):
    """
    Buy & Hold with DCA Hybrid
    
    - Enter when above EMA 200 (macro bullish)
    - DCA: Position adjustment when price drops
    - Very patient exits (high ROI targets)
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '4h'  # Longer TF for holding
    can_short = False
    
    # Very patient ROI - hold for big gains
    minimal_roi = {
        "0": 0.50,       # 50% target
        "720": 0.30,     # 30% after 5 days
        "1440": 0.20,    # 20% after 10 days
        "2880": 0.10,    # 10% after 20 days
    }
    
    # Wide stoploss for holding through volatility
    stoploss = -0.20  # 20% max loss
    
    # No trailing - hold positions
    trailing_stop = False
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 250
    
    # Enable DCA (position adjustment)
    position_adjustment_enable = True
    max_entry_position_adjustment = 3  # Up to 3 DCA entries
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend indicators
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        # RSI for oversold detection (DCA trigger)
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Initial entry: Price above EMA 200 (macro bullish)
        """
        dataframe.loc[
            (
                (dataframe['close'].shift(1) > dataframe['ema_200'].shift(1)) &
                (dataframe['ema_50'].shift(1) > dataframe['ema_200'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals - hold for ROI"""
        return dataframe
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:
        """
        DCA: Add to position when price drops significantly
        """
        # Only DCA if we're in loss
        if current_profit > -0.05:  # Only DCA when down 5%+
            return None
        
        # Check how many times we've already DCA'd
        filled_entries = trade.nr_of_successful_entries
        if filled_entries >= self.max_entry_position_adjustment + 1:
            return None
        
        # DCA amount decreases with each entry
        dca_stake = trade.stake_amount * (0.5 ** filled_entries)
        
        # Ensure we don't exceed max stake
        if dca_stake < min_stake:
            return None
        
        return dca_stake
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
