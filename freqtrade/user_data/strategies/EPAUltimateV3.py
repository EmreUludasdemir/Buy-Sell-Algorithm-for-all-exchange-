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
    
    # Fixed stoploss only - ablation study Variant D winner configuration
    # Disabled both mechanisms for clean exit behavior (see reports/stop_mechanism_ablation.md)
    use_custom_stoploss = False
    
    # Trailing stop disabled - rely on ROI table and exit signals
    trailing_stop = False
    trailing_stop_positive = 0.03        # Not used when trailing_stop=False
    trailing_stop_positive_offset = 0.05  # Not used when trailing_stop=False
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
    
    # Exit Signal Loss Reduction (see reports/exit_signal_chop_damping_ablation.md)
    # Fix A: Choppiness Gate - block exit_signal during choppy consolidation when profitable
    # Fix B: Profit-Dependent Damping - require 3-of-3 consensus when trade is green
    
    # Fix A: Choppiness Gate
    use_exit_chop_gate = BooleanParameter(default=False, space='sell', optimize=False)
    exit_chop_threshold = DecimalParameter(50.0, 70.0, default=61.8, space='sell', optimize=False)
    
    # Fix B: Profit-Dependent Consensus Damping
    use_profit_damping_exit = BooleanParameter(default=False, space='sell', optimize=False)
    profit_damping_threshold = DecimalParameter(0.005, 0.02, default=0.01, space='sell', optimize=False)
    
    # Exit Confidence Scoring (see reports/exit_confidence_ablation.md)
    # Gates exit_signal based on multi-factor confidence score to reduce false exits
    use_exit_confidence_scoring = BooleanParameter(default=False, space='sell', optimize=False)
    exit_confidence_threshold = IntParameter(1, 5, default=3, space='sell', optimize=False)
    exit_adx_min = IntParameter(15, 35, default=20, space='sell', optimize=False)
    exit_vol_mult = DecimalParameter(1.0, 2.5, default=1.2, space='sell', optimize=False)
    exit_rsi_low = IntParameter(30, 45, default=35, space='sell', optimize=False)
    exit_rsi_high = IntParameter(55, 75, default=65, space='sell', optimize=False)
    exit_ema_dist_min = DecimalParameter(0.0, 0.05, default=0.01, space='sell', optimize=False)
    
    # Entry Regime Filters (see reports/entry_regime_filters_ablation.md)
    # Filter 1: EMA200 Slope - only enter when 4h EMA200 in uptrend
    use_ema200_slope_filter = BooleanParameter(default=False, space='buy', optimize=False)
    ema200_slope_min = DecimalParameter(0.0, 0.001, default=0.0001, space='buy', optimize=False)
    
    # Filter 2: ADX Minimum - only enter in strong trends
    use_adx_min_filter = BooleanParameter(default=True, space='buy', optimize=False)
    adx_entry_min = IntParameter(15, 30, default=20, space='buy', optimize=False)
    
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
        
        # EMA200 slope for regime filter (pct change over 10 candles)
        dataframe['ema200_slope'] = dataframe['ema_200'].pct_change(periods=10)
        
        # Volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # RSI for exit confidence scoring
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # EMA 100 for exit confidence scoring
        dataframe['ema_100'] = ta.EMA(dataframe, timeperiod=100)
        
        # Volume mean for exit confidence scoring
        dataframe['vol_mean_20'] = dataframe['volume'].rolling(window=20).mean()
        
        # Strong bearish candle detection for exit confidence scoring
        dataframe['body_size'] = abs(dataframe['open'] - dataframe['close'])
        dataframe['candle_range'] = dataframe['high'] - dataframe['low']
        dataframe['close_to_low'] = (dataframe['close'] - dataframe['low']) / (dataframe['candle_range'] + 1e-9)
        dataframe['bear_candle_strong'] = (
            (dataframe['close'] < dataframe['open']) &
            (dataframe['body_size'] > 0.5 * dataframe['atr']) &
            (dataframe['close_to_low'] < 0.25)
        ).astype(int)
        
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
        
        # ==================== ENTRY REGIME FILTERS ====================
        # Filter 1: EMA200 Slope Filter (only in uptrend)
        ema200_ok = (
            (~self.use_ema200_slope_filter.value) |
            (dataframe['ema200_slope'] >= self.ema200_slope_min.value)
        )
        
        # Filter 2: ADX Minimum (only in strong trends)
        adx_ok = (
            (~self.use_adx_min_filter.value) |
            (dataframe['adx'] >= self.adx_entry_min.value)
        )
        
        # ====================  DYNAMIC KΙVANÇ CONFLUENCE ====================
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
            (ema200_ok) &    # NEW: Regime filter 1
            (adx_ok) &       # NEW: Regime filter 2
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
        
        Base logic: 2-of-3 consensus (prevents single-indicator whipsaws)
        - Supertrend reversal (supertrend_direction == -1)
        - QQE reversal (qqe_trend == -1)
        - EMA cross reversal (ema_fast < ema_slow)
        
        Enhancement (Fix B): Profit-Dependent Damping
        - When enabled and trade is profitable, require 3-of-3 consensus
        - Prevents single noisy indicator from triggering exit on winners
        - Note: This is applied in confirm_trade_exit(), not here
        
        This function generates the raw exit signal which is then gated by
        confirm_trade_exit() for choppiness and profit-dependent damping.
        """
        
        # Long exit: Calculate bearish consensus
        supertrend_bearish = (dataframe['supertrend_direction'] == -1).astype(int)
        qqe_bearish = (dataframe['qqe_trend'] == -1).astype(int)
        ema_bearish = (dataframe['ema_fast'] < dataframe['ema_slow']).astype(int)
        
        bearish_count = supertrend_bearish + qqe_bearish + ema_bearish
        
        # Store bearish_count for use in confirm_trade_exit (Fix B)
        dataframe['exit_bearish_count'] = bearish_count
        
        # Apply 2-of-3 consensus (will be tightened to 3-of-3 by Fix B if enabled)
        dataframe.loc[
            (bearish_count >= 2),  # At least 2 of 3 must be bearish
            'exit_long'
        ] = 1
        
        # Short exit: 2-of-3 consensus
        if self.can_short:
            supertrend_bullish = (dataframe['supertrend_direction'] == 1).astype(int)
            qqe_bullish = (dataframe['qqe_trend'] == 1).astype(int)
            ema_bullish = (dataframe['ema_fast'] > dataframe['ema_slow']).astype(int)
            
            bullish_count = supertrend_bullish + qqe_bullish + ema_bullish
            
            dataframe.loc[
                (bullish_count >= 2),  # At least 2 of 3 must be bullish
                'exit_short'
            ] = 1
        
        return dataframe
    
    # Note:
    # `use_custom_stoploss` is currently set to False for this strategy, so this
    # method is not invoked at runtime. It is intentionally kept here to allow
    # easy future activation and for experimentation/backtesting with an
    # ATR-based dynamic stoploss, without having to re-implement the logic.
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
        Custom exit logic - tiered profit targets:
        - 8%+ profit: Full exit
        - 5%+ profit after 16h: Full exit
        """
        # Calculate trade duration
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
        
        # Tiered profit targets
        if current_profit >= 0.08:
            return 'tiered_tp_8pct'
        
        if current_profit >= 0.05:
            if trade_duration >= 16:  # 4 x 4h candles
                return 'tiered_tp_5pct_time'
        
        return None
    
    def _exit_confidence_score(self, row: pd.Series) -> int:
        """
        Calculate exit confidence score (0-5) based on multiple factors.
        
        Higher score = more confident this is a genuine reversal, not noise.
        
        F1: ADX reversal strength (ADX >= min AND minus_di > plus_di)
        F2: Volume confirmation (volume >= mean * multiplier)
        F3: RSI not in extreme zone (neutral = more reliable exit)
        F4: Strong bearish candle (body > 0.5*ATR, close near low)
        F5: Meaningful break from EMA100 (not just noise)
        
        Returns: integer 0-5
        """
        score = 0
        
        # Factor 1: ADX reversal strength
        try:
            if (row.get('adx', 0) >= self.exit_adx_min.value and 
                row.get('minus_di', 0) > row.get('plus_di', 0)):
                score += 1
        except (KeyError, TypeError, AttributeError):
            pass
        
        # Factor 2: Volume confirmation
        try:
            vol_mean = row.get('vol_mean_20', row.get('volume', 0))
            if row.get('volume', 0) >= vol_mean * self.exit_vol_mult.value:
                score += 1
        except (KeyError, TypeError, AttributeError):
            pass
        
        # Factor 3: RSI not in extreme zone (extremes = less confident)
        try:
            rsi = row.get('rsi', 50)
            if self.exit_rsi_low.value <= rsi <= self.exit_rsi_high.value:
                score += 1
        except (KeyError, TypeError, AttributeError):
            pass
        
        # Factor 4: Strong bearish candle
        try:
            if row.get('bear_candle_strong', 0) == 1:
                score += 1
        except (KeyError, TypeError, AttributeError):
            pass
        
        # Factor 5: Meaningful break from EMA100
        try:
            close = row.get('close', 0)
            ema_100 = row.get('ema_100', close)
            if close > 0 and ema_100 > 0:
                if close < ema_100 and abs(close - ema_100) / ema_100 >= self.exit_ema_dist_min.value:
                    score += 1
        except (KeyError, TypeError, AttributeError, ZeroDivisionError):
            pass
        
        return score
    
    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str,
                           amount: float, rate: float, time_in_force: str,
                           exit_reason: str, current_time: datetime,
                           **kwargs) -> bool:
        """
        Exit signal gating with three optional protection mechanisms:
        
        Fix A: Choppiness Gate
        - Block exit_signal during choppy consolidation when trade is profitable
        - Rationale: 46% of exit_signal losses were "choppy" pattern
        - Logic: If CHOP > threshold AND profit > 0, block exit_signal
        
        Fix B: Profit-Dependent Consensus Damping  
        - Require 3-of-3 consensus (not 2-of-3) when trade is profitable
        - Rationale: Prevents single noisy indicator from exiting winners
        - Logic: If profit >= threshold, need all 3 bearish (Supertrend + QQE + EMA)
        
        Fix C: Exit Confidence Scoring (NEW)
        - Score exit quality on 5 factors: ADX, volume, RSI, candle, EMA distance
        - Only allow exit_signal when score >= threshold (default 3/5)
        - Rationale: Filter false exits that occur during minor pullbacks
        
        Critical: NEVER block stoploss, ROI, or custom_exit - only gate exit_signal
        """
        # Allow all non-exit_signal exits immediately (stoploss, ROI, custom_exit, force_exit)
        if exit_reason != 'exit_signal':
            return True
        
        # Get current profit ratio
        current_profit = trade.calc_profit_ratio(rate)
        
        # Get dataframe once for all checks
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return True  # No data, allow exit
        
        last_candle = dataframe.iloc[-1]
        
        # === FIX A: CHOPPINESS GATE ===
        if self.use_exit_chop_gate.value:
            chop = last_candle.get('choppiness', 0)
            
            # Block exit_signal if choppy AND profitable
            if chop > self.exit_chop_threshold.value and current_profit > 0:
                # Choppy consolidation - don't give back gains
                logger.info(f"🚫 CHOP GATE: Blocked exit_signal for {pair} (CHOP={chop:.1f} > {self.exit_chop_threshold.value}, profit={current_profit*100:.2f}%)")
                return False
        
        # === FIX B: PROFIT-DEPENDENT CONSENSUS DAMPING ===
        if self.use_profit_damping_exit.value:
            # Only apply damping when trade is profitable
            if current_profit >= self.profit_damping_threshold.value:
                # Require 3-of-3 consensus (stricter than default 2-of-3)
                bearish_count = last_candle.get('exit_bearish_count', 0)
                
                if bearish_count < 3:
                    # Less than 3-of-3 consensus - block exit_signal
                    logger.info(f"🚫 PROFIT DAMPING: Blocked exit_signal for {pair} (bearish_count={bearish_count}/3, profit={current_profit*100:.2f}%)")
                    return False
        
        # === FIX C: EXIT CONFIDENCE SCORING ===
        if self.use_exit_confidence_scoring.value:
            score = self._exit_confidence_score(last_candle)
            
            if score < self.exit_confidence_threshold.value:
                # Low confidence exit - block it
                logger.debug(
                    f"EXIT CONFIDENCE BLOCK: score={score}<thr={self.exit_confidence_threshold.value} "
                    f"pair={pair} profit={current_profit*100:.2f}% "
                    f"adx={last_candle.get('adx', 0):.1f} rsi={last_candle.get('rsi', 0):.1f} "
                    f"vol={last_candle.get('volume', 0):.0f} emaDist={abs(last_candle.get('close', 0) - last_candle.get('ema_100', 0)) / last_candle.get('ema_100', 1) * 100:.2f}%"
                )
                return False
        
        # All checks passed - allow exit_signal
        return True

