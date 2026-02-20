from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy, merge_informative_pair

from kivanc_indicators import supertrend

if TYPE_CHECKING:
    from freqtrade.persistence import Trade


class MACDVSupertrendStrategy(IStrategy):
    """
    LEAN-inspired version of MACDV + Supertrend strategy.

    Improvements ported from LEAN-style practices:
    - Market regime filter (BTC 1d EMA200)
    - Volatility-targeted position sizing (ATR ratio)
    - Time-based exit to reduce capital lock
    - Profit-locking dynamic stoploss tiers
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = False

    informative_pair = "BTC/USDT"
    informative_tf = "1d"

    minimal_roi = {
        "0": 0.10,
        "48": 0.06,
        "96": 0.04,
        "192": 0.02,
    }

    stoploss = -0.06

    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    use_custom_stoploss = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    process_only_new_candles = True
    startup_candle_count = 250

    fast_ema = IntParameter(10, 14, default=12, space="buy", optimize=True)
    slow_ema = IntParameter(24, 30, default=26, space="buy", optimize=True)
    signal_ema = IntParameter(7, 12, default=9, space="buy", optimize=True)
    atr_period = IntParameter(20, 30, default=26, space="buy", optimize=True)

    overbought_level = IntParameter(120, 180, default=150, space="buy", optimize=True)
    oversold_level = IntParameter(-180, -120, default=-150, space="buy", optimize=True)
    neutral_upper = IntParameter(30, 70, default=50, space="buy", optimize=True)

    supertrend_period = IntParameter(8, 14, default=10, space="buy", optimize=True)
    supertrend_mult = DecimalParameter(2.5, 3.5, default=3.0, decimals=1, space="buy", optimize=True)

    ema_trend_period = IntParameter(180, 220, default=200, space="buy", optimize=True)
    volume_threshold = DecimalParameter(0.6, 1.0, default=0.8, decimals=1, space="buy", optimize=True)

    # LEAN-style risk constants
    target_atr_ratio = 0.03
    min_position_scale = 0.40
    max_position_scale = 1.25
    time_stop_hours = 120
    time_stop_min_profit = 0.01

    def informative_pairs(self):
        return [(self.informative_pair, self.informative_tf)]

    def _apply_market_regime_filter(self, dataframe: DataFrame) -> DataFrame:
        """Use BTC 1d EMA200 as market regime filter."""
        dataframe["market_regime_ok"] = True

        if not self.dp:
            return dataframe

        try:
            informative = self.dp.get_pair_dataframe(pair=self.informative_pair, timeframe=self.informative_tf)
        except Exception:
            return dataframe

        if informative is None or informative.empty:
            return dataframe

        informative = informative.copy()
        informative["ema200"] = ta.EMA(informative, timeperiod=200)

        dataframe = merge_informative_pair(
            dataframe,
            informative,
            self.timeframe,
            self.informative_tf,
            ffill=True,
        )

        close_col = f"close_{self.informative_tf}"
        ema_col = f"ema200_{self.informative_tf}"
        if close_col in dataframe.columns and ema_col in dataframe.columns:
            dataframe["market_regime_ok"] = np.where(
                dataframe[ema_col].isna(),
                True,
                dataframe[close_col] > dataframe[ema_col],
            )

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_period.value)

        atr_safe = dataframe["atr"].replace(0, np.nan).ffill()
        dataframe["macdv"] = ((dataframe["ema_fast"] - dataframe["ema_slow"]) / atr_safe) * 100
        dataframe["macdv_signal"] = ta.EMA(dataframe["macdv"], timeperiod=self.signal_ema.value)
        dataframe["macdv_hist"] = dataframe["macdv"] - dataframe["macdv_signal"]

        dataframe["macdv_cross_up"] = (
            (dataframe["macdv"] > dataframe["macdv_signal"])
            & (dataframe["macdv"].shift(1) <= dataframe["macdv_signal"].shift(1))
        )
        dataframe["macdv_cross_down"] = (
            (dataframe["macdv"] < dataframe["macdv_signal"])
            & (dataframe["macdv"].shift(1) >= dataframe["macdv_signal"].shift(1))
        )

        dataframe["is_rebounding"] = (
            (dataframe["macdv"] > self.oversold_level.value)
            & (dataframe["macdv"] < self.neutral_upper.value)
            & (dataframe["macdv"] > dataframe["macdv_signal"])
        )
        dataframe["is_rallying"] = (
            (dataframe["macdv"] >= self.neutral_upper.value)
            & (dataframe["macdv"] < self.overbought_level.value)
            & (dataframe["macdv"] > dataframe["macdv_signal"])
        )
        dataframe["is_overbought"] = dataframe["macdv"] >= self.overbought_level.value
        dataframe["macdv_entry_zone"] = dataframe["is_rebounding"] | dataframe["is_rallying"]

        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period.value,
            multiplier=self.supertrend_mult.value,
        )
        dataframe["supertrend_dir"] = st_direction
        dataframe["supertrend_line"] = st_line
        dataframe["supertrend_flip_down"] = (
            (dataframe["supertrend_dir"] == -1)
            & (dataframe["supertrend_dir"].shift(1) == 1)
        )

        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.ema_trend_period.value)
        dataframe["above_ema_trend"] = dataframe["close"] > dataframe["ema_trend"]
        dataframe["below_ema_trend"] = dataframe["close"] < dataframe["ema_trend"]

        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["volume_ok"] = dataframe["volume"] > (
            dataframe["volume_sma"] * self.volume_threshold.value
        )

        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        dataframe = self._apply_market_regime_filter(dataframe)

        dataframe["atr_ratio"] = (dataframe["atr"] / dataframe["close"]).replace(
            [np.inf, -np.inf], np.nan
        )
        dataframe["atr_ratio"] = dataframe["atr_ratio"].fillna(self.target_atr_ratio).clip(
            lower=0.003, upper=0.20
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        long_conditions = (
            dataframe["macdv_cross_up"]
            & dataframe["macdv_entry_zone"]
            & (dataframe["supertrend_dir"] == 1)
            & dataframe["above_ema_trend"]
            & dataframe["volume_ok"]
            & dataframe["market_regime_ok"]
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[long_conditions, "enter_long"] = 1
        dataframe.loc[long_conditions, "enter_tag"] = "MACDV_ST_LONG"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_long_conditions = (
            dataframe["is_overbought"]
            | dataframe["supertrend_flip_down"]
            | (
                dataframe["macdv_cross_down"]
                & dataframe["below_ema_trend"]
                & (dataframe["macdv"] < 0)
            )
            | (~dataframe["market_regime_ok"])
        )

        dataframe.loc[exit_long_conditions, "exit_long"] = 1
        dataframe.loc[exit_long_conditions, "exit_tag"] = "MACDV_ST_EXIT_LONG"

        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        """Volatility targeting similar to LEAN Risk Management models."""
        stake = proposed_stake if proposed_stake and proposed_stake > 0 else max_stake
        if not stake or stake <= 0:
            return proposed_stake

        if not self.dp:
            return stake

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return stake

        atr_ratio = float(dataframe.iloc[-1].get("atr_ratio", self.target_atr_ratio))
        if atr_ratio <= 0:
            return stake

        scale = self.target_atr_ratio / atr_ratio
        scale = float(np.clip(scale, self.min_position_scale, self.max_position_scale))
        sized_stake = stake * scale

        if min_stake is not None:
            sized_stake = max(sized_stake, min_stake)
        if max_stake is not None and max_stake > 0:
            sized_stake = min(sized_stake, max_stake)

        return float(sized_stake)

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float:
        """Profit-lock tiers inspired by LEAN risk controls."""
        if current_profit >= 0.12:
            return -0.015
        if current_profit >= 0.08:
            return -0.025
        if current_profit >= 0.04:
            return -0.04

        if self.dp:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty:
                if not bool(dataframe.iloc[-1].get("market_regime_ok", True)) and current_profit > 0:
                    return -0.03

        return self.stoploss

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        """Time-based exit to prevent dead capital."""
        open_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0

        if open_hours >= self.time_stop_hours and current_profit < self.time_stop_min_profit:
            return "lean_time_stop"

        if open_hours >= (self.time_stop_hours * 1.5) and current_profit < 0:
            return "lean_hard_time_stop"

        return None

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return False

        last_candle = dataframe.iloc[-1]

        # Global regime gate
        if not bool(last_candle.get("market_regime_ok", True)):
            return False

        if float(last_candle.get("adx", 0)) >= 20:
            return True

        if bool(last_candle.get("is_rallying", False)):
            return True

        if bool(last_candle.get("is_rebounding", False)) and float(last_candle.get("macdv", 0)) > -50:
            return True

        return False
