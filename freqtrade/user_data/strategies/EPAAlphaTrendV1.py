"""
EPAAlphaTrendV1 Strategy - AlphaTrend + SMC Confluence
=======================================================
A 2H crypto strategy combining AlphaTrend with Smart Money Concepts
for reduced whipsaw and higher quality entries.

Strategy: "Strategy B: AlphaTrend SMC" from spec
- 4-Layer Entry System: Trend → Trigger → Confluence → Volume
- 5 Exit Conditions: Trend flip, Structure break, Momentum death, OB, Time failsafe
- ATR-based Dynamic Stops

Author: Emre Uludaşdemir
Version: 1.0.0
Based on: EPA AlphaTrend Strategy Development Spec
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_prev_date

# Import indicator modules
from alphatrend_indicators import (
    alphatrend as at_alphatrend,
    squeeze_momentum,
    wavetrend,
    choppiness_index
)
from smc_indicators import (
    calculate_swing_highs_lows,
    calculate_bos_choch,
    add_smc_zones,
    calculate_volatility_regime
)
from kivanc_indicators import supertrend

logger = logging.getLogger(__name__)


class EPAAlphaTrendV1(IStrategy):
    """
    EPAAlphaTrendV1 - AlphaTrend + SMC Confluence Strategy
    
    Entry Philosophy:
    - Only enter when trend, momentum, and structure align
    - SMC zones provide institutional-level precision
    - Multiple confirmations reduce false signals
    
    Exit Philosophy:
    - Exit on trend reversal or structure break
    - Time-based failsafe for dead trades
    - ATR-based trailing to protect profits
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Timeframe
    timeframe = '2h'
    
    # Disable shorting (spot markets)
    can_short = False
    
    # Exit configuration
    use_exit_signal = True
    use_custom_stoploss = True
    exit_profit_only = False
    
    # Process only new candles
    process_only_new_candles = True
    
    # Startup candles (need enough for indicators)
    startup_candle_count: int = 200
    
    # ═══════════════════════════════════════════════════════════════
    # ROI TABLE (from spec)
    # ═══════════════════════════════════════════════════════════════
    minimal_roi = {
        "0": 0.12,       # 12% immediate (unlikely)
        "24": 0.08,      # 8% after 48h (24 candles)
        "48": 0.05,      # 5% after 96h
        "96": 0.03,      # 3% after 192h (8 days)
        "144": 0.02      # 2% after 12 days
    }
    
    # Stoploss - disabled, using custom_stoploss
    stoploss = -0.99
    
    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02       # 2% trail distance
    trailing_stop_positive_offset = 0.04  # Activate at 4% profit
    trailing_only_offset_is_reached = True
    
    # ═══════════════════════════════════════════════════════════════
    # PROTECTIONS
    # ═══════════════════════════════════════════════════════════════
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 4  # 8h cooldown
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": False
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "max_allowed_drawdown": 0.15,
                "trade_limit": 10,
                "stop_duration_candles": 12
            }
        ]
    
    # ═══════════════════════════════════════════════════════════════
    # HYPEROPT PARAMETERS - TREND
    # ═══════════════════════════════════════════════════════════════
    alphatrend_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    alphatrend_coeff = DecimalParameter(0.8, 1.5, default=1.0, decimals=1, space='buy', optimize=True)
    adx_threshold = IntParameter(18, 35, default=22, space='buy', optimize=True)  # Lowered from 28
    chop_threshold = IntParameter(45, 65, default=55, space='buy', optimize=True)  # Raised from 50
    
    # ═══════════════════════════════════════════════════════════════
    # HYPEROPT PARAMETERS - MOMENTUM
    # ═══════════════════════════════════════════════════════════════
    squeeze_length = IntParameter(14, 24, default=20, space='buy', optimize=True)
    wavetrend_channel = IntParameter(8, 14, default=10, space='buy', optimize=True)
    wavetrend_average = IntParameter(18, 26, default=21, space='buy', optimize=True)
    wavetrend_overbought = IntParameter(50, 70, default=60, space='sell', optimize=True)
    
    # ═══════════════════════════════════════════════════════════════
    # HYPEROPT PARAMETERS - SMC
    # ═══════════════════════════════════════════════════════════════
    swing_length = IntParameter(15, 40, default=25, space='buy', optimize=False)
    ob_lookback = IntParameter(30, 80, default=50, space='buy', optimize=False)
    
    # ═══════════════════════════════════════════════════════════════
    # HYPEROPT PARAMETERS - RISK
    # ═══════════════════════════════════════════════════════════════
    atr_stoploss_mult = DecimalParameter(2.0, 4.0, default=3.0, decimals=1, space='sell', optimize=True)
    
    # ═══════════════════════════════════════════════════════════════
    # HYPEROPT PARAMETERS - FILTERS
    # ═══════════════════════════════════════════════════════════════
    confluence_required = IntParameter(2, 3, default=2, space='buy', optimize=False)
    volume_factor = DecimalParameter(0.5, 1.0, default=0.6, decimals=1, space='buy', optimize=False)
    
    # ═══════════════════════════════════════════════════════════════
    # INFORMATIVE PAIRS
    # ═══════════════════════════════════════════════════════════════
    def informative_pairs(self):
        """Define informative pairs for HTF analysis."""
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        
        for pair in pairs:
            informative_pairs.append((pair, '8h'))
            informative_pairs.append((pair, '1d'))
        
        return informative_pairs
    
    # ═══════════════════════════════════════════════════════════════
    # POPULATE INDICATORS
    # ═══════════════════════════════════════════════════════════════
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate all indicators for entry/exit decisions.
        
        Indicators:
        - AlphaTrend (trend direction)
        - ADX/DI (trend strength)
        - Choppiness (ranging detection)
        - Squeeze Momentum (breakout detection)
        - WaveTrend (momentum oscillator)
        - SuperTrend (trend confirmation)
        - SMC Zones (OB, FVG, BOS/CHoCH)
        - Volume SMA
        - EMA system
        - ATR
        """
        
        # ═══════════════════════════════════════════════════════════════
        # ALPHATREND
        # ═══════════════════════════════════════════════════════════════
        at_line, at_signal = at_alphatrend(
            dataframe,
            period=self.alphatrend_period.value,
            coeff=self.alphatrend_coeff.value
        )
        dataframe['alphatrend'] = at_line
        dataframe['alphatrend_signal'] = at_signal
        
        # AlphaTrend direction
        dataframe['alphatrend_bullish'] = (
            dataframe['alphatrend'] > dataframe['alphatrend_signal']
        ).astype(int)
        
        # AlphaTrend crossover (fresh signal)
        dataframe['alphatrend_cross_up'] = (
            (dataframe['alphatrend'] > dataframe['alphatrend_signal']) &
            (dataframe['alphatrend'].shift(1) <= dataframe['alphatrend_signal'].shift(1))
        ).astype(int)
        
        dataframe['alphatrend_cross_down'] = (
            (dataframe['alphatrend'] < dataframe['alphatrend_signal']) &
            (dataframe['alphatrend'].shift(1) >= dataframe['alphatrend_signal'].shift(1))
        ).astype(int)
        
        # ═══════════════════════════════════════════════════════════════
        # ADX / DI (Trend Strength)
        # ═══════════════════════════════════════════════════════════════
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # ═══════════════════════════════════════════════════════════════
        # CHOPPINESS INDEX
        # ═══════════════════════════════════════════════════════════════
        dataframe['choppiness'] = choppiness_index(dataframe, period=14)
        
        # ═══════════════════════════════════════════════════════════════
        # SQUEEZE MOMENTUM
        # ═══════════════════════════════════════════════════════════════
        squeeze_mom, squeeze_on = squeeze_momentum(
            dataframe,
            bb_length=self.squeeze_length.value,
            kc_length=self.squeeze_length.value
        )
        dataframe['squeeze_momentum'] = squeeze_mom
        dataframe['squeeze_on'] = squeeze_on.astype(int)
        
        # ═══════════════════════════════════════════════════════════════
        # WAVETREND
        # ═══════════════════════════════════════════════════════════════
        wt1, wt2 = wavetrend(
            dataframe,
            channel_length=self.wavetrend_channel.value,
            average_length=self.wavetrend_average.value
        )
        dataframe['wavetrend_1'] = wt1
        dataframe['wavetrend_2'] = wt2
        
        # WaveTrend bullish
        dataframe['wavetrend_bullish'] = (wt1 > wt2).astype(int)
        
        # ═══════════════════════════════════════════════════════════════
        # SUPERTREND
        # ═══════════════════════════════════════════════════════════════
        st_dir, st_line = supertrend(dataframe, period=10, multiplier=3.0)
        dataframe['supertrend_direction'] = st_dir
        dataframe['supertrend_line'] = st_line
        
        # ═══════════════════════════════════════════════════════════════
        # SMC ZONES (Order Blocks, FVG)
        # ═══════════════════════════════════════════════════════════════
        try:
            smc_zones = add_smc_zones(
                dataframe,
                impulse_candles=3,
                impulse_pct=0.02,
                lookback=self.ob_lookback.value
            )
            for col in smc_zones.columns:
                dataframe[col] = smc_zones[col]
        except Exception as e:
            logger.warning(f"SMC zones calculation failed: {e}")
            # Add default columns if SMC fails
            dataframe['smc_bull_confluence'] = 0
            dataframe['smc_bear_confluence'] = 0
        
        # ═══════════════════════════════════════════════════════════════
        # BOS / CHoCH (Structure Breaks)
        # ═══════════════════════════════════════════════════════════════
        try:
            swings = calculate_swing_highs_lows(dataframe, swing_length=self.swing_length.value)
            bos_choch = calculate_bos_choch(dataframe, swings)
            
            dataframe['bullish_bos'] = (bos_choch['BOS'] == 1).astype(int)
            dataframe['bearish_bos'] = (bos_choch['BOS'] == -1).astype(int)
            dataframe['bullish_choch'] = (bos_choch['CHOCH'] == 1).astype(int)
            dataframe['bearish_choch'] = (bos_choch['CHOCH'] == -1).astype(int)
        except Exception as e:
            logger.warning(f"BOS/CHoCH calculation failed: {e}")
            dataframe['bullish_bos'] = 0
            dataframe['bearish_bos'] = 0
            dataframe['bullish_choch'] = 0
            dataframe['bearish_choch'] = 0
        
        # ═══════════════════════════════════════════════════════════════
        # VOLUME
        # ═══════════════════════════════════════════════════════════════
        dataframe['volume_sma_20'] = dataframe['volume'].rolling(20).mean()
        
        # ═══════════════════════════════════════════════════════════════
        # EMAs
        # ═══════════════════════════════════════════════════════════════
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # ═══════════════════════════════════════════════════════════════
        # ATR
        # ═══════════════════════════════════════════════════════════════
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # ═══════════════════════════════════════════════════════════════
        # INFORMATIVE TIMEFRAMES
        # ═══════════════════════════════════════════════════════════════
        # 8H informative
        if self.dp:
            inf_8h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='8h')
            if not inf_8h.empty:
                inf_8h['adx_8h'] = ta.ADX(inf_8h, timeperiod=14)
                inf_8h['ema_50_8h'] = ta.EMA(inf_8h, timeperiod=50)
                
                # SuperTrend 8H
                st_dir_8h, _ = supertrend(inf_8h, period=10, multiplier=3.0)
                inf_8h['supertrend_dir_8h'] = st_dir_8h
                
                # Merge - use ffill for proper alignment
                dataframe = self._merge_informative(dataframe, inf_8h, '8h')
            
            # 1D informative
            inf_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1d')
            if not inf_1d.empty:
                inf_1d['ema_50_1d'] = ta.EMA(inf_1d, timeperiod=50)
                inf_1d['trend_1d'] = (inf_1d['close'] > inf_1d['ema_50_1d']).astype(int)
                
                # Merge
                dataframe = self._merge_informative(dataframe, inf_1d, '1d')
        
        # Fill NaN for informative columns if missing
        for col in ['adx_8h', 'ema_50_8h', 'supertrend_dir_8h', 'ema_50_1d', 'trend_1d']:
            if col not in dataframe.columns:
                dataframe[col] = np.nan
        
        return dataframe
    
    def _merge_informative(self, dataframe: DataFrame, inf_df: DataFrame, timeframe: str) -> DataFrame:
        """Merge informative dataframe with proper date alignment."""
        # Get columns to merge (exclude standard OHLCV)
        cols_to_merge = [c for c in inf_df.columns if c.endswith(f'_{timeframe}')]
        
        if not cols_to_merge:
            return dataframe
        
        # Rename date column for merge
        inf_df = inf_df[['date'] + cols_to_merge].copy()
        inf_df = inf_df.rename(columns={'date': f'date_{timeframe}'})
        
        # Convert dates
        dataframe['date_merge'] = pd.to_datetime(dataframe['date'])
        inf_df[f'date_{timeframe}'] = pd.to_datetime(inf_df[f'date_{timeframe}'])
        
        # Merge asof (backward looking)
        dataframe = pd.merge_asof(
            dataframe.sort_values('date_merge'),
            inf_df.sort_values(f'date_{timeframe}'),
            left_on='date_merge',
            right_on=f'date_{timeframe}',
            direction='backward'
        )
        
        # Clean up
        dataframe = dataframe.drop(columns=['date_merge', f'date_{timeframe}'], errors='ignore')
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # POPULATE ENTRY TREND
    # ═══════════════════════════════════════════════════════════════
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry logic with 4-layer system.
        
        Layer 1 - TREND FILTER (must be true):
        - AlphaTrend bullish
        - ADX > threshold
        - Choppiness < threshold
        - Close > EMA_50_1D (if available)
        
        Layer 2 - TRIGGER (at least 1):
        - AlphaTrend crossover (fresh signal)
        - BOS or CHoCH in last 10 bars
        
        Layer 3 - CONFLUENCE (at least 2 of 3):
        - Squeeze Momentum > 0
        - WaveTrend bullish
        - SuperTrend direction = 1
        
        Layer 4 - VOLUME:
        - Volume > SMA_20 * volume_factor
        """
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 1: TREND CONFIRMATION (RELAXED)
        # ═══════════════════════════════════════════════════════════════
        # AlphaTrend bullish is REQUIRED
        # Regime filter: ADX > threshold OR Choppiness < threshold (OR logic, not AND)
        regime_ok = (
            (dataframe['adx'] > self.adx_threshold.value) |
            (dataframe['choppiness'] < self.chop_threshold.value)
        )
        
        trend_ok = (
            (dataframe['alphatrend_bullish'] == 1) &
            regime_ok
        )
        
        # HTF filter is now OPTIONAL - just logged, not required
        # (Removed from trend_ok to increase signal frequency)
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 2: ENTRY TRIGGER (SIMPLIFIED)
        # ═══════════════════════════════════════════════════════════════
        # OPTION 1: Fresh AlphaTrend crossover (rare but strong)
        trigger_alphatrend_cross = dataframe['alphatrend_cross_up'] == 1
        
        # OPTION 2: AlphaTrend just became bullish within last 20 bars
        trigger_alphatrend_recent = (
            (dataframe['alphatrend_bullish'] == 1) &
            (dataframe['alphatrend_cross_up'].rolling(20).max() == 1)
        )
        
        # OPTION 3: Structure break in last 20 bars
        trigger_structure = (
            (dataframe['bullish_bos'].rolling(20).max() == 1) |
            (dataframe['bullish_choch'].rolling(20).max() == 1)
        )
        
        # OPTION 4: SuperTrend is bullish (not just flip)
        trigger_supertrend = (dataframe['supertrend_direction'] == 1)
        
        # Combined: Any trigger is OK
        entry_trigger = (
            trigger_alphatrend_cross | 
            trigger_alphatrend_recent | 
            trigger_structure | 
            trigger_supertrend
        )
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 3: CONFLUENCE CONFIRMATION
        # ═══════════════════════════════════════════════════════════════
        confirm_momentum = (dataframe['squeeze_momentum'] > 0).astype(int)
        confirm_wavetrend = dataframe['wavetrend_bullish']
        confirm_supertrend = (dataframe['supertrend_direction'] == 1).astype(int)
        
        confluence_count = confirm_momentum + confirm_wavetrend + confirm_supertrend
        confluence_ok = confluence_count >= self.confluence_required.value
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 4: VOLUME CONFIRMATION
        # ═══════════════════════════════════════════════════════════════
        volume_ok = dataframe['volume'] > (dataframe['volume_sma_20'] * self.volume_factor.value)
        
        # ═══════════════════════════════════════════════════════════════
        # DIAGNOSTIC LOGGING
        # ═══════════════════════════════════════════════════════════════
        total_bars = len(dataframe)
        
        # Individual layer pass rates
        layer1_count = trend_ok.sum()
        layer2_count = entry_trigger.sum()
        layer3_count = confluence_ok.sum()
        layer4_count = volume_ok.sum()
        
        # Cumulative filtering
        after_l1 = trend_ok.sum()
        after_l2 = (trend_ok & entry_trigger).sum()
        after_l3 = (trend_ok & entry_trigger & confluence_ok).sum()
        after_l4 = (trend_ok & entry_trigger & confluence_ok & volume_ok).sum()
        
        # Sub-component analysis
        at_bullish = (dataframe['alphatrend_bullish'] == 1).sum()
        adx_pass = (dataframe['adx'] > self.adx_threshold.value).sum()
        chop_pass = (dataframe['choppiness'] < self.chop_threshold.value).sum()
        htf_pass = (dataframe['trend_1d'] == 1).sum() if 'trend_1d' in dataframe.columns else total_bars
        
        at_cross = (dataframe['alphatrend_cross_up'] == 1).sum()
        bos_pass = (dataframe['bullish_bos'].rolling(10).max() == 1).sum()
        choch_pass = (dataframe['bullish_choch'].rolling(10).max() == 1).sum()
        
        print(f"""
═══════════════════════════════════════════════════════════
DIAGNOSTIC - {metadata['pair']}
═══════════════════════════════════════════════════════════
Total bars: {total_bars}

LAYER 1 COMPONENTS (Trend Filter):
- AlphaTrend Bullish: {at_bullish:4d} ({at_bullish/total_bars*100:5.1f}%)
- ADX > {self.adx_threshold.value}:        {adx_pass:4d} ({adx_pass/total_bars*100:5.1f}%)
- Choppiness < {self.chop_threshold.value}:   {chop_pass:4d} ({chop_pass/total_bars*100:5.1f}%)
- HTF Trend OK:      {htf_pass:4d} ({htf_pass/total_bars*100:5.1f}%)

LAYER 2 COMPONENTS (Entry Trigger):
- AT Crossover:      {at_cross:4d} ({at_cross/total_bars*100:5.1f}%)
- BOS (10 bar):      {bos_pass:4d} ({bos_pass/total_bars*100:5.1f}%)
- CHoCH (10 bar):    {choch_pass:4d} ({choch_pass/total_bars*100:5.1f}%)

LAYER PASS RATES (individual):
- L1 Trend OK:       {layer1_count:4d} ({layer1_count/total_bars*100:5.1f}%)
- L2 Trigger:        {layer2_count:4d} ({layer2_count/total_bars*100:5.1f}%)
- L3 Confluence:     {layer3_count:4d} ({layer3_count/total_bars*100:5.1f}%)
- L4 Volume:         {layer4_count:4d} ({layer4_count/total_bars*100:5.1f}%)

CUMULATIVE FILTERING:
- After L1:          {after_l1:4d} bars remain
- After L1+L2:       {after_l2:4d} bars remain
- After L1+L2+L3:    {after_l3:4d} bars remain
- After ALL:         {after_l4:4d} potential entries
═══════════════════════════════════════════════════════════
        """)
        
        # ═══════════════════════════════════════════════════════════════
        # FINAL ENTRY SIGNAL (SIMPLIFIED FOR TESTING)
        # ═══════════════════════════════════════════════════════════════
        # Temporarily removed L3 (confluence) and L4 (volume) to diagnose low trade count
        enter_long = (
            trend_ok &
            entry_trigger &
            # confluence_ok &  # Disabled for testing
            # volume_ok &      # Disabled for testing
            (dataframe['volume'] > 0)
        )
        
        # CRITICAL: Shift to avoid lookahead bias
        dataframe.loc[enter_long.shift(1).fillna(False), 'enter_long'] = 1
        
        # Entry tags for analysis
        dataframe.loc[
            enter_long.shift(1).fillna(False) & trigger_alphatrend_cross.shift(1).fillna(False),
            'enter_tag'
        ] = 'at_cross'
        
        dataframe.loc[
            enter_long.shift(1).fillna(False) & trigger_supertrend.shift(1).fillna(False) & ~trigger_alphatrend_cross.shift(1).fillna(False),
            'enter_tag'
        ] = 'supertrend'
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # POPULATE EXIT TREND
    # ═══════════════════════════════════════════════════════════════
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit logic with 4 signal conditions.
        
        1. TREND FLIP: AlphaTrend crosses down
        2. STRUCTURE BREAK: Bearish CHoCH
        3. MOMENTUM DEATH: Squeeze < 0 + WaveTrend bearish
        4. OVERBOUGHT REVERSAL: WaveTrend > 60 + declining + crossed
        """
        
        # ═══════════════════════════════════════════════════════════════
        # EXIT 1: TREND FLIP
        # ═══════════════════════════════════════════════════════════════
        exit_trend_flip = dataframe['alphatrend_cross_down'] == 1
        
        # ═══════════════════════════════════════════════════════════════
        # EXIT 2: STRUCTURE BREAK
        # ═══════════════════════════════════════════════════════════════
        exit_structure = dataframe['bearish_choch'] == 1
        
        # ═══════════════════════════════════════════════════════════════
        # EXIT 3: MOMENTUM DEATH
        # ═══════════════════════════════════════════════════════════════
        momentum_crossed_down = (
            (dataframe['squeeze_momentum'] < 0) &
            (dataframe['squeeze_momentum'].shift(1) >= 0)
        )
        exit_momentum = (
            momentum_crossed_down &
            (dataframe['wavetrend_bullish'] == 0)
        )
        
        # ═══════════════════════════════════════════════════════════════
        # EXIT 4: OVERBOUGHT REVERSAL
        # ═══════════════════════════════════════════════════════════════
        exit_overbought = (
            (dataframe['wavetrend_1'] > self.wavetrend_overbought.value) &
            (dataframe['wavetrend_1'] < dataframe['wavetrend_1'].shift(1)) &
            (dataframe['wavetrend_bullish'] == 0)
        )
        
        # ═══════════════════════════════════════════════════════════════
        # FINAL EXIT SIGNAL
        # ═══════════════════════════════════════════════════════════════
        exit_signal = (
            exit_trend_flip |
            exit_structure |
            exit_momentum |
            exit_overbought
        )
        
        # CRITICAL: Shift to avoid lookahead bias
        dataframe.loc[exit_signal.shift(1).fillna(False), 'exit_long'] = 1
        
        # Exit tags for analysis
        dataframe.loc[exit_trend_flip.shift(1).fillna(False), 'exit_tag'] = 'trend_flip'
        dataframe.loc[exit_structure.shift(1).fillna(False), 'exit_tag'] = 'structure_break'
        dataframe.loc[exit_momentum.shift(1).fillna(False), 'exit_tag'] = 'momentum_death'
        dataframe.loc[exit_overbought.shift(1).fillna(False), 'exit_tag'] = 'overbought'
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # CUSTOM STOPLOSS
    # ═══════════════════════════════════════════════════════════════
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        ATR-based dynamic stoploss.
        
        Base stop: 3x ATR below entry
        Profit-based tightening:
        - > 5% profit: Max 2.5% from current
        - > 3% profit: Max 4% from current
        """
        # Get ATR at entry
        atr = self._get_atr_at_entry(pair, trade)
        
        if atr is None or atr == 0:
            return self.stoploss  # Fallback
        
        # Base stop: 3x ATR below entry
        base_stop_distance = (atr * self.atr_stoploss_mult.value) / trade.open_rate
        base_stop = -base_stop_distance
        
        # Tighten based on profit
        if current_profit > 0.05:  # > 5% profit
            return max(base_stop, -0.025)  # Max 2.5% from current
        elif current_profit > 0.03:  # > 3% profit
            return max(base_stop, -0.04)  # Max 4%
        
        return base_stop
    
    def _get_atr_at_entry(self, pair: str, trade: Trade) -> Optional[float]:
        """Get ATR value at trade entry."""
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            trade_date = timeframe_to_prev_date(self.timeframe, trade.open_date_utc)
            candle = dataframe.loc[dataframe['date'] == trade_date]
            
            if not candle.empty and 'atr' in candle.columns:
                return candle['atr'].iloc[0]
        except Exception as e:
            logger.warning(f"Failed to get ATR at entry: {e}")
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # CUSTOM EXIT
    # ═══════════════════════════════════════════════════════════════
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    **kwargs) -> Optional[str]:
        """
        Time-based failsafe exit.
        
        Exit if trade is open for 48 candles (96 hours) with < 1% profit.
        """
        # Calculate trade duration in candles (2h = 1 candle)
        trade_duration_hours = (current_time - trade.open_date_utc).total_seconds() / 3600
        trade_duration_candles = trade_duration_hours / 2  # 2h timeframe
        
        # Time-based failsafe: 48 candles, < 1% profit
        if trade_duration_candles >= 48 and current_profit < 0.01:
            return 'time_failsafe'
        
        # Quick profit spike
        if current_profit >= 0.10:
            return 'profit_spike_10pct'
        
        return None
    
    # ═══════════════════════════════════════════════════════════════
    # LEVERAGE
    # ═══════════════════════════════════════════════════════════════
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """No leverage - spot trading only."""
        return 1.0
