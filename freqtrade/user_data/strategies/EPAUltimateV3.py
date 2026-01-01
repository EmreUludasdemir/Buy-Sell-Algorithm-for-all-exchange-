"""
EPA Ultimate Strategy V3 - Kıvanç Özbilgiç Integration
========================================================
Combines EPAStrategyV2 framework with Kıvanç Özbilgiç's popular TradingView indicators
for optimal BTC/USDT trading performance.

Key Features:
- EPAStrategyV2 base: ADX regime, Choppiness, EMA system, ATR Chandelier
- Kıvanç Indicators: Supertrend, Half Trend, QQE, Waddah Attar Explosion
- Multi-indicator confluence for high-probability entries
- Dynamic risk management based on market volatility regime
- Optimized for 4H timeframe BTC/USDT trading

Author: Emre Uludaşdemir
Version: 3.3.0 - Complete SMC toolkit (OB + FVG + LiqGrab + BOS + CHoCH)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as pta
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, BooleanParameter, merge_informative_pair
from freqtrade.persistence import Trade

# Import SMC indicators and volatility regime
from smc_indicators import (
    calculate_volatility_regime, 
    add_smc_zones_complete,
    calculate_smc_score_boost
)

# Import Kıvanç Özbilgiç indicators
from kivanc_indicators import add_kivanc_indicators

logger = logging.getLogger(__name__)


class EPAUltimateV3(IStrategy):
    """
    EPA Ultimate Strategy V3 - Maximum Confluence Trading
    
    Combines the best of:
    1. EPA Filters: ADX, Choppiness, EMA system, Volume
    2. Kıvanç Indicators: Supertrend, HalfTrend, QQE, WAE
    3. Smart risk management with volatility regime detection
    4. HTF trend filter for macro alignment
    
    Entry requires ALL of:
    - Trending market (ADX > threshold, Chop < threshold)
    - EMA alignment (fast > slow for direction)
    - Dynamic Kıvanç confluence (3/3 in HIGH_VOL, 2/3 otherwise)
    - Volume confirmation
    - HTF trend aligned
    
    V3.1 Changes:
    - Dynamic min_kivanc_signals based on volatility regime
    - WAE used for position sizing boost, not entry filter
    - Loosened EMA alignment (removed close > ema_trend)
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Optimal timeframe
    timeframe = '4h'
    
    # Disable shorting for spot markets
    can_short = False
    
    # ROI table - optimized for 4H timeframe with patient exits
    minimal_roi = {
        "0": 0.12,       # 12% initial target (was 10%)
        "360": 0.08,     # 8% after 6h
        "720": 0.05,     # 5% after 12h  
        "1440": 0.03,    # 3% after 24h
        "2880": 0.02,    # 2% after 48h
    }
    
    # Base stoploss - widened from -5% to -8% to reduce stop-outs
    stoploss = -0.08
    
    # ABLATION VARIANT A: trailing_stop ON, use_custom_stoploss OFF
    use_custom_stoploss = False
    
    # Trailing configuration - adjusted for wider stops
    trailing_stop = True
    trailing_stop_positive = 0.03        # Trail at 3% (was 2%)
    trailing_stop_positive_offset = 0.05  # Only trail after 5% profit (was 3%)
    trailing_only_offset_is_reached = True
    
    # Process only new candles
    process_only_new_candles = True
    
    # Disable exit signals - rely on ROI and trailing
    use_exit_signal = True
    exit_profit_only = False
    
    # Startup candle requirement
    startup_candle_count: int = 100
    
    # Protections
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 12
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 2,
                "stop_duration_candles": 24,
                "only_per_pair": False
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 4,
                "stop_duration_candles": 48,
                "max_allowed_drawdown": 0.12
            }
        ]
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # EMA Settings (from EPAStrategyV2)
    fast_ema = IntParameter(8, 15, default=10, space='buy', optimize=True)
    slow_ema = IntParameter(25, 40, default=30, space='buy', optimize=True)
    trend_ema = IntParameter(80, 120, default=100, space='buy', optimize=True)
    
    # Market Regime Filters
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(25, 45, default=30, space='buy', optimize=True)
    chop_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    chop_threshold = IntParameter(45, 65, default=50, space='buy', optimize=True)
    
    # Kıvanç Indicators - Supertrend
    supertrend_period = IntParameter(7, 15, default=10, space='buy', optimize=True)
    supertrend_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='buy', optimize=True)
    
    # Kıvanç Indicators - Half Trend
    halftrend_amplitude = IntParameter(1, 4, default=2, space='buy', optimize=True)
    halftrend_deviation = DecimalParameter(1.5, 3.0, default=2.0, space='buy', optimize=True)
    
    # Kıvanç Indicators - QQE
    qqe_rsi_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    qqe_factor = DecimalParameter(3.0, 5.0, default=4.238, space='buy', optimize=True)
    
    # Kıvanç Indicators - Waddah Attar
    wae_sensitivity = IntParameter(100, 200, default=150, space='buy', optimize=True)
    use_wae_filter = BooleanParameter(default=True, space='buy', optimize=True)
    
    # Risk Settings
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='sell', optimize=True)
    risk_per_trade = DecimalParameter(0.01, 0.02, default=0.015, space='sell', optimize=False)
    
    # Volatility regime position size multipliers
    high_vol_size_mult = DecimalParameter(0.3, 0.7, default=0.5, space='buy', optimize=False)
    low_vol_size_mult = DecimalParameter(1.0, 1.5, default=1.2, space='buy', optimize=False)
    
    # WAE boost for position sizing (when WAE confirms entry)
    wae_size_boost = DecimalParameter(1.0, 1.5, default=1.2, space='buy', optimize=False)
    
    # Signal Filters
    use_volume_filter = BooleanParameter(default=True, space='buy', optimize=True)
    volume_threshold = DecimalParameter(1.0, 2.0, default=1.2, space='buy', optimize=True)
    
    # HTF Trend Filter
    use_htf_filter = BooleanParameter(default=True, space='buy', optimize=True)
    htf_ema_period = IntParameter(20, 50, default=21, space='buy', optimize=True)
    
    # Confluence Settings
    min_kivanc_signals = IntParameter(2, 3, default=3, space='buy', optimize=True)
    
    # SMC Zone Settings (V4 Foundation)
    use_smc_zones = BooleanParameter(default=True, space='buy', optimize=False)
    smc_ob_boost = DecimalParameter(0.0, 0.25, default=0.15, space='buy', optimize=False)  # +15% at OB
    smc_fvg_boost = DecimalParameter(0.0, 0.20, default=0.10, space='buy', optimize=False)  # +10% at FVG
    
    def informative_pairs(self):
        """Higher timeframes for trend confirmation."""
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        
        for pair in pairs:
            informative_pairs.append((pair, '1d'))  # Daily for macro trend
        
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators - EPA base + Kıvanç indicators."""
        
        # ==================== EPA BASE INDICATORS ====================
        
        # Core EMAs
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        dataframe['ema_trend'] = ta.EMA(dataframe, timeperiod=self.trend_ema.value)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # Volatility Regime
        vol_regime = calculate_volatility_regime(dataframe, atr_period=14, lookback=50)
        dataframe['vol_regime'] = vol_regime['vol_regime']
        dataframe['vol_multiplier'] = vol_regime['vol_multiplier']
        dataframe['atr_zscore'] = vol_regime['atr_zscore']
        
        # HTF Trend Filter (1D)
        if self.dp and self.use_htf_filter.value:
            inf_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1d')
            if len(inf_1d) > 0:
                inf_1d['htf_ema'] = ta.EMA(inf_1d, timeperiod=self.htf_ema_period.value)
                inf_1d['htf_trend_up'] = (inf_1d['close'] > inf_1d['htf_ema']).astype(int)
                inf_1d['htf_trend_down'] = (inf_1d['close'] < inf_1d['htf_ema']).astype(int)
                
                dataframe = merge_informative_pair(
                    dataframe, inf_1d[['date', 'htf_trend_up', 'htf_trend_down']],
                    self.timeframe, '1d', ffill=True
                )
            else:
                dataframe['htf_trend_up_1d'] = 1
                dataframe['htf_trend_down_1d'] = 1
        else:
            dataframe['htf_trend_up_1d'] = 1
            dataframe['htf_trend_down_1d'] = 1
        
        dataframe['htf_bullish'] = dataframe['htf_trend_up_1d']
        dataframe['htf_bearish'] = dataframe['htf_trend_down_1d']
        
        # Market Regime Filters
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        # Choppiness Index
        dataframe['choppiness'] = self._calculate_choppiness(dataframe, self.chop_period.value)
        
        # Market regime classification
        dataframe['is_trending'] = (dataframe['adx'] > self.adx_threshold.value).astype(int)
        dataframe['is_choppy'] = (dataframe['choppiness'] > self.chop_threshold.value).astype(int)
        dataframe['trend_bullish'] = (dataframe['plus_di'] > dataframe['minus_di']).astype(int)
        dataframe['trend_bearish'] = (dataframe['minus_di'] > dataframe['plus_di']).astype(int)
        
        # Volume Analysis
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_spike'] = (dataframe['volume_ratio'] > self.volume_threshold.value).astype(int)
        
        # Dynamic Chandelier Exit
        base_mult = self.atr_multiplier.value
        dataframe['dynamic_atr_mult'] = base_mult * dataframe['vol_multiplier']
        dataframe['chandelier_long'] = dataframe['high'].rolling(22).max() - (dataframe['atr'] * dataframe['dynamic_atr_mult'])
        dataframe['chandelier_short'] = dataframe['low'].rolling(22).min() + (dataframe['atr'] * dataframe['dynamic_atr_mult'])
        
        # ==================== KΙVANÇ INDICATORS ====================
        
        dataframe = add_kivanc_indicators(
            dataframe,
            supertrend_period=self.supertrend_period.value,
            supertrend_multiplier=self.supertrend_multiplier.value,
            halftrend_amplitude=self.halftrend_amplitude.value,
            halftrend_deviation=self.halftrend_deviation.value,
            qqe_rsi_period=self.qqe_rsi_period.value,
            qqe_factor=self.qqe_factor.value,
            wae_sensitivity=self.wae_sensitivity.value
        )
        
        # ==================== CONFLUENCE SCORING ====================
        
        # Count bullish Kıvanç signals
        dataframe['kivanc_bull_count'] = (
            (dataframe['supertrend_direction'] == 1).astype(int) +
            (dataframe['halftrend_direction'] == 1).astype(int) +
            (dataframe['qqe_trend'] == 1).astype(int)
        )
        
        # Count bearish Kıvanç signals
        dataframe['kivanc_bear_count'] = (
            (dataframe['supertrend_direction'] == -1).astype(int) +
            (dataframe['halftrend_direction'] == -1).astype(int) +
            (dataframe['qqe_trend'] == -1).astype(int)
        )
        
        # ==================== SMC ZONES (V4 Complete) ====================
        # Includes: Order Blocks, FVG, Liquidity Grabs, BOS, CHoCH
        if self.use_smc_zones.value:
            smc_zones = add_smc_zones_complete(dataframe)
            dataframe = pd.concat([dataframe, smc_zones], axis=1)
        else:
            # Add placeholder columns if SMC disabled
            dataframe['price_at_ob_bull'] = 0
            dataframe['price_at_ob_bear'] = 0
            dataframe['price_in_fvg_bull'] = 0
            dataframe['price_in_fvg_bear'] = 0
            dataframe['liq_grab_bull'] = 0
            dataframe['liq_grab_bear'] = 0
            dataframe['bos_bull'] = 0
            dataframe['bos_bear'] = 0
            dataframe['choch_bull'] = 0
            dataframe['choch_bear'] = 0
            dataframe['smc_bull_score'] = 0
            dataframe['smc_bear_score'] = 0
            dataframe['smc_bull_confluence'] = 0
            dataframe['smc_bear_confluence'] = 0
        
        return dataframe
    
    def _calculate_choppiness(self, dataframe: DataFrame, period: int) -> pd.Series:
        """Calculate Choppiness Index (vectorized)."""
        atr_sum = ta.ATR(dataframe, timeperiod=1).rolling(period).sum()
        high_low_range = (
            dataframe['high'].rolling(period).max() - 
            dataframe['low'].rolling(period).min()
        )
        
        high_low_range = high_low_range.replace(0, np.nan)
        choppiness = 100 * np.log10(atr_sum / high_low_range) / np.log10(period)
        return choppiness.fillna(50)
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry logic with dynamic confluence (V3.1).
        
        V3.1 Changes:
        - Dynamic min_kivanc_signals: 3/3 in HIGH_VOL, 2/3 otherwise
        - WAE removed from entry (used for position sizing boost instead)
        - Loosened EMA alignment (removed close > ema_trend)
        
        Requires ALL conditions:
        1. EPA Filters: Trending market + EMA direction
        2. Kıvanç Confluence: Dynamic based on volatility
        3. Volume confirmation
        4. HTF trend aligned
        """
        
        # Volume filter
        volume_ok = (
            (~self.use_volume_filter.value) |
            (dataframe['volume_spike'] == 1)
        )
        
        # HTF alignment
        htf_ok_long = (dataframe['htf_bullish'] == 1)
        
        # ==================== DYNAMIC KΙVANÇ CONFLUENCE ====================
        # HIGH_VOL: Require 3/3 (strict - protect capital)
        # NORMAL/LOW_VOL: Require 2/3 (more trades in stable conditions)
        min_signals_required = np.where(
            dataframe['vol_regime'] == 'HIGH_VOL',
            3,  # Strict in high volatility
            2   # Relaxed in normal/low volatility
        )
        
        # Store WAE confirmation for position sizing (not entry filter)
        dataframe['wae_confirms_long'] = (
            dataframe['wae_trend_up'] > dataframe['wae_explosion_line']
        ).astype(int)
        
        dataframe['wae_confirms_short'] = (
            dataframe['wae_trend_down'] > dataframe['wae_explosion_line']
        ).astype(int)
        
        # ==================== LONG ENTRIES ====================
        
        # EPA Base Filters (LOOSENED: removed close > ema_trend)
        epa_filters_long = (
            (dataframe['is_trending'] == 1) &
            (dataframe['is_choppy'] == 0) &
            (dataframe['trend_bullish'] == 1) &
            (dataframe['ema_fast'] > dataframe['ema_slow'])
            # REMOVED: (dataframe['ema_slow'] > dataframe['ema_trend']) - too restrictive
            # REMOVED: (dataframe['close'] > dataframe['ema_trend']) - too restrictive
        )
        
        # Kıvanç Confluence (DYNAMIC based on volatility)
        kivanc_confluence_long = (
            dataframe['kivanc_bull_count'] >= min_signals_required
        )
        
        # Combined entry (WAE removed from conditions)
        dataframe.loc[
            (epa_filters_long) &
            (kivanc_confluence_long) &
            (volume_ok) &
            (htf_ok_long) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        # ==================== SHORT ENTRIES ====================
        
        if self.can_short:
            htf_ok_short = (dataframe['htf_bearish'] == 1)
            
            # EPA Base Filters (LOOSENED)
            epa_filters_short = (
                (dataframe['is_trending'] == 1) &
                (dataframe['is_choppy'] == 0) &
                (dataframe['trend_bearish'] == 1) &
                (dataframe['ema_fast'] < dataframe['ema_slow'])
            )
            
            # Kıvanç Confluence (DYNAMIC)
            kivanc_confluence_short = (
                dataframe['kivanc_bear_count'] >= min_signals_required
            )
            
            dataframe.loc[
                (epa_filters_short) &
                (kivanc_confluence_short) &
                (volume_ok) &
                (htf_ok_short) &
                (dataframe['volume'] > 0),
                'enter_short'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals based on trend reversal.
        
        Exit when multiple indicators flip:
        - Supertrend reversal
        - QQE reversal
        - EMA cross reversal
        """
        
        # Long exit: Multiple reversals
        dataframe.loc[
            (
                (dataframe['supertrend_direction'] == -1) |
                (dataframe['qqe_trend'] == -1)
            ) &
            (dataframe['ema_fast'] < dataframe['ema_slow']),
            'exit_long'
        ] = 1
        
        # Short exit
        if self.can_short:
            dataframe.loc[
                (
                    (dataframe['supertrend_direction'] == 1) |
                    (dataframe['qqe_trend'] == 1)
                ) &
                (dataframe['ema_fast'] > dataframe['ema_slow']),
                'exit_short'
            ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Dynamic stop loss using ATR-based calculation.
        Returns the WIDER of: fixed -8% or 3 ATR stop.
        This prevents premature stop-outs in volatile conditions.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return self.stoploss
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle.get('atr', 0)
        
        if atr <= 0:
            return self.stoploss
        
        # Calculate 3 ATR stop as percentage
        atr_stop = -3.0 * atr / current_rate
        
        # Use Chandelier Exit if available, otherwise ATR stop
        if trade.is_short:
            chandelier = last_candle.get('chandelier_short', 0)
            if chandelier > 0:
                chandelier_stop = (chandelier / current_rate) - 1
                atr_stop = min(atr_stop, chandelier_stop)  # More negative = wider
        else:
            chandelier = last_candle.get('chandelier_long', 0)
            if chandelier > 0:
                chandelier_stop = (chandelier / current_rate) - 1
                atr_stop = min(atr_stop, chandelier_stop)  # More negative = wider
        
        # Return wider of: fixed stoploss (-8%) or ATR-based stop
        return max(self.stoploss, atr_stop)
    
    def custom_stake_amount(self, pair: str, current_time: datetime,
                            current_rate: float, proposed_stake: float,
                            min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str],
                            side: str, **kwargs) -> float:
        """
        Dynamic position sizing based on:
        1. Risk per trade (% of wallet)
        2. Stop distance (ATR-based)
        3. Volatility regime (reduce size in high vol)
        4. WAE confirmation boost (V3.1)
        5. SMC zone boost (V3.2 - Order Block + FVG)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        vol_multiplier = last_candle['vol_multiplier']
        
        # Risk amount
        wallet = self.wallets.get_total_stake_amount()
        risk_amount = wallet * self.risk_per_trade.value
        
        # Adjust for volatility regime
        if last_candle['vol_regime'] == 'HIGH_VOL':
            risk_amount *= self.high_vol_size_mult.value  # Reduce size in high volatility
        elif last_candle['vol_regime'] == 'LOW_VOL':
            risk_amount *= self.low_vol_size_mult.value  # Increase size in low volatility
        
        # WAE confirmation boost (V3.1)
        # If WAE shows explosion in our direction, increase position size
        if side == 'long' and last_candle.get('wae_confirms_long', 0) == 1:
            risk_amount *= self.wae_size_boost.value
        elif side == 'short' and last_candle.get('wae_confirms_short', 0) == 1:
            risk_amount *= self.wae_size_boost.value
        
        # SMC zone boost (V3.2 - Order Block + FVG)
        # If entry at Order Block, add boost
        if side == 'long' and last_candle.get('price_at_ob_bull', 0) == 1:
            risk_amount *= (1.0 + self.smc_ob_boost.value)
        elif side == 'short' and last_candle.get('price_at_ob_bear', 0) == 1:
            risk_amount *= (1.0 + self.smc_ob_boost.value)
        
        # If entry in FVG, add boost
        if side == 'long' and last_candle.get('price_in_fvg_bull', 0) == 1:
            risk_amount *= (1.0 + self.smc_fvg_boost.value)
        elif side == 'short' and last_candle.get('price_in_fvg_bear', 0) == 1:
            risk_amount *= (1.0 + self.smc_fvg_boost.value)
        
        # SMC score boost (V3.3 - Liquidity Grab + BOS + CHoCH)
        # Extra boost if liquidity grab or BOS confirms entry
        smc_score = 0
        if side == 'long':
            smc_score = last_candle.get('smc_bull_score', 0)
            # Liquidity grab is strongest signal (+10% extra)
            if last_candle.get('liq_grab_bull', 0) == 1:
                risk_amount *= 1.10
        elif side == 'short':
            smc_score = last_candle.get('smc_bear_score', 0)
            if last_candle.get('liq_grab_bear', 0) == 1:
                risk_amount *= 1.10
        
        # Stop distance
        stop_distance_pct = (atr * self.atr_multiplier.value * vol_multiplier) / current_rate
        
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
        """Conservative leverage."""
        return 1.0
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    **kwargs) -> Optional[str]:
        """
        Tiered partial exits.
        
        Exit tiers:
        - 8%+ profit: Full exit
        - 5%+ profit after 16h: Full exit
        """
        if current_profit >= 0.08:
            return 'tiered_tp_8pct'
        
        if current_profit >= 0.05:
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
            if trade_duration >= 16:  # 4 x 4h candles
                return 'tiered_tp_5pct_time'
        
        return None
