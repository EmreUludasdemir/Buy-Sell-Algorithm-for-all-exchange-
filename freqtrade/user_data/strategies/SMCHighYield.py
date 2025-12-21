"""
SMC High Yield Strategy
========================
Based on SMCStrategy (the best performer) with tweaks for higher profitability.

Approach: Keep SMCStrategy's winning formula, but:
1. Higher stake amount (config.json değiştirilmeli)
2. More aggressive ROI (7-10% vs 5%)
3. Better trailing stops
4. Compound gains by keeping winners longer
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


class SMCHighYield(IStrategy):
    """
    SMC High Yield - Based on proven SMCStrategy with profit optimizations.
    
    Changes from SMCStrategy:
    - Higher ROI targets (7-10%)
    - Aggressive trailing for big winners
    - Same entry logic (proven to work)
    """
    
    INTERFACE_VERSION = 3
    
    timeframe = '15m'
    can_short = False
    
    # Higher ROI targets
    minimal_roi = {
        "0": 0.10,      # 10% initial (aggressive)
        "30": 0.07,     # 7% after 30 mins
        "60": 0.05,     # 5% after 1 hour
        "120": 0.03,    # 3% after 2 hours
        "240": 0.02,    # 2% after 4 hours
    }
    
    # Same stop loss as SMCStrategy
    stoploss = -0.03
    
    # Aggressive trailing
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    # Settings
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 100
    use_custom_stoploss = True
    
    # Same hyperparameters as SMCStrategy
    swing_length = IntParameter(5, 15, default=10, space='buy', optimize=True)
    ob_lookback = IntParameter(30, 80, default=50, space='buy', optimize=True)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Same indicators as SMCStrategy."""
        
        # EMAs
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # RSI & MACD
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # Volume
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # SMC
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
        dataframe['fvg_top'] = fvg['Top']
        dataframe['fvg_bottom'] = fvg['Bottom']
        
        # Trend
        dataframe['uptrend'] = (
            (dataframe['ema_9'] > dataframe['ema_21']) &
            (dataframe['ema_21'] > dataframe['ema_50'])
        ).astype(int)
        
        # Bullish structure
        lookback = 15
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
            (dataframe['fvg'].shift(1) == 1)
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Same entry logic as SMCStrategy."""
        
        # Main entry
        dataframe.loc[
            (
                (dataframe['uptrend'] == 1) &
                (dataframe['bullish_structure'] == 1) &
                ((dataframe['in_bullish_ob'] == 1) | (dataframe['near_fvg'] == 1)) &
                (dataframe['macdhist'] > 0) &
                (dataframe['rsi'] > 35) &
                (dataframe['rsi'] < 70) &
                (dataframe['volume_ratio'] > 0.8) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'smc_confluence')
        
        # Pullback entry
        dataframe.loc[
            (
                (dataframe['enter_long'] != 1) &
                (dataframe['uptrend'] == 1) &
                (dataframe['close'] > dataframe['ema_200']) &
                (dataframe['low'] <= dataframe['ema_21']) &
                (dataframe['close'] > dataframe['ema_21']) &
                (dataframe['close'] > dataframe['open']) &
                (dataframe['rsi'] < 50) &
                (dataframe['rsi'] > 30) &
                (dataframe['volume'] > 0)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'ema_pullback')
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Same exit as SMCStrategy but hold winners longer."""
        
        dataframe.loc[
            (
                (dataframe['choch'] == -1) |
                (dataframe['rsi'] > 80) |  # Higher RSI threshold
                (
                    (dataframe['ema_9'] < dataframe['ema_21']) &
                    (dataframe['close'] < dataframe['ema_50'])
                )
            ),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Progressive trailing for big winners:
        - 3%: Trail 40%
        - 5%: Trail 35%
        - 8%: Trail 30%
        """
        
        if current_profit > 0.08:
            return current_profit * -0.3
        elif current_profit > 0.05:
            return current_profit * -0.35
        elif current_profit > 0.03:
            return current_profit * -0.4
        elif current_profit > 0.015:
            return -0.01
        
        return None
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """Exit stale trades only."""
        
        trade_duration = current_time - trade.open_date_utc
        
        if trade_duration > timedelta(hours=8):
            if current_profit < 0.005:
                return 'time_exit'
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        return 1.0
