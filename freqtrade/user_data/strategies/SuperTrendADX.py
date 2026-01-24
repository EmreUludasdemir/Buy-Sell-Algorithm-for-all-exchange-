"""
Strategy 3: SuperTrend + ADX Strategy
=====================================
Based on research showing 67% win rate and 11.07% profit per trade.

Rules:
- Buy when SuperTrend turns bullish AND ADX > 25
- Sell when SuperTrend turns bearish
- ATR-based trailing stop for profit protection

Source: QuantifiedStrategies.com, GoodCrypto.app
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

    supertrend = [0.0] * len(df)
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
            supertrend[i] = lowerband.iloc[i]
        else:
            supertrend[i] = upperband.iloc[i]

    return supertrend, direction


class SuperTrendADX(IStrategy):
    """
    SuperTrend + ADX Strategy
    - 67% win rate, 11.07% avg profit per trade
    - Best for: 4H/Daily trending markets
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    minimal_roi = {
        "0": 0.12,
        "48": 0.08,
        "96": 0.05,
        "192": 0.03,
    }

    stoploss = -0.08
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # SuperTrend parameters
    st_period = IntParameter(8, 15, default=10, space="buy")
    st_multiplier = DecimalParameter(2.0, 4.0, default=3.0, decimals=1, space="buy")

    # ADX parameters
    adx_threshold = IntParameter(20, 35, default=25, space="buy")

    # Volume filter
    volume_mult = DecimalParameter(1.0, 2.0, default=1.2, decimals=1, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # SuperTrend
        st_line, st_dir = supertrend(dataframe, self.st_period.value, self.st_multiplier.value)
        dataframe["supertrend"] = st_line
        dataframe["st_direction"] = st_dir

        # SuperTrend flip signals
        dataframe["st_flip_up"] = (dataframe["st_direction"] == -1) & (dataframe["st_direction"].shift(1) == 1)
        dataframe["st_flip_down"] = (dataframe["st_direction"] == 1) & (dataframe["st_direction"].shift(1) == -1)

        # ADX
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["plus_di"] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe, timeperiod=14)

        # ATR
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # Volume
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["volume_ok"] = dataframe["volume"] > (dataframe["volume_sma"] * self.volume_mult.value)

        # EMA trend
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG: SuperTrend flip up + ADX strong + volume
        dataframe.loc[
            (dataframe["st_flip_up"])
            & (dataframe["adx"] > self.adx_threshold.value)
            & (dataframe["plus_di"] > dataframe["minus_di"])
            & (dataframe["volume_ok"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1

        # SHORT: SuperTrend flip down + ADX strong + volume
        dataframe.loc[
            (dataframe["st_flip_down"])
            & (dataframe["adx"] > self.adx_threshold.value)
            & (dataframe["minus_di"] > dataframe["plus_di"])
            & (dataframe["volume_ok"])
            & (dataframe["volume"] > 0),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit long on SuperTrend flip down
        dataframe.loc[(dataframe["st_flip_down"]), "exit_long"] = 1

        # Exit short on SuperTrend flip up
        dataframe.loc[(dataframe["st_flip_up"]), "exit_short"] = 1

        return dataframe
