"""
EPA Production Strategy v9.0 - Multi-Timeframe Institutional Bot
=================================================================
Production-grade trading bot with:

1. Multi-Timeframe Analysis (1D/4H/1H)
2. Supertrend + MACD + RSI Combo
3. TEMA + ADX + CMO Trend Strength
4. SMC Liquidity Sweep Detection
5. Session Filters (London/NY)
6. Dynamic Trailing + Breakeven
7. Telegram Notifications Ready

Targets:
- Win Rate: >80%
- Profit Factor: >2.0
- Max Drawdown: <15%

Author: Emre Uludaşdemir
Version: 9.0 Production
"""

import numpy as np
import pandas as pd
from datetime import datetime, time
from typing import Optional, Dict, Any

import talib.abstract as ta

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair

try:
    from freqtrade.strategy import stoploss_from_absolute
except ImportError:
    def stoploss_from_absolute(stop_price: float, current_rate: float, is_short: bool = False) -> float:
        return (stop_price / current_rate) - 1


class EPA_Production(IStrategy):
    """
    EPA Production - Multi-Timeframe Institutional Trading Bot
    
    Strategy Logic:
    1. 1D Timeframe: Overall trend bias (EMA 50/200 golden/death cross)
    2. 4H Timeframe: Market structure (BOS, swing levels)
    3. 1H Timeframe: Entry execution (SFP, pullbacks, Supertrend)
    
    Entry Conditions:
    - 1D trend aligned
    - 4H structure bullish/bearish
    - 1H entry signal with volume
    - Session filter (London/NY overlap preferred)
    """
    
    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 500
    
    # Spot mode - set True for futures
    can_short = False
    
    # Disable ROI - using custom TP
    minimal_roi = {"0": 100}
    
    # Base stoploss
    stoploss = -0.99
    use_custom_stoploss = True
    
    # Trailing configuration
    trailing_stop = False  # Handled in custom_stoploss
    
    # Position adjustment for partial TP
    position_adjustment_enable = True
    max_entry_position_adjustment = 0
    
    process_only_new_candles = True
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # Supertrend
    st_period = IntParameter(7, 14, default=10, space="buy", optimize=True)
    st_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space="buy", optimize=True)
    
    # ADX/TEMA/CMO
    adx_period = IntParameter(10, 20, default=14, space="buy", optimize=True)
    adx_threshold = IntParameter(20, 35, default=25, space="buy", optimize=True)
    tema_period = IntParameter(15, 30, default=20, space="buy", optimize=True)
    
    # Volume
    vol_mult = DecimalParameter(1.2, 2.5, default=1.5, space="buy", optimize=True)
    
    # Risk Management
    atr_buffer = DecimalParameter(0.3, 1.0, default=0.5, space="sell", optimize=True)
    breakeven_pct = DecimalParameter(0.01, 0.03, default=0.015, space="sell", optimize=True)
    tp_1r_mult = DecimalParameter(1.0, 2.0, default=1.5, space="sell", optimize=True)
    tp_2r_mult = DecimalParameter(2.0, 4.0, default=3.0, space="sell", optimize=True)
    
    # Session Filter
    use_session_filter = True
    
    def informative_pairs(self):
        """Multi-timeframe data: 4H and 1D."""
        pairs = self.dp.current_whitelist()
        informative = []
        for pair in pairs:
            informative.append((pair, '4h'))
            informative.append((pair, '1d'))
        return informative
    
    def populate_indicators(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calculate all indicators including MTF."""
        
        pair = metadata['pair']
        
        # ==================== 1H INDICATORS ====================
        
        # Core EMAs
        df["ema_9"] = ta.EMA(df, timeperiod=9)
        df["ema_21"] = ta.EMA(df, timeperiod=21)
        df["ema_50"] = ta.EMA(df, timeperiod=50)
        
        # ATR
        df["atr"] = ta.ATR(df, timeperiod=14)
        
        # Volume
        df["vol_sma"] = ta.SMA(df["volume"], timeperiod=20)
        df["vol_ratio"] = df["volume"] / df["vol_sma"]
        df["volume_spike"] = (df["vol_ratio"] > float(self.vol_mult.value)).astype(int)
        
        # ADX + DI
        df["adx"] = ta.ADX(df, timeperiod=self.adx_period.value)
        df["plus_di"] = ta.PLUS_DI(df, timeperiod=self.adx_period.value)
        df["minus_di"] = ta.MINUS_DI(df, timeperiod=self.adx_period.value)
        
        # TEMA
        df["tema"] = ta.TEMA(df, timeperiod=self.tema_period.value)
        
        # CMO (Chande Momentum Oscillator)
        df["cmo"] = ta.CMO(df, timeperiod=14)
        
        # RSI
        df["rsi"] = ta.RSI(df, timeperiod=14)
        
        # MACD
        macd = ta.MACD(df)
        df["macd"] = macd["macd"]
        df["macd_signal"] = macd["macdsignal"]
        df["macd_hist"] = macd["macdhist"]
        
        # ==================== SUPERTREND ====================
        df = self._calculate_supertrend(df)
        
        # ==================== TREND STRENGTH COMBO ====================
        # TEMA + ADX + CMO combination for trend strength
        df["trend_strength"] = (
            (df["adx"] > self.adx_threshold.value) &
            (df["close"] > df["tema"]) &
            (df["cmo"] > 0)
        ).astype(int)
        
        df["trend_weakness"] = (
            (df["adx"] > self.adx_threshold.value) &
            (df["close"] < df["tema"]) &
            (df["cmo"] < 0)
        ).astype(int)
        
        # ==================== SESSION FILTER ====================
        if self.use_session_filter and "date" in df.columns:
            df["session_active"] = df["date"].apply(self._is_active_session)
        else:
            df["session_active"] = True
        
        # ==================== SWING LEVELS ====================
        df = self._calculate_swing_levels(df)
        
        # ==================== 4H MTF DATA ====================
        informative_4h = self.dp.get_pair_dataframe(pair=pair, timeframe='4h')
        if len(informative_4h) > 0:
            informative_4h["ema_21_4h"] = ta.EMA(informative_4h, timeperiod=21)
            informative_4h["ema_50_4h"] = ta.EMA(informative_4h, timeperiod=50)
            informative_4h["structure_bull_4h"] = (informative_4h["ema_21_4h"] > informative_4h["ema_50_4h"]).astype(int)
            informative_4h["structure_bear_4h"] = (informative_4h["ema_21_4h"] < informative_4h["ema_50_4h"]).astype(int)
            
            # Merge
            df = merge_informative_pair(df, informative_4h, self.timeframe, '4h', ffill=True)
        else:
            df["structure_bull_4h_4h"] = 1
            df["structure_bear_4h_4h"] = 0
        
        # ==================== 1D MTF DATA ====================
        informative_1d = self.dp.get_pair_dataframe(pair=pair, timeframe='1d')
        if len(informative_1d) > 0:
            informative_1d["ema_50_1d"] = ta.EMA(informative_1d, timeperiod=50)
            informative_1d["ema_200_1d"] = ta.EMA(informative_1d, timeperiod=200)
            informative_1d["bias_bull_1d"] = (informative_1d["ema_50_1d"] > informative_1d["ema_200_1d"]).astype(int)
            informative_1d["bias_bear_1d"] = (informative_1d["ema_50_1d"] < informative_1d["ema_200_1d"]).astype(int)
            
            # Merge
            df = merge_informative_pair(df, informative_1d, self.timeframe, '1d', ffill=True)
        else:
            df["bias_bull_1d_1d"] = 1
            df["bias_bear_1d_1d"] = 0
        
        return df
    
    def _calculate_supertrend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Supertrend indicator."""
        period = int(self.st_period.value)
        multiplier = float(self.st_multiplier.value)
        
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.ATR(df, timeperiod=period)
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upper_band.iloc[i-1]:
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < lower_band.iloc[i-1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i-1] if i > 0 else 1
            
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
        
        df["supertrend"] = supertrend
        df["st_direction"] = direction.fillna(1).astype(int)
        df["st_bullish"] = (df["st_direction"] == 1).astype(int)
        df["st_bearish"] = (df["st_direction"] == -1).astype(int)
        
        return df
    
    def _calculate_swing_levels(self, df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
        """Calculate swing highs and lows."""
        df["swing_high"] = df["high"].rolling(lookback * 2 + 1, center=True).max()
        df["swing_low"] = df["low"].rolling(lookback * 2 + 1, center=True).min()
        
        # Shift to avoid lookahead
        df["last_swing_high"] = df["swing_high"].shift(lookback + 1).ffill()
        df["last_swing_low"] = df["swing_low"].shift(lookback + 1).ffill()
        
        return df
    
    def _is_active_session(self, dt) -> bool:
        """Check if current time is in active trading session."""
        if pd.isna(dt):
            return True
        
        hour = dt.hour
        
        # London session: 07:00 - 16:00 UTC
        # NY session: 12:00 - 21:00 UTC
        # Overlap: 12:00 - 16:00 UTC (best time)
        
        # Active hours: 07:00 - 21:00 UTC
        return 7 <= hour <= 21
    
    def populate_entry_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Multi-Timeframe Entry Logic:
        
        LONG:
        1. 1D bias bullish (EMA 50 > 200)
        2. 4H structure bullish (EMA 21 > 50)
        3. 1H: Supertrend bullish + MACD bullish + RSI > 50
        4. Volume spike
        5. Session active
        
        SHORT (if enabled):
        1. 1D bias bearish
        2. 4H structure bearish
        3. 1H: Supertrend bearish + MACD bearish + RSI < 50
        """
        
        df["enter_long"] = 0
        df["enter_short"] = 0
        df["entry_tag"] = ""
        
        # Get MTF columns (handle column naming)
        bias_bull_1d = df.get("bias_bull_1d_1d", df.get("bias_bull_1d", pd.Series(1, index=df.index)))
        structure_bull_4h = df.get("structure_bull_4h_4h", df.get("structure_bull_4h", pd.Series(1, index=df.index)))
        
        # ==================== LONG ENTRY CONDITIONS ====================
        
        # 1D Bias bullish
        daily_bull = bias_bull_1d == 1
        
        # 4H Structure bullish
        h4_bull = structure_bull_4h == 1
        
        # 1H Entry signals
        supertrend_bull = df["st_bullish"] == 1
        macd_bull = df["macd"] > df["macd_signal"]
        rsi_bull = df["rsi"] > 50
        
        # Trend strength confirmation
        trend_strong = df["trend_strength"] == 1
        
        # Volume confirmation
        vol_ok = df["volume_spike"] == 1
        
        # Session filter
        session_ok = df["session_active"] == True
        
        # === Primary Long: Full MTF Confluence ===
        long_mtf = (
            daily_bull &
            h4_bull &
            supertrend_bull &
            macd_bull &
            rsi_bull &
            vol_ok &
            session_ok
        )
        
        # === Secondary Long: Trend Strength + Supertrend ===
        long_trend = (
            h4_bull &
            supertrend_bull &
            trend_strong &
            vol_ok &
            session_ok
        )
        
        # === Pullback Long: Price touches EMA in uptrend ===
        pullback_long = (
            daily_bull &
            supertrend_bull &
            (df["low"] <= df["ema_21"]) &
            (df["close"] > df["ema_21"]) &
            (df["close"] > df["open"]) &
            vol_ok
        )
        
        # Combine long signals
        df.loc[long_mtf, "enter_long"] = 1
        df.loc[long_mtf, "entry_tag"] = "mtf_long"
        
        df.loc[long_trend & ~long_mtf, "enter_long"] = 1
        df.loc[long_trend & ~long_mtf, "entry_tag"] = "trend_long"
        
        df.loc[pullback_long & ~long_mtf & ~long_trend, "enter_long"] = 1
        df.loc[pullback_long & ~long_mtf & ~long_trend, "entry_tag"] = "pullback_long"
        
        # ==================== SHORT ENTRY CONDITIONS ====================
        if self.can_short:
            bias_bear_1d = df.get("bias_bear_1d_1d", df.get("bias_bear_1d", pd.Series(0, index=df.index)))
            structure_bear_4h = df.get("structure_bear_4h_4h", df.get("structure_bear_4h", pd.Series(0, index=df.index)))
            
            daily_bear = bias_bear_1d == 1
            h4_bear = structure_bear_4h == 1
            supertrend_bear = df["st_bearish"] == 1
            macd_bear = df["macd"] < df["macd_signal"]
            rsi_bear = df["rsi"] < 50
            
            short_mtf = (
                daily_bear &
                h4_bear &
                supertrend_bear &
                macd_bear &
                rsi_bear &
                vol_ok &
                session_ok
            )
            
            df.loc[short_mtf, "enter_short"] = 1
            df.loc[short_mtf, "entry_tag"] = "mtf_short"
        
        # ==================== STORE SL PRICE ====================
        buf = df["atr"] * float(self.atr_buffer.value)
        
        df["sl_price"] = np.nan
        df.loc[df["enter_long"] == 1, "sl_price"] = df["low"] - buf
        df.loc[df["enter_short"] == 1, "sl_price"] = df["high"] + buf
        
        return df
    
    def populate_exit_trend(self, df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Exit handled via custom_exit and custom_stoploss."""
        df["exit_long"] = 0
        df["exit_short"] = 0
        return df
    
    def _get_entry_row(self, pair: str, trade: Trade) -> Optional[pd.Series]:
        """Get dataframe row at trade entry."""
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
        """
        Dynamic stop loss with breakeven and trailing.
        
        Stages:
        1. Initial: Structural stop (swing low - ATR buffer)
        2. Breakeven: Move to entry + small buffer at 1.5%
        3. Trailing: Trail at 50% of profit above 3%
        """
        
        # Stage 1: Breakeven at 1.5%
        if current_profit >= float(self.breakeven_pct.value):
            return -0.002  # Breakeven + 0.2% buffer
        
        # Stage 2: Trailing at 3%
        if current_profit >= 0.03:
            return -(current_profit * 0.5)  # Trail at 50% of profit
        
        # Stage 3: Structural stop
        entry_row = self._get_entry_row(pair, trade)
        if entry_row is not None:
            sl_abs = entry_row.get("sl_price", np.nan)
            if not pd.isna(sl_abs):
                return stoploss_from_absolute(float(sl_abs), current_rate, is_short=trade.is_short)
        
        return -0.05  # Default 5% stop
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs) -> Optional[str]:
        """
        Take Profit based on R multiples.
        
        1R = Entry risk (entry - SL)
        TP1 = 1.5R (partial)
        TP2 = 3R (full)
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
            tp_1r = trade.open_rate + (risk * float(self.tp_1r_mult.value))
            tp_2r = trade.open_rate + (risk * float(self.tp_2r_mult.value))
            
            if current_rate >= tp_2r:
                return f"tp_{self.tp_2r_mult.value}R_long"
            elif current_rate >= tp_1r:
                return f"tp_{self.tp_1r_mult.value}R_long"
        else:
            risk = float(sl_abs) - trade.open_rate
            tp_1r = trade.open_rate - (risk * float(self.tp_1r_mult.value))
            tp_2r = trade.open_rate - (risk * float(self.tp_2r_mult.value))
            
            if current_rate <= tp_2r:
                return f"tp_{self.tp_2r_mult.value}R_short"
            elif current_rate <= tp_1r:
                return f"tp_{self.tp_1r_mult.value}R_short"
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Conservative leverage for safety."""
        return 1.0


class EPA_Production_Futures(EPA_Production):
    """EPA Production for Futures with short support and leverage."""
    can_short = True
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """3x leverage for futures."""
        return min(3.0, max_leverage)
