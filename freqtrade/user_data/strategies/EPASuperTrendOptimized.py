"""
EPA SuperTrend Optimized Strategy
==================================
Optimized SuperTrend parameters from Hyperopt.

Author: Emre Uludaşdemir
Version: 1.2.0 - Hyperopt Optimized

Optimization Results:
--------------------
- Epochs: 40
- Best Profit: +26.56% (vs baseline +4.98%)
- Win Rate: 82.7%
- Drawdown: 12.33%

Optimized Parameters:
--------------------
- SuperTrend Period: 14 (was 10)
- SuperTrend Multiplier: 3.5 (was 3.0)
- EMA Filter: Disabled
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


class EPASuperTrendOptimized(IStrategy):
    """
    SuperTrend Strategy - Hyperopt Optimized
    
    Key changes from baseline:
    - Period: 14 (more stable than 10)
    - Multiplier: 3.5 (wider bands, less whipsaws)
    - Result: +26.56% profit, 82.7% win rate, 12.33% DD
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # ==========================================
    # OPTIMIZED PARAMETERS (Hyperopt Results)
    # ==========================================
    
    # SuperTrend parameters - OPTIMIZED
    supertrend_period = 14      # Was 10, now 14
    supertrend_multiplier = 3.5  # Was 3.0, now 3.5
    
    # ==========================================
    # ROI TABLE
    # ==========================================
    minimal_roi = {
        "0": 0.15,
        "120": 0.10,
        "240": 0.07,
        "480": 0.04,
        "720": 0.02,
    }
    
    # ==========================================
    # RISK MANAGEMENT
    # ==========================================
    stoploss = -0.08
    
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 50
    
    # ==========================================
    # PROTECTIONS
    # ==========================================
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 3,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 4,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.2,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 8,
                "only_per_pair": True,
            },
        ]
    
    # ==========================================
    # INDICATORS
    # ==========================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate SuperTrend with optimized parameters"""
        
        # SuperTrend calculation with OPTIMIZED parameters
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
        
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        
        # EMA for context
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        # ATR for volatility-based stops
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Signal: SuperTrend bullish flip
        
        Optimized conditions:
        1. SuperTrend direction changes from -1 to 1
        2. Volume confirmation (> 0)
        """
        
        dataframe.loc[
            (
                # SuperTrend bullish flip
                (dataframe['supertrend_direction'] == 1) &
                (dataframe['supertrend_direction'].shift(1) == -1) &
                
                # Volume exists
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'st_optimized')
        
        return dataframe
    
    # ==========================================
    # EXIT LOGIC
    # ==========================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals - using ROI/trailing/stoploss only"""
        return dataframe
    
    # ==========================================
    # LEVERAGE
    # ==========================================
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
    
    # ==========================================
    # CUSTOM STOPLOSS
    # ==========================================
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        """ATR-based dynamic stoploss"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return self.stoploss
        
        last_candle = dataframe.iloc[-1]
        
        if 'atr' in last_candle and last_candle['atr'] > 0:
            atr_stop = -(last_candle['atr'] * 2) / current_rate
            return max(self.stoploss, atr_stop)
        
        return self.stoploss
