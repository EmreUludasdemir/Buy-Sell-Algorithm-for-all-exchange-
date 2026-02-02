"""
Strategy 4: Triple Confluence Strategy
=======================================
Combines SuperTrend + RSI + MACD for high-probability trades.

Rules:
- Buy when: SuperTrend bullish + RSI > 50 (momentum) + MACD cross up
- Sell when: Any 2 of 3 indicators turn bearish
- Requires all 3 confirmations for entry (high confluence)

Source: Multiple quant research studies
"""

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy


def supertrend(df: DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple:
    """Calculate SuperTrend indicator."""
    hl2 = (df["high"] + df["low"]) / 2
    atr = ta.ATR(df["high"], df["low"], df["close"], timeperiod=period)

    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    supertrend_line = [0.0] * len(df)
    direction = [1] * len(df)

    for i in range(1, len(df)):
        if df["close"].iloc[i] > upperband.iloc[i - 1]:
            direction[i] = -1
        elif df["close"].iloc[i] < lowerband.iloc[i - 1]:
            direction[i] = 1
        else:
            direction[i] = direction[i - 1]

            if direction[i] == -1 and lowerband.iloc[i] < lowerband.iloc[i - 1]:
                lowerband.iloc[i] = lowerband.iloc[i - 1]
            if direction[i] == 1 and upperband.iloc[i] > upperband.iloc[i - 1]:
                upperband.iloc[i] = upperband.iloc[i - 1]

        if direction[i] == -1:
            supertrend_line[i] = lowerband.iloc[i]
        else:
            supertrend_line[i] = upperband.iloc[i]

    return supertrend_line, direction


class TripleConfluence(IStrategy):
    """
    Triple Confluence Strategy
    - Requires SuperTrend + RSI + MACD agreement
    - Best for: 4H/Daily trending markets
    - High win rate due to multiple confirmations
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    minimal_roi = {
        "0": 0.15,
        "48": 0.10,
        "96": 0.06,
        "192": 0.03,
    }

    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    # SuperTrend parameters
    st_period = IntParameter(8, 14, default=10, space="buy")
    st_multiplier = DecimalParameter(2.0, 4.0, default=3.0, decimals=1, space="buy")

    # RSI parameters
    rsi_period = IntParameter(10, 20, default=14, space="buy")
    rsi_bull_threshold = IntParameter(45, 55, default=50, space="buy")
    rsi_bear_threshold = IntParameter(45, 55, default=50, space="buy")

    # MACD parameters
    macd_fast = IntParameter(8, 15, default=12, space="buy")
    macd_slow = IntParameter(20, 30, default=26, space="buy")
    macd_signal = IntParameter(7, 12, default=9, space="buy")

    # Volume filter
    volume_mult = DecimalParameter(1.0, 2.0, default=1.2, decimals=1, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # SuperTrend
        st_line, st_dir = supertrend(dataframe, self.st_period.value, self.st_multiplier.value)
        dataframe["supertrend"] = st_line
        dataframe["st_direction"] = st_dir
        dataframe["st_bullish"] = dataframe["st_direction"] == -1
        dataframe["st_bearish"] = dataframe["st_direction"] == 1

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        dataframe["rsi_bullish"] = dataframe["rsi"] > self.rsi_bull_threshold.value
        dataframe["rsi_bearish"] = dataframe["rsi"] < self.rsi_bear_threshold.value

        # MACD
        macd = ta.MACD(
            dataframe,
            fastperiod=self.macd_fast.value,
            slowperiod=self.macd_slow.value,
            signalperiod=self.macd_signal.value,
        )
        dataframe["macd"] = macd["macd"]
        dataframe["macd_signal"] = macd["macdsignal"]
        dataframe["macd_hist"] = macd["macdhist"]

        # MACD cross signals
        dataframe["macd_bullish"] = (dataframe["macd"] > dataframe["macd_signal"]) & (dataframe["macd_hist"] > 0)
        dataframe["macd_bearish"] = (dataframe["macd"] < dataframe["macd_signal"]) & (dataframe["macd_hist"] < 0)

        # MACD cross events
        dataframe["macd_cross_up"] = (dataframe["macd"] > dataframe["macd_signal"]) & (
            dataframe["macd"].shift(1) <= dataframe["macd_signal"].shift(1)
        )
        dataframe["macd_cross_down"] = (dataframe["macd"] < dataframe["macd_signal"]) & (
            dataframe["macd"].shift(1) >= dataframe["macd_signal"].shift(1)
        )

        # Volume
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["volume_ok"] = dataframe["volume"] > (dataframe["volume_sma"] * self.volume_mult.value)

        # EMA for trend filter
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # Count bullish/bearish signals
        dataframe["bull_count"] = (
            dataframe["st_bullish"].astype(int)
            + dataframe["rsi_bullish"].astype(int)
            + dataframe["macd_bullish"].astype(int)
        )
        dataframe["bear_count"] = (
            dataframe["st_bearish"].astype(int)
            + dataframe["rsi_bearish"].astype(int)
            + dataframe["macd_bearish"].astype(int)
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG: All 3 indicators bullish + MACD cross up
        dataframe.loc[
            (dataframe["st_bullish"])
            & (dataframe["rsi_bullish"])
            & (dataframe["macd_cross_up"])
            & (dataframe["close"] > dataframe["ema200"])
            & (dataframe["volume_ok"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1

        # SHORT: All 3 indicators bearish + MACD cross down
        dataframe.loc[
            (dataframe["st_bearish"])
            & (dataframe["rsi_bearish"])
            & (dataframe["macd_cross_down"])
            & (dataframe["close"] < dataframe["ema200"])
            & (dataframe["volume_ok"])
            & (dataframe["volume"] > 0),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit long when 2 of 3 indicators turn bearish
        dataframe.loc[(dataframe["bear_count"] >= 2), "exit_long"] = 1

        # Exit short when 2 of 3 indicators turn bullish
        dataframe.loc[(dataframe["bull_count"] >= 2), "exit_short"] = 1

        return dataframe
