"""
EPA SuperTrend Multi-Pair Optimized Strategy
=============================================
Best parameters + multiple pairs for higher profit.

Author: Emre Uludaşdemir
Version: 2.1.0 - Multi-Pair Edition

Based on Hyperopt results:
- SuperTrend Period: 14 (optimal)
- SuperTrend Multiplier: 3.5 (optimal)
- 7 pairs for diversification
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


class EPASuperTrendMultiPair(IStrategy):
    """
    SuperTrend Multi-Pair Strategy
    
    Uses proven optimal parameters across 7 pairs.
    Conservative approach with proven settings.
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'
    can_short = False
    
    # ==========================================
    # PROVEN OPTIMAL PARAMETERS (from hyperopt)
    # ==========================================
    supertrend_period = 14
    supertrend_multiplier = 3.5
    
    # ==========================================
    # ROI TABLE - Same as optimized baseline
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
                "trade_limit": 6,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.2,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 8,
                "only_per_pair": True,
            },
        ]
    
    # ==========================================
    # INDICATORS
    # ==========================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate SuperTrend with optimal parameters"""
        
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
        
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        
        # EMA for context
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        # RSI for momentum
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry on SuperTrend flip with RSI confirmation"""
        
        dataframe.loc[
            (
                # SuperTrend bullish flip
                (dataframe['supertrend_direction'] == 1) &
                (dataframe['supertrend_direction'].shift(1) == -1) &
                
                # RSI not overbought (avoid buying at top)
                (dataframe['rsi'] < 70) &
                
                # Volume exists
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'st_multi')
        
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
    # POSITION SIZING BY PAIR
    # ==========================================
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: float, max_stake: float,
                           leverage: float, entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Stake sizing based on pair quality:
        - Majors (BTC, ETH): 100%
        - High quality alts (SOL, BNB): 85%
        - Medium alts (XRP, AVAX): 70%
        - High volatility (DOGE): 50%
        """
        majors = ['BTC/USDT', 'ETH/USDT']
        high_quality = ['SOL/USDT', 'BNB/USDT']
        medium = ['XRP/USDT', 'AVAX/USDT']
        
        if any(m in pair for m in majors):
            return proposed_stake
        elif any(m in pair for m in high_quality):
            return proposed_stake * 0.85
        elif any(m in pair for m in medium):
            return proposed_stake * 0.70
        else:  # DOGE etc
            return proposed_stake * 0.50
