"""
SMC High Profit Strategy
=========================
Optimized for MAXIMUM PROFIT with acceptable drawdown.

Key changes from base SMCStrategy:
1. Higher ROI targets (10-15% vs 5%)
2. Wider stop loss (5% vs 3%) for breathing room
3. Aggressive trailing stop
4. Stronger entry filters (higher confluence)
5. Bull market bias (trend filter)
6. Larger position size in config
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

from smc_indicators import (
    calculate_swing_highs_lows,
    calculate_bos_choch,
    calculate_order_blocks,
    calculate_fvg,
)

logger = logging.getLogger(__name__)


class SMCHighProfit(IStrategy):
    """
    SMC High Profit - Optimized for Maximum Returns
    
    Target: 15-20% monthly returns with <10% drawdown
    
    Key Features:
    - Aggressive ROI (10-15%)
    - Strong trend filter
    - High confluence entry (multiple confirmations)
    - Stepped trailing stop
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '15m'
    can_short = False
    
    # AGGRESSIVE ROI - Higher targets
    minimal_roi = {
        "0": 0.15,      # 15% initial target (very aggressive)
        "60": 0.10,     # 10% after 1 hour
        "120": 0.07,    # 7% after 2 hours
        "240": 0.04,    # 4% after 4 hours
        "480": 0.02,    # 2% after 8 hours
    }
    
    # Wider stop loss for breathing room
    stoploss = -0.05  # 5% stop loss
    
    # Aggressive trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.03      # Trail at 3% profit
    trailing_stop_positive_offset = 0.05  # After 5% profit
    trailing_only_offset_is_reached = True
    
    # Settings
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 150
    use_custom_stoploss = True
    
    # Hyperparameters
    swing_length = IntParameter(8, 15, default=12, space='buy', optimize=True)
    min_volume_factor = DecimalParameter(1.0, 2.0, default=1.3, space='buy', optimize=True)
    
    def informative_pairs(self):
        """4h and 1h for trend confirmation."""
        pairs = self.dp.current_whitelist()
        return [
            (pair, '1h') for pair in pairs
        ] + [
            (pair, '4h') for pair in pairs
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate indicators for high-profit setup."""
        
        # ═══════════════════════════════════════════════════════════
        #                    TREND (Strong filter)
        # ═══════════════════════════════════════════════════════════
        
        # EMA cascade for ultra-strong trend
        dataframe['ema_8'] = ta.EMA(dataframe, timeperiod=8)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Perfect uptrend (all EMAs aligned)
        dataframe['perfect_uptrend'] = (
            (dataframe['ema_8'] > dataframe['ema_21']) &
            (dataframe['ema_21'] > dataframe['ema_50']) &
            (dataframe['ema_50'] > dataframe['ema_100']) &
            (dataframe['close'] > dataframe['ema_200'])
        ).astype(int)
        
        # Trend acceleration (price pulling away from EMAs)
        dataframe['trend_strength'] = (
            (dataframe['close'] - dataframe['ema_50']) / dataframe['close'] * 100
        )
        
        # ═══════════════════════════════════════════════════════════
        #                    MOMENTUM
        # ═══════════════════════════════════════════════════════════
        
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=7)
        
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # MACD momentum increasing
        dataframe['macd_increasing'] = (
            (dataframe['macdhist'] > dataframe['macdhist'].shift(1)) &
            (dataframe['macdhist'] > 0)
        ).astype(int)
        
        # Stochastic RSI for oversold entry
        stoch = ta.STOCH(dataframe)
        dataframe['stoch_k'] = stoch['slowk']
        dataframe['stoch_d'] = stoch['slowd']
        
        # ═══════════════════════════════════════════════════════════
        #                    VOLUME
        # ═══════════════════════════════════════════════════════════
        
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # Volume spike detection
        dataframe['volume_spike'] = (
            dataframe['volume_ratio'] > self.min_volume_factor.value
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    ATR for volatility
        # ═══════════════════════════════════════════════════════════
        
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # Good volatility (not too high, not too low)
        dataframe['good_volatility'] = (
            (dataframe['atr_pct'] > 0.5) & (dataframe['atr_pct'] < 3.0)
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    SMC INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        swing_len = self.swing_length.value
        
        swings = calculate_swing_highs_lows(dataframe, swing_len)
        dataframe['swing_hl'] = swings['HighLow']
        
        structure = calculate_bos_choch(dataframe, swings)
        dataframe['bos'] = structure['BOS']
        dataframe['choch'] = structure['CHOCH']
        
        obs = calculate_order_blocks(dataframe, swings)
        dataframe['ob'] = obs['OB']
        dataframe['ob_top'] = obs['Top']
        dataframe['ob_bottom'] = obs['Bottom']
        
        fvg = calculate_fvg(dataframe)
        dataframe['fvg'] = fvg['FVG']
        
        # ═══════════════════════════════════════════════════════════
        #                    DERIVED SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        # Recent bullish structure
        lookback = 12
        bos_bull = (dataframe['bos'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        choch_bull = (dataframe['choch'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        dataframe['bullish_structure'] = ((bos_bull > 0) | (choch_bull > 0)).astype(int)
        
        # In order block
        ob_top = dataframe['ob_top'].ffill()
        ob_bottom = dataframe['ob_bottom'].ffill()
        ob_type = dataframe['ob'].ffill()
        
        dataframe['in_bullish_ob'] = (
            (dataframe['close'] >= ob_bottom) &
            (dataframe['close'] <= ob_top) &
            (ob_type == 1)
        ).astype(int)
        
        # Near FVG
        dataframe['near_fvg'] = (
            (dataframe['fvg'] == 1) |
            (dataframe['fvg'].shift(1) == 1) |
            (dataframe['fvg'].shift(2) == 1)
        ).astype(int)
        
        # Breakout pattern
        dataframe['breakout'] = (
            (dataframe['close'] > dataframe['high'].rolling(20).max().shift(1)) &
            (dataframe['volume_spike'] == 1)
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        High-profit entries - ONLY take the best setups:
        1. Perfect trend + SMC zone + Momentum + Volume
        2. Breakout with volume
        """
        
        # PREMIUM ENTRY - Full confluence (highest probability)
        dataframe.loc[
            (
                # Perfect trend
                (dataframe['perfect_uptrend'] == 1) &
                
                # Bullish structure
                (dataframe['bullish_structure'] == 1) &
                
                # In SMC zone
                ((dataframe['in_bullish_ob'] == 1) | (dataframe['near_fvg'] == 1)) &
                
                # Momentum confirmation
                (dataframe['macd_increasing'] == 1) &
                (dataframe['rsi'] > 40) &
                (dataframe['rsi'] < 65) &
                
                # Volume confirmation
                (dataframe['volume_spike'] == 1) &
                
                # Good volatility
                (dataframe['good_volatility'] == 1) &
                
                # Trend strength positive
                (dataframe['trend_strength'] > 0) &
                
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'premium_smc')
        
        # BREAKOUT ENTRY - Momentum play
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                
                # Breakout
                (dataframe['breakout'] == 1) &
                
                # Strong trend
                (dataframe['perfect_uptrend'] == 1) &
                
                # MACD positive and increasing
                (dataframe['macd'] > 0) &
                (dataframe['macd_increasing'] == 1) &
                
                # RSI not overbought
                (dataframe['rsi'] < 70) &
                
                # Volume explosion
                (dataframe['volume_ratio'] > 1.5) &
                
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'breakout_momentum')
        
        # PULLBACK ENTRY - Buy the dip in strong trend
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                
                # Strong trend
                (dataframe['perfect_uptrend'] == 1) &
                
                # Pullback to EMA21
                (dataframe['low'] <= dataframe['ema_21']) &
                (dataframe['close'] > dataframe['ema_21']) &
                
                # Bullish candle
                (dataframe['close'] > dataframe['open']) &
                
                # Stochastic oversold
                (dataframe['stoch_k'] < 30) &
                
                # RSI reset
                (dataframe['rsi'] < 50) &
                (dataframe['rsi'] > 35) &
                
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'pullback_dip')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on trend weakness or reversal signals."""
        
        dataframe.loc[
            (
                # Bearish CHOCH (strongest exit)
                (dataframe['choch'] == -1) |
                
                # RSI extreme overbought
                (dataframe['rsi'] > 80) |
                
                # MACD bearish crossover
                (
                    (dataframe['macd'] < dataframe['macdsignal']) &
                    (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1)) &
                    (dataframe['macdhist'] < 0)
                ) |
                
                # Trend breakdown
                (
                    (dataframe['close'] < dataframe['ema_50']) &
                    (dataframe['ema_8'] < dataframe['ema_21'])
                )
            ),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Stepped trailing for high profits:
        - 5% profit: Keep 60%
        - 8% profit: Keep 70%
        - 12% profit: Keep 80%
        """
        
        if current_profit > 0.12:  # > 12%
            return current_profit * -0.2  # Keep 80%
        elif current_profit > 0.08:  # > 8%
            return current_profit * -0.3  # Keep 70%
        elif current_profit > 0.05:  # > 5%
            return current_profit * -0.4  # Keep 60%
        elif current_profit > 0.03:  # > 3%
            return -0.02  # Fixed 2% trail
        
        return None
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """Take profit at milestones or exit stale trades."""
        
        # Quick profit take
        if current_profit > 0.10:  # > 10%
            trade_duration = current_time - trade.open_date_utc
            if trade_duration > timedelta(hours=4):
                return 'take_profit_10pct'
        
        # Exit stale trades
        trade_duration = current_time - trade.open_date_utc
        if trade_duration > timedelta(hours=12):
            if current_profit < 0.02:
                return 'time_exit'
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Spot only."""
        return 1.0
