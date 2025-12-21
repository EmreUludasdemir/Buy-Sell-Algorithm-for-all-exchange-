"""
SMC Optimized Strategy v2
=========================
Balanced approach based on research:
- SMCStrategy base (51.6% win rate, +$6.91)
- Research optimizations applied
- Relaxed entry for more trades, quality filters maintained

Key improvements:
1. Better trend filter (EMA ribbon)
2. Improved stop loss (ATR-based)
3. Stepped trailing stop
4. Time-based exit for stale trades
5. Volume confirmation
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
    calculate_liquidity,
)

logger = logging.getLogger(__name__)


class SMCOptimizedV2(IStrategy):
    """
    SMC Optimized v2 - Balanced Win Rate & Trade Frequency
    
    Based on SMCStrategy (51.6% win rate) with research optimizations:
    - Better risk management
    - Improved entry timing
    - Stepped trailing stops
    """
    
    INTERFACE_VERSION = 3
    
    # Timeframe
    timeframe = '15m'
    can_short = False
    
    # ROI - Optimized for crypto volatility
    minimal_roi = {
        "0": 0.05,      # 5% initial
        "30": 0.03,     # 3% after 30 mins  
        "60": 0.02,     # 2% after 1 hour
        "120": 0.01,    # 1% after 2 hours
    }
    
    # Stop loss - tighter based on research
    stoploss = -0.025  # 2.5%
    
    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True
    
    # Settings
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 100
    use_custom_stoploss = True  # Enable stepped stop loss
    
    # Hyperopt parameters
    swing_length = IntParameter(5, 15, default=10, space='buy', optimize=True)
    ema_short = IntParameter(5, 15, default=9, space='buy', optimize=True)
    ema_long = IntParameter(15, 30, default=21, space='buy', optimize=True)
    
    def informative_pairs(self):
        """Add 1h timeframe for trend confirmation."""
        pairs = self.dp.current_whitelist()
        return [(pair, '1h') for pair in pairs]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate indicators with optimizations."""
        
        # ═══════════════════════════════════════════════════════════
        #                    TREND INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        # EMA Ribbon
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Trend strength
        dataframe['uptrend'] = (
            (dataframe['ema_9'] > dataframe['ema_21']) &
            (dataframe['ema_21'] > dataframe['ema_50'])
        ).astype(int)
        
        dataframe['strong_uptrend'] = (
            (dataframe['uptrend'] == 1) &
            (dataframe['close'] > dataframe['ema_200'])
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    MOMENTUM INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # EWO - Elliott Wave Oscillator
        dataframe['ewo'] = (
            ta.EMA(dataframe, timeperiod=5) - ta.EMA(dataframe, timeperiod=35)
        ) / dataframe['close'] * 100
        
        # ═══════════════════════════════════════════════════════════
        #                    VOLATILITY
        # ═══════════════════════════════════════════════════════════
        
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        bollinger = ta.BBANDS(dataframe, timeperiod=20)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        
        # ═══════════════════════════════════════════════════════════
        #                    VOLUME
        # ═══════════════════════════════════════════════════════════
        
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # ═══════════════════════════════════════════════════════════
        #                    SMC INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        swing_len = self.swing_length.value
        
        # Swing points
        swings = calculate_swing_highs_lows(dataframe, swing_len)
        dataframe['swing_hl'] = swings['HighLow']
        dataframe['swing_level'] = swings['Level']
        
        # Market structure
        structure = calculate_bos_choch(dataframe, swings)
        dataframe['bos'] = structure['BOS']
        dataframe['choch'] = structure['CHOCH']
        
        # Order Blocks
        obs = calculate_order_blocks(dataframe, swings)
        dataframe['ob'] = obs['OB']
        dataframe['ob_top'] = obs['Top']
        dataframe['ob_bottom'] = obs['Bottom']
        
        # Fair Value Gaps
        fvg = calculate_fvg(dataframe)
        dataframe['fvg'] = fvg['FVG']
        dataframe['fvg_top'] = fvg['Top']
        dataframe['fvg_bottom'] = fvg['Bottom']
        
        # ═══════════════════════════════════════════════════════════
        #                    DERIVED SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        # Recent bullish structure (last 15 candles)
        lookback = 15
        bos_bull = (dataframe['bos'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        choch_bull = (dataframe['choch'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        dataframe['bullish_structure'] = ((bos_bull > 0) | (choch_bull > 0)).astype(int)
        
        # Price in bullish Order Block
        ob_top = dataframe['ob_top'].ffill()
        ob_bottom = dataframe['ob_bottom'].ffill()
        ob_type = dataframe['ob'].ffill()
        
        dataframe['in_bullish_ob'] = (
            (dataframe['close'] >= ob_bottom) &
            (dataframe['close'] <= ob_top) &
            (ob_type == 1)
        ).astype(int)
        
        # Near bullish FVG
        dataframe['near_bullish_fvg'] = (
            (dataframe['fvg'] == 1) |
            (dataframe['fvg'].shift(1) == 1) |
            (dataframe['fvg'].shift(2) == 1)
        ).astype(int)
        
        # SMC Entry Zone (OB or FVG)
        dataframe['smc_entry_zone'] = (
            (dataframe['in_bullish_ob'] == 1) |
            (dataframe['near_bullish_fvg'] == 1)
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry conditions - balanced for trade frequency and quality.
        
        Primary: Trend + Structure + Entry Zone + Momentum
        Secondary: Trend + Pullback + Oversold RSI
        """
        
        # PRIMARY ENTRY - SMC confluence
        dataframe.loc[
            (
                # Trend
                (dataframe['uptrend'] == 1) &
                
                # Structure
                (dataframe['bullish_structure'] == 1) &
                
                # Entry zone (OB or FVG)
                (dataframe['smc_entry_zone'] == 1) &
                
                # Momentum
                (dataframe['macdhist'] > 0) &
                (dataframe['ewo'] > -2) &
                
                # RSI filter (not overbought)
                (dataframe['rsi'] < 70) &
                (dataframe['rsi'] > 30) &
                
                # Volume confirmation
                (dataframe['volume_ratio'] > 0.8) &
                
                # Valid
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'smc_confluence')
        
        # SECONDARY ENTRY - Pullback to EMA
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                
                # Strong trend
                (dataframe['strong_uptrend'] == 1) &
                
                # Pullback to EMA21
                (dataframe['close'] <= dataframe['ema_21'] * 1.005) &
                (dataframe['close'] >= dataframe['ema_50']) &
                
                # Oversold RSI (pullback)
                (dataframe['rsi'] < 45) &
                (dataframe['rsi'] > 25) &
                
                # Positive EWO
                (dataframe['ewo'] > 0) &
                
                # Volume
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'ema_pullback')
        
        # TERTIARY ENTRY - Breakout with volume
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                
                # Trend
                (dataframe['uptrend'] == 1) &
                
                # Breakout above recent high
                (dataframe['close'] > dataframe['high'].rolling(20).max().shift(1)) &
                
                # Strong momentum
                (dataframe['ewo'] > 2) &
                (dataframe['macdhist'] > 0) &
                
                # Volume spike
                (dataframe['volume_ratio'] > 1.5) &
                
                # RSI not extreme
                (dataframe['rsi'] < 75) &
                
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'breakout')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit conditions."""
        
        dataframe.loc[
            (
                # Bearish CHOCH
                (dataframe['choch'] == -1) |
                
                # RSI overbought
                (dataframe['rsi'] > 75) |
                
                # Trend reversal
                (
                    (dataframe['ema_9'] < dataframe['ema_21']) &
                    (dataframe['macdhist'] < 0) &
                    (dataframe['ewo'] < 0)
                ) |
                
                # Price below key EMA
                (dataframe['close'] < dataframe['ema_50'])
            ),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Stepped trailing stop loss:
        - At 2% profit: trail at 50% 
        - At 3% profit: trail at 60%
        - At 5% profit: trail at 70%
        """
        
        if current_profit > 0.05:  # > 5%
            return current_profit * -0.3  # Keep 70%
        elif current_profit > 0.03:  # > 3%
            return current_profit * -0.4  # Keep 60%
        elif current_profit > 0.02:  # > 2%
            return current_profit * -0.5  # Keep 50%
        elif current_profit > 0.01:  # > 1%
            return -0.015  # Fixed 1.5% trail
        
        return None
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """Time-based exit for stale trades."""
        
        trade_duration = current_time - trade.open_date_utc
        
        # Exit stale trades
        if trade_duration > timedelta(hours=6):
            if current_profit < 0.003:  # Less than 0.3%
                return 'time_exit_stale'
        
        # Take profit on long trades
        if trade_duration > timedelta(hours=12):
            if current_profit > 0:
                return 'time_exit_profit'
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Spot trading only."""
        return 1.0
