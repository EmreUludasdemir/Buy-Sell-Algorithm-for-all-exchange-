"""
Regime Strategy - Basit ama Etkili
===================================
Bull market'te buy-hold, bear market'te aktif trading.

Kural:
- Fiyat > EMA200 → LONG aç, tut (exit yok)
- Fiyat < EMA200 → SHORT sinyalleri aktif

Bu strateji "market'ı yenmeye" değil, "market'la birlikte hareket etmeye" odaklanır.
"""

from datetime import datetime
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class RegimeStrategy(IStrategy):
    """
    Regime-Based Strategy

    Bull (Fiyat > EMA200): Long pozisyon aç ve tut
    Bear (Fiyat < EMA200): Short sinyalleri aktif
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True

    # Çok geniş ROI - pozisyonu tutmak için
    minimal_roi = {
        "0": 0.50,     # %50 - neredeyse hiç ROI exit olmaz
        "720": 0.20,   # 30 gün sonra %20
    }

    stoploss = -0.15  # %15 geniş stop (trend kırılmasını bekle)

    # Trailing stop - karı kilitle
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.10
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count = 250

    # Parametreler
    ema_period = IntParameter(150, 250, default=200, space="buy", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Sadece EMA200 - basit tut."""

        # Ana trend filtresi
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=self.ema_period.value)

        # Rejim tespiti
        dataframe["bull_regime"] = dataframe["close"] > dataframe["ema200"]
        dataframe["bear_regime"] = dataframe["close"] < dataframe["ema200"]

        # Rejim değişimi
        dataframe["regime_to_bull"] = (
            (dataframe["bull_regime"]) &
            (~dataframe["bull_regime"].shift(1).fillna(False))
        )
        dataframe["regime_to_bear"] = (
            (dataframe["bear_regime"]) &
            (~dataframe["bear_regime"].shift(1).fillna(False))
        )

        # Supertrend (sadece bear market short için)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=10)
        hl2 = (dataframe["high"] + dataframe["low"]) / 2
        dataframe["upper_band"] = hl2 + (3.0 * dataframe["atr"])
        dataframe["lower_band"] = hl2 - (3.0 * dataframe["atr"])

        # Basit supertrend direction
        dataframe["st_dir"] = 1  # default bullish
        for i in range(1, len(dataframe)):
            if dataframe["close"].iloc[i] > dataframe["upper_band"].iloc[i-1]:
                dataframe.loc[dataframe.index[i], "st_dir"] = 1
            elif dataframe["close"].iloc[i] < dataframe["lower_band"].iloc[i-1]:
                dataframe.loc[dataframe.index[i], "st_dir"] = -1
            else:
                dataframe.loc[dataframe.index[i], "st_dir"] = dataframe["st_dir"].iloc[i-1]

        # Supertrend flip
        dataframe["st_flip_down"] = (
            (dataframe["st_dir"] == -1) &
            (dataframe["st_dir"].shift(1) == 1)
        )
        dataframe["st_flip_up"] = (
            (dataframe["st_dir"] == 1) &
            (dataframe["st_dir"].shift(1) == -1)
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        LONG: Bull rejime geçişte veya bull rejimde ST flip up
        SHORT: Bear rejimde ST flip down
        """

        # ═══ LONG ENTRY ═══
        # Bull rejime geçiş VEYA bull rejimde supertrend bullish
        long_conditions = (
            (
                dataframe["regime_to_bull"] |  # Rejim değişimi
                (dataframe["bull_regime"] & dataframe["st_flip_up"])  # Bull'da dip al
            ) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[long_conditions, "enter_long"] = 1
        dataframe.loc[long_conditions, "enter_tag"] = "REGIME_LONG"

        # ═══ SHORT ENTRY ═══
        # SADECE bear rejimde short
        short_conditions = (
            (dataframe["bear_regime"]) &
            (dataframe["st_flip_down"]) &  # Supertrend bearish flip
            (dataframe["volume"] > 0)
        )

        dataframe.loc[short_conditions, "enter_short"] = 1
        dataframe.loc[short_conditions, "enter_tag"] = "REGIME_SHORT"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        LONG EXIT: Sadece bear rejime geçişte
        SHORT EXIT: Bull rejime geçişte veya ST flip up
        """

        # ═══ LONG EXIT ═══
        # SADECE rejim değiştiğinde çık (bear'e geçiş)
        exit_long = dataframe["regime_to_bear"]

        dataframe.loc[exit_long, "exit_long"] = 1
        dataframe.loc[exit_long, "exit_tag"] = "REGIME_CHANGE"

        # ═══ SHORT EXIT ═══
        # Rejim değişimi veya supertrend flip
        exit_short = (
            dataframe["regime_to_bull"] |
            (dataframe["bear_regime"] & dataframe["st_flip_up"])
        )

        dataframe.loc[exit_short, "exit_short"] = 1
        dataframe.loc[exit_short, "exit_tag"] = "REGIME_EXIT"

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
    ) -> Optional[float]:
        """
        Long pozisyonlarda geniş stoploss (trend kırılmasını bekle).
        Short pozisyonlarda sıkı stoploss.
        """
        if trade.is_short:
            # Short'ta sıkı stop
            if current_profit > 0.05:
                return -0.03
            return -0.08
        else:
            # Long'da geniş stop - trend bozulmadıkça tutmaya devam
            if current_profit > 0.20:
                return -0.10  # %20+ kârda %10 trailing
            elif current_profit > 0.10:
                return -0.12
            return -0.15  # Varsayılan geniş stop
