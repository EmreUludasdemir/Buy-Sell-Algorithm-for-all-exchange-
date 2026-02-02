"""
Strategy 2: MACD + RSI Combo Strategy
=====================================
Based on research showing 73% win rate with 0.88% avg gain per trade.

Rules:
- Buy when MACD crosses above signal AND RSI < 70 (not overbought)
- Sell when MACD crosses below signal AND RSI > 30 (not oversold)
- ADX > 20 filter for trending markets

Source: QuantifiedStrategies.com
"""

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IntParameter, IStrategy


class MACDRSICombo(IStrategy):
    """
    MACD + RSI Combination Strategy
    - 73% win rate, 0.88% avg gain per trade
    - Best for: 4H/Daily trending markets
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    minimal_roi = {
        "0": 0.06,
        "48": 0.04,
        "96": 0.025,
        "144": 0.015,
    }

    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # MACD parameters
    macd_fast = IntParameter(8, 15, default=12, space="buy")
    macd_slow = IntParameter(20, 30, default=26, space="buy")
    macd_signal = IntParameter(7, 12, default=9, space="buy")

    # RSI parameters
    rsi_period = IntParameter(10, 18, default=14, space="buy")
    rsi_ob = IntParameter(65, 80, default=70, space="buy")
    rsi_os = IntParameter(20, 35, default=30, space="buy")

    # ADX filter
    adx_threshold = IntParameter(15, 30, default=20, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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

        # MACD crossovers
        dataframe["macd_cross_up"] = (dataframe["macd"] > dataframe["macd_signal"]) & (
            dataframe["macd"].shift(1) <= dataframe["macd_signal"].shift(1)
        )
        dataframe["macd_cross_down"] = (dataframe["macd"] < dataframe["macd_signal"]) & (
            dataframe["macd"].shift(1) >= dataframe["macd_signal"].shift(1)
        )

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)

        # ADX
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        # ATR
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # EMA trend filter
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG: MACD cross up + RSI not overbought + ADX trending
        dataframe.loc[
            (dataframe["macd_cross_up"])
            & (dataframe["rsi"] < self.rsi_ob.value)
            & (dataframe["rsi"] > self.rsi_os.value)
            & (dataframe["adx"] > self.adx_threshold.value)
            & (dataframe["close"] > dataframe["ema50"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1

        # SHORT: MACD cross down + RSI not oversold + ADX trending
        dataframe.loc[
            (dataframe["macd_cross_down"])
            & (dataframe["rsi"] > self.rsi_os.value)
            & (dataframe["rsi"] < self.rsi_ob.value)
            & (dataframe["adx"] > self.adx_threshold.value)
            & (dataframe["close"] < dataframe["ema50"])
            & (dataframe["volume"] > 0),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit long on MACD cross down or RSI overbought
        dataframe.loc[(dataframe["macd_cross_down"]) | (dataframe["rsi"] > 80), "exit_long"] = 1

        # Exit short on MACD cross up or RSI oversold
        dataframe.loc[(dataframe["macd_cross_up"]) | (dataframe["rsi"] < 20), "exit_short"] = 1

        return dataframe
