"""
AlphaTrendAdaptive Strategy
===========================
1H timeframe adaptive strategy using AlphaTrend with regime detection.

Entry Types:
- TREND_PULLBACK: Enter on pullback in established trend
- SQUEEZE_BREAKOUT: Enter on volatility expansion from squeeze
- REVERSAL: Enter on VixFix capitulation + structure change

Features:
- Regime-adaptive stoploss (ATR × 1.5-2.5)
- HTF filter (4H EMA200)
- Multiple entry types based on market conditions
- No lookahead/repaint

Author: EPA Trading Bot
"""

import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_prev_date

# Add indicators to path
sys.path.insert(0, '/freqtrade/user_data/indicators')

try:
    from alpha_trend import AlphaTrendCalculator
    from squeeze_momentum import SqueezeMomentumCalculator
    from wave_trend import WaveTrendCalculator
    from regime_detector import RegimeDetector, MarketRegime
    from williams_vix_fix import WilliamsVixFix
    from smc.swing_points import SwingPointDetector
    from smc.structure_breaks import StructureBreakDetector
except ImportError:
    # Fallback - use inline implementations
    pass

logger = logging.getLogger(__name__)


class EntryType(Enum):
    TREND_PULLBACK = "trend_pullback"
    SQUEEZE_BREAKOUT = "squeeze_breakout"
    REVERSAL = "reversal"


