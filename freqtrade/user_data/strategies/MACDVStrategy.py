"""
MACD-V (Volatility Normalized MACD) Strategy
=============================================
Alex Spiroglou tarafından geliştirilen ve Charles H. Dow Award kazanan strateji.

MACD-V Formülü:
- MACD-V = [(12-EMA - 26-EMA) / ATR(26)] × 100
- Signal Line = 9-EMA of MACD-V
- Histogram = MACD-V - Signal Line

7 Momentum Aşaması:
- Risk (Oversold): MACD-V < -150
- Rebounding: -150 < MACD-V < 50, signal üstünde → LONG ENTRY
- Rallying: 50 < MACD-V < 150, signal üstünde → HOLD
- Risk (Overbought): MACD-V > 150 → LONG EXIT
- Retracing: MACD-V > -50, signal altında → SHORT ENTRY
- Reversing: -150 < MACD-V < -50, signal altında → HOLD SHORT

Neutral Zone: -50 ile +50 arası (false sinyalleri filtreler)

Sources:
- https://chartschool.stockcharts.com/technical-indicators/macd-v
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4099617
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IntParameter, IStrategy


if TYPE_CHECKING:
    from freqtrade.persistence import Trade


class MACDVStrategy(IStrategy):
    """
    MACD-V Volatility Normalized Momentum Strategy

    Klasik MACD'yi ATR ile normalize ederek:
    - Farklı piyasalar arasında karşılaştırılabilir değerler üretir
    - Overbought/Oversold seviyeleri belirler (±150)
    - Neutral zone ile false sinyalleri filtreler (±50)
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    # ROI tablosu - MACD-V'nin momentum aşamalarına göre ayarlandı
    minimal_roi = {
        "0": 0.08,  # İlk 8% kar al
        "48": 0.05,  # 48 bar sonra 5%
        "96": 0.03,  # 96 bar sonra 3%
        "144": 0.015,  # 144 bar sonra 1.5%
    }

    stoploss = -0.08
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    # MACD-V Parametreleri
    fast_ema = IntParameter(8, 15, default=12, space="buy", optimize=True)
    slow_ema = IntParameter(20, 30, default=26, space="buy", optimize=True)
    signal_ema = IntParameter(7, 12, default=9, space="buy", optimize=True)
    atr_period = IntParameter(20, 30, default=26, space="buy", optimize=True)

    # Momentum Zone Seviyeleri
    overbought_level = IntParameter(120, 180, default=150, space="buy", optimize=True)
    oversold_level = IntParameter(-180, -120, default=-150, space="buy", optimize=True)
    neutral_upper = IntParameter(30, 70, default=50, space="buy", optimize=True)
    neutral_lower = IntParameter(-70, -30, default=-50, space="buy", optimize=True)

    # Trend filtresi
    use_ema_filter = True
    ema_filter_period = IntParameter(150, 250, default=200, space="buy", optimize=True)

    # ADX filtresi
    adx_threshold = IntParameter(15, 30, default=20, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        MACD-V ve yardımcı indikatörleri hesapla.

        MACD-V = [(Fast EMA - Slow EMA) / ATR] × 100
        Bu formül momentum'u volatilite ile normalize eder.
        """
        # EMA'ları hesapla
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)

        # ATR hesapla (volatilite ölçümü)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_period.value)

        # MACD-V hesapla: [(Fast EMA - Slow EMA) / ATR] × 100
        # ATR sıfır olmasını önle
        atr_safe = dataframe["atr"].replace(0, np.nan).fillna(method="ffill")
        dataframe["macdv"] = ((dataframe["ema_fast"] - dataframe["ema_slow"]) / atr_safe) * 100

        # Signal Line: MACD-V'nin EMA'sı
        dataframe["macdv_signal"] = ta.EMA(dataframe["macdv"], timeperiod=self.signal_ema.value)

        # Histogram
        dataframe["macdv_hist"] = dataframe["macdv"] - dataframe["macdv_signal"]

        # MACD-V Crossovers
        dataframe["macdv_cross_up"] = (dataframe["macdv"] > dataframe["macdv_signal"]) & (
            dataframe["macdv"].shift(1) <= dataframe["macdv_signal"].shift(1)
        )

        dataframe["macdv_cross_down"] = (dataframe["macdv"] < dataframe["macdv_signal"]) & (
            dataframe["macdv"].shift(1) >= dataframe["macdv_signal"].shift(1)
        )

        # Momentum Aşamaları
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

        dataframe["is_retracing"] = (dataframe["macdv"] > self.neutral_lower.value) & (
            dataframe["macdv"] < dataframe["macdv_signal"]
        )

        dataframe["is_reversing"] = (
            (dataframe["macdv"] <= self.neutral_lower.value)
            & (dataframe["macdv"] > self.oversold_level.value)
            & (dataframe["macdv"] < dataframe["macdv_signal"])
        )

        dataframe["is_oversold"] = dataframe["macdv"] <= self.oversold_level.value

        # Neutral Zone (false sinyal filtresi)
        dataframe["in_neutral_zone"] = dataframe["macdv"].abs() < self.neutral_upper.value

        # Trend Filter EMA
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.ema_filter_period.value)

        # ADX (trend gücü)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        # Volume SMA
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        MACD-V momentum aşamalarına göre giriş sinyalleri.

        LONG: Rebounding zone'da (oversold'dan çıkış) + signal cross up
        SHORT: Retracing zone'da (overbought'tan düşüş) + signal cross down
        """
        # ====== LONG ENTRY ======
        # Rebounding: Oversold'dan çıkıp toparlanma aşaması
        # MACD-V signal'ı yukarı kesiyor VE neutral zone dışında
        long_conditions = (
            # MACD-V signal'ı yukarı kesiyor
            (dataframe["macdv_cross_up"])
            # Oversold'dan çıkış veya rebounding
            & (
                (dataframe["macdv"].shift(1) <= self.oversold_level.value)  # Oversold'dan çıkış
                | (dataframe["is_rebounding"])  # Veya rebounding zone'da
            )
            # Trend filtresi: Fiyat EMA üstünde
            & (dataframe["close"] > dataframe["ema_trend"])
            # ADX filtresi: Yeterli trend gücü
            & (dataframe["adx"] > self.adx_threshold.value)
            # Volume filtresi
            & (dataframe["volume"] > dataframe["volume_sma"] * 0.5)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[long_conditions, "enter_long"] = 1

        # ====== SHORT ENTRY ======
        # Retracing: Overbought'tan düşüş aşaması
        # MACD-V signal'ı aşağı kesiyor
        short_conditions = (
            # MACD-V signal'ı aşağı kesiyor
            (dataframe["macdv_cross_down"])
            # Overbought'tan düşüş veya retracing
            & (
                (dataframe["macdv"].shift(1) >= self.overbought_level.value)  # Overbought'tan düşüş
                | (dataframe["is_retracing"])  # Veya retracing zone'da
            )
            # Trend filtresi: Fiyat EMA altında
            & (dataframe["close"] < dataframe["ema_trend"])
            # ADX filtresi
            & (dataframe["adx"] > self.adx_threshold.value)
            # Volume filtresi
            & (dataframe["volume"] > dataframe["volume_sma"] * 0.5)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[short_conditions, "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        MACD-V momentum aşamalarına göre çıkış sinyalleri.

        LONG EXIT: Overbought (>150) veya signal cross down
        SHORT EXIT: Oversold (<-150) veya signal cross up
        """
        # ====== LONG EXIT ======
        # Overbought zone veya momentum kaybı
        exit_long_conditions = (
            # Overbought seviyesine ulaştı
            (dataframe["is_overbought"])
            # VEYA MACD-V signal'ı aşağı kesti
            | (dataframe["macdv_cross_down"])
            # VEYA rallying'den retracing'e geçiş
            | ((dataframe["is_rallying"].shift(1)) & (dataframe["is_retracing"]))
        )
        dataframe.loc[exit_long_conditions, "exit_long"] = 1

        # ====== SHORT EXIT ======
        # Oversold zone veya momentum kaybı
        exit_short_conditions = (
            # Oversold seviyesine ulaştı
            (dataframe["is_oversold"])
            # VEYA MACD-V signal'ı yukarı kesti
            | (dataframe["macdv_cross_up"])
            # VEYA reversing'den rebounding'e geçiş
            | ((dataframe["is_reversing"].shift(1)) & (dataframe["is_rebounding"]))
        )
        dataframe.loc[exit_short_conditions, "exit_short"] = 1

        return dataframe

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
        """
        MACD-V bazlı dinamik stoploss.

        Momentum güçlüyse (rallying/reversing) daha geniş stoploss.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return self.stoploss

        last_candle = dataframe.iloc[-1]

        # Rallying zone'da daha geniş stoploss (trend devam ediyor)
        if trade.is_short:
            if last_candle.get("is_reversing", False):
                return -0.12  # Short'ta momentum güçlü, geniş stoploss
        else:
            if last_candle.get("is_rallying", False):
                return -0.12  # Long'da momentum güçlü, geniş stoploss

        # Kar varsa stoploss'u sıkılaştır
        if current_profit > 0.04:
            return -0.04
        elif current_profit > 0.02:
            return -0.06

        return self.stoploss
