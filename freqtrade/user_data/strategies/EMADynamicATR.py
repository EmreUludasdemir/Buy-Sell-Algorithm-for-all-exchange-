"""
Strategy 5: EMA + ADX + ATR Dynamic Strategy
=============================================
Based on research showing 82% profit in 1 month with proper risk management.

Rules:
- Buy when: EMA crossover + ADX > 25 + price above EMA200
- Sell when: EMA cross down OR ATR trailing stop hit
- Dynamic position sizing based on ATR

Source: QuantifiedStrategies.com research
"""

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy


class EMADynamicATR(IStrategy):
    """
    EMA + ADX + ATR Dynamic Strategy
    - EMA crossover for entry timing
    - ADX for trend strength confirmation
    - ATR for dynamic stop loss and take profit
    - Best for: 4H/Daily trending markets
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    minimal_roi = {
        "0": 0.20,
        "48": 0.12,
        "96": 0.08,
        "192": 0.04,
    }

    stoploss = -0.12
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # EMA parameters
    ema_fast = IntParameter(8, 15, default=9, space="buy")
    ema_slow = IntParameter(18, 30, default=21, space="buy")
    ema_trend = IntParameter(150, 250, default=200, space="buy")

    # ADX parameters
    adx_period = IntParameter(10, 20, default=14, space="buy")
    adx_threshold = IntParameter(20, 35, default=25, space="buy")

    # ATR parameters
    atr_period = IntParameter(10, 20, default=14, space="buy")
    atr_sl_mult = DecimalParameter(1.0, 3.0, default=1.5, decimals=1, space="buy")
    atr_tp_mult = DecimalParameter(2.0, 5.0, default=3.0, decimals=1, space="buy")

    # Volume filter
    volume_mult = DecimalParameter(1.0, 2.0, default=1.1, decimals=1, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMAs
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.ema_trend.value)

        # EMA crossover signals
        dataframe["ema_cross_up"] = (dataframe["ema_fast"] > dataframe["ema_slow"]) & (
            dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1)
        )
        dataframe["ema_cross_down"] = (dataframe["ema_fast"] < dataframe["ema_slow"]) & (
            dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1)
        )

        # EMA trend state
        dataframe["ema_bullish"] = dataframe["ema_fast"] > dataframe["ema_slow"]
        dataframe["ema_bearish"] = dataframe["ema_fast"] < dataframe["ema_slow"]

        # ADX
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=self.adx_period.value)
        dataframe["plus_di"] = ta.PLUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe, timeperiod=self.adx_period.value)
        dataframe["adx_strong"] = dataframe["adx"] > self.adx_threshold.value

        # ATR
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_period.value)

        # Calculate dynamic SL/TP levels
        dataframe["sl_long"] = dataframe["close"] - (dataframe["atr"] * self.atr_sl_mult.value)
        dataframe["tp_long"] = dataframe["close"] + (dataframe["atr"] * self.atr_tp_mult.value)
        dataframe["sl_short"] = dataframe["close"] + (dataframe["atr"] * self.atr_sl_mult.value)
        dataframe["tp_short"] = dataframe["close"] - (dataframe["atr"] * self.atr_tp_mult.value)

        # RSI for additional momentum confirmation
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Volume
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["volume_ok"] = dataframe["volume"] > (dataframe["volume_sma"] * self.volume_mult.value)

        # Trend strength score (0-4)
        dataframe["trend_score"] = (
            (dataframe["ema_bullish"]).astype(int)
            + (dataframe["close"] > dataframe["ema_trend"]).astype(int)
            + (dataframe["adx_strong"]).astype(int)
            + (dataframe["plus_di"] > dataframe["minus_di"]).astype(int)
        )

        dataframe["downtrend_score"] = (
            (dataframe["ema_bearish"]).astype(int)
            + (dataframe["close"] < dataframe["ema_trend"]).astype(int)
            + (dataframe["adx_strong"]).astype(int)
            + (dataframe["minus_di"] > dataframe["plus_di"]).astype(int)
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # LONG: EMA cross up + strong trend + volume
        dataframe.loc[
            (dataframe["ema_cross_up"])
            & (dataframe["close"] > dataframe["ema_trend"])
            & (dataframe["adx_strong"])
            & (dataframe["plus_di"] > dataframe["minus_di"])
            & (dataframe["rsi"] > 40)
            & (dataframe["rsi"] < 70)
            & (dataframe["volume_ok"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1

        # SHORT: EMA cross down + strong downtrend + volume
        dataframe.loc[
            (dataframe["ema_cross_down"])
            & (dataframe["close"] < dataframe["ema_trend"])
            & (dataframe["adx_strong"])
            & (dataframe["minus_di"] > dataframe["plus_di"])
            & (dataframe["rsi"] < 60)
            & (dataframe["rsi"] > 30)
            & (dataframe["volume_ok"])
            & (dataframe["volume"] > 0),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit long on EMA cross down or trend reversal
        dataframe.loc[(dataframe["ema_cross_down"]) | (dataframe["trend_score"] <= 1), "exit_long"] = 1

        # Exit short on EMA cross up or trend reversal
        dataframe.loc[(dataframe["ema_cross_up"]) | (dataframe["downtrend_score"] <= 1), "exit_short"] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs) -> float:
        """
        Dynamic ATR-based stop loss.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return self.stoploss

        last_candle = dataframe.iloc[-1]
        atr = last_candle["atr"]

        if atr > 0:
            # Calculate dynamic stop based on ATR
            atr_stop = (atr * self.atr_sl_mult.value) / current_rate
            return -min(atr_stop, abs(self.stoploss))

        return self.stoploss
