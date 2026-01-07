"""
EPA SuperTrend Aggressive Strategy
===================================
Aggressive multi-pair strategy optimized for maximum profit.

Author: Emre Uludaşdemir
Version: 2.0.0 - Aggressive Edition

Key Features:
------------
- 7 pairs: BTC, ETH, SOL, BNB, XRP, DOGE, AVAX
- Faster ROI targets
- Lower multiplier for more trades
- 5 max open trades
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


class EPASuperTrendAggressive(IStrategy):
    """
    SuperTrend Aggressive - Maximum Profit Focus
    
    Targets: Higher trade frequency, faster exits, more pairs
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # ==========================================
    # HYPEROPT PARAMETERS
    # ==========================================
    
    # SuperTrend - wider range for optimization
    buy_st_period = CategoricalParameter([7, 8, 10, 12, 14, 16], default=10, space='buy', optimize=True)
    buy_st_multiplier = CategoricalParameter([2.0, 2.5, 3.0, 3.5], default=3.0, space='buy', optimize=True)
    
    # ==========================================
    # AGGRESSIVE ROI - Faster profit taking
    # ==========================================
    minimal_roi = {
        "0": 0.10,      # 10% max (was 15%)
        "60": 0.06,     # After 2.5h, take 6% (was 4h)
        "120": 0.04,    # After 5h, take 4%
        "240": 0.02,    # After 10h, take 2%
        "360": 0.01,    # After 15h, take 1%
    }
    
    # ==========================================
    # RISK MANAGEMENT
    # ==========================================
    stoploss = -0.06  # Tighter stoploss (was -0.08)
    
    # Trailing stop - more aggressive
    trailing_stop = True
    trailing_stop_positive = 0.02    # Start trailing at 2% (was 3%)
    trailing_stop_positive_offset = 0.03  # Trail from 3% (was 5%)
    trailing_only_offset_is_reached = True
    
    use_exit_signal = False
    process_only_new_candles = True
    startup_candle_count = 50
    
    # ==========================================
    # PROTECTIONS - Less restrictive
    # ==========================================
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 2,  # Shorter cooldown
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 6,  # More trades allowed
                "stop_duration_candles": 8,
                "max_allowed_drawdown": 0.25,  # Higher DD tolerance
            },
        ]
    
    # ==========================================
    # INDICATORS
    # ==========================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate SuperTrend for all hyperopt combinations"""
        
        for period in [7, 8, 10, 12, 14, 16]:
            for mult in [2.0, 2.5, 3.0, 3.5]:
                st_dir, st_line = supertrend(dataframe, period=period, multiplier=mult)
                dataframe[f'st_dir_{period}_{mult}'] = st_dir
        
        # RSI for potential momentum filter
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Aggressive entry on SuperTrend flip"""
        
        period = self.buy_st_period.value
        mult = self.buy_st_multiplier.value
        col = f'st_dir_{period}_{mult}'
        
        conditions = (
            (dataframe[col] == 1) &
            (dataframe[col].shift(1) == -1) &
            (dataframe['volume'] > 0)
        )
        
        dataframe.loc[conditions, ['enter_long', 'enter_tag']] = (1, f'st_agg_{period}_{mult}')
        
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
    
    # ==========================================
    # CUSTOM STAKE - Position sizing by pair
    # ==========================================
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: float, max_stake: float,
                           leverage: float, entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Stake sizing based on pair volatility:
        - Majors (BTC, ETH): 100%
        - Mid-caps (SOL, BNB): 80%
        - Small-caps (DOGE, XRP, AVAX): 60%
        """
        majors = ['BTC/USDT', 'ETH/USDT']
        midcaps = ['SOL/USDT', 'BNB/USDT']
        
        if any(m in pair for m in majors):
            return proposed_stake
        elif any(m in pair for m in midcaps):
            return proposed_stake * 0.8
        else:
            return proposed_stake * 0.6
