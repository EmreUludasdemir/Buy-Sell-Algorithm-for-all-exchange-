import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter


BASE_STRATEGY_DIR = Path(__file__).resolve().parents[1] / "strategies"
if str(BASE_STRATEGY_DIR) not in sys.path:
    sys.path.append(str(BASE_STRATEGY_DIR))

from KivancSupertrendedMovingAverages1D import KivancSupertrendedMovingAverages1D


class KivancSupertrendedMovingAveragesFutures1D(KivancSupertrendedMovingAverages1D):
    """
    Futures research variant of the production Kivanc STMA strategy.

    This class reuses the daily logic and enables short execution for
    Binance USDT-margined futures backtests. It is not the production bot.
    """

    can_short = True

    # Research-only filters inspired by time-series momentum literature and
    # crypto trend-following papers that bias capital toward the long side.
    use_tsmom_filter = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    tsmom_lookback = IntParameter(90, 365, default=252, space="buy", optimize=True)
    tsmom_threshold = DecimalParameter(0.0, 0.50, default=0.0, decimals=3, space="buy", optimize=True)
    use_rolling_sharpe_filter = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    rolling_sharpe_window = IntParameter(30, 180, default=90, space="buy", optimize=True)
    rolling_sharpe_threshold = DecimalParameter(-0.50, 1.50, default=0.0, decimals=2, space="buy", optimize=True)
    long_stake_multiplier = DecimalParameter(0.50, 1.70, default=1.0, decimals=2, space="buy", optimize=True)
    short_stake_multiplier = DecimalParameter(0.30, 1.30, default=1.0, decimals=2, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)

        tsmom_lookback = int(self.tsmom_lookback.value)
        sharpe_window = int(self.rolling_sharpe_window.value)

        daily_return = dataframe["close"].pct_change()
        rolling_mean = daily_return.rolling(window=sharpe_window, min_periods=sharpe_window).mean()
        rolling_std = daily_return.rolling(window=sharpe_window, min_periods=sharpe_window).std()
        rolling_sharpe = math.sqrt(365.0) * (rolling_mean / rolling_std.replace(0, np.nan))

        dataframe["tsmom_return"] = dataframe["close"].pct_change(tsmom_lookback).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        dataframe["rolling_sharpe"] = rolling_sharpe.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)

        long_condition = (dataframe.get("enter_long", 0) == 1) & (dataframe["volume"] > 0)
        short_condition = (dataframe.get("enter_short", 0) == 1) & (dataframe["volume"] > 0)

        if bool(self.use_tsmom_filter.value):
            threshold = float(self.tsmom_threshold.value)
            long_condition &= dataframe["tsmom_return"] > threshold
            short_condition &= dataframe["tsmom_return"] < -threshold

        if bool(self.use_rolling_sharpe_filter.value):
            sharpe_threshold = float(self.rolling_sharpe_threshold.value)
            long_condition &= dataframe["rolling_sharpe"] > sharpe_threshold
            short_condition &= dataframe["rolling_sharpe"] < -sharpe_threshold

        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = pd.NA

        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[long_condition, "enter_tag"] = "ST_MA_LONG_RESEARCH"
        dataframe.loc[short_condition, "enter_short"] = 1
        dataframe.loc[short_condition, "enter_tag"] = "ST_MA_SHORT_RESEARCH"
        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time,
        current_rate: float,
        proposed_stake: float,
        min_stake,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        multiplier = float(self.long_stake_multiplier.value if side == "long" else self.short_stake_multiplier.value)
        desired_stake = proposed_stake * multiplier
        if max_stake is not None:
            desired_stake = min(desired_stake, max_stake)
        if min_stake is not None:
            desired_stake = max(desired_stake, min_stake)
        return desired_stake
