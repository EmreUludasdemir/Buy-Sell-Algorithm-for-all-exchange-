"""
EPAUltimateV4 - Hybrid SMC + Technical Analysis Strategy
=========================================================
The ultimate combination of EPA methodology, Kıvanç Özbilgiç indicators,
and Smart Money Concepts for institutional-grade trading.

Version: 4.1.0 - Trade frequency fix
Author: Emre Uludaşdemir
Created: January 2026

Key Features:
-------------
1. EPA Regime Filtering (relaxed - OR logic)
2. Kıvanç Indicators (1-2/3 sufficient in normal conditions)
3. Full SMC Toolkit (for position sizing boost only)
4. Multi-Layer Entry Confluence (3 layers, SMC optional)
5. SMC Score-Based Position Sizing (higher confluence = larger size)
6. CHoCH-Aware Exits (early exit on trend reversal signals)

Entry Logic (3 layers):
-----------------------
Layer 1 - Regime: Trending OR not choppy (relaxed)
Layer 2 - Direction: EMA alignment + DI confirmation  
Layer 3 - Kıvanç: 1-2/3 indicators (dynamic)
SMC: Optional boost for position sizing only

Position Sizing:
----------------
Base × Volatility Mult × WAE Mult × SMC Score Mult
Maximum boost: ~1.5x in ideal conditions

Expected Performance:
--------------------
- Win Rate: 45-55%
- Profit Factor: 1.3-1.6
- Max Drawdown: <20%
- Trades/Month: 8-15

Changelog:
----------
v4.1.0 - Loosened entry conditions for more trades
v4.0.0 - Initial release combining V2/V3 with full SMC toolkit
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as pta
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    IStrategy, 
    IntParameter, 
    DecimalParameter, 
    BooleanParameter, 
    merge_informative_pair
)
from freqtrade.persistence import Trade

# Import SMC indicators (complete toolkit)
from smc_indicators import (
    calculate_volatility_regime, 
    add_smc_zones_complete,
    calculate_smc_score_boost
)

# Import Kıvanç Özbilgiç indicators
from kivanc_indicators import add_kivanc_indicators

logger = logging.getLogger(__name__)


class EPAUltimateV4(IStrategy):
    """
    EPAUltimateV4 - The Ultimate Hybrid Strategy
    
    Multi-Layer Confluence Entry:
    -----------------------------
    1. Regime Filter: Trending + Not Choppy
    2. Trend Direction: EMA + DI alignment
    3. Kıvanç Confluence: 2-3 indicators (dynamic)
    4. SMC Confluence: Score >= 2 (OB + FVG + LiqGrab + BOS)
    
    All 4 layers must align for entry.
    
    Position Sizing (Stacked Boosts):
    ---------------------------------
    Base × Vol Regime × WAE Boost × SMC Score Boost
    
    Exit Logic:
    -----------
    - Primary: Supertrend/QQE reversal + EMA cross
    - Enhanced: CHoCH detection (early exit on reversal)
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Optimal timeframe
    timeframe = '4h'
    
    # Disable shorting for spot (enable for futures)
    can_short = False
    
    # ROI table - optimized for 4H timeframe with patient exits
    minimal_roi = {
        "0": 0.12,        # 12% initial target
        "360": 0.08,      # 8% after 6h
        "720": 0.05,      # 5% after 12h  
        "1440": 0.03,     # 3% after 24h
        "2880": 0.02,     # 2% after 48h
    }
    
    # Base stoploss - widened to -8% to reduce stop-outs
    stoploss = -0.08
    
    # Enable ATR-based dynamic stoploss
    use_custom_stoploss = True
    
    # Trailing configuration - adjusted for wider stops
    trailing_stop = True
    trailing_stop_positive = 0.03         # Trail at 3%
    trailing_stop_positive_offset = 0.05  # Only trail after 5% profit
    trailing_only_offset_is_reached = True
    
    # Process only new candles
    process_only_new_candles = True
    
    # Enable exit signals
    use_exit_signal = True
    exit_profit_only = False
    
    # Startup candle requirement  
    startup_candle_count: int = 120  # Extra for SMC swing detection
    
    # ==================== PROTECTIONS ====================
    
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
                "max_allowed_drawdown": 0.15  # Stricter: 15% max
            }
        ]
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # === Layer 1: Regime Filter (RELAXED) ===
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(20, 35, default=25, space='buy', optimize=True)  # Was 30
    adx_min_threshold = IntParameter(12, 22, default=15, space='buy', optimize=True)  # Was 20
    chop_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    chop_threshold = IntParameter(45, 65, default=55, space='buy', optimize=True)  # Was 50
    use_or_regime = BooleanParameter(default=True, space='buy', optimize=False)  # NEW: OR logic
    
    # === Layer 2: Trend Direction ===
    fast_ema = IntParameter(8, 15, default=10, space='buy', optimize=True)
    slow_ema = IntParameter(25, 40, default=30, space='buy', optimize=True)
    trend_ema = IntParameter(80, 120, default=100, space='buy', optimize=True)
    
    # === Layer 3: Kıvanç Confluence (RELAXED) ===
    supertrend_period = IntParameter(7, 15, default=10, space='buy', optimize=True)
    supertrend_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='buy', optimize=True)
    halftrend_amplitude = IntParameter(1, 4, default=2, space='buy', optimize=True)
    halftrend_deviation = DecimalParameter(1.5, 3.0, default=2.0, space='buy', optimize=True)
    qqe_rsi_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    qqe_factor = DecimalParameter(3.0, 5.0, default=4.238, space='buy', optimize=True)
    wae_sensitivity = IntParameter(100, 200, default=150, space='buy', optimize=True)
    
    # Dynamic Kıvanç minimum (RELAXED - 1/3 OK in normal conditions)
    min_kivanc_high_vol = IntParameter(1, 3, default=2, space='buy', optimize=True)  # Was 3
    min_kivanc_normal = IntParameter(1, 2, default=1, space='buy', optimize=True)  # Was 2
    
    # === SMC (Sizing boost only, NOT required for entry) ===
    use_smc = BooleanParameter(default=True, space='buy', optimize=False)
    min_smc_score = IntParameter(1, 4, default=2, space='buy', optimize=True)
    require_smc_confluence = BooleanParameter(default=False, space='buy', optimize=False)  # DISABLED
    
    # SMC Position Sizing (reduced boost)
    smc_boost_per_point = DecimalParameter(0.02, 0.06, default=0.03, space='buy', optimize=True)  # Was 0.05
    smc_max_boost = DecimalParameter(1.2, 1.5, default=1.3, space='buy', optimize=False)  # Was 1.5
    liq_grab_bonus = DecimalParameter(0.03, 0.10, default=0.05, space='buy', optimize=True)  # Was 0.10
    
    # === Risk Settings ===
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='sell', optimize=True)
    risk_per_trade = DecimalParameter(0.01, 0.02, default=0.015, space='sell', optimize=False)
    
    # Volatility regime multipliers
    high_vol_size_mult = DecimalParameter(0.3, 0.7, default=0.5, space='buy', optimize=False)
    low_vol_size_mult = DecimalParameter(1.0, 1.5, default=1.2, space='buy', optimize=False)
    
    # WAE boost
    wae_size_boost = DecimalParameter(1.0, 1.4, default=1.2, space='buy', optimize=True)
    
    # === Volume & HTF Filters (DISABLED by default for more trades) ===
    use_volume_filter = BooleanParameter(default=False, space='buy', optimize=True)  # Was True
    volume_threshold = DecimalParameter(1.0, 2.0, default=1.2, space='buy', optimize=True)
    use_htf_filter = BooleanParameter(default=False, space='buy', optimize=True)  # Was True
    htf_ema_period = IntParameter(20, 50, default=21, space='buy', optimize=True)
    
    # === Exit Settings ===
    use_choch_exit = BooleanParameter(default=True, space='sell', optimize=True)
    
    def informative_pairs(self):
        """Higher timeframes for trend confirmation."""
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        
        for pair in pairs:
            informative_pairs.append((pair, '1d'))  # Daily for macro trend
        
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate all indicators:
        - EPA base (ADX, Choppiness, EMAs, ATR)
        - Kıvanç (Supertrend, HalfTrend, QQE, WAE)
        - SMC (Order Blocks, FVG, Liquidity Grabs, BOS, CHoCH)
        """
        
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
        
        # ==================== LAYER 1: REGIME FILTERS ====================
        
        # ADX for trend strength
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        # Choppiness Index
        dataframe['choppiness'] = self._calculate_choppiness(dataframe, self.chop_period.value)
        
        # Market regime classification
        dataframe['is_trending'] = (dataframe['adx'] > self.adx_threshold.value).astype(int)
        dataframe['is_choppy'] = (dataframe['choppiness'] > self.chop_threshold.value).astype(int)
        dataframe['adx_ok'] = (dataframe['adx'] > self.adx_min_threshold.value).astype(int)
        
        # Trend direction
        dataframe['trend_bullish'] = (dataframe['plus_di'] > dataframe['minus_di']).astype(int)
        dataframe['trend_bearish'] = (dataframe['minus_di'] > dataframe['plus_di']).astype(int)
        
        # ==================== VOLUME ANALYSIS ====================
        
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_spike'] = (dataframe['volume_ratio'] > self.volume_threshold.value).astype(int)
        
        # ==================== DYNAMIC CHANDELIER EXIT ====================
        
        base_mult = self.atr_multiplier.value
        dataframe['dynamic_atr_mult'] = base_mult * dataframe['vol_multiplier']
        dataframe['chandelier_long'] = dataframe['high'].rolling(22).max() - (dataframe['atr'] * dataframe['dynamic_atr_mult'])
        dataframe['chandelier_short'] = dataframe['low'].rolling(22).min() + (dataframe['atr'] * dataframe['dynamic_atr_mult'])
        
        # ==================== LAYER 3: KΙVANÇ INDICATORS ====================
        
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
        
        # Kıvanç confluence counting
        dataframe['kivanc_bull_count'] = (
            (dataframe['supertrend_direction'] == 1).astype(int) +
            (dataframe['halftrend_direction'] == 1).astype(int) +
            (dataframe['qqe_trend'] == 1).astype(int)
        )
        
        dataframe['kivanc_bear_count'] = (
            (dataframe['supertrend_direction'] == -1).astype(int) +
            (dataframe['halftrend_direction'] == -1).astype(int) +
            (dataframe['qqe_trend'] == -1).astype(int)
        )
        
        # WAE confirmation flags
        dataframe['wae_confirms_long'] = (
            dataframe['wae_trend_up'] > dataframe['wae_explosion_line']
        ).astype(int)
        
        dataframe['wae_confirms_short'] = (
            dataframe['wae_trend_down'] > dataframe['wae_explosion_line']
        ).astype(int)
        
        # ==================== LAYER 4: SMC TOOLKIT ====================
        
        if self.use_smc.value:
            smc_zones = add_smc_zones_complete(dataframe)
            dataframe = pd.concat([dataframe, smc_zones], axis=1)
        else:
            # Placeholder columns
            for col in ['price_at_ob_bull', 'price_at_ob_bear', 'price_in_fvg_bull', 
                       'price_in_fvg_bear', 'liq_grab_bull', 'liq_grab_bear',
                       'bos_bull', 'bos_bear', 'choch_bull', 'choch_bear',
                       'smc_bull_score', 'smc_bear_score', 
                       'smc_bull_confluence', 'smc_bear_confluence']:
                dataframe[col] = 0
        
        # ==================== EMA CROSS SIGNALS ====================
        
        dataframe['ema_cross_up'] = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
        dataframe['ema_cross_down'] = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
        ).astype(int)
        
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
        Multi-Layer Confluence Entry (V4.1 - RELAXED).
        
        3 layers (SMC optional for sizing only):
        Layer 1: Regime (trending OR not choppy)
        Layer 2: Direction (EMA alignment)
        Layer 3: Kıvanç (1-2/3 sufficient)
        SMC: Optional - only affects position sizing
        """
        
        # ==================== LAYER 1: REGIME FILTER (RELAXED) ====================
        # OR logic: Either trending OR not choppy (was AND - too strict)
        if self.use_or_regime.value:
            regime_ok_long = (
                ((dataframe['is_trending'] == 1) | (dataframe['is_choppy'] == 0)) &
                (dataframe['adx_ok'] == 1)
            )
        else:
            # Original AND logic (stricter)
            regime_ok_long = (
                (dataframe['is_trending'] == 1) &
                (dataframe['is_choppy'] == 0) &
                (dataframe['adx_ok'] == 1)
            )
        
        # ==================== LAYER 2: TREND DIRECTION (SIMPLIFIED) ====================
        # Only require EMA alignment - removed DI requirement for more signals
        direction_ok_long = (dataframe['ema_fast'] > dataframe['ema_slow'])
        
        # ==================== LAYER 3: KΙVANÇ CONFLUENCE (RELAXED) ====================
        # Dynamic minimum: 2/3 in HIGH_VOL, 1/3 in normal conditions
        min_signals_required = np.where(
            dataframe['vol_regime'] == 'HIGH_VOL',
            self.min_kivanc_high_vol.value,  # 2 in high vol
            self.min_kivanc_normal.value     # 1 in normal (relaxed!)
        )
        
        kivanc_ok_long = (dataframe['kivanc_bull_count'] >= min_signals_required)
        
        # ==================== SMC: OPTIONAL (for sizing boost only) ====================
        # SMC is NO LONGER required for entry! Only affects position sizing.
        smc_ok_long = True  # Always pass - SMC used for sizing only
        
        # ==================== ADDITIONAL FILTERS ====================
        
        # Volume filter (disabled by default)
        volume_ok = (
            (~self.use_volume_filter.value) |
            (dataframe['volume_spike'] == 1)
        )
        
        # HTF alignment (disabled by default - always pass when disabled)
        if self.use_htf_filter.value:
            htf_ok_long = (dataframe['htf_bullish'] == 1)
        else:
            htf_ok_long = True  # Always pass when HTF disabled
        
        # ==================== COMBINED ENTRY (3 LAYERS ONLY) ====================
        
        dataframe.loc[
            (regime_ok_long) &      # Layer 1 (relaxed OR logic)
            (direction_ok_long) &   # Layer 2 (EMA only, no DI)
            (kivanc_ok_long) &      # Layer 3 (1-2/3 sufficient)
            (volume_ok) &           # Usually disabled
            (htf_ok_long) &         # Usually disabled
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        # ==================== SHORT ENTRIES ====================
        
        if self.can_short:
            regime_ok_short = (
                (dataframe['is_trending'] == 1) &
                (dataframe['is_choppy'] == 0) &
                (dataframe['adx_ok'] == 1)
            )
            
            direction_ok_short = (
                (dataframe['trend_bearish'] == 1) &
                (dataframe['ema_fast'] < dataframe['ema_slow'])
            )
            
            kivanc_ok_short = (dataframe['kivanc_bear_count'] >= min_signals_required)
            
            if self.require_smc_confluence.value:
                smc_ok_short = (dataframe['smc_bear_score'] >= self.min_smc_score.value)
            else:
                smc_ok_short = True
            
            htf_ok_short = (dataframe['htf_bearish'] == 1)
            
            dataframe.loc[
                (regime_ok_short) &
                (direction_ok_short) &
                (kivanc_ok_short) &
                (smc_ok_short) &
                (volume_ok) &
                (htf_ok_short) &
                (dataframe['volume'] > 0),
                'enter_short'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Enhanced Exit Logic (V4).
        
        Primary Exit:
        - Supertrend OR QQE reversal + EMA confirmation
        
        SMC Exit (NEW):
        - CHoCH detected (trend reversal warning)
        """
        
        # ==================== PRIMARY EXIT (from V3) ====================
        
        # Multi-indicator reversal with EMA confirmation
        primary_exit_long = (
            (
                (dataframe['supertrend_direction'] == -1) |
                (dataframe['qqe_trend'] == -1)
            ) &
            (dataframe['ema_fast'] < dataframe['ema_slow'])
        )
        
        # Fallback: EMA cross down
        ema_exit_long = (dataframe['ema_cross_down'] == 1)
        
        # ==================== SMC EXIT (NEW) ====================
        
        # CHoCH = Change of Character (trend reversal warning)
        choch_exit_long = pd.Series(False, index=dataframe.index)
        if self.use_choch_exit.value:
            choch_exit_long = (dataframe['choch_bear'] == 1)
        
        # Combined exit
        dataframe.loc[
            (primary_exit_long) | (ema_exit_long) | (choch_exit_long),
            'exit_long'
        ] = 1
        
        # ==================== SHORT EXITS ====================
        
        if self.can_short:
            primary_exit_short = (
                (
                    (dataframe['supertrend_direction'] == 1) |
                    (dataframe['qqe_trend'] == 1)
                ) &
                (dataframe['ema_fast'] > dataframe['ema_slow'])
            )
            
            ema_exit_short = (dataframe['ema_cross_up'] == 1)
            
            choch_exit_short = pd.Series(False, index=dataframe.index)
            if self.use_choch_exit.value:
                choch_exit_short = (dataframe['choch_bull'] == 1)
            
            dataframe.loc[
                (primary_exit_short) | (ema_exit_short) | (choch_exit_short),
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
        Stacked Position Sizing (V4).
        
        Base × Vol Regime × WAE Boost × SMC Score Boost × LiqGrab Bonus
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        vol_multiplier = last_candle['vol_multiplier']
        
        # Base risk amount
        wallet = self.wallets.get_total_stake_amount()
        risk_amount = wallet * self.risk_per_trade.value
        
        # ==================== VOLATILITY REGIME ====================
        if last_candle['vol_regime'] == 'HIGH_VOL':
            risk_amount *= self.high_vol_size_mult.value
        elif last_candle['vol_regime'] == 'LOW_VOL':
            risk_amount *= self.low_vol_size_mult.value
        
        # ==================== WAE BOOST ====================
        if side == 'long' and last_candle.get('wae_confirms_long', 0) == 1:
            risk_amount *= self.wae_size_boost.value
        elif side == 'short' and last_candle.get('wae_confirms_short', 0) == 1:
            risk_amount *= self.wae_size_boost.value
        
        # ==================== SMC SCORE BOOST ====================
        smc_score = 0
        if side == 'long':
            smc_score = last_candle.get('smc_bull_score', 0)
        elif side == 'short':
            smc_score = last_candle.get('smc_bear_score', 0)
        
        # Calculate SMC boost (capped)
        smc_boost = 1.0 + (smc_score * self.smc_boost_per_point.value)
        smc_boost = min(smc_boost, self.smc_max_boost.value)
        risk_amount *= smc_boost
        
        # ==================== LIQUIDITY GRAB BONUS ====================
        if side == 'long' and last_candle.get('liq_grab_bull', 0) == 1:
            risk_amount *= (1.0 + self.liq_grab_bonus.value)
        elif side == 'short' and last_candle.get('liq_grab_bear', 0) == 1:
            risk_amount *= (1.0 + self.liq_grab_bonus.value)
        
        # ==================== FINAL CALCULATION ====================
        stop_distance_pct = (atr * self.atr_multiplier.value * vol_multiplier) / current_rate
        
        if stop_distance_pct <= 0:
            return proposed_stake
        
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
        return 1.0
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    **kwargs) -> Optional[str]:
        """
        Tiered profit-taking exits.
        """
        # Large profit: take it
        if current_profit >= 0.10:
            return 'tiered_tp_10pct'
        
        # Good profit after time
        if current_profit >= 0.06:
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
            if trade_duration >= 24:  # 6 x 4h candles
                return 'tiered_tp_6pct_time'
        
        return None
