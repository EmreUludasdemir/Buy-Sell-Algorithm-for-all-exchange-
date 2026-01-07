"""
EPA SuperTrend Baseline Strategy
=================================
Simple trend-following strategy based on SuperTrend indicator.
No complex filters - just pure SuperTrend signals.

Author: Emre Uludaşdemir
Version: 1.0.0

Strategy Logic:
--------------
Entry: SuperTrend direction changes from -1 to 1 (bullish flip)
Exit: ROI / Trailing Stop / Stoploss only (no exit signals)

SuperTrend Settings:
-------------------
- ATR Period: 10 (standard crypto setting)
- Multiplier: 3.0 (Kıvanç default)
"""

import talib.abstract as ta
import pandas as pd
import numpy as np
from pandas import DataFrame
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade

# Import SuperTrend from kivanc_indicators
from kivanc_indicators import supertrend


class EPASuperTrend(IStrategy):
    """
    SuperTrend Baseline Strategy
    
    Simple trend-following approach:
    - Entry on SuperTrend bullish flip
    - Exit via ROI/trailing/stoploss only
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '2h'  # Same as other EPA strategies
    can_short = False  # Long only for now
    
    # ==========================================
    # STRATEGY PARAMETERS (Hyperopt-able)
    # ==========================================
    
    # SuperTrend parameters
    supertrend_period = 10
    supertrend_multiplier = 3.0
    
    # ==========================================
    # ROI TABLE - Conservative profit-taking
    # ==========================================
    minimal_roi = {
        "0": 0.15,      # 15% max profit target
        "120": 0.10,    # After 4h, take 10%
        "240": 0.07,    # After 8h, take 7%
        "480": 0.04,    # After 16h, take 4%
        "720": 0.02,    # After 24h, take 2%
    }
    
    # ==========================================
    # RISK MANAGEMENT
    # ==========================================
    stoploss = -0.08  # 8% stoploss
    
    # Trailing stop - let winners run
    trailing_stop = True
    trailing_stop_positive = 0.03    # Activate at 3% profit
    trailing_stop_positive_offset = 0.05  # Trail from 5%
    trailing_only_offset_is_reached = True
    
    # Exit settings
    use_exit_signal = False  # Only ROI/trailing/stoploss
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
                "stop_duration_candles": 3,  # Wait 3 candles after trade
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,  # Look back 48 candles
                "trade_limit": 4,              # Max 4 trades in period
                "stop_duration_candles": 12,   # Stop for 12 candles
                "max_allowed_drawdown": 0.2,   # 20% max drawdown
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
        """Calculate SuperTrend indicator"""
        
        # SuperTrend calculation
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
        
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        
        # EMA for additional context (optional filter)
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
        
        Conditions:
        1. SuperTrend direction changes from -1 to 1
        2. Volume confirmation (> 0)
        """
        
        dataframe.loc[
            (
                # SuperTrend bullish flip: direction was -1, now 1
                (dataframe['supertrend_direction'] == 1) &
                (dataframe['supertrend_direction'].shift(1) == -1) &
                
                # Volume exists
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    # ==========================================
    # EXIT LOGIC (disabled - using ROI/trailing only)
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
        """Conservative leverage - 1x for baseline testing"""
        return 1.0
    
    # ==========================================
    # CUSTOM STOPLOSS (ATR-based)
    # ==========================================
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        """
        Dynamic stoploss based on ATR.
        Uses the WIDER of: fixed stoploss or 2x ATR.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return self.stoploss
        
        last_candle = dataframe.iloc[-1]
        
        # ATR-based stop: 2x ATR below entry
        if 'atr' in last_candle and last_candle['atr'] > 0:
            atr_stop = -(last_candle['atr'] * 2) / current_rate
            
            # Return the wider (less negative) of the two
            return max(self.stoploss, atr_stop)
        
        return self.stoploss
