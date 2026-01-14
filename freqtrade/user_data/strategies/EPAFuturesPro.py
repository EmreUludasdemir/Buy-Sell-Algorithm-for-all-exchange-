"""
EPA Futures Pro - Ultimate Crypto Futures Strategy
====================================================
Research-based crypto futures strategy for Freqtrade.

Combines:
- Triple SuperTrend (Multi-timeframe confirmation)
- ADX Filter (Trend strength > 25)
- RSI Momentum (Overbought/Oversold + 50 crossover)
- EMA 200 Trend Filter (Major trend direction)
- MACD Momentum (Trend confirmation)
- ATR Dynamic SL/TP (1.5x SL, 3x TP)
- Volume Spike Detection

Research Sources:
- QuantifiedStrategies.com (RSI 91% win rate)
- FMZQuant (EMA-MACD-SuperTrend-ADX-ATR strategy)
- GoodCrypto.app (SuperTrend best settings)
- Mudrex Learn (SuperTrend profitable strategies)

Author: Emre Uludaşdemir
Role: Financial Markets Researcher & Algorithm Designer
Version: 1.0.0
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, BooleanParameter
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


def supertrend(df: DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple:
    """
    Calculate SuperTrend indicator.
    Returns: (supertrend_line, direction)
    Direction: -1 = Bullish, 1 = Bearish
    """
    hl2 = (df['high'] + df['low']) / 2
    atr = ta.ATR(df['high'], df['low'], df['close'], timeperiod=period)

    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=float)

    supertrend.iloc[0] = upperband.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(df)):
        if df['close'].iloc[i] > upperband.iloc[i-1]:
            direction.iloc[i] = -1
        elif df['close'].iloc[i] < lowerband.iloc[i-1]:
            direction.iloc[i] = 1
        else:
            direction.iloc[i] = direction.iloc[i-1]

            if direction.iloc[i] == -1 and lowerband.iloc[i] < lowerband.iloc[i-1]:
                lowerband.iloc[i] = lowerband.iloc[i-1]
            if direction.iloc[i] == 1 and upperband.iloc[i] > upperband.iloc[i-1]:
                upperband.iloc[i] = upperband.iloc[i-1]

        if direction.iloc[i] == -1:
            supertrend.iloc[i] = lowerband.iloc[i]
        else:
            supertrend.iloc[i] = upperband.iloc[i]

    return supertrend, direction


class EPAFuturesPro(IStrategy):
    """
    EPA Futures Pro - Ultimate Crypto Futures Strategy

    Entry Logic:
    1. Triple SuperTrend confirmation (2/3 must agree)
    2. ADX > 25 (strong trend)
    3. RSI momentum confirmation
    4. EMA 200 trend filter
    5. MACD momentum confirmation
    6. Volume spike detection

    Exit Logic:
    1. SuperTrend reversal
    2. ATR-based trailing stop
    3. Fixed stop loss / take profit

    Optimized for: BTC/USDT, ETH/USDT Futures (1H timeframe)
    """

    # Strategy version
    INTERFACE_VERSION = 3

    # Timeframe
    timeframe = '1h'

    # Enable shorting for futures
    can_short = True

    # ROI table - futures style
    minimal_roi = {
        "0": 0.10,      # 10% initial
        "60": 0.06,     # 6% after 1h
        "120": 0.04,    # 4% after 2h
        "240": 0.02,    # 2% after 4h
        "480": 0.01,    # 1% after 8h
    }

    # Stop loss
    stoploss = -0.05  # 5% base stop loss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # Use custom stoploss
    use_custom_stoploss = True

    # Process only new candles
    process_only_new_candles = True

    # Use exit signals
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Position stacking
    position_adjustment_enable = False
    max_entry_position_adjustment = 2

    # Startup candles
    startup_candle_count = 250

    # ═══════════════════════════════════════════════════════════════════════
    # HYPEROPT PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════

    # Triple SuperTrend
    st1_period = IntParameter(8, 15, default=10, space='buy', optimize=True)
    st1_mult = DecimalParameter(1.0, 2.5, default=1.5, decimals=1, space='buy', optimize=True)
    st2_period = IntParameter(9, 15, default=11, space='buy', optimize=True)
    st2_mult = DecimalParameter(1.5, 3.0, default=2.0, decimals=1, space='buy', optimize=True)
    st3_period = IntParameter(10, 18, default=12, space='buy', optimize=True)
    st3_mult = DecimalParameter(2.0, 4.0, default=3.0, decimals=1, space='buy', optimize=True)
    st_confirm_required = IntParameter(1, 3, default=2, space='buy', optimize=True)

    # ADX
    use_adx = BooleanParameter(default=True, space='buy', optimize=True)
    adx_threshold = IntParameter(15, 35, default=25, space='buy', optimize=True)

    # RSI
    use_rsi = BooleanParameter(default=True, space='buy', optimize=True)
    rsi_period = IntParameter(10, 21, default=14, space='buy', optimize=True)
    rsi_ob = IntParameter(65, 85, default=70, space='buy', optimize=True)
    rsi_os = IntParameter(15, 35, default=30, space='buy', optimize=True)

    # EMA
    use_ema200 = BooleanParameter(default=True, space='buy', optimize=True)
    ema_fast = IntParameter(5, 15, default=9, space='buy', optimize=True)
    ema_slow = IntParameter(15, 30, default=21, space='buy', optimize=True)

    # MACD
    use_macd = BooleanParameter(default=True, space='buy', optimize=True)

    # Volume
    use_volume = BooleanParameter(default=True, space='buy', optimize=True)
    volume_mult = DecimalParameter(1.0, 2.0, default=1.2, decimals=1, space='buy', optimize=True)

    # Risk Management
    atr_sl_mult = DecimalParameter(1.0, 3.0, default=1.5, decimals=1, space='sell', optimize=True)
    atr_tp_mult = DecimalParameter(2.0, 5.0, default=3.0, decimals=1, space='sell', optimize=True)

    # Min score required
    min_score = IntParameter(3, 5, default=4, space='buy', optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators."""

        # ═══ TRIPLE SUPERTREND ═══
        st1, st1_dir = supertrend(dataframe, self.st1_period.value, self.st1_mult.value)
        st2, st2_dir = supertrend(dataframe, self.st2_period.value, self.st2_mult.value)
        st3, st3_dir = supertrend(dataframe, self.st3_period.value, self.st3_mult.value)

        dataframe['st1'] = st1
        dataframe['st1_dir'] = st1_dir
        dataframe['st2'] = st2
        dataframe['st2_dir'] = st2_dir
        dataframe['st3'] = st3
        dataframe['st3_dir'] = st3_dir

        # SuperTrend bullish/bearish counts
        dataframe['st_bull_count'] = (
            (dataframe['st1_dir'] == -1).astype(int) +
            (dataframe['st2_dir'] == -1).astype(int) +
            (dataframe['st3_dir'] == -1).astype(int)
        )
        dataframe['st_bear_count'] = (
            (dataframe['st1_dir'] == 1).astype(int) +
            (dataframe['st2_dir'] == 1).astype(int) +
            (dataframe['st3_dir'] == 1).astype(int)
        )

        # SuperTrend signals
        dataframe['st_bullish'] = dataframe['st_bull_count'] >= self.st_confirm_required.value
        dataframe['st_bearish'] = dataframe['st_bear_count'] >= self.st_confirm_required.value

        # SuperTrend flip
        dataframe['st_flip_up'] = (
            (dataframe['st_bull_count'] >= self.st_confirm_required.value) &
            (dataframe['st_bull_count'].shift(1) < self.st_confirm_required.value)
        )
        dataframe['st_flip_down'] = (
            (dataframe['st_bear_count'] >= self.st_confirm_required.value) &
            (dataframe['st_bear_count'].shift(1) < self.st_confirm_required.value)
        )

        # ═══ ADX/DMI ═══
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        dataframe['strong_trend'] = dataframe['adx'] > self.adx_threshold.value
        dataframe['di_bullish'] = dataframe['plus_di'] > dataframe['minus_di']
        dataframe['di_bearish'] = dataframe['minus_di'] > dataframe['plus_di']

        # ═══ RSI ═══
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        dataframe['rsi_bullish'] = (dataframe['rsi'] > 50) & (dataframe['rsi'] < self.rsi_ob.value)
        dataframe['rsi_bearish'] = (dataframe['rsi'] < 50) & (dataframe['rsi'] > self.rsi_os.value)

        # ═══ EMA ═══
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)

        dataframe['ema_bullish'] = dataframe['ema_fast'] > dataframe['ema_slow']
        dataframe['ema_bearish'] = dataframe['ema_fast'] < dataframe['ema_slow']
        dataframe['above_ema200'] = dataframe['close'] > dataframe['ema_200']
        dataframe['below_ema200'] = dataframe['close'] < dataframe['ema_200']

        # EMA crossovers
        dataframe['ema_cross_up'] = (
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
        )
        dataframe['ema_cross_down'] = (
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
        )

        # ═══ MACD ═══
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']

        dataframe['macd_bullish'] = (dataframe['macd'] > dataframe['macd_signal']) & (dataframe['macd_hist'] > 0)
        dataframe['macd_bearish'] = (dataframe['macd'] < dataframe['macd_signal']) & (dataframe['macd_hist'] < 0)

        # MACD crossovers
        dataframe['macd_cross_up'] = (
            (dataframe['macd'] > dataframe['macd_signal']) &
            (dataframe['macd'].shift(1) <= dataframe['macd_signal'].shift(1))
        )
        dataframe['macd_cross_down'] = (
            (dataframe['macd'] < dataframe['macd_signal']) &
            (dataframe['macd'].shift(1) >= dataframe['macd_signal'].shift(1))
        )

        # ═══ VOLUME ═══
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_spike'] = dataframe['volume'] > (dataframe['volume_sma'] * self.volume_mult.value)

        # ═══ ATR ═══
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)

        # ═══ SCORING SYSTEM ═══
        # Bull Score (0-6)
        dataframe['bull_score'] = (
            dataframe['st_bullish'].astype(int) +
            ((dataframe['strong_trend'] & dataframe['di_bullish']) | ~self.use_adx.value).astype(int) +
            (dataframe['rsi_bullish'] | ~self.use_rsi.value).astype(int) +
            (dataframe['above_ema200'] | ~self.use_ema200.value).astype(int) +
            (dataframe['macd_bullish'] | ~self.use_macd.value).astype(int) +
            dataframe['ema_bullish'].astype(int)
        )

        # Bear Score (0-6)
        dataframe['bear_score'] = (
            dataframe['st_bearish'].astype(int) +
            ((dataframe['strong_trend'] & dataframe['di_bearish']) | ~self.use_adx.value).astype(int) +
            (dataframe['rsi_bearish'] | ~self.use_rsi.value).astype(int) +
            (dataframe['below_ema200'] | ~self.use_ema200.value).astype(int) +
            (dataframe['macd_bearish'] | ~self.use_macd.value).astype(int) +
            dataframe['ema_bearish'].astype(int)
        )

        # ═══ ENTRY TRIGGERS ═══
        # Long triggers
        dataframe['trigger_long_st'] = dataframe['st_flip_up']
        dataframe['trigger_long_ema'] = dataframe['ema_cross_up'] & dataframe['st_bullish']
        dataframe['trigger_long_macd'] = dataframe['macd_cross_up'] & dataframe['st_bullish'] & self.use_macd.value

        dataframe['any_trigger_long'] = (
            dataframe['trigger_long_st'] |
            dataframe['trigger_long_ema'] |
            dataframe['trigger_long_macd']
        )

        # Short triggers
        dataframe['trigger_short_st'] = dataframe['st_flip_down']
        dataframe['trigger_short_ema'] = dataframe['ema_cross_down'] & dataframe['st_bearish']
        dataframe['trigger_short_macd'] = dataframe['macd_cross_down'] & dataframe['st_bearish'] & self.use_macd.value

        dataframe['any_trigger_short'] = (
            dataframe['trigger_short_st'] |
            dataframe['trigger_short_ema'] |
            dataframe['trigger_short_macd']
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define entry conditions."""

        # ═══ LONG CONDITIONS ═══
        conditions_long = (
            dataframe['any_trigger_long'] &
            (dataframe['bull_score'] >= self.min_score.value) &
            (dataframe['strong_trend'] | ~self.use_adx.value) &
            (dataframe['rsi'] < self.rsi_ob.value) &
            (dataframe['above_ema200'] | ~self.use_ema200.value) &
            (dataframe['volume_spike'] | ~self.use_volume.value) &
            (dataframe['volume'] > 0)
        )

        dataframe.loc[conditions_long, 'enter_long'] = 1
        dataframe.loc[conditions_long, 'enter_tag'] = 'EPA_FUT_LONG'

        # ═══ SHORT CONDITIONS ═══
        conditions_short = (
            dataframe['any_trigger_short'] &
            (dataframe['bear_score'] >= self.min_score.value) &
            (dataframe['strong_trend'] | ~self.use_adx.value) &
            (dataframe['rsi'] > self.rsi_os.value) &
            (dataframe['below_ema200'] | ~self.use_ema200.value) &
            (dataframe['volume_spike'] | ~self.use_volume.value) &
            (dataframe['volume'] > 0)
        )

        dataframe.loc[conditions_short, 'enter_short'] = 1
        dataframe.loc[conditions_short, 'enter_tag'] = 'EPA_FUT_SHORT'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define exit conditions."""

        # ═══ EXIT LONG ═══
        exit_long = (
            dataframe['st_flip_down'] |  # SuperTrend reversal
            dataframe['ema_cross_down']  # EMA cross reversal
        )

        dataframe.loc[exit_long, 'exit_long'] = 1
        dataframe.loc[exit_long, 'exit_tag'] = 'ST_REVERSAL'

        # ═══ EXIT SHORT ═══
        exit_short = (
            dataframe['st_flip_up'] |  # SuperTrend reversal
            dataframe['ema_cross_up']  # EMA cross reversal
        )

        dataframe.loc[exit_short, 'exit_short'] = 1
        dataframe.loc[exit_short, 'exit_tag'] = 'ST_REVERSAL'

        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        ATR-based dynamic stop loss.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if dataframe.empty:
            return None

        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']

        if atr is None or pd.isna(atr):
            return None

        # Calculate ATR-based stop loss
        if trade.is_short:
            stop_price = trade.open_rate + (atr * self.atr_sl_mult.value)
            stop_loss = (stop_price / current_rate) - 1
        else:
            stop_price = trade.open_rate - (atr * self.atr_sl_mult.value)
            stop_loss = 1 - (stop_price / current_rate)

        # Ensure stop loss is negative (loss)
        return -abs(stop_loss)

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        Define leverage for futures trading.
        Conservative leverage based on ATR volatility.
        """
        # Conservative fixed leverage
        return 3.0

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    **kwargs) -> Optional[str]:
        """
        Custom exit logic for take profit based on ATR.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if dataframe.empty:
            return None

        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']

        if atr is None or pd.isna(atr):
            return None

        # Calculate ATR-based take profit
        if trade.is_short:
            tp_price = trade.open_rate - (atr * self.atr_tp_mult.value)
            if current_rate <= tp_price:
                return 'ATR_TP'
        else:
            tp_price = trade.open_rate + (atr * self.atr_tp_mult.value)
            if current_rate >= tp_price:
                return 'ATR_TP'

        return None
