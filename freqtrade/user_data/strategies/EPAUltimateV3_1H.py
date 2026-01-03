"""
EPA Ultimate Strategy V3 - 1H Timeframe Edition
================================================
SIMPLIFIED version - 4 core conditions only.

Key Features:
- 4H trend filter (direction)
- 1H SuperTrend + RSI (timing)
- Volume optional (hyperopt decides)

Entry Logic (v1.1 - Simplified):
1. 4H SuperTrend bullish (direction)
2. 4H RSI > 40 (not oversold)
3. 1H SuperTrend bullish (timing)
4. 1H RSI in range (not extreme)

Removed (over-filtering on 1H):
- EMA fast > slow alignment
- OBV filter
- Choppiness index
- ADX threshold

Author: Emre Uludaşdemir
Version: 1.1.0 (2026-01-03) - Simplified entry
"""

import logging
from functools import reduce
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as pta
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, BooleanParameter, CategoricalParameter, merge_informative_pair
from freqtrade.persistence import Trade

# Import Kıvanç Özbilgiç indicators
from kivanc_indicators import supertrend, halftrend, qqe, waddah_attar_explosion

logger = logging.getLogger(__name__)


class EPAUltimateV3_1H(IStrategy):
    """
    1H Timeframe - SIMPLIFIED Entry (v1.1)
    
    Entry = 4 conditions only:
    1. 4H SuperTrend bullish
    2. 4H RSI > 40
    3. 1H SuperTrend bullish
    4. 1H RSI 25-70
    
    Why simplified?
    - EMA alignment flips hourly on 1H (noise)
    - Too many filters = no trades
    """
    
    INTERFACE_VERSION = 3
    
    # === BASIC SETTINGS ===
    timeframe = '1h'
    can_short = False
    
    # Process only new candles
    process_only_new_candles = True
    
    # Startup candle requirement
    startup_candle_count: int = 150  # Need more for 4H informative
    
    # === HYPEROPT SPACES ===
    
    # RSI Parameters (widened range for more trades)
    buy_rsi_low = IntParameter(20, 35, default=25, space='buy', optimize=True)
    buy_rsi_high = IntParameter(60, 80, default=70, space='buy', optimize=True)
    sell_rsi = IntParameter(65, 80, default=75, space='sell', optimize=True)
    
    # SuperTrend (key trend indicator)
    supertrend_period = IntParameter(8, 16, default=12, space='buy', optimize=True)
    supertrend_mult = DecimalParameter(1.8, 3.0, default=2.2, decimals=1, space='buy', optimize=True)
    
    # ATR Period (smoothness vs responsiveness)
    atr_period = IntParameter(18, 28, default=24, space='buy', optimize=True)
    
    # EMA Periods (scaled from 4H)
    ema_fast = IntParameter(9, 15, default=12, space='buy', optimize=True)
    ema_slow = IntParameter(28, 40, default=33, space='buy', optimize=True)
    ema_trend = IntParameter(80, 120, default=100, space='buy', optimize=True)
    
    # ADX Threshold (trend strength) - lowered for more triggers
    adx_threshold = IntParameter(15, 30, default=20, space='buy', optimize=True)
    
    # Choppiness Threshold (avoid ranging) - raised for more opportunities
    chop_threshold = IntParameter(50, 65, default=58, space='buy', optimize=True)
    
    # Volume Filter - default OFF for more trades
    use_volume_filter = BooleanParameter(default=False, space='buy', optimize=True)
    volume_mult = DecimalParameter(0.8, 1.5, default=1.0, decimals=1, space='buy', optimize=True)
    
    # 4H Trend Filter - ENABLED (critical for direction)
    use_4h_filter = BooleanParameter(default=True, space='buy', optimize=False)
    
    # === ROI - FORCE EXIT EVEN AT LOSS ===
    # Accept up to 1% loss to force exit on first candle
    minimal_roi = {
        "0": -0.01,     # Accept 1% loss immediately
    }
    
    # === STOPLOSS ===
    stoploss = -0.03  # 3% tight stop for 1H
    
    # === TRAILING STOP - DISABLED for testing ===
    trailing_stop = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.02
    # trailing_only_offset_is_reached = True
    
    # === POSITION MANAGEMENT ===
    use_exit_signal = False  # DISABLED - rely on ROI/stoploss only
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # === PROTECTION MECHANISMS (CRITICAL for 1H!) ===
    @property
    def protections(self):
        return [
            {
                # Don't enter new trades for 2 hours after closing one
                "method": "CooldownPeriod",
                "stop_duration_candles": 2
            },
            {
                # After 3 losing trades in 24h, pause for 4 hours
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 4,
                "required_profit": -0.02,
                "only_per_pair": False
            },
            {
                # If 12% drawdown in 48h, pause for 12 hours
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 10,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.12
            }
        ]
    
    def informative_pairs(self):
        """4H timeframe for trend confirmation."""
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, '4h') for pair in pairs]
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate indicators:
        1. 1H indicators for entry signals
        2. 4H indicators for trend filter
        """
        
        # ===========================================
        # === 1H INDICATORS (Entry Signals) ===
        # ===========================================
        
        # RSI (21 period = balanced sensitivity)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=21)
        
        # ATR (use hyperopt parameter)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period.value)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # SuperTrend (main trend indicator) - returns (direction, line)
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period.value,
            multiplier=self.supertrend_mult.value
        )
        dataframe['supertrend'] = st_line
        dataframe['supertrend_direction'] = st_direction
        
        # EMAs (trend confirmation)
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['ema_trend'] = ta.EMA(dataframe, timeperiod=self.ema_trend.value)
        
        # ADX (trend strength)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        
        # Choppiness Index (avoid ranging markets)
        dataframe['choppiness'] = self._calculate_choppiness(dataframe, 14)
        
        # Volume Analysis
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # OBV (volume confirmation)
        dataframe['obv'] = ta.OBV(dataframe)
        dataframe['obv_sma'] = ta.SMA(dataframe['obv'], timeperiod=20)
        
        # HalfTrend (additional confirmation) - returns (direction, up, down)
        ht_direction, ht_up, ht_down = halftrend(dataframe, amplitude=2, channel_deviation=2.0)
        dataframe['halftrend_direction'] = ht_direction
        
        # QQE (RSI-based trend filter) - returns (trend, rsi_ma, line)
        qqe_trend, qqe_rsi_ma, qqe_line = qqe(dataframe, rsi_period=14, sf=5, qq_factor=4.238)
        dataframe['qqe_trend'] = qqe_trend
        
        # ===========================================
        # === 4H TREND FILTER (CRITICAL!) ===
        # ===========================================
        
        if self.dp and self.use_4h_filter.value:
            inf_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='4h')
            
            if len(inf_4h) > 0:
                # 4H SuperTrend (main filter) - returns (direction, line)
                st_4h_direction, st_4h_line = supertrend(inf_4h, period=10, multiplier=3.0)
                inf_4h['st_direction_4h'] = st_4h_direction
                
                # 4H RSI (additional filter)
                inf_4h['rsi_4h'] = ta.RSI(inf_4h, timeperiod=14)
                
                # 4H EMA (long-term trend)
                inf_4h['ema_50_4h'] = ta.EMA(inf_4h, timeperiod=50)
                inf_4h['ema_bullish_4h'] = (inf_4h['close'] > inf_4h['ema_50_4h']).astype(int)
                
                # Merge 4H into 1H
                dataframe = merge_informative_pair(
                    dataframe, 
                    inf_4h[['date', 'st_direction_4h', 'rsi_4h', 'ema_bullish_4h']],
                    self.timeframe, '4h', ffill=True
                )
            else:
                dataframe['st_direction_4h_4h'] = 1
                dataframe['rsi_4h_4h'] = 50
                dataframe['ema_bullish_4h_4h'] = 1
        else:
            dataframe['st_direction_4h_4h'] = 1
            dataframe['rsi_4h_4h'] = 50
            dataframe['ema_bullish_4h_4h'] = 1
        
        # ===========================================
        # === CONFLUENCE SCORING ===
        # ===========================================
        
        # Count bullish signals (SuperTrend + HalfTrend + QQE)
        dataframe['bull_count'] = (
            (dataframe['supertrend_direction'] == 1).astype(int) +
            (dataframe['halftrend_direction'] == 1).astype(int) +
            (dataframe['qqe_trend'] == 1).astype(int)
        )
        
        return dataframe
    
    def _calculate_choppiness(self, dataframe: DataFrame, period: int) -> pd.Series:
        """Calculate Choppiness Index."""
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
        ALWAYS TRUE Entry (DEBUG TEST)
        
        This should generate MAXIMUM possible trades.
        If still 5 trades = issue is exit/ROI, not entry!
        """
        
        conditions = []
        
        # ALWAYS TRUE - just check RSI exists
        conditions.append(dataframe['rsi'] > 0)
        
        # Volume not zero
        conditions.append(dataframe['volume'] > 0)
        
        # Combine all conditions
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        1H Exit Signals - Simple RSI-based exit
        """
        
        # Exit when RSI > 70 (overbought)
        dataframe.loc[
            (dataframe['rsi'] > 70),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stake_amount(self, pair: str, current_time: datetime,
                            current_rate: float, proposed_stake: float,
                            min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str],
                            side: str, **kwargs) -> float:
        """
        Dynamic position sizing based on volatility.
        Reduce size when ATR% is high.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        atr_pct = last_candle.get('atr_pct', 2.0)
        
        # Reduce stake in high volatility
        # Normal: ATR 2% = 100% stake
        # High: ATR 4% = 50% stake
        vol_factor = min(1.0, 2.0 / max(atr_pct, 1.0))
        
        adjusted_stake = proposed_stake * vol_factor
        
        # Clamp to min/max
        if min_stake is not None:
            adjusted_stake = max(min_stake, adjusted_stake)
        adjusted_stake = min(max_stake, adjusted_stake)
        
        return adjusted_stake
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Conservative leverage - no leverage for spot."""
        return 1.0
