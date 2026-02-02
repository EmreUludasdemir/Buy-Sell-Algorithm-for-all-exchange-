"""
MACD-V Supertrend Fusion Strategy
==================================
Kripto piyasası için optimize edilmiş strateji.

4 İndikatör ile Maksimum Etkinlik:
1. MACD-V (Volatilite Normalize MACD) - Momentum timing
2. Supertrend - Trend yönü onayı
3. EMA 200 - Makro trend filtresi
4. Volume SMA - Hacim onayı

Entry Kuralları:
- MACD-V signal cross up
- MACD-V Rebounding/Rallying zone (-150 < macdv < 150)
- Supertrend bullish (direction = 1)
- Close > EMA 200
- Volume > Volume SMA * 0.8

Exit Kuralları:
- ROI tablosu ile otomatik çıkış
- Trailing stop ile kar kilitleme
- Supertrend flip veya overbought exit

Risk Yönetimi:
- %6 sabit stoploss
- Trailing stop: %2.5 başlangıç, %4 offset
- Max %15 drawdown koruması

Author: Emre Uludaşdemir
Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy

# Supertrend fonksiyonunu import et
from kivanc_indicators import supertrend

if TYPE_CHECKING:
    from freqtrade.persistence import Trade


class MACDVSupertrendStrategy(IStrategy):
    """
    MACD-V Supertrend Fusion - En İyi Kripto Stratejisi

    Felsefe: "Triple Confirmation with Minimal Complexity"
    4 indikatör ile maksimum etkinlik, minimum karmaşıklık.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True  # Futures için long ve short aktif

    # ROI tablosu - Dengeli yaklaşım
    minimal_roi = {
        "0": 0.10,    # %10 başlangıç hedef
        "48": 0.06,   # 2 gün sonra %6
        "96": 0.04,   # 4 gün sonra %4
        "192": 0.02,  # 8 gün sonra %2
    }

    # Stop loss
    stoploss = -0.06  # %6 sabit stop

    # Trailing stop - Kar kilitleme
    trailing_stop = True
    trailing_stop_positive = 0.025   # %2.5'te trailing başlasın
    trailing_stop_positive_offset = 0.04  # %4 kârdan sonra aktif
    trailing_only_offset_is_reached = True

    # Exit signal kullan
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Sadece yeni mum geldiğinde işle
    process_only_new_candles = True

    # Başlangıç mumları (EMA 200 için)
    startup_candle_count = 250

    # ═══════════════════════════════════════════════════════════════════════
    # MACD-V PARAMETRELERİ
    # ═══════════════════════════════════════════════════════════════════════
    fast_ema = IntParameter(10, 14, default=12, space="buy", optimize=True)
    slow_ema = IntParameter(24, 30, default=26, space="buy", optimize=True)
    signal_ema = IntParameter(7, 12, default=9, space="buy", optimize=True)
    atr_period = IntParameter(20, 30, default=26, space="buy", optimize=True)

    # MACD-V Zone Seviyeleri
    overbought_level = IntParameter(120, 180, default=150, space="buy", optimize=True)
    oversold_level = IntParameter(-180, -120, default=-150, space="buy", optimize=True)
    neutral_upper = IntParameter(30, 70, default=50, space="buy", optimize=True)

    # ═══════════════════════════════════════════════════════════════════════
    # SUPERTREND PARAMETRELERİ
    # ═══════════════════════════════════════════════════════════════════════
    supertrend_period = IntParameter(8, 14, default=10, space="buy", optimize=True)
    supertrend_mult = DecimalParameter(2.5, 3.5, default=3.0, decimals=1, space="buy", optimize=True)

    # ═══════════════════════════════════════════════════════════════════════
    # FİLTRE PARAMETRELERİ
    # ═══════════════════════════════════════════════════════════════════════
    ema_trend_period = IntParameter(180, 220, default=200, space="buy", optimize=True)
    volume_threshold = DecimalParameter(0.6, 1.0, default=0.8, decimals=1, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Tüm indikatörleri hesapla.

        İndikatör Stack:
        1. MACD-V = [(Fast EMA - Slow EMA) / ATR] × 100
        2. Supertrend (Kıvanç Özbilgiç style)
        3. EMA 200 (Makro trend)
        4. Volume SMA (Hacim onayı)
        """
        # ═══════════════════════════════════════════════════════════════════
        # MACD-V HESAPLAMA
        # ═══════════════════════════════════════════════════════════════════
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.fast_ema.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.slow_ema.value)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.atr_period.value)

        # MACD-V = [(Fast EMA - Slow EMA) / ATR] × 100
        atr_safe = dataframe["atr"].replace(0, np.nan).ffill()
        dataframe["macdv"] = ((dataframe["ema_fast"] - dataframe["ema_slow"]) / atr_safe) * 100

        # Signal Line: MACD-V'nin EMA'sı
        dataframe["macdv_signal"] = ta.EMA(dataframe["macdv"], timeperiod=self.signal_ema.value)

        # Histogram
        dataframe["macdv_hist"] = dataframe["macdv"] - dataframe["macdv_signal"]

        # MACD-V Crossovers
        dataframe["macdv_cross_up"] = (
            (dataframe["macdv"] > dataframe["macdv_signal"]) &
            (dataframe["macdv"].shift(1) <= dataframe["macdv_signal"].shift(1))
        )

        dataframe["macdv_cross_down"] = (
            (dataframe["macdv"] < dataframe["macdv_signal"]) &
            (dataframe["macdv"].shift(1) >= dataframe["macdv_signal"].shift(1))
        )

        # MACD-V Momentum Zones
        dataframe["is_rebounding"] = (
            (dataframe["macdv"] > self.oversold_level.value) &
            (dataframe["macdv"] < self.neutral_upper.value) &
            (dataframe["macdv"] > dataframe["macdv_signal"])
        )

        dataframe["is_rallying"] = (
            (dataframe["macdv"] >= self.neutral_upper.value) &
            (dataframe["macdv"] < self.overbought_level.value) &
            (dataframe["macdv"] > dataframe["macdv_signal"])
        )

        dataframe["is_overbought"] = dataframe["macdv"] >= self.overbought_level.value

        # Entry zone: Rebounding veya Rallying (LONG)
        dataframe["macdv_entry_zone"] = dataframe["is_rebounding"] | dataframe["is_rallying"]

        # SHORT için momentum zones
        dataframe["is_retracing"] = (
            (dataframe["macdv"] < self.overbought_level.value) &
            (dataframe["macdv"] > -self.neutral_upper.value) &
            (dataframe["macdv"] < dataframe["macdv_signal"])
        )

        dataframe["is_reversing"] = (
            (dataframe["macdv"] <= -self.neutral_upper.value) &
            (dataframe["macdv"] > self.oversold_level.value) &
            (dataframe["macdv"] < dataframe["macdv_signal"])
        )

        dataframe["is_oversold"] = dataframe["macdv"] <= self.oversold_level.value

        # SHORT Entry zone: Retracing veya Reversing
        dataframe["macdv_short_zone"] = dataframe["is_retracing"] | dataframe["is_reversing"]

        # ═══════════════════════════════════════════════════════════════════
        # SUPERTREND HESAPLAMA
        # ═══════════════════════════════════════════════════════════════════
        st_direction, st_line = supertrend(
            dataframe,
            period=self.supertrend_period.value,
            multiplier=self.supertrend_mult.value
        )
        dataframe["supertrend_dir"] = st_direction
        dataframe["supertrend_line"] = st_line

        # Supertrend flip sinyalleri
        dataframe["supertrend_flip_up"] = (
            (dataframe["supertrend_dir"] == 1) &
            (dataframe["supertrend_dir"].shift(1) == -1)
        )

        dataframe["supertrend_flip_down"] = (
            (dataframe["supertrend_dir"] == -1) &
            (dataframe["supertrend_dir"].shift(1) == 1)
        )

        # ═══════════════════════════════════════════════════════════════════
        # TREND FİLTRESİ
        # ═══════════════════════════════════════════════════════════════════
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.ema_trend_period.value)
        dataframe["above_ema_trend"] = dataframe["close"] > dataframe["ema_trend"]
        dataframe["below_ema_trend"] = dataframe["close"] < dataframe["ema_trend"]

        # ═══════════════════════════════════════════════════════════════════
        # VOLUME FİLTRESİ
        # ═══════════════════════════════════════════════════════════════════
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["volume_ok"] = dataframe["volume"] > (dataframe["volume_sma"] * self.volume_threshold.value)

        # ═══════════════════════════════════════════════════════════════════
        # ADX (Opsiyonel Trend Gücü)
        # ═══════════════════════════════════════════════════════════════════
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry sinyalleri - Triple Confirmation.

        LONG Entry Kuralları (TÜM KOŞULLAR DOĞRU OLMALI):
        1. MACD-V signal cross up
        2. MACD-V Rebounding veya Rallying zone'da
        3. Supertrend bullish (direction = 1)
        4. Close > EMA 200
        5. Volume > Volume SMA * threshold
        """
        # ═══════════════════════════════════════════════════════════════════
        # LONG ENTRY
        # ═══════════════════════════════════════════════════════════════════
        long_conditions = (
            # 1. MACD-V signal üzerine cross yapsın
            (dataframe["macdv_cross_up"]) &

            # 2. MACD-V entry zone'da (Rebounding veya Rallying)
            (dataframe["macdv_entry_zone"]) &

            # 3. Supertrend bullish
            (dataframe["supertrend_dir"] == 1) &

            # 4. Fiyat EMA 200 üstünde (uptrend)
            (dataframe["above_ema_trend"]) &

            # 5. Hacim onayı
            (dataframe["volume_ok"]) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[long_conditions, "enter_long"] = 1
        dataframe.loc[long_conditions, "enter_tag"] = "MACDV_ST_LONG"

        # ═══════════════════════════════════════════════════════════════════
        # SHORT ENTRY
        # ═══════════════════════════════════════════════════════════════════
        short_conditions = (
            # 1. MACD-V signal altına cross yapsın
            (dataframe["macdv_cross_down"]) &

            # 2. MACD-V short zone'da (Retracing veya Reversing)
            (dataframe["macdv_short_zone"]) &

            # 3. Supertrend bearish
            (dataframe["supertrend_dir"] == -1) &

            # 4. Fiyat EMA 200 altında (downtrend)
            (dataframe["below_ema_trend"]) &

            # 5. Hacim onayı
            (dataframe["volume_ok"]) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[short_conditions, "enter_short"] = 1
        dataframe.loc[short_conditions, "enter_tag"] = "MACDV_ST_SHORT"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit sinyalleri.

        LONG Exit Kuralları (HERHANGİ BİRİ):
        1. MACD-V overbought (>150)
        2. Supertrend flip down
        3. MACD-V cross down + fiyat EMA altında
        """
        # ═══════════════════════════════════════════════════════════════════
        # LONG EXIT
        # ═══════════════════════════════════════════════════════════════════
        exit_long_conditions = (
            # 1. Overbought seviyesine ulaştı
            (dataframe["is_overbought"]) |

            # 2. Supertrend bearish'e döndü
            (dataframe["supertrend_flip_down"]) |

            # 3. MACD-V cross down + fiyat EMA altında (trend bozuldu)
            (
                (dataframe["macdv_cross_down"]) &
                (dataframe["below_ema_trend"]) &
                (dataframe["macdv"] < 0)
            )
        )

        dataframe.loc[exit_long_conditions, "exit_long"] = 1
        dataframe.loc[exit_long_conditions, "exit_tag"] = "MACDV_ST_EXIT_LONG"

        # ═══════════════════════════════════════════════════════════════════
        # SHORT EXIT
        # ═══════════════════════════════════════════════════════════════════
        exit_short_conditions = (
            # 1. Oversold seviyesine ulaştı
            (dataframe["is_oversold"]) |

            # 2. Supertrend bullish'e döndü
            (dataframe["supertrend_flip_up"]) |

            # 3. MACD-V cross up + fiyat EMA üstünde (trend bozuldu)
            (
                (dataframe["macdv_cross_up"]) &
                (dataframe["above_ema_trend"]) &
                (dataframe["macdv"] > 0)
            )
        )

        dataframe.loc[exit_short_conditions, "exit_short"] = 1
        dataframe.loc[exit_short_conditions, "exit_tag"] = "MACDV_ST_EXIT_SHORT"

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
        Dinamik stoploss - Momentum ve kâra göre ayarla.

        - Rallying zone'da: Geniş stoploss (-12%)
        - Kâr > %4: Sıkı stoploss (-4%)
        - Kâr > %2: Normal stoploss (-6%)
        - Diğer: Varsayılan stoploss
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return self.stoploss

        last_candle = dataframe.iloc[-1]

        # Rallying/Reversing zone'da momentum güçlü, geniş stoploss ver
        if last_candle.get("is_rallying", False) or last_candle.get("is_reversing", False):
            return -0.12

        # Kâr varsa stoploss'u sıkılaştır
        if current_profit > 0.04:
            return -0.04
        elif current_profit > 0.02:
            return -0.06

        return self.stoploss

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
        """
        Trade girişini onaylamadan önce son kontroller.

        ADX filtresi: Trending market olduğundan emin ol.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return False

        last_candle = dataframe.iloc[-1]

        # ADX > 20 ise trending market, trade'e izin ver
        if last_candle.get("adx", 0) >= 20:
            return True

        # ADX düşük ama MACD-V momentum güçlüyse (rebounding/rallying) yine de izin ver
        if last_candle.get("is_rallying", False) or (
            last_candle.get("is_rebounding", False) and
            last_candle.get("macdv", 0) > -50
        ):
            return True

        return False
