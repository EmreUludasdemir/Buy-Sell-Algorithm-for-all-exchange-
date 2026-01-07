"""
EPA SuperTrend Hyperopt Strategy (Simplified)
==============================================
Optimizable version - simplified for hyperopt compatibility.

Author: Emre Uludaşdemir
Version: 1.2.0

Hyperopt Parameters:
-------------------
- SuperTrend period: 8, 10, 12, 14, 16
- SuperTrend multiplier: 2.0, 2.5, 3.0, 3.5
- EMA filter: on/off
"""

import talib.abstract as ta
import pandas as pd
import numpy as np
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy, CategoricalParameter
from freqtrade.persistence import Trade

from kivanc_indicators import supertrend


class EPASuperTrendHyperopt(IStrategy):
    """
    SuperTrend Strategy with Hyperopt Parameters (Simplified)
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # ==========================================
    # HYPEROPT PARAMETERS - Categorical for stability
    # ==========================================
    
    # SuperTrend period options
    buy_st_period = CategoricalParameter([8, 10, 12, 14, 16], default=10, space='buy', optimize=True)
    
    # SuperTrend multiplier options
    buy_st_multiplier = CategoricalParameter([2.0, 2.5, 3.0, 3.5], default=3.0, space='buy', optimize=True)
    
    # EMA filter
    buy_use_ema = CategoricalParameter([True, False], default=False, space='buy', optimize=True)
    
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
    startup_candle_count = 250
    
    # ==========================================
    # PROTECTIONS
    # ==========================================
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 3},
            {"method": "MaxDrawdown", "lookback_period_candles": 48, "trade_limit": 4, "stop_duration_candles": 12, "max_allowed_drawdown": 0.2},
            {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 2, "stop_duration_candles": 8, "only_per_pair": True},
        ]
    
    # ==========================================
    # INDICATORS
    # ==========================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate SuperTrend for all hyperopt combinations"""
        
        # Pre-calculate all combinations for hyperopt
        for period in [8, 10, 12, 14, 16]:
            for mult in [2.0, 2.5, 3.0, 3.5]:
                st_dir, st_line = supertrend(dataframe, period=period, multiplier=mult)
                dataframe[f'st_dir_{period}_{mult}'] = st_dir
        
        # EMA for optional filter
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry with hyperopt parameters"""
        
        period = self.buy_st_period.value
        mult = self.buy_st_multiplier.value
        col = f'st_dir_{period}_{mult}'
        
        # Base conditions
        conditions = (
            (dataframe[col] == 1) &
            (dataframe[col].shift(1) == -1) &
            (dataframe['volume'] > 0)
        )
        
        # EMA filter
        if self.buy_use_ema.value:
            conditions = conditions & (dataframe['close'] > dataframe['ema_200'])
        
        dataframe.loc[conditions, ['enter_long', 'enter_tag']] = (1, f'st_{period}_{mult}')
        
        return dataframe
    
    # ==========================================
    # EXIT LOGIC
    # ==========================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
    
    # ==========================================
    # LEVERAGE
    # ==========================================
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
