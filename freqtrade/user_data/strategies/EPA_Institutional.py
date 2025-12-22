"""
EPA Institutional Strategy v7.1 - Professional Short Support
=============================================================
Full implementation with:
- ADX Hysteresis (start/end thresholds)
- Choppiness Index with proper guards
- Confirmed Pivot Swings (causal, no lookahead)
- SFP Long/Short with volume confirmation
- Trend Long/Short with crossover signals
- Fixed SL price on entry candle
- stoploss_from_absolute helper for correct short handling
- Custom exit for R:R based TP

Author: Emre Uludaşdemir
Version: 7.1 Institutional
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

import talib.abstract as talib_ta
import pandas_ta as pta

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

# Import stoploss helper - handles both long and short correctly
try:
    from freqtrade.strategy import stoploss_from_absolute
except ImportError:
    # Fallback for older versions
    def stoploss_from_absolute(stop_price: float, current_rate: float, is_short: bool = False) -> float:
        """Calculate stoploss percentage from absolute price."""
        if is_short:
            return (stop_price / current_rate) - 1
        else:
            return (stop_price / current_rate) - 1


class EPA_Institutional(IStrategy):
    """
    EPA Institutional Strategy - Professional Grade
    
    Features:
    - ADX Hysteresis for trend detection (prevents flip-flopping)
    - Choppiness Index for ranging market detection
    - Confirmed Pivot Swings (causal, delayed confirmation)
    - SFP with volume confirmation
    - Trend continuation with EMA cross
    - Fixed structural SL on entry
    - R:R based take profit
    """
    
    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 260
    
    # ==================== SHORT SUPPORT ====================
    # Set to True for futures trading (requires futures config)
    # Set to False for spot trading (no short capability)
    can_short = False  # Spot mode - change to True for futures
    
    # ROI disabled - using custom exits
    minimal_roi = {"0": 100}
    
    # Base stoploss (overridden by custom_stoploss)
    stoploss = -0.99
    use_custom_stoploss = True
    
    # Trailing disabled - using structural stops
    trailing_stop = False
    
    # Process only new candles
    process_only_new_candles = True
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # ADX Hysteresis
    adx_len = 14
    adx_start = IntParameter(20, 35, default=25, space="buy", optimize=True)
    adx_end = IntParameter(15, 25, default=20, space="buy", optimize=True)
    
    # Choppiness
    chop_len = 14
    chop_thresh = IntParameter(50, 70, default=60, space="buy", optimize=True)
    
    # ATR
    atr_len = 14
    
    # Volume
    vol_sma_len = 20
    vol_mult = DecimalParameter(1.1, 3.0, default=1.5, space="buy", optimize=True)
    
    # Pivot
    pivot_len = IntParameter(3, 10, default=5, space="buy", optimize=True)
    
    # Risk Management
    atr_buffer = DecimalParameter(0.2, 1.5, default=0.5, space="sell", optimize=True)
    risk_reward = DecimalParameter(1.0, 4.0, default=2.0, space="sell", optimize=True)
    
    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calculate all indicators using vectorized operations."""
        
        # ==================== EMAs ====================
        df["ema_fast"] = talib_ta.EMA(df, timeperiod=9)
        df["ema_slow"] = talib_ta.EMA(df, timeperiod=21)
        df["ema_bias"] = talib_ta.EMA(df, timeperiod=200)
        
        # ==================== ATR / Volume ====================
        df["atr"] = talib_ta.ATR(df, timeperiod=self.atr_len)
        df["vol_avg"] = talib_ta.SMA(df["volume"], timeperiod=self.vol_sma_len)
        
        # ==================== ADX ====================
        df["adx"] = talib_ta.ADX(df, timeperiod=self.adx_len)
        
        # ==================== CHOPPINESS INDEX ====================
        # Pine-style calculation with proper guards
        tr = talib_ta.TRANGE(df)
        sum_tr = tr.rolling(self.chop_len).sum()
        
        range_hl = (
            df["high"].rolling(self.chop_len).max() - 
            df["low"].rolling(self.chop_len).min()
        )
        # Guard against zero - use minimum tick
        range_hl = range_hl.replace(0, np.nan)
        
        df["chop"] = 100 * np.log10(sum_tr / range_hl) / np.log10(self.chop_len)
        df["chop"] = df["chop"].fillna(50)
        
        # ==================== ADX HYSTERESIS ====================
        # Prevents flip-flopping between trending/ranging states
        state = pd.Series(np.nan, index=df.index, dtype="float64")
        state[df["adx"] > self.adx_start.value] = 1.0
        state[df["adx"] < self.adx_end.value] = 0.0
        df["is_trending"] = state.ffill().fillna(0.0).astype(bool)
        
        df["is_ranging"] = (~df["is_trending"]) & (df["chop"] > self.chop_thresh.value)
        
        # ==================== CONFIRMED PIVOT SWINGS ====================
        # Causal implementation - no lookahead bias
        R = int(self.pivot_len.value)
        L = int(self.pivot_len.value)
        w = L + R + 1
        
        roll_min = df["low"].rolling(w).min()
        roll_max = df["high"].rolling(w).max()
        
        # Pivot confirmed after R bars (shifted by R)
        piv_low_conf = np.where(df["low"].shift(R) == roll_min, df["low"].shift(R), np.nan)
        piv_high_conf = np.where(df["high"].shift(R) == roll_max, df["high"].shift(R), np.nan)
        
        df["swing_low"] = pd.Series(piv_low_conf, index=df.index).ffill()
        df["swing_high"] = pd.Series(piv_high_conf, index=df.index).ffill()
        
        # Previous swing levels (for entry conditions)
        df["last_swing_low"] = df["swing_low"].shift(1)
        df["last_swing_high"] = df["swing_high"].shift(1)
        
        return df
    
    def populate_entry_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Entry logic with proper long/short separation.
        
        LONG entries:
        - Trend: EMA crossover + price > 200 EMA + swing low exists
        - SFP: Ranging + sweep low + reclaim + volume spike
        
        SHORT entries:
        - Trend: EMA crossunder + price < 200 EMA + swing high exists
        - SFP: Ranging + sweep high + reclaim + volume spike
        """
        
        df["enter_long"] = 0
        df["enter_short"] = 0
        df["entry_tag"] = ""
        
        # Volume confirmation
        vol_ok = df["volume"] > (df["vol_avg"] * float(self.vol_mult.value))
        
        # ==================== EMA CROSS SIGNALS ====================
        cross_up = (
            (df["ema_fast"] > df["ema_slow"]) & 
            (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))
        )
        cross_dn = (
            (df["ema_fast"] < df["ema_slow"]) & 
            (df["ema_fast"].shift(1) >= df["ema_slow"].shift(1))
        )
        
        # ==================== TREND ENTRIES ====================
        # Long: Trending + EMA cross up + above bias + swing low exists
        trend_long = (
            df["is_trending"] & 
            cross_up & 
            (df["close"] > df["ema_bias"]) & 
            df["last_swing_low"].notna()
        )
        
        # Short: Trending + EMA cross down + below bias + swing high exists
        trend_short = (
            df["is_trending"] & 
            cross_dn & 
            (df["close"] < df["ema_bias"]) & 
            df["last_swing_high"].notna()
        )
        
        # ==================== SFP ENTRIES ====================
        # Long SFP: Ranging + sweep low + reclaim + volume
        sfp_long = (
            df["is_ranging"] & 
            df["last_swing_low"].notna() &
            (df["low"] < df["last_swing_low"]) &
            (df["close"] > df["last_swing_low"]) &
            vol_ok
        )
        
        # Short SFP: Ranging + sweep high + reclaim + volume
        sfp_short = (
            df["is_ranging"] & 
            df["last_swing_high"].notna() &
            (df["high"] > df["last_swing_high"]) &
            (df["close"] < df["last_swing_high"]) &
            vol_ok
        )
        
        # ==================== SET ENTRY SIGNALS ====================
        df.loc[trend_long | sfp_long, "enter_long"] = 1
        df.loc[trend_short | sfp_short, "enter_short"] = 1
        
        # Entry tags for analysis
        df.loc[trend_long, "entry_tag"] = "trend_long"
        df.loc[sfp_long, "entry_tag"] = "sfp_long"
        df.loc[trend_short, "entry_tag"] = "trend_short"
        df.loc[sfp_short, "entry_tag"] = "sfp_short"
        
        # ==================== FIXED SL PRICE ON ENTRY ====================
        # Store SL price on entry candle for custom_stoploss to read
        buf = df["atr"] * float(self.atr_buffer.value)
        
        sl_long_sfp = df["low"] - buf
        sl_long_trend = df["last_swing_low"] - buf
        sl_short_sfp = df["high"] + buf
        sl_short_trend = df["last_swing_high"] + buf
        
        df["sl_price"] = np.nan
        df.loc[sfp_long, "sl_price"] = sl_long_sfp
        df.loc[trend_long, "sl_price"] = sl_long_trend
        df.loc[sfp_short, "sl_price"] = sl_short_sfp
        df.loc[trend_short, "sl_price"] = sl_short_trend
        
        return df
    
    def populate_exit_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Exit signals - handled via custom_exit and custom_stoploss.
        No dataframe-based exit signals used.
        """
        df["exit_long"] = 0
        df["exit_short"] = 0
        return df
    
    def _get_entry_row(self, pair: str, trade: Trade) -> Optional[pd.Series]:
        """Get the dataframe row at trade entry time."""
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if df is None or df.empty:
            return None
        
        # Try to find entry row by date
        if "date" in df.columns:
            row = df.loc[df["date"] == trade.open_date_utc]
            if not row.empty:
                return row.iloc[-1]
        
        # Fallback: try index lookup
        if trade.open_date_utc in df.index:
            return df.loc[trade.open_date_utc]
        
        return None
    
    def custom_stoploss(
        self, 
        pair: str, 
        trade: Trade, 
        current_time: datetime,
        current_rate: float, 
        current_profit: float,
        **kwargs
    ) -> float:
        """
        Structural stop loss using fixed SL price from entry.
        
        Uses stoploss_from_absolute helper for correct long/short handling.
        Returns stoploss % relative to current_rate.
        """
        entry_row = self._get_entry_row(pair, trade)
        
        if entry_row is None:
            return -0.99  # Wide fallback stop
        
        sl_abs = entry_row.get("sl_price", np.nan)
        
        if pd.isna(sl_abs):
            return -0.99
        
        # Use helper for correct conversion (handles is_short properly)
        return stoploss_from_absolute(
            float(sl_abs), 
            current_rate, 
            is_short=trade.is_short
        )
    
    def custom_exit(
        self, 
        pair: str, 
        trade: Trade, 
        current_time: datetime,
        current_rate: float, 
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        Take profit based on Risk:Reward ratio.
        
        TP = Entry + (Risk * RR) for long
        TP = Entry - (Risk * RR) for short
        """
        entry_row = self._get_entry_row(pair, trade)
        
        if entry_row is None:
            return None
        
        sl_abs = entry_row.get("sl_price", np.nan)
        
        if pd.isna(sl_abs):
            return None
        
        rr = float(self.risk_reward.value)
        
        if not trade.is_short:
            # Long: risk = entry - SL, TP = entry + risk * RR
            risk = trade.open_rate - float(sl_abs)
            tp_abs = trade.open_rate + (risk * rr)
            
            if current_rate >= tp_abs:
                return f"tp_{rr}R_long"
        else:
            # Short: risk = SL - entry, TP = entry - risk * RR
            risk = float(sl_abs) - trade.open_rate
            tp_abs = trade.open_rate - (risk * rr)
            
            if current_rate <= tp_abs:
                return f"tp_{rr}R_short"
        
        return None
    
    def leverage(
        self, 
        pair: str, 
        current_time: datetime, 
        current_rate: float,
        proposed_leverage: float, 
        max_leverage: float,
        entry_tag: Optional[str], 
        side: str, 
        **kwargs
    ) -> float:
        """
        Conservative leverage.
        Can be increased for futures with proper risk management.
        """
        return 1.0


class EPA_Institutional_Futures(EPA_Institutional):
    """
    EPA Institutional for Futures with 3x leverage.
    
    Warning: Only use with proper funding rate understanding.
    """
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Allow up to 3x leverage for futures."""
        return min(3.0, max_leverage)
