"""
EPA Momentum Aggressive Strategy
=================================
Simplified trend-following strategy designed to capture maximum market gains.
Removes most filters in favor of riding momentum.

Key Differences from EPAUltimateV3:
- Only 3 entry conditions: Supertrend + EMA cross + ADX
- NO choppiness filter
- NO SMC zones required
- NO volume filter
- NO HTF alignment
- Trailing stop ENABLED for letting winners run
- More aggressive ROI targets

Author: Emre Uludaşdemir
Version: 1.0.0 - Aggressive Momentum Capture
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as pta
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, BooleanParameter
from freqtrade.persistence import Trade

# Import Kıvanç Özbilgiç indicators
from kivanc_indicators import add_kivanc_indicators

logger = logging.getLogger(__name__)


class EPAMomentumAggressive(IStrategy):
    """
    Aggressive Momentum Strategy - Maximize Market Capture
    
    Philosophy: Ride the trend, don't filter it out!
    
    Entry: Supertrend + EMA cross + ADX > 20
    Exit: Trailing stop + ROI
    """
    
    INTERFACE_VERSION = 3
    timeframe = '2h'
    can_short = False

    # AGGRESSIVE ROI - Faster profit taking
    minimal_roi = {
        "0": 0.30,      # 30% max target
        "60": 0.15,     # 15% after 1h
        "180": 0.08,    # 8% after 3h
        "360": 0.03,    # 3% after 6h
        "720": 0.01     # 1% after 12h
    }

    # Moderate stoploss
    stoploss = -0.08  # 8% stoploss

    # TRAILING STOP ENABLED - Let winners run!
    trailing_stop = True
    trailing_stop_positive = 0.03      # Start trailing at 3% profit
    trailing_stop_positive_offset = 0.05  # Offset of 5%
    trailing_only_offset_is_reached = True
    
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    startup_candle_count: int = 100  # Need enough candles for indicators
    
    # Minimal protections - let it trade
    @property
    def protections(self):
        return [
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": False
            }
        ]
    
    # ==================== SIMPLIFIED PARAMETERS ====================
    
    # EMA Settings
    fast_ema = IntParameter(5, 15, default=8, space='buy', optimize=True)
    slow_ema = IntParameter(15, 35, default=21, space='buy', optimize=True)
    
    # ADX - Lower threshold for more entries
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(15, 30, default=20, space='buy', optimize=True)
    
    # Supertrend - Main signal
    supertrend_period = IntParameter(7, 15, default=10, space='buy', optimize=True)
    supertrend_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='buy', optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate minimal indicators for fast momentum trading."""
        
        # EMAs
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        
        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        # Supertrend from Kıvanç indicators
        dataframe = add_kivanc_indicators(
            dataframe,
            supertrend_period=self.supertrend_period.value,
            supertrend_multiplier=self.supertrend_multiplier.value,
            halftrend_amplitude=2,
            halftrend_deviation=2.0,
            qqe_rsi_period=14,
            qqe_factor=4.238,
            wae_sensitivity=150
        )
        
        # ATR for volatility awareness
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        SIMPLIFIED ENTRY - Only 3 conditions:
        1. Supertrend bullish
        2. EMA fast > slow (trend direction)
        3. ADX > threshold (trend strength)
        """
        
        # SIMPLIFIED: Just Supertrend + EMA cross
        # Removed ADX requirement to get more trades
        dataframe.loc[
            (dataframe['supertrend_direction'] == 1) &  # Supertrend bullish
            (dataframe['ema_fast'] > dataframe['ema_slow']) &  # EMA cross up
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on trend reversal."""
        
        dataframe.loc[
            (dataframe['supertrend_direction'] == -1) |  # Supertrend flips
            (dataframe['ema_fast'] < dataframe['ema_slow']),  # EMA cross down
            'exit_long'
        ] = 1
        
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