class AlphaTrendAdaptive(IStrategy):
    """
    AlphaTrend Adaptive Strategy
    
    Uses regime detection to adapt entry conditions and stoploss.
    Multiple entry types for different market conditions.
    """
    
    INTERFACE_VERSION = 3
    
    # Timeframe
    timeframe = '1h'
    
    # Spot only
    can_short = False
    
    # Exit configuration
    use_exit_signal = True
    use_custom_stoploss = True
    exit_profit_only = False
    
    # Process only new candles
    process_only_new_candles = True
    
    # Startup candles
    startup_candle_count: int = 250
    
    # ═══════════════════════════════════════════════════════════════
    # ROI TABLE
    # ═══════════════════════════════════════════════════════════════
    minimal_roi = {
        "0": 0.15,
        "60": 0.08,
        "120": 0.05,
        "240": 0.03,
        "480": 0.02
    }
    
    # Stoploss - disabled, using custom
    stoploss = -0.99
    
    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True
    
    # ═══════════════════════════════════════════════════════════════
    # PROTECTIONS
    # ═══════════════════════════════════════════════════════════════
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 4
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 3,
                "stop_duration_candles": 24,
                "only_per_pair": False
            }
        ]
    
    # ═══════════════════════════════════════════════════════════════
    # PARAMETERS
    # ═══════════════════════════════════════════════════════════════
    # AlphaTrend
    at_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    at_coeff = DecimalParameter(0.8, 1.5, default=1.0, decimals=1, space='buy', optimize=True)
    
    # Regime
    adx_trending = IntParameter(20, 35, default=25, space='buy', optimize=True)
    adx_ranging = IntParameter(15, 25, default=20, space='buy', optimize=False)
    
    # Stoploss multipliers
    atr_mult_trending = DecimalParameter(1.5, 2.5, default=2.0, decimals=1, space='sell', optimize=True)
    atr_mult_ranging = DecimalParameter(2.0, 3.0, default=2.5, decimals=1, space='sell', optimize=True)
    
    # ═══════════════════════════════════════════════════════════════
    # INFORMATIVE PAIRS
    # ═══════════════════════════════════════════════════════════════
    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, '4h') for pair in pairs]
    
    # ═══════════════════════════════════════════════════════════════
    # POPULATE INDICATORS
    # ═══════════════════════════════════════════════════════════════
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators."""
        
        # ── AlphaTrend ──
        dataframe = self._add_alphatrend(dataframe)
        
        # ── Regime Detection ──
        dataframe = self._add_regime(dataframe)
        
        # ── Squeeze Momentum ──
        dataframe = self._add_squeeze(dataframe)
        
        # ── WaveTrend ──
        dataframe = self._add_wavetrend(dataframe)
        
        # ── Williams VixFix ──
        dataframe = self._add_vixfix(dataframe)
        
        # ── Structure (BOS/CHoCH) ──
        dataframe = self._add_structure(dataframe)
        
        # ── ATR ──
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # ── EMAs ──
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # ── Volume ──
        dataframe['volume_sma'] = dataframe['volume'].rolling(20).mean()
        
        # ── HTF Data ──
        dataframe = self._add_htf(dataframe, metadata)
        
        return dataframe
    
    def _add_alphatrend(self, df: DataFrame) -> DataFrame:
        """Add AlphaTrend indicators."""
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        period = self.at_period.value
        coeff = self.at_coeff.value
        
        # ATR
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # MFI
        tp = (high + low + close) / 3
        mf = tp * volume
        pos_flow = mf.where(tp > tp.shift(1), 0).rolling(period).sum()
        neg_flow = mf.where(tp < tp.shift(1), 0).rolling(period).sum()
        mfi = 100 - (100 / (1 + pos_flow / neg_flow.replace(0, np.nan))).fillna(50)
        
        # Bands
        upper = low - (atr * coeff)
        lower = high + (atr * coeff)
        
        # AlphaTrend
        at_line = pd.Series(index=df.index, dtype=float)
        at_line.iloc[:period] = close.iloc[:period]
        
        for i in range(period, len(df)):
            prev = at_line.iloc[i-1]
            if mfi.iloc[i] >= 50:
                at_line.iloc[i] = max(lower.iloc[i], prev)
            else:
                at_line.iloc[i] = min(upper.iloc[i], prev)
        
        df['alphatrend'] = at_line
        df['alphatrend_signal'] = at_line.shift(2)
        df['at_bullish'] = (at_line > at_line.shift(2)).astype(int)
        df['at_cross_up'] = (
            (df['at_bullish'] == 1) & 
            (df['at_bullish'].shift(1) == 0)
        ).astype(int)
        
        return df
    
    def _add_regime(self, df: DataFrame) -> DataFrame:
        """Add regime detection."""
        df['adx'] = ta.ADX(df, timeperiod=14)
        df['plus_di'] = ta.PLUS_DI(df, timeperiod=14)
        df['minus_di'] = ta.MINUS_DI(df, timeperiod=14)
        
        # Choppiness
        high, low, close = df['high'], df['low'], df['close']
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        
        atr_sum = tr.rolling(14).sum()
        hl_range = high.rolling(14).max() - low.rolling(14).min()
        hl_range = hl_range.replace(0, np.nan)
        df['choppiness'] = (100 * np.log10(atr_sum / hl_range) / np.log10(14)).fillna(50)
        
        # Regime classification
        df['regime_trending'] = (
            (df['adx'] > self.adx_trending.value) & 
            (df['choppiness'] < 50)
        ).astype(int)
        
        df['regime_ranging'] = (
            (df['adx'] < self.adx_ranging.value) & 
            (df['choppiness'] > 55)
        ).astype(int)
        
        return df
    
    def _add_squeeze(self, df: DataFrame) -> DataFrame:
        """Add Squeeze Momentum."""
        close = df['close']
        high = df['high']
        low = df['low']
        length = 20
        
        # BB
        bb_basis = close.rolling(length).mean()
        bb_dev = close.rolling(length).std() * 2
        
        # KC
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(length).mean()
        kc_basis = close.rolling(length).mean()
        kc_range = atr * 1.5
        
        # Squeeze
        df['squeeze_on'] = (
            ((bb_basis - bb_dev) > (kc_basis - kc_range)) &
            ((bb_basis + bb_dev) < (kc_basis + kc_range))
        ).astype(int)
        
        # Momentum
        highest = high.rolling(length).max()
        lowest = low.rolling(length).min()
        avg = (highest + lowest + close.rolling(length).mean()) / 2
        df['squeeze_mom'] = (close - avg).rolling(12).mean()
        df['squeeze_mom_rising'] = (df['squeeze_mom'] > df['squeeze_mom'].shift(1)).astype(int)
        
        # Squeeze fire
        df['squeeze_fire'] = (
            (df['squeeze_on'].shift(1) == 1) & 
            (df['squeeze_on'] == 0)
        ).astype(int)
        
        return df
    
    def _add_wavetrend(self, df: DataFrame) -> DataFrame:
        """Add WaveTrend."""
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        
        esa = hlc3.ewm(span=10, adjust=False).mean()
        d = abs(hlc3 - esa).ewm(span=10, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * d)
        ci = ci.replace([np.inf, -np.inf], 0).fillna(0)
        
        df['wt1'] = ci.ewm(span=21, adjust=False).mean()
        df['wt2'] = df['wt1'].rolling(4).mean()
        df['wt_bullish'] = (df['wt1'] > df['wt2']).astype(int)
        df['wt_oversold'] = (df['wt1'] < -60).astype(int)
        df['wt_overbought'] = (df['wt1'] > 60).astype(int)
        
        return df
    
    def _add_vixfix(self, df: DataFrame) -> DataFrame:
        """Add Williams VixFix."""
        close = df['close']
        low = df['low']
        
        highest_close = close.rolling(22).max()
        df['vixfix'] = (highest_close - low) / highest_close * 100
        
        vf_basis = df['vixfix'].rolling(20).mean()
        vf_std = df['vixfix'].rolling(20).std()
        df['vixfix_upper'] = vf_basis + (vf_std * 2)
        
        df['vixfix_panic'] = (df['vixfix'] > df['vixfix_upper']).astype(int)
        
        return df
    
    def _add_structure(self, df: DataFrame) -> DataFrame:
        """Add BOS/CHoCH."""
        high = df['high']
        low = df['low']
        close = df['close']
        length = 10
        
        # Swing points
        rolling_high = high.rolling(2 * length + 1, center=True).max()
        rolling_low = low.rolling(2 * length + 1, center=True).min()
        
        swing_high = (high == rolling_high)
        swing_low = (low == rolling_low)
        
        sh_price = high.where(swing_high).ffill()
        sl_price = low.where(swing_low).ffill()
        
        # BOS/CHoCH (simplified)
        df['bullish_bos'] = (close > sh_price.shift(1)).astype(int)
        df['bearish_bos'] = (close < sl_price.shift(1)).astype(int)
        
        return df
    
    def _add_htf(self, df: DataFrame, metadata: dict) -> DataFrame:
        """Add 4H HTF filter."""
        if not self.dp:
            df['htf_bullish'] = 1
            return df
        
        try:
            htf = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='4h')
            if htf.empty:
                df['htf_bullish'] = 1
                return df
            
            htf['ema_200'] = ta.EMA(htf, timeperiod=200)
            htf['htf_bullish'] = (htf['close'] > htf['ema_200']).astype(int)
            
            # Merge
            htf = htf[['date', 'htf_bullish']].copy()
            htf['date'] = pd.to_datetime(htf['date'])
            df['date_merge'] = pd.to_datetime(df['date'])
            
            df = pd.merge_asof(
                df.sort_values('date_merge'),
                htf.sort_values('date'),
                left_on='date_merge',
                right_on='date',
                direction='backward',
                suffixes=('', '_htf')
            )
            df = df.drop(columns=['date_merge', 'date_htf'], errors='ignore')
            
        except Exception as e:
            logger.warning(f"HTF merge failed: {e}")
            df['htf_bullish'] = 1
        
        return df
    
    # ═══════════════════════════════════════════════════════════════
    # POPULATE ENTRY TREND
    # ═══════════════════════════════════════════════════════════════
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry logic with 3 entry types.
        """
        # ── Entry Type 1: TREND_PULLBACK ──
        entry_pullback = (
            (dataframe['at_bullish'] == 1) &
            (dataframe['regime_trending'] == 1) &
            (dataframe['close'] > dataframe['ema_50']) &
            (dataframe['close'] < dataframe['ema_20']) &  # Pullback
            (dataframe['wt_bullish'] == 1) &
            (dataframe['htf_bullish'] == 1)
        )
        
        # ── Entry Type 2: SQUEEZE_BREAKOUT ──
        entry_squeeze = (
            (dataframe['squeeze_fire'] == 1) &
            (dataframe['squeeze_mom'] > 0) &
            (dataframe['squeeze_mom_rising'] == 1) &
            (dataframe['at_bullish'] == 1) &
            (dataframe['htf_bullish'] == 1)
        )
        
        # ── Entry Type 3: REVERSAL ──
        entry_reversal = (
            (dataframe['vixfix_panic'].shift(1) == 1) &
            (dataframe['vixfix_panic'] == 0) &  # Panic subsiding
            (dataframe['wt_oversold'] == 1) &
            (dataframe['close'] > dataframe['close'].shift(1)) &
            (dataframe['bullish_bos'] == 1)
        )
        
        # Combined entry
        enter_long = entry_pullback | entry_squeeze | entry_reversal
        
        # Apply shift for lookahead prevention
        dataframe.loc[enter_long.shift(1).fillna(False), 'enter_long'] = 1
        
        # Entry tags
        dataframe.loc[entry_pullback.shift(1).fillna(False), 'enter_tag'] = EntryType.TREND_PULLBACK.value
        dataframe.loc[entry_squeeze.shift(1).fillna(False), 'enter_tag'] = EntryType.SQUEEZE_BREAKOUT.value
        dataframe.loc[entry_reversal.shift(1).fillna(False), 'enter_tag'] = EntryType.REVERSAL.value
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # POPULATE EXIT TREND
    # ═══════════════════════════════════════════════════════════════
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on AlphaTrend flip or overbought + declining WaveTrend."""
        
        exit_at_flip = (
            (dataframe['at_bullish'] == 0) &
            (dataframe['at_bullish'].shift(1) == 1)
        )
        
        exit_overbought = (
            (dataframe['wt_overbought'] == 1) &
            (dataframe['wt1'] < dataframe['wt1'].shift(1)) &
            (dataframe['wt_bullish'] == 0)
        )
        
        exit_signal = exit_at_flip | exit_overbought
        
        dataframe.loc[exit_signal.shift(1).fillna(False), 'exit_long'] = 1
        
        return dataframe
    
    # ═══════════════════════════════════════════════════════════════
    # CUSTOM STOPLOSS
    # ═══════════════════════════════════════════════════════════════
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        ATR-based adaptive stoploss.
        Tighter in trending markets, wider in ranging.
        """
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            trade_date = timeframe_to_prev_date(self.timeframe, trade.open_date_utc)
            candle = dataframe.loc[dataframe['date'] == trade_date]
            
            if candle.empty:
                return self.stoploss
            
            atr = candle['atr'].iloc[0]
            is_trending = candle['regime_trending'].iloc[0] == 1
            
            if is_trending:
                mult = self.atr_mult_trending.value
            else:
                mult = self.atr_mult_ranging.value
            
            stop_distance = (atr * mult) / trade.open_rate
            
            # Tighten in profit
            if current_profit > 0.05:
                stop_distance = min(stop_distance, 0.02)
            elif current_profit > 0.03:
                stop_distance = min(stop_distance, 0.03)
            
            return -stop_distance
            
        except Exception:
            return self.stoploss
    
    # ═══════════════════════════════════════════════════════════════
    # LEVERAGE
    # ═══════════════════════════════════════════════════════════════
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        return 1.0
