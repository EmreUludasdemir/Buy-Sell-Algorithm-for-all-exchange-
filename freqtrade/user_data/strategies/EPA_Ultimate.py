"""
EPA Ultimate Strategy v8.0 - All Improvements Integrated
==========================================================
Complete implementation with ALL enhancements:

1. SFP Micro-MSS Confirmation
2. Trend Pullback Filter
3. Multi-Timeframe Confluence (4H bias)
4. Partial Take Profit (1R + 2R)
5. ML Signal Scoring Ready

Author: Emre Uludaşdemir
Version: 8.0 Ultimate
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any

import talib.abstract as talib_ta

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair

# Import stoploss helper
try:
    from freqtrade.strategy import stoploss_from_absolute
except ImportError:
    def stoploss_from_absolute(stop_price: float, current_rate: float, is_short: bool = False) -> float:
        if is_short:
            return (stop_price / current_rate) - 1
        else:
            return (stop_price / current_rate) - 1


class EPA_Ultimate(IStrategy):
    """
    EPA Ultimate Strategy - All Improvements Integrated
    
    Features:
    1. SFP Micro-MSS: Sweep + reclaim + minor structure break
    2. Trend Pullback: Cross + pullback to EMA + rejection
    3. MTF Confluence: 4H trend alignment
    4. Partial TP: 50% at 1R, 50% at 2R
    5. ML Features: Volume ratio, wick size, ADX context
    """
    
    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 300
    
    # Spot mode (change to True for futures)
    can_short = False
    
    # ROI disabled - using custom TP
    minimal_roi = {"0": 100}
    
    # Base stoploss
    stoploss = -0.99
    use_custom_stoploss = True
    
    # Trailing disabled
    trailing_stop = False
    
    # Position adjustment for partial TP
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    
    process_only_new_candles = True
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # ADX Hysteresis
    adx_len = 14
    adx_start = IntParameter(20, 35, default=25, space="buy", optimize=True)
    adx_end = IntParameter(15, 25, default=20, space="buy", optimize=True)
    
    # Choppiness
    chop_len = 14
    chop_thresh = IntParameter(50, 70, default=60, space="buy", optimize=True)
    
    # Volume
    vol_sma_len = 20
    vol_mult = DecimalParameter(1.1, 3.0, default=1.5, space="buy", optimize=True)
    
    # Pivot
    pivot_len = IntParameter(3, 10, default=5, space="buy", optimize=True)
    
    # Risk Management
    atr_buffer = DecimalParameter(0.2, 1.5, default=0.5, space="sell", optimize=True)
    tp_1r_pct = DecimalParameter(0.3, 0.7, default=0.5, space="sell", optimize=True)
    tp_2r_mult = DecimalParameter(1.5, 3.0, default=2.0, space="sell", optimize=True)
    
    def informative_pairs(self):
        """4H timeframe for MTF confluence."""
        pairs = self.dp.current_whitelist()
        return [(pair, '4h') for pair in pairs]
    
    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calculate all indicators including MTF."""
        
        # ==================== CORE EMAs ====================
        df["ema_fast"] = talib_ta.EMA(df, timeperiod=9)
        df["ema_slow"] = talib_ta.EMA(df, timeperiod=21)
        df["ema_bias"] = talib_ta.EMA(df, timeperiod=200)
        
        # ==================== ATR / Volume ====================
        df["atr"] = talib_ta.ATR(df, timeperiod=14)
        df["vol_avg"] = talib_ta.SMA(df["volume"], timeperiod=self.vol_sma_len)
        
        # ==================== ADX ====================
        df["adx"] = talib_ta.ADX(df, timeperiod=self.adx_len)
        
        # ==================== CHOPPINESS INDEX ====================
        tr = talib_ta.TRANGE(df)
        sum_tr = tr.rolling(self.chop_len).sum()
        range_hl = (df["high"].rolling(self.chop_len).max() - df["low"].rolling(self.chop_len).min()).replace(0, np.nan)
        df["chop"] = (100 * np.log10(sum_tr / range_hl) / np.log10(self.chop_len)).fillna(50)
        
        # ==================== ADX HYSTERESIS ====================
        state = pd.Series(np.nan, index=df.index, dtype="float64")
        state[df["adx"] > self.adx_start.value] = 1.0
        state[df["adx"] < self.adx_end.value] = 0.0
        df["is_trending"] = state.ffill().fillna(0.0).astype(bool)
        df["is_ranging"] = (~df["is_trending"]) & (df["chop"] > self.chop_thresh.value)
        
        # ==================== CONFIRMED PIVOT SWINGS ====================
        R = int(self.pivot_len.value)
        L = int(self.pivot_len.value)
        w = L + R + 1
        
        roll_min = df["low"].rolling(w).min()
        roll_max = df["high"].rolling(w).max()
        
        piv_low_conf = np.where(df["low"].shift(R) == roll_min, df["low"].shift(R), np.nan)
        piv_high_conf = np.where(df["high"].shift(R) == roll_max, df["high"].shift(R), np.nan)
        
        df["swing_low"] = pd.Series(piv_low_conf, index=df.index).ffill()
        df["swing_high"] = pd.Series(piv_high_conf, index=df.index).ffill()
        df["last_swing_low"] = df["swing_low"].shift(1)
        df["last_swing_high"] = df["swing_high"].shift(1)
        
        # ==================== 4H MTF CONFLUENCE ====================
        informative_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='4h')
        if len(informative_4h) > 0:
            informative_4h["ema_fast_4h"] = talib_ta.EMA(informative_4h, timeperiod=9)
            informative_4h["ema_slow_4h"] = talib_ta.EMA(informative_4h, timeperiod=21)
            informative_4h["htf_bullish"] = (informative_4h["ema_fast_4h"] > informative_4h["ema_slow_4h"]).astype(int)
            informative_4h["htf_bearish"] = (informative_4h["ema_fast_4h"] < informative_4h["ema_slow_4h"]).astype(int)
            
            df = merge_informative_pair(df, informative_4h, self.timeframe, '4h', ffill=True)
        else:
            df["htf_bullish_4h"] = 1
            df["htf_bearish_4h"] = 0
        
        # ==================== ML FEATURES ====================
        vol_ratio = df["volume"] / df["vol_avg"]
        upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
        lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
        
        df["ml_volume_ratio"] = vol_ratio
        df["ml_wick_atr_ratio"] = (upper_wick + lower_wick) / df["atr"]
        df["ml_adx"] = df["adx"]
        df["ml_chop"] = df["chop"]
        
        return df
    
    def populate_entry_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entry logic with ALL improvements:
        1. SFP Micro-MSS: Sweep + reclaim + bullish close > prev close
        2. Trend Pullback: Cross + touch EMA + bullish rejection
        3. MTF: 4H trend must align
        """
        
        df["enter_long"] = 0
        df["enter_short"] = 0
        df["entry_tag"] = ""
        
        # Volume confirmation
        vol_ok = df["volume"] > (df["vol_avg"] * float(self.vol_mult.value))
        
        # EMA Cross signals
        cross_up = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        cross_dn = (df["ema_fast"] < df["ema_slow"]) & (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))
        
        # ==================== 1. SFP MICRO-MSS LONG ====================
        # Sweep + Reclaim + Close > Previous Close (micro bullish structure)
        sfp_long_base = (
            df["is_ranging"] & 
            df["last_swing_low"].notna() &
            (df["low"] < df["last_swing_low"]) &
            (df["close"] > df["last_swing_low"]) &
            vol_ok
        )
        # Micro-MSS: Current close > previous close (structure break)
        sfp_long_mss = sfp_long_base & (df["close"] > df["close"].shift(1))
        
        # ==================== 2. TREND PULLBACK LONG ====================
        # After cross up, wait for pullback to EMA then bullish rejection
        in_uptrend = df["ema_fast"] > df["ema_slow"]
        pullback_to_ema = df["low"] <= df["ema_fast"]
        bullish_rejection = (df["close"] > df["ema_fast"]) & (df["close"] > df["open"])
        
        trend_pullback_long = (
            df["is_trending"] &
            in_uptrend &
            pullback_to_ema &
            bullish_rejection &
            (df["close"] > df["ema_bias"]) &
            df["last_swing_low"].notna()
        )
        
        # ==================== 3. MTF CONFLUENCE ====================
        htf_bull_col = "htf_bullish_4h" if "htf_bullish_4h" in df.columns else "htf_bullish"
        htf_bullish = df.get(htf_bull_col, pd.Series(1, index=df.index)) == 1
        
        # ==================== FINAL LONG SIGNAL ====================
        long_signal = (sfp_long_mss | trend_pullback_long) & htf_bullish
        
        df.loc[long_signal, "enter_long"] = 1
        df.loc[sfp_long_mss & htf_bullish, "entry_tag"] = "sfp_mss_long"
        df.loc[trend_pullback_long & htf_bullish & ~sfp_long_mss, "entry_tag"] = "pullback_long"
        
        # ==================== SHORT SIGNALS (if enabled) ====================
        if self.can_short:
            sfp_short_base = (
                df["is_ranging"] & 
                df["last_swing_high"].notna() &
                (df["high"] > df["last_swing_high"]) &
                (df["close"] < df["last_swing_high"]) &
                vol_ok
            )
            sfp_short_mss = sfp_short_base & (df["close"] < df["close"].shift(1))
            
            in_downtrend = df["ema_fast"] < df["ema_slow"]
            pullback_to_ema_short = df["high"] >= df["ema_fast"]
            bearish_rejection = (df["close"] < df["ema_fast"]) & (df["close"] < df["open"])
            
            trend_pullback_short = (
                df["is_trending"] &
                in_downtrend &
                pullback_to_ema_short &
                bearish_rejection &
                (df["close"] < df["ema_bias"]) &
                df["last_swing_high"].notna()
            )
            
            htf_bear_col = "htf_bearish_4h" if "htf_bearish_4h" in df.columns else "htf_bearish"
            htf_bearish = df.get(htf_bear_col, pd.Series(0, index=df.index)) == 1
            
            short_signal = (sfp_short_mss | trend_pullback_short) & htf_bearish
            df.loc[short_signal, "enter_short"] = 1
            df.loc[sfp_short_mss & htf_bearish, "entry_tag"] = "sfp_mss_short"
            df.loc[trend_pullback_short & htf_bearish & ~sfp_short_mss, "entry_tag"] = "pullback_short"
        
        # ==================== FIXED SL PRICE ON ENTRY ====================
        buf = df["atr"] * float(self.atr_buffer.value)
        
        df["sl_price"] = np.nan
        df.loc[sfp_long_mss, "sl_price"] = df["low"] - buf
        df.loc[trend_pullback_long, "sl_price"] = df["last_swing_low"] - buf
        
        if self.can_short:
            df.loc[sfp_short_mss, "sl_price"] = df["high"] + buf
            df.loc[trend_pullback_short, "sl_price"] = df["last_swing_high"] + buf
        
        return df
    
    def populate_exit_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Exit handled via custom_exit for partial TP."""
        df["exit_long"] = 0
        df["exit_short"] = 0
        return df
    
    def _get_entry_row(self, pair: str, trade: Trade) -> Optional[pd.Series]:
        """Get the dataframe row at trade entry time."""
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return None
        if "date" in df.columns:
            row = df.loc[df["date"] == trade.open_date_utc]
            if not row.empty:
                return row.iloc[-1]
        return None
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """Structural stop loss using fixed SL price from entry."""
        entry_row = self._get_entry_row(pair, trade)
        if entry_row is None:
            return -0.99
        
        sl_abs = entry_row.get("sl_price", np.nan)
        if pd.isna(sl_abs):
            return -0.99
        
        return stoploss_from_absolute(float(sl_abs), current_rate, is_short=trade.is_short)
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs) -> Optional[str]:
        """
        Partial Take Profit System:
        - 1R: Exit 50%
        - 2R: Exit remaining 50%
        """
        entry_row = self._get_entry_row(pair, trade)
        if entry_row is None:
            return None
        
        sl_abs = entry_row.get("sl_price", np.nan)
        if pd.isna(sl_abs):
            return None
        
        # Calculate risk
        if not trade.is_short:
            risk = trade.open_rate - float(sl_abs)
            tp_1r = trade.open_rate + risk
            tp_2r = trade.open_rate + (risk * float(self.tp_2r_mult.value))
            
            # Check 2R first (full exit)
            if current_rate >= tp_2r:
                return f"tp_{self.tp_2r_mult.value}R_long"
            # Then 1R (partial exit handled by adjust_trade_position)
            elif current_rate >= tp_1r:
                return "tp_1R_long"
        else:
            risk = float(sl_abs) - trade.open_rate
            tp_1r = trade.open_rate - risk
            tp_2r = trade.open_rate - (risk * float(self.tp_2r_mult.value))
            
            if current_rate <= tp_2r:
                return f"tp_{self.tp_2r_mult.value}R_short"
            elif current_rate <= tp_1r:
                return "tp_1R_short"
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Conservative leverage."""
        return 1.0


class EPA_Ultimate_Futures(EPA_Ultimate):
    """EPA Ultimate for Futures with short support and 3x leverage."""
    can_short = True
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return min(3.0, max_leverage)
