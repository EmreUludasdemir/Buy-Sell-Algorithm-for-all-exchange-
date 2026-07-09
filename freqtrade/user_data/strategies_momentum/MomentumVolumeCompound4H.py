from datetime import datetime
from typing import Optional

import numpy as np
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    DecimalParameter,
    IntParameter,
    IStrategy,
    merge_informative_pair,
)
from pandas import DataFrame


class MomentumVolumeCompound4H(IStrategy):
    """
    Short-horizon momentum strategy for high-volume crypto pairs.

    Market dynamics stack:
    - 1d informative layer defines the regime: price above a long EMA with a
      rising medium EMA and daily RSI above the midline. Entries only fire
      while the daily regime is bullish, so the 4h layer never fights the
      higher timeframe.
    - 4h execution layer looks for momentum ignition: either a fast/slow EMA
      crossover or a Donchian breakout above the recent high, confirmed by a
      volume surge against the rolling volume mean and an ADX trend-strength
      gate. RSI must sit in a momentum band (strong but not exhausted).

    Exit design is intentionally short-term: a tiered ROI ladder takes profit
    within hours-to-days, a trailing stop protects extended moves, and the
    signal exits close the trade on trend flip or RSI overheat.

    Compounding: custom_stake_amount sizes every entry as a fixed fraction of
    the CURRENT total wallet value, so realized profit from closed trades is
    automatically rolled into the next position. On top of that, a win-streak
    boost increases the stake fraction after consecutive winning trades and
    resets to the base size after any loss.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    informative_timeframe = "1d"
    can_short = False

    # Short-term risk layer: ROI keys are minutes (12h / 24h / 48h steps).
    minimal_roi = {"0": 0.06, "720": 0.035, "1440": 0.02, "2880": 0.01}
    stoploss = -0.045
    trailing_stop = True
    trailing_stop_positive = 0.018
    trailing_stop_positive_offset = 0.032
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    process_only_new_candles = True
    startup_candle_count = 210

    plot_config = {
        "main_plot": {
            "ema_fast": {"color": "green"},
            "ema_slow": {"color": "red"},
            "breakout_level": {"color": "orange"},
        },
        "subplots": {
            "Momentum": {
                "rsi": {"color": "purple"},
                "adx": {"color": "black"},
            },
            "Volume": {
                "volume_ratio": {"color": "blue"},
            },
        },
    }

    # 4h execution layer.
    ema_fast_period = IntParameter(8, 25, default=12, space="buy", optimize=True)
    ema_slow_period = IntParameter(26, 80, default=36, space="buy", optimize=True)
    breakout_lookback = IntParameter(10, 40, default=20, space="buy", optimize=True)
    rsi_entry_min = IntParameter(45, 60, default=50, space="buy", optimize=True)
    rsi_entry_max = IntParameter(65, 85, default=78, space="buy", optimize=True)
    rsi_overheat = IntParameter(75, 95, default=84, space="sell", optimize=True)
    adx_min = IntParameter(15, 35, default=20, space="buy", optimize=True)
    volume_mean_window = IntParameter(20, 60, default=30, space="buy", optimize=True)
    volume_surge_mult = DecimalParameter(
        1.0, 3.0, default=1.5, decimals=1, space="buy", optimize=True
    )

    # 1d regime layer.
    daily_ema_slow = IntParameter(100, 250, default=200, space="buy", optimize=True)
    daily_ema_fast = IntParameter(30, 90, default=50, space="buy", optimize=True)
    daily_rsi_min = IntParameter(45, 60, default=50, space="buy", optimize=True)

    # Compounding layer: fraction of the current total wallet used per entry,
    # plus a bounded boost that grows with consecutive winning trades.
    compound_stake_fraction = DecimalParameter(
        0.10, 0.50, default=0.25, decimals=2, space="buy", optimize=False
    )
    win_streak_boost = DecimalParameter(
        0.0, 0.50, default=0.15, decimals=2, space="buy", optimize=False
    )
    max_win_streak_boosts = IntParameter(1, 5, default=3, space="buy", optimize=False)

    def informative_pairs(self):
        if self.dp is None:
            return []
        pairs = self.dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # --- 1d regime layer ---
        informative = self.dp.get_pair_dataframe(
            pair=metadata["pair"], timeframe=self.informative_timeframe
        )
        informative["ema_slow_d"] = ta.EMA(informative, timeperiod=int(self.daily_ema_slow.value))
        informative["ema_fast_d"] = ta.EMA(informative, timeperiod=int(self.daily_ema_fast.value))
        informative["rsi_d"] = ta.RSI(informative, timeperiod=14)
        informative["bull_regime"] = (
            (informative["close"] > informative["ema_slow_d"])
            & (informative["ema_fast_d"] > informative["ema_slow_d"])
            & (informative["rsi_d"] > int(self.daily_rsi_min.value))
        ).astype(int)

        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True
        )

        # --- 4h execution layer ---
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=int(self.ema_fast_period.value))
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=int(self.ema_slow_period.value))
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        lookback = int(self.breakout_lookback.value)
        dataframe["breakout_level"] = dataframe["high"].rolling(lookback).max().shift(1)

        vol_window = int(self.volume_mean_window.value)
        volume_mean = dataframe["volume"].rolling(vol_window, min_periods=1).mean()
        dataframe["volume_ratio"] = (
            (dataframe["volume"] / volume_mean.replace(0, np.nan))
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )

        dataframe["ema_cross_up"] = (
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
        ).astype(int)
        dataframe["ema_cross_down"] = (
            (dataframe["ema_fast"] < dataframe["ema_slow"])
            & (dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1))
        ).astype(int)
        dataframe["breakout"] = (dataframe["close"] > dataframe["breakout_level"]).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        regime_col = f"bull_regime_{self.informative_timeframe}"
        common = (
            (dataframe[regime_col] == 1)
            & (dataframe["rsi"] > int(self.rsi_entry_min.value))
            & (dataframe["rsi"] < int(self.rsi_entry_max.value))
            & (dataframe["adx"] > int(self.adx_min.value))
            & (dataframe["volume_ratio"] > float(self.volume_surge_mult.value))
            & (dataframe["volume"] > 0)
        )

        cross_entry = common & (dataframe["ema_cross_up"] == 1)
        breakout_entry = (
            common
            & (dataframe["breakout"] == 1)
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
        )

        dataframe.loc[breakout_entry, "enter_long"] = 1
        dataframe.loc[breakout_entry, "enter_tag"] = "MOM_BREAKOUT"
        dataframe.loc[cross_entry, "enter_long"] = 1
        dataframe.loc[cross_entry, "enter_tag"] = "MOM_EMA_CROSS"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        trend_flip = (dataframe["ema_cross_down"] == 1) & (dataframe["volume"] > 0)
        overheat = dataframe["rsi"] > int(self.rsi_overheat.value)

        dataframe.loc[trend_flip, "exit_long"] = 1
        dataframe.loc[trend_flip, "exit_tag"] = "MOM_TREND_FLIP"
        dataframe.loc[overheat, "exit_long"] = 1
        dataframe.loc[overheat, "exit_tag"] = "MOM_OVERHEAT"
        return dataframe

    def _current_win_streak(self) -> int:
        """Consecutive profitable closed trades, newest first; any loss resets."""
        try:
            closed_trades = Trade.get_trades_proxy(is_open=False)
        except Exception:
            return 0
        closed_trades = [trade for trade in closed_trades if trade.close_date is not None]
        closed_trades.sort(key=lambda trade: trade.close_date, reverse=True)

        streak = 0
        for trade in closed_trades:
            profit = trade.close_profit if trade.close_profit is not None else 0.0
            if profit > 0:
                streak += 1
            else:
                break
        return streak

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        stake = proposed_stake

        # Base compounding: size from the CURRENT total wallet, so realized
        # profit automatically increases the next position.
        if self.wallets is not None:
            total_wallet = self.wallets.get_total_stake_amount()
            if total_wallet > 0:
                stake = total_wallet * float(self.compound_stake_fraction.value)

        # Win-streak boost: after consecutive winners, push more of the gains
        # into the next entry; the first loss drops back to the base fraction.
        streak = min(self._current_win_streak(), int(self.max_win_streak_boosts.value))
        stake *= 1.0 + float(self.win_streak_boost.value) * streak

        if max_stake is not None:
            stake = min(stake, max_stake)
        if min_stake is not None:
            stake = max(stake, min_stake)
        return stake
