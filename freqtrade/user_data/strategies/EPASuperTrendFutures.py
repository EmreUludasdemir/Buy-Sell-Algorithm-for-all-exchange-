"""
EPA SuperTrend Futures Strategy
================================
Futures-ready trend-following strategy with LONG and SHORT support.
Based on SuperTrend indicator - optimized for crypto futures.

Author: Emre Uludaşdemir
Version: 1.0.0

Strategy Logic:
--------------
LONG Entry: SuperTrend direction changes from -1 to 1 (bullish flip)
SHORT Entry: SuperTrend direction changes from 1 to -1 (bearish flip)
Exit: ROI / Trailing Stop / Stoploss only

Futures Settings:
-----------------
- Trading Mode: Futures (isolated margin)
- Leverage: 3x (conservative)
- Both LONG and SHORT enabled
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


class EPASuperTrendFutures(IStrategy):
    """
    SuperTrend Futures Strategy
    
    Bi-directional trend-following:
    - LONG on SuperTrend bullish flip
    - SHORT on SuperTrend bearish flip
    - Exit via ROI/trailing/stoploss
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '4h'  # Longer timeframe for futures - less noise
    can_short = True  # Enable SHORT trading
    
    # ==========================================
    # STRATEGY PARAMETERS
    # ==========================================
    
    # SuperTrend parameters
    supertrend_period = 10
    supertrend_multiplier = 3.0
    
    # ==========================================
    # ROI TABLE - Conservative for futures
    # ==========================================
    minimal_roi = {
        "0": 0.12,      # 12% max profit target
        "60": 0.08,     # After 2h, take 8%
        "120": 0.05,    # After 4h, take 5%
        "240": 0.03,    # After 8h, take 3%
        "480": 0.02,    # After 16h, take 2%
    }
    
    # ==========================================
    # RISK MANAGEMENT
    # ==========================================
    stoploss = -0.06  # 6% stoploss (tighter for futures)
    
    # Trailing stop - let winners run
    trailing_stop = True
    trailing_stop_positive = 0.025   # Activate at 2.5% profit
    trailing_stop_positive_offset = 0.04  # Trail from 4%
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
                "stop_duration_candles": 2,  # Faster recovery for futures
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 6,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.15,  # Tighter for futures
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 6,
                "only_per_pair": True,
            },
        ]
    
    # ==========================================
    # INDICATORS
    # ==========================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate SuperTrend and supporting indicators"""
        
        # SuperTrend calculation
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period,
            multiplier=self.supertrend_multiplier
        )
        
        dataframe['supertrend_direction'] = st_direction
        dataframe['supertrend_line'] = st_line
        
        # EMA for trend context
        dataframe['ema_50'] = ta.EMA(dataframe['close'], timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe['close'], timeperiod=200)
        
        # ATR for volatility-based calculations
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # RSI for overbought/oversold filter
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)
        
        return dataframe
    
    # ==========================================
    # ENTRY LOGIC
    # ==========================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Signals:
        
        LONG: SuperTrend bullish flip (direction -1 -> 1)
        SHORT: SuperTrend bearish flip (direction 1 -> -1)
        """
        
        # ==========================================
        # LONG ENTRY
        # ==========================================
        dataframe.loc[
            (
                # SuperTrend bullish flip: direction was -1, now 1
                (dataframe['supertrend_direction'] == 1) &
                (dataframe['supertrend_direction'].shift(1) == -1) &
                
                # Volume exists
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'supertrend_long')
        
        # ==========================================
        # SHORT ENTRY
        # ==========================================
        dataframe.loc[
            (
                # SuperTrend bearish flip: direction was 1, now -1
                (dataframe['supertrend_direction'] == -1) &
                (dataframe['supertrend_direction'].shift(1) == 1) &
                
                # Volume exists
                (dataframe['volume'] > 0)
            ),
            ['enter_short', 'enter_tag']
        ] = (1, 'supertrend_short')
        
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
        """
        Conservative leverage for futures.
        
        - Default: 3x leverage
        - Major pairs (BTC, ETH): 3x
        - Altcoins: 2x (more volatile)
        """
        major_pairs = ['BTC/USDT', 'ETH/USDT']
        
        if any(major in pair for major in major_pairs):
            return 3.0
        else:
            return 2.0
    
    # ==========================================
    # CUSTOM STOPLOSS (ATR-based)
    # ==========================================
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        """
        Dynamic stoploss based on ATR.
        Uses the WIDER of: fixed stoploss or 1.5x ATR.
        More conservative for futures.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return self.stoploss
        
        last_candle = dataframe.iloc[-1]
        
        # ATR-based stop: 1.5x ATR
        if 'atr' in last_candle and last_candle['atr'] > 0:
            atr_stop = -(last_candle['atr'] * 1.5) / current_rate
            
            # Return the wider (less negative) of the two
            return max(self.stoploss, atr_stop)
        
        return self.stoploss
    
    # ==========================================
    # CUSTOM STAKE AMOUNT
    # ==========================================
    def custom_stake_amount(self, pair: str, current_time: datetime,
                            current_rate: float, proposed_stake: float,
                            min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str],
                            side: str, **kwargs) -> float:
        """
        Dynamic stake sizing based on pair volatility.
        
        Major pairs: Full stake
        Altcoins: 70% stake (higher volatility)
        """
        major_pairs = ['BTC/USDT', 'ETH/USDT']
        
        if any(major in pair for major in major_pairs):
            return proposed_stake
        else:
            return proposed_stake * 0.7
