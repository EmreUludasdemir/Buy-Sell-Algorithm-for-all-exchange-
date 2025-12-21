"""
SMC Pro Strategy - Optimized for High Win Rate
===============================================
Based on research findings:
- Machete Strategy (664% profit)
- RSI_MACD_BB (94% win rate)
- SMC optimization (liquidity sweeps + OB/FVG confluence)

Key optimizations:
1. Liquidity sweep BEFORE entry (institutional trigger)
2. OB + FVG confluence requirement
3. Multi-timeframe trend alignment
4. Stronger entry filters (RSI, Volume, EWO)
5. Stepped trailing stop loss
6. Time-based exit optimization
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter
from freqtrade.persistence import Trade

from smc_indicators import (
    calculate_swing_highs_lows,
    calculate_bos_choch,
    calculate_order_blocks,
    calculate_fvg,
    calculate_liquidity,
)

logger = logging.getLogger(__name__)


class SMCProStrategy(IStrategy):
    """
    SMC Pro - Optimized Smart Money Strategy
    
    Based on extensive research, this strategy implements:
    - Liquidity sweep confirmation before entry
    - OB + FVG confluence zones
    - Multi-timeframe trend alignment
    - Strict entry filters for high win rate
    - Stepped trailing stop loss
    """
    
    INTERFACE_VERSION = 3
    
    # Timeframe
    timeframe = '15m'
    can_short = False
    
    # Optimized ROI - More aggressive for crypto
    minimal_roi = {
        "0": 0.08,      # 8% initial target
        "20": 0.05,     # 5% after 20 mins
        "40": 0.03,     # 3% after 40 mins
        "60": 0.02,     # 2% after 1 hour
        "120": 0.01,    # 1% after 2 hours
    }
    
    # Tighter stop loss with better R:R
    stoploss = -0.02  # 2% stop loss
    
    # Stepped trailing stop (based on research)
    trailing_stop = True
    trailing_stop_positive = 0.01      # Start trailing at 1%
    trailing_stop_positive_offset = 0.015  # After 1.5% profit
    trailing_only_offset_is_reached = True
    
    # Process settings
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 100
    
    # Optimized hyperparameters
    swing_length = IntParameter(5, 15, default=8, space='buy', optimize=True)
    rsi_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    rsi_buy_threshold = IntParameter(25, 45, default=35, space='buy', optimize=True)
    volume_factor = DecimalParameter(1.0, 2.0, default=1.2, space='buy', optimize=True)
    
    # Sell parameters
    rsi_sell_threshold = IntParameter(65, 85, default=75, space='sell', optimize=True)
    
    def informative_pairs(self):
        """Multi-timeframe analysis - critical for SMC."""
        pairs = self.dp.current_whitelist()
        return [
            (pair, '1h') for pair in pairs
        ] + [
            (pair, '4h') for pair in pairs
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all optimized indicators."""
        
        # ═══════════════════════════════════════════════════════════
        #                    CORE TECHNICAL INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        # Multiple EMAs for trend strength
        dataframe['ema_8'] = ta.EMA(dataframe, timeperiod=8)
        dataframe['ema_13'] = ta.EMA(dataframe, timeperiod=13)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_55'] = ta.EMA(dataframe, timeperiod=55)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # RSI with optimized period
        rsi_period = self.rsi_period.value
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=rsi_period)
        
        # EWO - Elliott Wave Oscillator (key for momentum)
        dataframe['ewo'] = (
            ta.EMA(dataframe, timeperiod=5) - ta.EMA(dataframe, timeperiod=35)
        ) / dataframe['close'] * 100
        
        # MACD for momentum confirmation
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (
            dataframe['bb_upper'] - dataframe['bb_lower']
        )
        
        # ATR for volatility and stops
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = dataframe['atr'] / dataframe['close'] * 100
        
        # Volume analysis
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # Money Flow Index
        dataframe['mfi'] = ta.MFI(dataframe, timeperiod=14)
        
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
        
        # Liquidity
        liq = calculate_liquidity(dataframe, swings)
        dataframe['liquidity'] = liq['Liquidity']
        dataframe['liquidity_level'] = liq['Level']
        dataframe['liquidity_swept'] = liq['Swept']
        
        # ═══════════════════════════════════════════════════════════
        #                    CONFLUENCE SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        # Strong uptrend confirmation
        dataframe['strong_uptrend'] = (
            (dataframe['ema_8'] > dataframe['ema_13']) &
            (dataframe['ema_13'] > dataframe['ema_21']) &
            (dataframe['ema_21'] > dataframe['ema_55']) &
            (dataframe['close'] > dataframe['ema_200'])
        ).astype(int)
        
        # Recent bullish structure (BOS or CHOCH in last 10 candles)
        lookback = 10
        bos_bull = (dataframe['bos'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        choch_bull = (dataframe['choch'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        dataframe['bullish_structure'] = ((bos_bull > 0) | (choch_bull > 0)).astype(int)
        
        bos_bear = (dataframe['bos'] == -1).rolling(lookback, min_periods=1).max().fillna(0)
        choch_bear = (dataframe['choch'] == -1).rolling(lookback, min_periods=1).max().fillna(0)
        dataframe['bearish_structure'] = ((bos_bear > 0) | (choch_bear > 0)).astype(int)
        
        # Price in bullish Order Block
        dataframe['in_bullish_ob'] = (
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['ob'].ffill() == 1)
        ).astype(int)
        
        # Bullish FVG present
        dataframe['bullish_fvg'] = (dataframe['fvg'] == 1).astype(int)
        
        # Recent liquidity sweep (KEY - institucional trigger)
        # Fixed: convert to int before rolling to avoid type errors
        liq_swept_int = dataframe['liquidity_swept'].notna().astype(int)
        liq_bullish_int = (dataframe['liquidity'] == 1).astype(int)
        swept_recent = liq_swept_int.rolling(5, min_periods=1).max().fillna(0)
        bull_recent = liq_bullish_int.rolling(5, min_periods=1).max().fillna(0)
        dataframe['liquidity_sweep_bull'] = ((swept_recent > 0) & (bull_recent > 0)).astype(int)
        
        # OB + FVG Confluence (high probability zone)
        dataframe['ob_fvg_confluence'] = (
            (dataframe['in_bullish_ob'] == 1) | 
            (dataframe['bullish_fvg'] == 1)
        ).astype(int)
        
        # Momentum confirmation
        dataframe['momentum_bullish'] = (
            (dataframe['ewo'] > 0) &
            (dataframe['macdhist'] > 0) &
            (dataframe['rsi'] > 40) &
            (dataframe['rsi'] < 70)
        ).astype(int)
        
        # Volume spike
        volume_factor = self.volume_factor.value
        dataframe['volume_spike'] = (
            dataframe['volume_ratio'] > volume_factor
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Optimized entry conditions based on research:
        1. Strong uptrend (EMA alignment)
        2. Bullish market structure (BOS/CHOCH)
        3. OB or FVG zone
        4. Liquidity sweep trigger (KEY)
        5. Momentum + Volume confirmation
        6. RSI not overbought
        """
        
        rsi_buy = self.rsi_buy_threshold.value
        
        # PRIMARY ENTRY - Full confluence
        dataframe.loc[
            (
                # 1. Trend confirmation
                (dataframe['strong_uptrend'] == 1) &
                
                # 2. Market structure bullish
                (dataframe['bullish_structure'] == 1) &
                
                # 3. In entry zone (OB or FVG)
                (dataframe['ob_fvg_confluence'] == 1) &
                
                # 4. Liquidity sweep occurred (institutional trigger)
                (dataframe['liquidity_sweep_bull'] == 1) &
                
                # 5. Momentum confirmation
                (dataframe['momentum_bullish'] == 1) &
                
                # 6. Volume confirmation
                (dataframe['volume_spike'] == 1) &
                
                # 7. RSI filter
                (dataframe['rsi'] > rsi_buy) &
                (dataframe['rsi'] < 70) &
                
                # 8. Not at Bollinger upper (overbought)
                (dataframe['bb_percent'] < 0.9) &
                
                # Valid volume
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'smc_full_confluence')
        
        # SECONDARY ENTRY - Strong OB without liquidity sweep
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &  # Not already marked
                
                # Trend
                (dataframe['strong_uptrend'] == 1) &
                
                # Structure
                (dataframe['bullish_structure'] == 1) &
                
                # In bullish OB specifically
                (dataframe['in_bullish_ob'] == 1) &
                
                # Momentum
                (dataframe['ewo'] > 2) &  # Stronger EWO requirement
                (dataframe['macdhist'] > 0) &
                
                # RSI pullback zone
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 50) &  # Oversold for pullback
                
                # Volume
                (dataframe['volume_ratio'] > 0.8) &
                
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'smc_ob_pullback')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit conditions based on research."""
        
        rsi_sell = self.rsi_sell_threshold.value
        
        dataframe.loc[
            (
                # Bearish structure break
                (dataframe['choch'] == -1) |
                
                # RSI overbought
                (dataframe['rsi'] > rsi_sell) |
                
                # Price at Bollinger upper
                (
                    (dataframe['close'] > dataframe['bb_upper']) &
                    (dataframe['rsi'] > 70)
                ) |
                
                # EWO momentum reversal
                (
                    (dataframe['ewo'] < -2) &
                    (dataframe['macdhist'] < 0)
                ) |
                
                # Trend reversal
                (
                    (dataframe['ema_8'] < dataframe['ema_21']) &
                    (dataframe['close'] < dataframe['ema_55'])
                )
            ),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Stepped trailing stop loss based on research:
        - At 1% profit: trail at 50% of profit
        - At 2% profit: trail at 60% of profit
        - At 3% profit: trail at 70% of profit
        """
        
        if current_profit > 0.03:  # > 3%
            return max(-0.01, current_profit * 0.3 * -1)  # Keep 70% of profit
        elif current_profit > 0.02:  # > 2%
            return max(-0.015, current_profit * 0.4 * -1)  # Keep 60% of profit
        elif current_profit > 0.01:  # > 1%
            return max(-0.02, current_profit * 0.5 * -1)  # Keep 50% of profit
        
        return None  # Use default stoploss
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """Time-based exit for stale trades."""
        
        # Exit if trade is open for more than 4 hours with minimal profit
        if current_time - trade.open_date_utc > timedelta(hours=4):
            if current_profit < 0.005:  # Less than 0.5%
                return 'time_exit_stale'
        
        # Exit if trade is open for more than 8 hours
        if current_time - trade.open_date_utc > timedelta(hours=8):
            if current_profit > 0:
                return 'time_exit_profit'
        
        return None
    
    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str,
                           amount: float, rate: float, time_in_force: str,
                           exit_reason: str, current_time: datetime,
                           **kwargs) -> bool:
        """Confirm exit - don't exit at a loss if close to breakeven."""
        
        profit = trade.calc_profit_ratio(rate)
        
        # If we're at a small loss (-0.5% to 0%), hold for potential recovery
        if exit_reason in ['exit_signal', 'sell_signal']:
            if -0.005 < profit < 0:
                # Check if trend is still bullish
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if len(dataframe) > 0:
                    last = dataframe.iloc[-1]
                    if last.get('strong_uptrend', 0) == 1:
                        return False  # Don't exit, trend still good
        
        return True
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """No leverage for safe spot trading."""
        return 1.0
