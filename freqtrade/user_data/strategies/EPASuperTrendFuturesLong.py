"""
EPA SuperTrend Futures Long-Only Strategy - 2x Leverage
========================================================
Optimized futures strategy based on EPASuperTrendOptimized performance.
BTC/ETH only with 2x leverage for enhanced returns.

Author: Emre Uludaşdemir
Version: 2.0.0 - Futures Optimized

Key Features:
-------------
1. Optimized SuperTrend (period=14, multiplier=3.5)
2. 2x Leverage (balanced risk/reward)
3. BTC/ETH only (proven performance)
4. Leverage-adjusted risk management
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


class EPASuperTrendFuturesLong(IStrategy):
    """
    SuperTrend Futures - 2x Leverage Version
    
    Based on EPASuperTrendOptimized (+27.89% profit):
    - Optimized parameters: period=14, multiplier=3.5
    - 2x leverage for enhanced returns
    - Leverage-adjusted stoploss and trailing
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'  # Same as EPASuperTrendOptimized
    can_short = False  # LONG ONLY
    
    # ==========================================
    # OPTIMIZED SUPERTREND PARAMETERS
    # ==========================================
    supertrend_period = 14       # Optimized (was 10)
    supertrend_multiplier = 3.5  # Optimized (was 3.0)
    
    # ==========================================
    # ROI TABLE (adjusted for leverage)
    # ==========================================
    minimal_roi = {
        "0": 0.08,      # 8% (= 16% with 2x)
        "60": 0.05,     # 5% (= 10% with 2x)
        "120": 0.035,   # 3.5% (= 7% with 2x)
        "240": 0.02,    # 2% (= 4% with 2x)
        "360": 0.01,    # 1% (= 2% with 2x)
    }
    
    # ==========================================
    # RISK MANAGEMENT (leverage-adjusted)
    # ==========================================
    stoploss = -0.04  # 4% (= 8% effective with 2x leverage)
    
    trailing_stop = True
    trailing_stop_positive = 0.015   # 1.5% (= 3% with 2x)
    trailing_stop_positive_offset = 0.025  # 2.5% (= 5% with 2x)
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
                "max_allowed_drawdown": 0.20,  # Account for leverage
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
        
        # SuperTrend with OPTIMIZED parameters
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
        
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        
        # EMA for context (not used in entry)
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        # ATR for dynamic stoploss
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry: SuperTrend bullish flip only
        
        Same as EPASuperTrendOptimized (no EMA filter)
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
        ] = (1, 'st_futures_2x')
        
        return dataframe
    
    # ==========================================
    # EXIT LOGIC
    # ==========================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """No exit signals - using ROI/trailing/stoploss only"""
        return dataframe
    
    # ==========================================
    # LEVERAGE - 2x
    # ==========================================
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """2x leverage for balanced risk/reward"""
        return 2.0
    
    # ==========================================
    # CUSTOM STOPLOSS
    # ==========================================
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        """ATR-based dynamic stoploss (adjusted for leverage)"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return self.stoploss
        
        last_candle = dataframe.iloc[-1]
        
        if 'atr' in last_candle and last_candle['atr'] > 0:
            # ATR stop (adjusted for 2x leverage)
            atr_stop = -(last_candle['atr'] * 1.5) / current_rate
            return max(self.stoploss, atr_stop)
        
        return self.stoploss
