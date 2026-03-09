import math
from typing import Tuple

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame, Series

from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy


class KivancSupertrendedMovingAverages1D(IStrategy):
    """
    Single production strategy for this repository.

    The system ports Kivanc Ozbilgic's SuperTrended Moving Averages logic into
    a long-horizon Freqtrade strategy for daily crypto data.

    The class keeps the canonical entry logic and the production 1D defaults.
    Alternate validated risk packs live under user_data/profiles and are
    applied temporarily by the research scripts during 4H validation runs.
    Short-side signals are calculated for research, but spot production remains
    long-only until a futures configuration is introduced.
    """

    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False

    # Risk layer defaults for the production 1D profile.
    minimal_roi = {"0": 1.0}
    stoploss = -0.20
    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    process_only_new_candles = True
    startup_candle_count = 400
    plot_config = {
        "main_plot": {
            "st_ma": {"color": "orange"},
            "st_up": {"color": "green"},
            "st_dn": {"color": "red"},
            "regime_ema": {"color": "blue"},
        },
        "subplots": {
            "Signals": {
                "buy_signal": {"color": "green"},
                "sell_signal": {"color": "red"},
                "st_trend": {"color": "blue"},
                "research_short_signal": {"color": "purple"},
            },
            "Trend": {
                "adx": {"color": "black"},
                "regime_slope_pct": {"color": "brown"},
            }
        },
    }

    ma_type = CategoricalParameter(
        ["SMA", "EMA", "WMA", "DEMA", "TMA", "VAR", "WWMA", "ZLEMA", "TSF", "HULL", "TILL"],
        default="EMA",
        space="buy",
        optimize=True,
    )
    ma_length = IntParameter(20, 300, default=100, space="buy", optimize=True)
    atr_period = IntParameter(7, 30, default=10, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(0.1, 5.0, default=0.5, decimals=1, space="buy", optimize=True)
    use_builtin_atr = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    t3_volume_factor = DecimalParameter(0.1, 1.0, default=0.7, decimals=1, space="buy", optimize=True)
    use_regime_filter = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    regime_ema_length = IntParameter(100, 300, default=200, space="buy", optimize=True)
    regime_slope_lookback = IntParameter(3, 30, default=10, space="buy", optimize=True)
    regime_slope_min = DecimalParameter(0.0, 0.1, default=0.0, decimals=3, space="buy", optimize=True)
    use_adx_filter = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    adx_threshold = IntParameter(10, 40, default=20, space="buy", optimize=True)

    @staticmethod
    def _wma(src: Series, length: int) -> Series:
        period = max(1, int(length))
        return pd.Series(ta.WMA(src, timeperiod=period), index=src.index)

    @staticmethod
    def _wwma(src: Series, length: int) -> Series:
        period = max(1, int(length))
        alpha = 1.0 / period
        out = np.zeros(len(src), dtype=float)
        out[0] = float(src.iloc[0])
        for i in range(1, len(src)):
            value = float(src.iloc[i])
            out[i] = alpha * value + (1 - alpha) * out[i - 1]
        return pd.Series(out, index=src.index)

    @staticmethod
    def _var_ma(src: Series, length: int) -> Series:
        period = max(1, int(length))
        valpha = 2.0 / (period + 1.0)

        diff = src.diff()
        vud1 = diff.where(diff > 0, 0.0)
        vdd1 = (-diff).where(diff < 0, 0.0)
        vud = vud1.rolling(window=9, min_periods=1).sum()
        vdd = vdd1.rolling(window=9, min_periods=1).sum()

        denom = (vud + vdd).replace(0, np.nan)
        vcmo = ((vud - vdd) / denom).fillna(0.0)

        out = np.zeros(len(src), dtype=float)
        out[0] = float(src.iloc[0])
        for i in range(1, len(src)):
            k = valpha * abs(float(vcmo.iloc[i]))
            out[i] = k * float(src.iloc[i]) + (1.0 - k) * out[i - 1]
        return pd.Series(out, index=src.index)

    @staticmethod
    def _zlema(src: Series, length: int) -> Series:
        period = max(1, int(length))
        lag = period // 2 if period % 2 == 0 else (period - 1) // 2
        ema_data = src + src - src.shift(lag)
        return pd.Series(ta.EMA(ema_data, timeperiod=period), index=src.index)

    @staticmethod
    def _tsf(src: Series, length: int) -> Series:
        period = max(2, int(length))
        lrc = pd.Series(ta.LINEARREG(src, timeperiod=period), index=src.index)
        lrc1 = lrc.shift(1)
        lrs = lrc - lrc1
        return lrc + lrs

    @staticmethod
    def _t3(src: Series, length: int, volume_factor: float) -> Series:
        period = max(1, int(length))
        b = float(max(0.0, min(1.0, volume_factor)))
        b2 = b * b
        b3 = b2 * b

        e1 = pd.Series(ta.EMA(src, timeperiod=period), index=src.index)
        e2 = pd.Series(ta.EMA(e1, timeperiod=period), index=src.index)
        e3 = pd.Series(ta.EMA(e2, timeperiod=period), index=src.index)
        e4 = pd.Series(ta.EMA(e3, timeperiod=period), index=src.index)
        e5 = pd.Series(ta.EMA(e4, timeperiod=period), index=src.index)
        e6 = pd.Series(ta.EMA(e5, timeperiod=period), index=src.index)

        c1 = -b3
        c2 = 3 * b2 + 3 * b3
        c3 = -6 * b2 - 3 * b - 3 * b3
        c4 = 1 + 3 * b + b3 + 3 * b2
        return c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3

    def _get_ma(self, src: Series) -> Series:
        length = int(self.ma_length.value)
        ma_type = str(self.ma_type.value)

        ema = pd.Series(ta.EMA(src, timeperiod=length), index=src.index)
        dema = 2 * ema - pd.Series(ta.EMA(ema, timeperiod=length), index=src.index)

        if ma_type == "SMA":
            return pd.Series(ta.SMA(src, timeperiod=length), index=src.index)
        if ma_type == "EMA":
            return ema
        if ma_type == "WMA":
            return self._wma(src, length)
        if ma_type == "DEMA":
            return dema
        if ma_type == "TMA":
            return pd.Series(
                ta.SMA(
                    pd.Series(ta.SMA(src, timeperiod=math.ceil(length / 2.0)), index=src.index),
                    timeperiod=math.floor(length / 2.0) + 1,
                ),
                index=src.index,
            )
        if ma_type == "VAR":
            return self._var_ma(src, length)
        if ma_type == "WWMA":
            return self._wwma(src, length)
        if ma_type == "ZLEMA":
            return self._zlema(src, length)
        if ma_type == "TSF":
            return self._tsf(src, length)
        if ma_type == "HULL":
            half_len = max(1, int(length / 2))
            sqrt_len = max(1, int(round(math.sqrt(length))))
            hma_input = 2 * self._wma(src, half_len) - self._wma(src, length)
            return self._wma(hma_input, sqrt_len)
        if ma_type == "TILL":
            return self._t3(src, length, float(self.t3_volume_factor.value))
        return ema

    def _supertrended_ma(self, dataframe: DataFrame, ma: Series) -> Tuple[Series, Series, Series, Series, Series]:
        close = dataframe["close"]
        period = int(self.atr_period.value)
        multiplier = float(self.atr_multiplier.value)

        tr = pd.Series(ta.TRANGE(dataframe), index=dataframe.index)
        atr_sma = tr.rolling(window=period, min_periods=1).mean()
        atr_builtin = pd.Series(ta.ATR(dataframe, timeperiod=period), index=dataframe.index)
        atr = atr_builtin if bool(self.use_builtin_atr.value) else atr_sma
        atr = atr.fillna(atr_sma).bfill()

        up = (ma - multiplier * atr).astype(float).copy()
        dn = (ma + multiplier * atr).astype(float).copy()

        trend = np.ones(len(dataframe), dtype=int)

        for i in range(1, len(dataframe)):
            prev_up = float(up.iloc[i - 1])
            prev_dn = float(dn.iloc[i - 1])
            prev_close = float(close.iloc[i - 1])

            if prev_close > prev_up:
                up.iloc[i] = max(float(up.iloc[i]), prev_up)
            if prev_close < prev_dn:
                dn.iloc[i] = min(float(dn.iloc[i]), prev_dn)

            if trend[i - 1] == -1 and float(close.iloc[i]) > prev_dn:
                trend[i] = 1
            elif trend[i - 1] == 1 and float(close.iloc[i]) < prev_up:
                trend[i] = -1
            else:
                trend[i] = trend[i - 1]

        trend_s = pd.Series(trend, index=dataframe.index)
        buy_signal = (trend_s == 1) & (trend_s.shift(1) == -1)
        sell_signal = (trend_s == -1) & (trend_s.shift(1) == 1)
        return trend_s, up, dn, buy_signal, sell_signal

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ma = self._get_ma(dataframe["close"])
        trend, up, dn, buy_signal, sell_signal = self._supertrended_ma(dataframe, ma)
        regime_ema = pd.Series(
            ta.EMA(dataframe["close"], timeperiod=int(self.regime_ema_length.value)),
            index=dataframe.index,
        )
        regime_slope = regime_ema.pct_change(int(self.regime_slope_lookback.value)).fillna(0.0)
        adx = pd.Series(ta.ADX(dataframe, timeperiod=14), index=dataframe.index).fillna(0.0)
        slope_min = float(self.regime_slope_min.value)
        bull_regime = (dataframe["close"] > regime_ema) & (regime_slope > slope_min)
        bear_regime = (dataframe["close"] < regime_ema) & (regime_slope < -slope_min)
        trend_strength_ok = adx > int(self.adx_threshold.value)

        dataframe["st_ma"] = ma
        dataframe["st_up"] = up
        dataframe["st_dn"] = dn
        dataframe["st_trend"] = trend
        dataframe["regime_ema"] = regime_ema
        dataframe["regime_slope_pct"] = regime_slope * 100.0
        dataframe["adx"] = adx
        dataframe["bull_regime"] = bull_regime.astype(int)
        dataframe["bear_regime"] = bear_regime.astype(int)
        dataframe["trend_strength_ok"] = trend_strength_ok.astype(int)
        dataframe["buy_signal"] = buy_signal.astype(int)
        dataframe["sell_signal"] = sell_signal.astype(int)
        dataframe["research_short_signal"] = 0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        condition = (dataframe["buy_signal"] == 1) & (dataframe["volume"] > 0)
        if bool(self.use_regime_filter.value):
            condition &= dataframe["bull_regime"] == 1
        if bool(self.use_adx_filter.value):
            condition &= dataframe["trend_strength_ok"] == 1

        dataframe.loc[condition, "enter_long"] = 1
        dataframe.loc[condition, "enter_tag"] = "ST_MA_BUY"

        short_condition = (dataframe["sell_signal"] == 1) & (dataframe["volume"] > 0)
        if bool(self.use_regime_filter.value):
            short_condition &= dataframe["bear_regime"] == 1
        if bool(self.use_adx_filter.value):
            short_condition &= dataframe["trend_strength_ok"] == 1
        dataframe.loc[short_condition, "research_short_signal"] = 1

        if self.can_short:
            dataframe.loc[short_condition, "enter_short"] = 1
            dataframe.loc[short_condition, "enter_tag"] = "ST_MA_SHORT"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        condition = (dataframe["sell_signal"] == 1) & (dataframe["volume"] > 0)
        dataframe.loc[condition, "exit_long"] = 1
        dataframe.loc[condition, "exit_tag"] = "ST_MA_SELL"

        if self.can_short:
            short_exit = (dataframe["buy_signal"] == 1) & (dataframe["volume"] > 0)
            dataframe.loc[short_exit, "exit_short"] = 1
            dataframe.loc[short_exit, "exit_tag"] = "ST_MA_COVER"
        return dataframe
