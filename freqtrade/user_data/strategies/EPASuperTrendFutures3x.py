"""
EPA SuperTrend Futures 3x Leverage Strategy
============================================
High leverage version for comparison testing.
3x leverage with tighter risk management.

Author: Emre Uludaşdemir
Version: 1.0.0 - Futures 3x

WARNING: Higher leverage = higher risk!
"""

import talib.abstract as ta
import pandas as pd
import numpy as np
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

from kivanc_indicators import supertrend


class EPASuperTrendFutures3x(IStrategy):
    """
    SuperTrend Futures - 3x Leverage Version
    
    Higher risk/reward profile:
    - 3x leverage
    - Tighter stoploss (-3%)
    - More aggressive trailing
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # ==========================================
    # OPTIMIZED SUPERTREND PARAMETERS
    # ==========================================
    supertrend_period = 14
    supertrend_multiplier = 3.5
    
    # ==========================================
    # ROI TABLE (adjusted for 3x leverage)
    # ==========================================
    minimal_roi = {
        "0": 0.05,      # 5% (= 15% with 3x)
        "60": 0.033,    # 3.3% (= 10% with 3x)
        "120": 0.023,   # 2.3% (= 7% with 3x)
        "240": 0.013,   # 1.3% (= 4% with 3x)
        "360": 0.007,   # 0.7% (= 2% with 3x)
    }
    
    # ==========================================
    # RISK MANAGEMENT (3x leverage)
    # ==========================================
    stoploss = -0.027  # 2.7% (= ~8% effective with 3x)
    
    trailing_stop = True
    trailing_stop_positive = 0.01    # 1% (= 3% with 3x)
    trailing_stop_positive_offset = 0.017  # 1.7% (= 5% with 3x)
    trailing_only_offset_is_reached = True
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 50
    
    # ==========================================
    # PROTECTIONS (stricter for 3x)
    # ==========================================
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 4,  # Longer cooldown
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 3,  # Fewer trades before protection
                "stop_duration_candles": 16,
                "max_allowed_drawdown": 0.25,  # 25% max DD
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": True,
            },
        ]
    
    # ==========================================
    # INDICATORS
    # ==========================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate SuperTrend with optimized parameters"""
        
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
        
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry: SuperTrend bullish flip"""
        
        dataframe.loc[
            (
                (dataframe['supertrend_direction'] == 1) &
                (dataframe['supertrend_direction'].shift(1) == -1) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'st_futures_3x')
        
        return dataframe
    
    # ==========================================
    # EXIT LOGIC
    # ==========================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals - using ROI/trailing/stoploss only"""
        return dataframe
    
    # ==========================================
    # LEVERAGE - 3x
    # ==========================================
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """3x leverage - higher risk/reward"""
        return 3.0
    
    # ==========================================
    # CUSTOM STOPLOSS
    # ==========================================
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        """ATR-based dynamic stoploss (tight for 3x)"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return self.stoploss
        
        last_candle = dataframe.iloc[-1]
        
        if 'atr' in last_candle and last_candle['atr'] > 0:
            # Tighter ATR stop for 3x
            atr_stop = -(last_candle['atr'] * 1.0) / current_rate
            return max(self.stoploss, atr_stop)
        
        return self.stoploss
