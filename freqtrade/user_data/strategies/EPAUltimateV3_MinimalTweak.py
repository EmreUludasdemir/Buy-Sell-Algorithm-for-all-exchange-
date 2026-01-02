"""
EPA Ultimate Strategy V3 - MINIMAL TWEAKS (V3.5)
================================================
Based on EPAUltimateV3 with MINIMAL changes - keeping what works!

LESSON LEARNED FROM TESTS:
1. ❌ Tight stoploss (5%) = disaster for altcoins
2. ❌ Aggressive ROI (20%) + trailing = early exits, fewer profits
3. ❌ Adding more altcoins = worse performance (strategy optimized for BTC/ETH/BNB/SOL/XRP)
4. ✅ Original strategy (13.87%) works well!

MINIMAL CHANGES (V3.5):
- Slightly tighter ROI (keep profits faster)
- Slightly relaxed protections (more trades)
- NO trailing stop changes
- NO stoploss changes

Author: Emre Uludaşdemir
Version: 3.5.0 - Minimal Tweaks Only
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

from smc_indicators import (
    calculate_volatility_regime, 
    add_smc_zones_complete,
    calculate_smc_score_boost
)

from kivanc_indicators import add_kivanc_indicators

logger = logging.getLogger(__name__)


class EPAUltimateV3_MinimalTweak(IStrategy):
    """
    EPA Ultimate Strategy V3.5 - Minimal Tweaks
    
    Changes from V3:
    - Slightly faster ROI (take profits earlier)
    - Relaxed cooldown (more trading opportunities)
    - KEEP everything else the same!
    """
    
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False

    # ==================== SLIGHTLY FASTER ROI ====================
    # Take profits a bit earlier, but not too aggressive
    minimal_roi = {
        "0": 0.10,      # 10% target in first 4h (was 12% - slightly faster)
        "240": 0.06,    # 6% after 10h (was 8%)
        "480": 0.04,    # 4% after 20h (was 5%)
        "960": 0.02,    # 2% after 40h (was 3%)
    }

    # ==================== KEEP ORIGINAL STOPLOSS ====================
    stoploss = -0.08

    # KEEP original - don't enable trailing
    use_custom_stoploss = False
    
    # KEEP original trailing config
    trailing_stop = False
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    startup_candle_count: int = 100
    
    # SLIGHTLY RELAXED Protections
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 8  # REDUCED: 12 → 8 (more trades)
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 3,  # INCREASED: 2 → 3
                "stop_duration_candles": 18,  # REDUCED: 24 → 18
                "only_per_pair": False
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 5,  # INCREASED: 4 → 5
                "stop_duration_candles": 36,  # REDUCED: 48 → 36
                "max_allowed_drawdown": 0.14  # INCREASED: 0.12 → 0.14
            }
        ]
    
    # ==================== SAME HYPEROPT PARAMETERS ====================

    fast_ema = IntParameter(8, 15, default=10, space='buy', optimize=True)
    slow_ema = IntParameter(25, 40, default=30, space='buy', optimize=True)
    trend_ema = IntParameter(80, 120, default=100, space='buy', optimize=True)
    
    adx_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    adx_threshold = IntParameter(25, 45, default=30, space='buy', optimize=True)
    chop_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    chop_threshold = IntParameter(45, 65, default=50, space='buy', optimize=True)
    
    supertrend_period = IntParameter(7, 15, default=10, space='buy', optimize=True)
    supertrend_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='buy', optimize=True)
    
    halftrend_amplitude = IntParameter(1, 4, default=2, space='buy', optimize=True)
    halftrend_deviation = DecimalParameter(1.5, 3.0, default=2.0, space='buy', optimize=True)
    
    qqe_rsi_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    qqe_factor = DecimalParameter(3.0, 5.0, default=4.238, space='buy', optimize=True)
    
    wae_sensitivity = IntParameter(100, 200, default=150, space='buy', optimize=True)
    use_wae_filter = BooleanParameter(default=True, space='buy', optimize=True)
    
    atr_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='sell', optimize=True)
    risk_per_trade = DecimalParameter(0.01, 0.02, default=0.015, space='sell', optimize=False)
    
    high_vol_size_mult = DecimalParameter(0.3, 0.7, default=0.5, space='buy', optimize=False)
    low_vol_size_mult = DecimalParameter(1.0, 1.5, default=1.2, space='buy', optimize=False)
    wae_size_boost = DecimalParameter(1.0, 1.5, default=1.2, space='buy', optimize=False)
    
    use_volume_filter = BooleanParameter(default=True, space='buy', optimize=True)
    volume_threshold = DecimalParameter(1.0, 2.0, default=1.2, space='buy', optimize=True)
    
    use_htf_filter = BooleanParameter(default=True, space='buy', optimize=True)
    htf_ema_period = IntParameter(20, 50, default=21, space='buy', optimize=True)
    
    # SAME confluence requirement
    min_kivanc_signals = IntParameter(2, 3, default=3, space='buy', optimize=True)
    
    use_smc_zones = BooleanParameter(default=True, space='buy', optimize=False)
    smc_ob_boost = DecimalParameter(0.0, 0.25, default=0.15, space='buy', optimize=False)
    smc_fvg_boost = DecimalParameter(0.0, 0.20, default=0.10, space='buy', optimize=False)
    min_smc_score = IntParameter(0, 3, default=1, space='buy', optimize=True)

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        for pair in pairs:
            informative_pairs.append((pair, '1d'))
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        dataframe['ema_trend'] = ta.EMA(dataframe, timeperiod=self.trend_ema.value)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        vol_regime = calculate_volatility_regime(dataframe, atr_period=14, lookback=50)
        dataframe['vol_regime'] = vol_regime['vol_regime']
        dataframe['vol_multiplier'] = vol_regime['vol_multiplier']
        dataframe['atr_zscore'] = vol_regime['atr_zscore']
        
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
        
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        
        dataframe['choppiness'] = self._calculate_choppiness(dataframe, self.chop_period.value)
        
        dataframe['is_trending'] = (dataframe['adx'] > self.adx_threshold.value).astype(int)
        dataframe['is_choppy'] = (dataframe['choppiness'] > self.chop_threshold.value).astype(int)
        dataframe['trend_bullish'] = (dataframe['plus_di'] > dataframe['minus_di']).astype(int)
        dataframe['trend_bearish'] = (dataframe['minus_di'] > dataframe['plus_di']).astype(int)
        
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_spike'] = (dataframe['volume_ratio'] > self.volume_threshold.value).astype(int)
        
        base_mult = self.atr_multiplier.value
        dataframe['dynamic_atr_mult'] = base_mult * dataframe['vol_multiplier']
        dataframe['chandelier_long'] = dataframe['high'].rolling(22).max() - (dataframe['atr'] * dataframe['dynamic_atr_mult'])
        dataframe['chandelier_short'] = dataframe['low'].rolling(22).min() + (dataframe['atr'] * dataframe['dynamic_atr_mult'])
        
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
        
        if self.use_smc_zones.value:
            smc_zones = add_smc_zones_complete(dataframe)
            dataframe = pd.concat([dataframe, smc_zones], axis=1)
        else:
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
        atr_sum = ta.ATR(dataframe, timeperiod=1).rolling(period).sum()
        high_low_range = (
            dataframe['high'].rolling(period).max() - 
            dataframe['low'].rolling(period).min()
        )
        
        high_low_range = high_low_range.replace(0, np.nan)
        choppiness = 100 * np.log10(atr_sum / high_low_range) / np.log10(period)
        return choppiness.fillna(50)
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        volume_ok = (
            (~self.use_volume_filter.value) |
            (dataframe['volume_spike'] == 1)
        )
        
        htf_ok_long = (dataframe['htf_bullish'] == 1)
        
        # SAME dynamic confluence as V3
        min_signals_required = np.where(
            dataframe['vol_regime'] == 'HIGH_VOL',
            3,
            self.min_kivanc_signals.value
        )
        
        dataframe['wae_confirms_long'] = (
            dataframe['wae_trend_up'] > dataframe['wae_explosion_line']
        ).astype(int)
        
        dataframe['wae_confirms_short'] = (
            dataframe['wae_trend_down'] > dataframe['wae_explosion_line']
        ).astype(int)
        
        epa_filters_long = (
            (dataframe['is_trending'] == 1) &
            (dataframe['is_choppy'] == 0) &
            (dataframe['trend_bullish'] == 1) &
            (dataframe['ema_fast'] > dataframe['ema_slow'])
        )
        
        kivanc_confluence_long = (
            dataframe['kivanc_bull_count'] >= min_signals_required
        )

        smc_ok_long = (
            (self.min_smc_score.value == 0) |
            (dataframe['smc_bull_score'] >= self.min_smc_score.value)
        )

        dataframe.loc[
            (epa_filters_long) &
            (kivanc_confluence_long) &
            (smc_ok_long) &
            (volume_ok) &
            (htf_ok_long) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1
        
        if self.can_short:
            htf_ok_short = (dataframe['htf_bearish'] == 1)
            
            epa_filters_short = (
                (dataframe['is_trending'] == 1) &
                (dataframe['is_choppy'] == 0) &
                (dataframe['trend_bearish'] == 1) &
                (dataframe['ema_fast'] < dataframe['ema_slow'])
            )
            
            kivanc_confluence_short = (
                dataframe['kivanc_bear_count'] >= min_signals_required
            )

            smc_ok_short = (
                (self.min_smc_score.value == 0) |
                (dataframe['smc_bear_score'] >= self.min_smc_score.value)
            )

            dataframe.loc[
                (epa_filters_short) &
                (kivanc_confluence_short) &
                (smc_ok_short) &
                (volume_ok) &
                (htf_ok_short) &
                (dataframe['volume'] > 0),
                'enter_short'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        dataframe.loc[
            (
                (dataframe['supertrend_direction'] == -1) |
                (dataframe['qqe_trend'] == -1)
            ) &
            (dataframe['ema_fast'] < dataframe['ema_slow']),
            'exit_long'
        ] = 1
        
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
    
    def custom_stake_amount(self, pair: str, current_time: datetime,
                            current_rate: float, proposed_stake: float,
                            min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str],
                            side: str, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        vol_multiplier = last_candle['vol_multiplier']
        
        wallet = self.wallets.get_total_stake_amount()
        risk_amount = wallet * self.risk_per_trade.value
        
        if last_candle['vol_regime'] == 'HIGH_VOL':
            risk_amount *= self.high_vol_size_mult.value
        elif last_candle['vol_regime'] == 'LOW_VOL':
            risk_amount *= self.low_vol_size_mult.value
        
        if side == 'long' and last_candle.get('wae_confirms_long', 0) == 1:
            risk_amount *= self.wae_size_boost.value
        elif side == 'short' and last_candle.get('wae_confirms_short', 0) == 1:
            risk_amount *= self.wae_size_boost.value
        
        if side == 'long' and last_candle.get('price_at_ob_bull', 0) == 1:
            risk_amount *= (1.0 + self.smc_ob_boost.value)
        elif side == 'short' and last_candle.get('price_at_ob_bear', 0) == 1:
            risk_amount *= (1.0 + self.smc_ob_boost.value)
        
        if side == 'long' and last_candle.get('price_in_fvg_bull', 0) == 1:
            risk_amount *= (1.0 + self.smc_fvg_boost.value)
        elif side == 'short' and last_candle.get('price_in_fvg_bear', 0) == 1:
            risk_amount *= (1.0 + self.smc_fvg_boost.value)
        
        if side == 'long':
            if last_candle.get('liq_grab_bull', 0) == 1:
                risk_amount *= 1.10
        elif side == 'short':
            if last_candle.get('liq_grab_bear', 0) == 1:
                risk_amount *= 1.10
        
        stop_distance_pct = (atr * self.atr_multiplier.value * vol_multiplier) / current_rate
        
        if stop_distance_pct <= 0:
            return proposed_stake
        
        position_size = risk_amount / stop_distance_pct
        
        if min_stake is not None:
            position_size = max(min_stake, position_size)
        position_size = min(max_stake, position_size)
        
        return position_size
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    **kwargs) -> Optional[str]:
        """Same tiered exits as V3."""
        if current_profit >= 0.08:
            return 'tiered_tp_8pct'
        
        if current_profit >= 0.05:
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
            if trade_duration >= 16:
                return 'tiered_tp_5pct_time'
        
        return None
