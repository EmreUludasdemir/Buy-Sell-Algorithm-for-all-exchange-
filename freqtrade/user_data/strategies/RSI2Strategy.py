"""
Strategy 1: RSI2 Mean Reversion Strategy
=========================================
Based on research showing 91% win rate on RSI 2 strategy.

Rules:
- Buy when RSI(2) < 10 and price > SMA(200)
- Sell when RSI(2) > 90 or after 5 bars
- Works best in trending markets with mean reversion pullbacks

Source: QuantifiedStrategies.com
"""

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IntParameter, IStrategy


class RSI2Strategy(IStrategy):
    """
    RSI 2 Mean Reversion Strategy
    - 91% win rate reported in research
    - Best for: 4H/Daily timeframes
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    # ROI - Quick exits for mean reversion
    minimal_roi = {
        "0": 0.04,  # 4% target
        "24": 0.025,  # 2.5% after 24 hours
        "48": 0.015,  # 1.5% after 48 hours
        "72": 0.01,  # 1% after 72 hours
    }

    stoploss = -0.05  # 5% stop loss
    trailing_stop = False

    # Hyperopt parameters
    rsi_period = IntParameter(2, 5, default=2, space="buy")
    rsi_buy_threshold = IntParameter(5, 15, default=10, space="buy")
    rsi_sell_threshold = IntParameter(85, 95, default=90, space="sell")
    sma_period = IntParameter(150, 250, default=200, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI 2
        dataframe["rsi2"] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)

        # SMA 200 trend filter
        dataframe["sma200"] = ta.SMA(dataframe, timeperiod=self.sma_period.value)

        # RSI 14 for additional confirmation
        dataframe["rsi14"] = ta.RSI(dataframe, timeperiod=14)

        # ATR for volatility
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG: RSI2 oversold + above SMA200 (uptrend)
        dataframe.loc[
            (dataframe["rsi2"] < self.rsi_buy_threshold.value)
            & (dataframe["close"] > dataframe["sma200"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1

        # SHORT: RSI2 overbought + below SMA200 (downtrend)
        dataframe.loc[
            (dataframe["rsi2"] > self.rsi_sell_threshold.value)
            & (dataframe["close"] < dataframe["sma200"])
            & (dataframe["volume"] > 0),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit long when RSI2 overbought
        dataframe.loc[(dataframe["rsi2"] > self.rsi_sell_threshold.value), "exit_long"] = 1

        # Exit short when RSI2 oversold
        dataframe.loc[(dataframe["rsi2"] < self.rsi_buy_threshold.value), "exit_short"] = 1

        return dataframe
