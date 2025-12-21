"""
EPA Strategy - Efloud Price Action for Freqtrade
=================================================
Based on @EfloudTheSurfer's methodology and Pine Script v6.

Key concepts from research:
1. EMA Cross + Breakout + Pullback signals
2. SFP (Swing Failure Pattern) - fake breakouts
3. Breaker Blocks - failed OB becomes S/R
4. Mitigation Blocks - institutional rebalancing
5. Simple trend following with trailing stops

Settings from Pine Script:
- Fast EMA: 10, Slow EMA: 30, Trend EMA: 100
- Stop Loss: 5%, Take Profit: 10%
- Trailing: 3%
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


class EPAStrategy(IStrategy):
    """
    EPA Strategy - Efloud Price Action
    
    Based on the EPA Pine Script v6:
    - EMA Cross signals (Fast crosses Slow)
    - Breakout signals (new highs/lows)
    - Pullback signals (to EMA in trend)
    - SFP detection (fake breakouts)
    
    Risk Management:
    - Stop Loss: 5%
    - Take Profit: 10%
    - Trailing: 3%
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '15m'
    can_short = False
    
    # ROI - Based on EPA settings (10% TP)
    minimal_roi = {
        "0": 0.10,     # 10% - original EPA setting
        "60": 0.05,    # 5% after 1 hour
        "120": 0.03,   # 3% after 2 hours
        "240": 0.01,   # 1% after 4 hours
    }
    
    # Stop Loss - 5% from EPA
    stoploss = -0.05
    
    # Trailing - 3% from EPA
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    # Settings
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 100
    
    # EPA parameters from Pine Script
    fast_ema = IntParameter(5, 15, default=10, space='buy', optimize=True)
    slow_ema = IntParameter(20, 50, default=30, space='buy', optimize=True)
    trend_ema = IntParameter(50, 150, default=100, space='buy', optimize=True)
    breakout_len = IntParameter(10, 30, default=20, space='buy', optimize=True)
    
    def informative_pairs(self):
        """Weekly trend filter like EPA."""
        pairs = self.dp.current_whitelist()
        return [(pair, '1h') for pair in pairs]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate EPA indicators."""
        
        # ═══════════════════════════════════════════════════════════
        #                    EPA EMAs (from Pine Script)
        # ═══════════════════════════════════════════════════════════
        
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        dataframe['ema_trend'] = ta.EMA(dataframe, timeperiod=self.trend_ema.value)
        
        # ═══════════════════════════════════════════════════════════
        #                    TREND DETERMINATION
        # ═══════════════════════════════════════════════════════════
        
        # Simple trend: Fast EMA above/below Slow EMA
        dataframe['uptrend'] = (dataframe['ema_fast'] > dataframe['ema_slow']).astype(int)
        dataframe['downtrend'] = (dataframe['ema_fast'] < dataframe['ema_slow']).astype(int)
        
        # Strong trend: Also above/below Trend EMA
        dataframe['strong_uptrend'] = (
            (dataframe['uptrend'] == 1) &
            (dataframe['close'] > dataframe['ema_trend'])
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    EMA CROSS SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        # EMA cross-over/under
        dataframe['ema_cross_up'] = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        dataframe['ema_cross_down'] = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    BREAKOUT SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        blen = self.breakout_len.value
        
        # Highest high and lowest low of last N bars (shifted by 1)
        dataframe['highest_high'] = dataframe['high'].rolling(blen).max().shift(1)
        dataframe['lowest_low'] = dataframe['low'].rolling(blen).min().shift(1)
        
        # Breakout up: close > highest high and previous close was below
        dataframe['breakout_up'] = (
            (dataframe['close'] > dataframe['highest_high']) &
            (dataframe['close'].shift(1) <= dataframe['highest_high'])
        ).astype(int)
        
        # Breakout down
        dataframe['breakout_down'] = (
            (dataframe['close'] < dataframe['lowest_low']) &
            (dataframe['close'].shift(1) >= dataframe['lowest_low'])
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    PULLBACK SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        # Pullback to Fast EMA in uptrend
        dataframe['pullback_up'] = (
            (dataframe['uptrend'] == 1) &
            (dataframe['low'] <= dataframe['ema_fast']) &
            (dataframe['close'] > dataframe['ema_fast']) &
            (dataframe['close'] > dataframe['open'])  # Bullish candle
        ).astype(int)
        
        # Pullback to Fast EMA in downtrend
        dataframe['pullback_down'] = (
            (dataframe['downtrend'] == 1) &
            (dataframe['high'] >= dataframe['ema_fast']) &
            (dataframe['close'] < dataframe['ema_fast']) &
            (dataframe['close'] < dataframe['open'])  # Bearish candle
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    SFP (Swing Failure Pattern)
        # ═══════════════════════════════════════════════════════════
        
        # SFP Bullish: Price breaks below recent low then closes above
        dataframe['recent_low'] = dataframe['low'].rolling(10).min().shift(1)
        dataframe['sfp_bullish'] = (
            (dataframe['low'] < dataframe['recent_low']) &
            (dataframe['close'] > dataframe['recent_low']) &
            (dataframe['close'] > dataframe['open'])
        ).astype(int)
        
        # SFP Bearish: Price breaks above recent high then closes below
        dataframe['recent_high'] = dataframe['high'].rolling(10).max().shift(1)
        dataframe['sfp_bearish'] = (
            (dataframe['high'] > dataframe['recent_high']) &
            (dataframe['close'] < dataframe['recent_high']) &
            (dataframe['close'] < dataframe['open'])
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════
        #                    ADDITIONAL INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        # RSI for filter
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ATR for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # Volume
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # ═══════════════════════════════════════════════════════════
        #                    SMC INDICATORS (Optional)
        # ═══════════════════════════════════════════════════════════
        
        try:
            swings = calculate_swing_highs_lows(dataframe, 10)
            structure = calculate_bos_choch(dataframe, swings)
            dataframe['bos'] = structure['BOS']
            dataframe['choch'] = structure['CHOCH']
            
            obs = calculate_order_blocks(dataframe, swings)
            dataframe['ob'] = obs['OB']
            dataframe['ob_top'] = obs['Top']
            dataframe['ob_bottom'] = obs['Bottom']
        except Exception as e:
            logger.debug(f"SMC indicators failed: {e}")
            dataframe['bos'] = 0
            dataframe['choch'] = 0
            dataframe['ob'] = 0
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        EPA entry conditions:
        1. EMA Cross Up
        2. Breakout Up
        3. Pullback Up
        4. SFP Bullish (bonus)
        
        All filtered by uptrend
        """
        
        # PRIMARY: EMA Cross + Uptrend
        dataframe.loc[
            (
                (dataframe['ema_cross_up'] == 1) &
                (dataframe['uptrend'] == 1) &
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 70) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'epa_ema_cross')
        
        # SECONDARY: Breakout with strong trend
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                (dataframe['breakout_up'] == 1) &
                (dataframe['strong_uptrend'] == 1) &
                (dataframe['volume_ratio'] > 1.0) &
                (dataframe['rsi'] < 75) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'epa_breakout')
        
        # TERTIARY: Pullback in uptrend
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                (dataframe['pullback_up'] == 1) &
                (dataframe['strong_uptrend'] == 1) &
                (dataframe['rsi'] > 35) &
                (dataframe['rsi'] < 55) &  # Pullback zone
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'epa_pullback')
        
        # BONUS: SFP Bullish (high probability reversal)
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                (dataframe['sfp_bullish'] == 1) &
                (dataframe['uptrend'] == 1) &
                (dataframe['rsi'] < 60) &
                (dataframe['volume_ratio'] > 0.8) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'epa_sfp')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        EPA exit conditions:
        1. EMA Cross Down (trend reversal)
        2. SFP Bearish (reversal signal)
        3. RSI overbought
        4. CHOCH (market structure change)
        """
        
        dataframe.loc[
            (
                # Trend reversal
                (dataframe['ema_cross_down'] == 1) |
                
                # SFP Bearish
                (dataframe['sfp_bearish'] == 1) |
                
                # RSI overbought
                (dataframe['rsi'] > 75) |
                
                # Bearish CHOCH
                (dataframe['choch'] == -1)
            ),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        EPA trailing stop logic:
        - After 3% profit: trail at 50%
        - After 5% profit: trail at 60%
        - After 8% profit: trail at 70%
        """
        
        if current_profit > 0.08:
            return current_profit * -0.3  # Keep 70%
        elif current_profit > 0.05:
            return current_profit * -0.4  # Keep 60%
        elif current_profit > 0.03:
            return current_profit * -0.5  # Keep 50%
        
        return None
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """Exit stale trades."""
        
        trade_duration = current_time - trade.open_date_utc
        
        # Exit after 8 hours with minimal profit
        if trade_duration > timedelta(hours=8):
            if current_profit < 0.01:
                return 'time_exit'
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Spot trading only."""
        return 1.0
