"""
EPA Strategy V2 - Efloud Price Action with Advanced Filters
============================================================
Upgraded from Pine Script v6 with:
- Market Regime Filtering (ADX + Choppiness)
- Dynamic Risk Engine (Chandelier Exit)
- SFP Volume Confirmation
- ML-Ready Feature Extraction

Author: Emre Uludaşdemir
Version: 2.0.0
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

logger = logging.getLogger(__name__)


class EPAStrategyV2(IStrategy):
    """
    EPA Strategy V2 - Enhanced Price Action with Smart Money Concepts
    
    Key Features:
    - ADX-based market regime filtering
    - Choppiness Index for ranging market detection
    - ATR Chandelier Exit for dynamic stops
    - Volume-confirmed SFP signals
    - Position sizing based on volatility
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Optimal timeframe
    timeframe = '15m'
    
    # Disable shorting for spot markets (set True for futures)
    can_short = False
    
    # ROI table - more conservative due to regime filtering
    minimal_roi = {
        "0": 0.08,      # 8% initial target
        "30": 0.05,     # 5% after 30 mins
        "60": 0.03,     # 3% after 60 mins
        "120": 0.02,    # 2% after 120 mins
        "240": 0.01,    # 1% after 240 mins
    }
    
    # Base stoploss (overridden by custom_stoploss)
    stoploss = -0.05
    
    # Trailing configuration
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True
    
    # Process only new candles for efficiency
    process_only_new_candles = True
    
    # Disable exit signals - ROI and trailing stop perform better
    use_exit_signal = False
    exit_profit_only = False
    
    # Startup candle requirement
    startup_candle_count: int = 100
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # EMA Settings
    fast_ema = IntParameter(8, 15, default=10, space='buy', optimize=True)
    slow_ema = IntParameter(25, 40, default=30, space='buy', optimize=True)
    trend_ema = IntParameter(80, 120, default=100, space='buy', optimize=True)
    
    # Market Regime Filters
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(20, 40, default=30, space='buy', optimize=True)
    chop_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    chop_threshold = IntParameter(50, 70, default=60, space='buy', optimize=True)
    
    # Risk Settings
    atr_multiplier = DecimalParameter(1.5, 4.0, default=2.5, space='sell', optimize=True)
    risk_per_trade = DecimalParameter(0.005, 0.02, default=0.01, space='sell', optimize=False)
    
    # Signal Filters
    use_volume_filter = BooleanParameter(default=True, space='buy', optimize=True)
    volume_threshold = DecimalParameter(1.0, 2.0, default=1.2, space='buy', optimize=True)
    
    # Breakout Settings
    breakout_period = IntParameter(15, 30, default=20, space='buy', optimize=True)
    
    def informative_pairs(self):
        """Higher timeframes for trend confirmation."""
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        
        for pair in pairs:
            informative_pairs.append((pair, '1h'))
            informative_pairs.append((pair, '4h'))
        
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators using vectorized operations."""
        
        # ==================== CORE EMAs ====================
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        dataframe['ema_trend'] = ta.EMA(dataframe, timeperiod=self.trend_ema.value)
        
        # ==================== VOLATILITY ====================
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # ==================== MARKET REGIME FILTERS ====================
        
        # ADX for trend strength
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        # Choppiness Index (vectorized)
        dataframe['choppiness'] = self._calculate_choppiness(dataframe, self.chop_period.value)
        
        # Market regime classification
        dataframe['is_trending'] = (dataframe['adx'] > self.adx_threshold.value).astype(int)
        dataframe['is_choppy'] = (dataframe['choppiness'] > self.chop_threshold.value).astype(int)
        
        # Trend direction
        dataframe['trend_bullish'] = (dataframe['plus_di'] > dataframe['minus_di']).astype(int)
        dataframe['trend_bearish'] = (dataframe['minus_di'] > dataframe['plus_di']).astype(int)
        
        # ==================== VOLUME ANALYSIS ====================
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_spike'] = (dataframe['volume_ratio'] > self.volume_threshold.value).astype(int)
        
        # ==================== BREAKOUT LEVELS ====================
        bp = self.breakout_period.value
        dataframe['highest_high'] = dataframe['high'].rolling(bp).max().shift(1)
        dataframe['lowest_low'] = dataframe['low'].rolling(bp).min().shift(1)
        
        # ==================== CHANDELIER EXIT ====================
        atr_mult = self.atr_multiplier.value
        dataframe['chandelier_long'] = dataframe['high'].rolling(22).max() - (dataframe['atr'] * atr_mult)
        dataframe['chandelier_short'] = dataframe['low'].rolling(22).min() + (dataframe['atr'] * atr_mult)
        
        # ==================== SIGNAL DETECTION ====================
        
        # EMA Cross signals
        dataframe['ema_cross_up'] = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        dataframe['ema_cross_down'] = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        # Breakout signals
        dataframe['breakout_up'] = (
            (dataframe['close'] > dataframe['highest_high']) &
            (dataframe['close'].shift(1) <= dataframe['highest_high'].shift(1))
        ).astype(int)
        
        dataframe['breakout_down'] = (
            (dataframe['close'] < dataframe['lowest_low']) &
            (dataframe['close'].shift(1) >= dataframe['lowest_low'].shift(1))
        ).astype(int)
        
        # Pullback signals (to EMA in trend)
        dataframe['pullback_up'] = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['low'] <= dataframe['ema_fast']) &
            (dataframe['close'] > dataframe['ema_fast']) &
            (dataframe['close'] > dataframe['open'])
        ).astype(int)
        
        dataframe['pullback_down'] = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['high'] >= dataframe['ema_fast']) &
            (dataframe['close'] < dataframe['ema_fast']) &
            (dataframe['close'] < dataframe['open'])
        ).astype(int)
        
        # ==================== SFP (Swing Failure Pattern) ====================
        # SFP with close confirmation + volume
        dataframe['sfp_bullish'] = (
            (dataframe['low'] < dataframe['lowest_low']) &
            (dataframe['close'] > dataframe['lowest_low']) &
            (dataframe['close'] > dataframe['open']) &
            (dataframe['volume_ratio'] > 1.0)
        ).astype(int)
        
        dataframe['sfp_bearish'] = (
            (dataframe['high'] > dataframe['highest_high']) &
            (dataframe['close'] < dataframe['highest_high']) &
            (dataframe['close'] < dataframe['open']) &
            (dataframe['volume_ratio'] > 1.0)
        ).astype(int)
        
        # ==================== ML FEATURES ====================
        dataframe['ml_sfp_volume_ratio'] = np.where(
            (dataframe['sfp_bullish'] == 1) | (dataframe['sfp_bearish'] == 1),
            dataframe['volume_ratio'],
            np.nan
        )
        
        # Normalized wick size
        upper_wick = dataframe['high'] - dataframe[['open', 'close']].max(axis=1)
        lower_wick = dataframe[['open', 'close']].min(axis=1) - dataframe['low']
        dataframe['ml_atr_normalized_wick'] = (upper_wick + lower_wick) / dataframe['atr']
        
        dataframe['ml_adx_at_signal'] = dataframe['adx']
        
        return dataframe
    
    def _calculate_choppiness(self, dataframe: DataFrame, period: int) -> pd.Series:
        """Calculate Choppiness Index (vectorized)."""
        atr_sum = ta.ATR(dataframe, timeperiod=1).rolling(period).sum()
        high_low_range = (
            dataframe['high'].rolling(period).max() - 
            dataframe['low'].rolling(period).min()
        )
        
        # Avoid division by zero
        high_low_range = high_low_range.replace(0, np.nan)
        
        choppiness = 100 * np.log10(atr_sum / high_low_range) / np.log10(period)
        return choppiness.fillna(50)
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry logic with market regime filtering.
        
        Rules:
        - Trending (ADX > 30): Only trend-continuation signals
        - Choppy (Choppiness > 60): Only reversal signals at extremes
        - Normal: All signals allowed
        """
        
        # Volume filter condition
        volume_ok = (
            (~self.use_volume_filter.value) |
            (dataframe['volume_spike'] == 1)
        )
        
        # ==================== LONG ENTRIES ====================
        
        # Trend continuation in strong uptrend
        trend_long = (
            (dataframe['is_trending'] == 1) &
            (dataframe['trend_bullish'] == 1) &
            (
                (dataframe['breakout_up'] == 1) |
                (dataframe['pullback_up'] == 1)
            ) &
            (dataframe['close'] > dataframe['ema_trend'])
        )
        
        # Range reversal in choppy market
        range_long = (
            (dataframe['is_choppy'] == 1) &
            (dataframe['sfp_bullish'] == 1)
        )
        
        # Normal market - all signals
        normal_long = (
            (dataframe['is_trending'] == 0) &
            (dataframe['is_choppy'] == 0) &
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (
                (dataframe['ema_cross_up'] == 1) |
                (dataframe['breakout_up'] == 1) |
                (dataframe['pullback_up'] == 1)
            )
        )
        
        dataframe.loc[
            (volume_ok) &
            (trend_long | range_long | normal_long) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        # ==================== SHORT ENTRIES ====================
        
        if self.can_short:
            # Trend continuation in strong downtrend
            trend_short = (
                (dataframe['is_trending'] == 1) &
                (dataframe['trend_bearish'] == 1) &
                (
                    (dataframe['breakout_down'] == 1) |
                    (dataframe['pullback_down'] == 1)
                ) &
                (dataframe['close'] < dataframe['ema_trend'])
            )
            
            # Range reversal in choppy market
            range_short = (
                (dataframe['is_choppy'] == 1) &
                (dataframe['sfp_bearish'] == 1)
            )
            
            # Normal market - all signals
            normal_short = (
                (dataframe['is_trending'] == 0) &
                (dataframe['is_choppy'] == 0) &
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (
                    (dataframe['ema_cross_down'] == 1) |
                    (dataframe['breakout_down'] == 1) |
                    (dataframe['pullback_down'] == 1)
                )
            )
            
            dataframe.loc[
                (volume_ok) &
                (trend_short | range_short | normal_short) &
                (dataframe['volume'] > 0),
                'enter_short'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals based on trend reversal only.
        
        Note: Chandelier Exit removed from exit_signal because it caused
        excessive premature exits. ROI and trailing stop handle profit-taking.
        """
        
        # Long exit: Only EMA cross down (strong reversal signal)
        dataframe.loc[
            (dataframe['ema_cross_down'] == 1),
            'exit_long'
        ] = 1
        
        # Short exit
        if self.can_short:
            dataframe.loc[
                (dataframe['ema_cross_up'] == 1),
                'exit_short'
            ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Dynamic stop loss using ATR-based Chandelier Exit.
        Tightens as trade moves into profit.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
        
        last_candle = dataframe.iloc[-1]
        
        if trade.is_short:
            # Short: use chandelier_short
            stop_price = last_candle['chandelier_short']
            return (stop_price / current_rate) - 1
        else:
            # Long: use chandelier_long
            stop_price = last_candle['chandelier_long']
            return (stop_price / current_rate) - 1
    
    def custom_stake_amount(self, pair: str, current_time: datetime,
                            current_rate: float, proposed_stake: float,
                            min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str],
                            side: str, **kwargs) -> float:
        """
        Dynamic position sizing based on risk per trade.
        
        Formula: Position = (WalletBalance * RiskPct) / StopDistance
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        
        # Risk amount (1% of wallet by default)
        wallet = self.wallets.get_total_stake_amount()
        risk_amount = wallet * self.risk_per_trade.value
        
        # Stop distance (ATR multiplier)
        stop_distance_pct = (atr * self.atr_multiplier.value) / current_rate
        
        if stop_distance_pct <= 0:
            return proposed_stake
        
        # Calculate position size
        position_size = risk_amount / stop_distance_pct
        
        # Clamp to min/max
        if min_stake is not None:
            position_size = max(min_stake, position_size)
        position_size = min(max_stake, position_size)
        
        return position_size
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Conservative leverage for safety."""
        return 1.0  # No leverage for spot / low leverage for futures
