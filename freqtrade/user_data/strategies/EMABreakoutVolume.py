"""
EMA Ribbon Breakout Strategy with Volume Confirmation
======================================================
LoneStockTrader'ın EGM (Earnings Growth Momentum) metodolojisinden ilham alınarak
oluşturulmuş teknik analiz stratejisi.

Strateji Mantığı:
-----------------
1. EMA Ribbon: 8, 13, 21, 34, 55, 89 EMA'larla trend yönünü belirle
2. Ribbon Expansion: EMA'lar birbirinden ayrılıyorsa güçlü trend
3. Volume Surge: Ortalama hacmin 1.5x+ üstünde işlem hacmi
4. Breakout: Fiyat tüm EMA'ların üstünde ve consolidation'dan çıkış

CANSLIM/EGM Prensipleri (Teknik Kısım):
- Cup & Handle, Base Breakout pattern'ları
- Volume confirmation (kurumsal alım göstergesi)
- 7-8% stop loss disiplini
- Trend yönünde işlem (M = Market Direction)

Kaynak:
- LoneStockTrader (@LoneStockTrader) - EGM Strategy
- William O'Neil - CANSLIM Methodology
- https://traderlion.com/trading-strategies/canslim/
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy


if TYPE_CHECKING:
    from freqtrade.persistence import Trade


class EMABreakoutVolume(IStrategy):
    """
    EMA Ribbon Breakout Strategy

    Çoklu EMA ribbon ile trend yönünü belirler ve
    volume surge ile breakout'ları yakalar.

    Best for: 4H/Daily trending markets
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    # ROI - Breakout stratejisi için geniş hedefler
    minimal_roi = {
        "0": 0.15,  # İlk 15% kar al
        "48": 0.10,  # 48 bar sonra 10%
        "96": 0.06,  # 96 bar sonra 6%
        "192": 0.03,  # 192 bar sonra 3%
    }

    # CANSLIM tarzı sıkı stop loss (7-8%)
    stoploss = -0.08
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # EMA Ribbon Periyotları (Fibonacci bazlı)
    ema_fast = IntParameter(5, 10, default=8, space="buy", optimize=True)
    ema_2 = IntParameter(10, 16, default=13, space="buy", optimize=True)
    ema_3 = IntParameter(18, 25, default=21, space="buy", optimize=True)
    ema_4 = IntParameter(30, 40, default=34, space="buy", optimize=True)
    ema_5 = IntParameter(50, 60, default=55, space="buy", optimize=True)
    ema_slow = IntParameter(80, 100, default=89, space="buy", optimize=True)

    # Volume parametreleri
    volume_surge_mult = DecimalParameter(1.2, 2.5, default=1.5, decimals=1, space="buy", optimize=True)
    volume_ma_period = IntParameter(15, 25, default=20, space="buy", optimize=True)

    # Breakout parametreleri
    consolidation_bars = IntParameter(5, 15, default=10, space="buy", optimize=True)
    breakout_atr_mult = DecimalParameter(0.3, 1.0, default=0.5, decimals=1, space="buy", optimize=True)

    # ADX trend filtresi
    adx_threshold = IntParameter(15, 30, default=20, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        EMA Ribbon ve Volume indikatörlerini hesapla.
        """
        # ===== EMA RIBBON =====
        # Fibonacci tabanlı EMA'lar (8, 13, 21, 34, 55, 89)
        dataframe["ema_8"] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe["ema_13"] = ta.EMA(dataframe, timeperiod=self.ema_2.value)
        dataframe["ema_21"] = ta.EMA(dataframe, timeperiod=self.ema_3.value)
        dataframe["ema_34"] = ta.EMA(dataframe, timeperiod=self.ema_4.value)
        dataframe["ema_55"] = ta.EMA(dataframe, timeperiod=self.ema_5.value)
        dataframe["ema_89"] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)

        # EMA 200 - Long term trend
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        # ===== RIBBON ALIGNMENT (Trend Yönü) =====
        # Bullish: Tüm EMA'lar sıralı (fast > slow)
        dataframe["ribbon_bullish"] = (
            (dataframe["ema_8"] > dataframe["ema_13"])
            & (dataframe["ema_13"] > dataframe["ema_21"])
            & (dataframe["ema_21"] > dataframe["ema_34"])
            & (dataframe["ema_34"] > dataframe["ema_55"])
            & (dataframe["ema_55"] > dataframe["ema_89"])
        )

        # Bearish: Tüm EMA'lar ters sıralı
        dataframe["ribbon_bearish"] = (
            (dataframe["ema_8"] < dataframe["ema_13"])
            & (dataframe["ema_13"] < dataframe["ema_21"])
            & (dataframe["ema_21"] < dataframe["ema_34"])
            & (dataframe["ema_34"] < dataframe["ema_55"])
            & (dataframe["ema_55"] < dataframe["ema_89"])
        )

        # ===== RIBBON EXPANSION (Trend Gücü) =====
        # EMA'lar arasındaki mesafe artıyorsa trend güçleniyor
        dataframe["ribbon_width"] = (dataframe["ema_8"] - dataframe["ema_89"]).abs() / dataframe["close"] * 100
        dataframe["ribbon_expanding"] = dataframe["ribbon_width"] > dataframe["ribbon_width"].shift(1)

        # ===== PRICE vs EMA RIBBON =====
        # Fiyat tüm EMA'ların üstünde
        dataframe["price_above_ribbon"] = (
            (dataframe["close"] > dataframe["ema_8"])
            & (dataframe["close"] > dataframe["ema_13"])
            & (dataframe["close"] > dataframe["ema_21"])
            & (dataframe["close"] > dataframe["ema_34"])
            & (dataframe["close"] > dataframe["ema_55"])
            & (dataframe["close"] > dataframe["ema_89"])
        )

        # Fiyat tüm EMA'ların altında
        dataframe["price_below_ribbon"] = (
            (dataframe["close"] < dataframe["ema_8"])
            & (dataframe["close"] < dataframe["ema_13"])
            & (dataframe["close"] < dataframe["ema_21"])
            & (dataframe["close"] < dataframe["ema_34"])
            & (dataframe["close"] < dataframe["ema_55"])
            & (dataframe["close"] < dataframe["ema_89"])
        )

        # ===== VOLUME ANALYSIS =====
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=self.volume_ma_period.value)
        dataframe["volume_surge"] = dataframe["volume"] > dataframe["volume_sma"] * self.volume_surge_mult.value

        # Volume ratio (ne kadar yüksek o kadar güçlü breakout)
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_sma"]

        # ===== BREAKOUT DETECTION =====
        # ATR for volatility-adjusted breakout
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # Son N bar'ın en yüksek ve en düşük değerleri (consolidation range)
        dataframe["highest_high"] = dataframe["high"].rolling(window=self.consolidation_bars.value).max()
        dataframe["lowest_low"] = dataframe["low"].rolling(window=self.consolidation_bars.value).min()

        # Consolidation range
        dataframe["consolidation_range"] = dataframe["highest_high"] - dataframe["lowest_low"]

        # Breakout yukarı: Fiyat consolidation high'ını kırıyor
        dataframe["breakout_up"] = (dataframe["close"] > dataframe["highest_high"].shift(1)) & (
            dataframe["close"] > dataframe["highest_high"].shift(1) + (dataframe["atr"] * self.breakout_atr_mult.value)
        )

        # Breakout aşağı
        dataframe["breakout_down"] = (dataframe["close"] < dataframe["lowest_low"].shift(1)) & (
            dataframe["close"] < dataframe["lowest_low"].shift(1) - (dataframe["atr"] * self.breakout_atr_mult.value)
        )

        # ===== MOMENTUM INDICATORS =====
        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # ADX - Trend Strength
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        # MACD for momentum confirmation
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macd_signal"] = macd["macdsignal"]
        dataframe["macd_hist"] = macd["macdhist"]

        # ===== EMA RIBBON CROSSOVER =====
        # Fast EMA ribbon'ı yukarı kesiyor (trend başlangıcı)
        dataframe["ribbon_cross_up"] = (dataframe["ema_8"] > dataframe["ema_21"]) & (
            dataframe["ema_8"].shift(1) <= dataframe["ema_21"].shift(1)
        )

        dataframe["ribbon_cross_down"] = (dataframe["ema_8"] < dataframe["ema_21"]) & (
            dataframe["ema_8"].shift(1) >= dataframe["ema_21"].shift(1)
        )

        # ===== PULLBACK TO EMA (Buy the Dip) =====
        # Fiyat EMA 21'e geri çekildi ve bounce yapıyor
        dataframe["pullback_to_ema21"] = (
            (dataframe["low"] <= dataframe["ema_21"] * 1.01)
            & (dataframe["close"] > dataframe["ema_21"])
            & (dataframe["ribbon_bullish"])
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry sinyalleri:
        1. Breakout + Volume Surge + Bullish Ribbon
        2. Pullback to EMA + Bullish Ribbon
        """
        # ====== LONG ENTRY: BREAKOUT ======
        # Primary: Strong breakout with volume confirmation
        long_breakout = (
            # Breakout yukarı
            (dataframe["breakout_up"])
            # Volume surge (kurumsal alım)
            & (dataframe["volume_surge"])
            # EMA Ribbon bullish alignment
            & (dataframe["ribbon_bullish"])
            # Fiyat tüm EMA'ların üstünde
            & (dataframe["price_above_ribbon"])
            # Long-term trend pozitif
            & (dataframe["close"] > dataframe["ema_200"])
            # ADX trend gücü
            & (dataframe["adx"] > self.adx_threshold.value)
            # RSI aşırı alımda değil
            & (dataframe["rsi"] < 75)
            & (dataframe["volume"] > 0)
        )

        # Secondary: Pullback to EMA21 in uptrend
        long_pullback = (
            # Pullback sonrası bounce
            (dataframe["pullback_to_ema21"])
            # Volume normal veya yüksek
            & (dataframe["volume"] > dataframe["volume_sma"] * 0.8)
            # MACD pozitif
            & (dataframe["macd"] > dataframe["macd_signal"])
            # Long-term trend pozitif
            & (dataframe["close"] > dataframe["ema_200"])
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[long_breakout | long_pullback, "enter_long"] = 1

        # ====== SHORT ENTRY: BREAKDOWN ======
        short_breakdown = (
            # Breakdown aşağı
            (dataframe["breakout_down"])
            # Volume surge
            & (dataframe["volume_surge"])
            # EMA Ribbon bearish alignment
            & (dataframe["ribbon_bearish"])
            # Fiyat tüm EMA'ların altında
            & (dataframe["price_below_ribbon"])
            # Long-term trend negatif
            & (dataframe["close"] < dataframe["ema_200"])
            # ADX trend gücü
            & (dataframe["adx"] > self.adx_threshold.value)
            # RSI aşırı satımda değil
            & (dataframe["rsi"] > 25)
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[short_breakdown, "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit sinyalleri:
        1. Ribbon reversal
        2. Fiyat ribbon'ın altına/üstüne geçiş
        3. Volume düşüşü ile momentum kaybı
        """
        # ====== LONG EXIT ======
        exit_long = (
            # EMA ribbon bearish'e döndü
            (dataframe["ribbon_bearish"])
            # VEYA fiyat ribbon'ın altına düştü
            | (dataframe["price_below_ribbon"])
            # VEYA fast EMA slow EMA'yı aşağı kesti
            | (dataframe["ribbon_cross_down"])
            # VEYA RSI aşırı alım
            | (dataframe["rsi"] > 80)
        )
        dataframe.loc[exit_long, "exit_long"] = 1

        # ====== SHORT EXIT ======
        exit_short = (
            # EMA ribbon bullish'e döndü
            (dataframe["ribbon_bullish"])
            # VEYA fiyat ribbon'ın üstüne çıktı
            | (dataframe["price_above_ribbon"])
            # VEYA fast EMA slow EMA'yı yukarı kesti
            | (dataframe["ribbon_cross_up"])
            # VEYA RSI aşırı satım
            | (dataframe["rsi"] < 20)
        )
        dataframe.loc[exit_short, "exit_short"] = 1

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
        CANSLIM tarzı dinamik stoploss.

        - İlk 7-8% sıkı stop (capital protection)
        - Kar varsa trailing stop aktif
        - Büyük kar varsa daha sıkı stop
        """
        # Kar %10'u geçtiyse, stop'u sıkılaştır
        if current_profit > 0.10:
            return -0.05  # Max %5 geri çekilme

        # Kar %5'i geçtiyse
        if current_profit > 0.05:
            return -0.06  # Max %6 geri çekilme

        # Kar varsa biraz daha geniş
        if current_profit > 0.02:
            return -0.07

        # Default CANSLIM stop: %8
        return self.stoploss
