"""
Teknik Göstergeler - Tüm "ölçülebilir" kuralların hesaplaması

Thread'deki kavramlar:
- ADR% (Average Daily Range %): Gün içi volatilite
- ATR% (Average True Range %): Gap dahil volatilite  
- RS (Relative Strength): Benchmark'a göre güç
- MA Squeeze: 10/20/50 sıkışması
- Weekly Base: Haftalık konsolidasyon kalitesi
"""

from __future__ import annotations
from typing import Tuple, Optional
import numpy as np
import pandas as pd


# ============================================================================
# VOLATILITE GÖSTERGELERİ
# ============================================================================

def true_range(df: pd.DataFrame) -> pd.Series:
    """
    True Range: Günlük aralık + gap'ler
    TR = max(H-L, |H-prevClose|, |L-prevClose|)
    """
    prev_close = df["Close"].shift(1)
    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev_close).abs()
    tr3 = (df["Low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range (Wilder smoothing)
    """
    tr = true_range(df)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def atr_pct(df: pd.DataFrame, period: int = 14) -> float:
    """
    ATR% = ATR / Close * 100
    "Genel volatilite var mı, gap de var mı?" sorusunun cevabı.
    Kural: ATR% >= 5
    """
    a = atr(df, period).iloc[-1]
    return float(a / df["Close"].iloc[-1] * 100)


def adr_pct(df: pd.DataFrame, window: int = 20) -> float:
    """
    ADR% = mean((High-Low)/Close) * 100
    "Gün içinde oynuyor mu?" sorusunun cevabı.
    Kural: ADR% >= 4
    """
    rng = (df["High"] - df["Low"]) / df["Close"]
    return float(rng.tail(window).mean() * 100)


# ============================================================================
# HAREKETLI ORTALAMALAR
# ============================================================================

def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=span, adjust=False).mean()


def ma_squeeze_value(df: pd.DataFrame, w1: int = 10, w2: int = 20, w3: int = 50) -> float:
    """
    MA Squeeze = (max(MA10,MA20,MA50) - min(...)) / Close
    
    "Sıkışma" = enerji birikimi = %2-3 altında değer
    Kural: squeeze <= 0.03 (%3)
    """
    c = df["Close"]
    ma10 = sma(c, w1).iloc[-1]
    ma20 = sma(c, w2).iloc[-1]
    ma50 = sma(c, w3).iloc[-1]
    close = c.iloc[-1]
    
    if any(pd.isna(x) for x in [ma10, ma20, ma50]):
        return np.nan
    
    mx, mn = max(ma10, ma20, ma50), min(ma10, ma20, ma50)
    return float((mx - mn) / close)


def ma_stack_bullish(df: pd.DataFrame, w1: int = 10, w2: int = 20, w3: int = 50) -> bool:
    """
    Bullish MA Stack: MA10 > MA20 > MA50 ve fiyat MA20 üstünde
    "Sıkışma açılımı" için gerekli.
    """
    c = df["Close"]
    ma10 = sma(c, w1)
    ma20 = sma(c, w2)
    ma50 = sma(c, w3)
    
    if any(pd.isna(x.iloc[-1]) for x in [ma10, ma20, ma50]):
        return False
    
    return (
        ma10.iloc[-1] > ma20.iloc[-1] > ma50.iloc[-1] and
        c.iloc[-1] > ma20.iloc[-1]
    )


def ma_stack_bullish_series(df: pd.DataFrame, w1: int = 10, w2: int = 20, w3: int = 50) -> pd.Series:
    """MA stack durumunu tüm veri için hesapla (backtest için)"""
    c = df["Close"]
    ma10 = sma(c, w1)
    ma20 = sma(c, w2)
    ma50 = sma(c, w3)
    
    return (ma10 > ma20) & (ma20 > ma50) & (c > ma20)


def ma_slopes_positive(df: pd.DataFrame, window: int = 5) -> bool:
    """
    Tüm MA'ların eğimi pozitif mi?
    "Açılım yukarı" kontrolü.
    """
    c = df["Close"]
    ma10 = sma(c, 10)
    ma20 = sma(c, 20)
    ma50 = sma(c, 50)
    
    def is_rising(s: pd.Series, w: int) -> bool:
        if len(s) < w:
            return False
        return float(s.iloc[-1]) > float(s.iloc[-w])
    
    return all(is_rising(ma, window) for ma in [ma10, ma20, ma50])


# ============================================================================
# RELATIVE STRENGTH (LİDERLİK)
# ============================================================================

def rs_series(sym_close: pd.Series, bench_close: pd.Series) -> pd.Series:
    """
    Relative Strength = Hisse/Benchmark
    Paranın nereye aktığını gösterir.
    """
    aligned = pd.concat([sym_close, bench_close], axis=1, join="inner").dropna()
    if aligned.empty:
        return pd.Series(dtype=float)
    return aligned.iloc[:, 0] / aligned.iloc[:, 1]


def slope_last(series: pd.Series, window: int = 20) -> float:
    """
    Son N günün linear regression slope'u.
    RS slope > 0 = liderlik artıyor.
    """
    y = series.tail(window).values
    if len(y) < window or np.any(np.isnan(y)):
        return np.nan
    x = np.arange(window)
    return float(np.polyfit(x, y, 1)[0])


def rs_above_ma(sym_close: pd.Series, bench_close: pd.Series, ma_period: int = 50) -> bool:
    """
    RS line MA üstünde mi?
    "4-8 hafta yükselişte" kontrolünün basit versiyonu.
    """
    rs = rs_series(sym_close, bench_close)
    if rs.empty or len(rs) < ma_period:
        return False
    rs_ma = sma(rs, ma_period)
    return float(rs.iloc[-1]) > float(rs_ma.iloc[-1])


def relative_performance(df: pd.DataFrame, bench_df: pd.DataFrame, days: int = 60) -> float:
    """
    Son N günde benchmark'tan ne kadar iyi/kötü performans?
    """
    if len(df) < days or len(bench_df) < days:
        return np.nan
    
    sym_ret = (df["Close"].iloc[-1] / df["Close"].iloc[-days]) - 1
    bench_ret = (bench_df["Close"].iloc[-1] / bench_df["Close"].iloc[-days]) - 1
    
    return float(sym_ret - bench_ret)


# ============================================================================
# DONCHIAN CHANNEL (BREAKOUT)
# ============================================================================

def donchian_high(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Son N günün en yüksek değeri (breakout seviyesi)"""
    return df["High"].rolling(window).max()


def donchian_low(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Son N günün en düşük değeri (stop seviyesi)"""
    return df["Low"].rolling(window).min()


def is_breakout(df: pd.DataFrame, window: int = 20) -> bool:
    """
    Bugünkü kapanış önceki Donchian High'ı kırdı mı?
    Entry sinyali.
    """
    dc = donchian_high(df, window)
    return float(df["Close"].iloc[-1]) > float(dc.iloc[-2])


# ============================================================================
# WEEKLY BASE (KONSOLIDASYON)
# ============================================================================

def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Günlük veriyi haftalığa çevir"""
    w = df.resample("W-FRI").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()
    return w


def weekly_base_score(df_daily: pd.DataFrame, weeks_min: int = 5, weeks_lookback: int = 20) -> float:
    """
    Haftalık base kalitesi (0-1 arası skor).
    
    İyi base:
    - Range dar (volatilite düşük)
    - Süre yeterli (min 5 hafta)
    
    Kural: base_score >= 0.4
    """
    w = to_weekly(df_daily)
    w = w.tail(weeks_lookback)
    
    if len(w) < weeks_min:
        return np.nan
    
    # Son weeks_min haftanın range'i
    recent = w.tail(weeks_min)
    hi = recent["High"].max()
    lo = recent["Low"].min()
    
    if lo <= 0:
        return np.nan
    
    base_range = (hi - lo) / lo  # 0.30 = %30 range
    
    # Range dar = skor yüksek (invert)
    # 0.60 range = 0 skor, 0.0 range = 1 skor
    return float(max(0.0, 1.0 - min(base_range, 1.0)))


def weekly_volatility_contracting(df_daily: pd.DataFrame, weeks: int = 8) -> bool:
    """
    Haftalık volatilite azalıyor mu?
    "Enerji birikiyor" kontrolü.
    """
    w = to_weekly(df_daily)
    if len(w) < weeks:
        return False
    
    recent = w.tail(weeks)
    ranges = (recent["High"] - recent["Low"]) / recent["Close"]
    
    # İlk yarı vs son yarı
    first_half = ranges.iloc[:weeks//2].mean()
    second_half = ranges.iloc[weeks//2:].mean()
    
    return second_half < first_half


# ============================================================================
# HACİM ANALİZİ
# ============================================================================

def avg_volume(df: pd.DataFrame, window: int = 20) -> float:
    """Ortalama hacim (likidite kontrolü)"""
    return float(df["Volume"].tail(window).mean())


def volume_breakout(df: pd.DataFrame, threshold: float = 1.5) -> bool:
    """
    Bugünkü hacim ortalamanın threshold katı mı?
    Breakout doğrulama.
    """
    avg = avg_volume(df, 20)
    if avg <= 0:
        return False
    return float(df["Volume"].iloc[-1]) > (avg * threshold)


def up_down_volume_ratio(df: pd.DataFrame, window: int = 20) -> float:
    """
    Yükseliş günlerindeki hacim / Düşüş günlerindeki hacim
    > 1 = alıcılar baskın
    
    "Büyük günlerde hacim artıyor, düşüş günlerinde azalıyor" kontrolü.
    """
    recent = df.tail(window)
    price_change = recent["Close"] - recent["Open"]
    
    up_vol = recent.loc[price_change > 0, "Volume"].sum()
    down_vol = recent.loc[price_change < 0, "Volume"].sum()
    
    if down_vol <= 0:
        return np.inf
    return float(up_vol / down_vol)


# ============================================================================
# 52 HAFTA YÜKSEK/DÜŞÜK
# ============================================================================

def pct_from_52w_high(df: pd.DataFrame) -> float:
    """52 hafta yüksekten uzaklık (%)"""
    if len(df) < 252:
        return np.nan
    high_52w = df["High"].tail(252).max()
    current = df["Close"].iloc[-1]
    return float((current - high_52w) / high_52w * 100)


def pct_from_52w_low(df: pd.DataFrame) -> float:
    """52 hafta düşükten uzaklık (%)"""
    if len(df) < 252:
        return np.nan
    low_52w = df["Low"].tail(252).min()
    current = df["Close"].iloc[-1]
    return float((current - low_52w) / low_52w * 100)


def near_52w_high(df: pd.DataFrame, threshold: float = 0.10) -> bool:
    """
    52 hafta yüksekten %threshold içinde mi?
    Lider hisseler genelde zirve yakınında.
    """
    pct = pct_from_52w_high(df)
    if np.isnan(pct):
        return False
    return pct >= -threshold * 100  # e.g., -10% = %10 aşağıda
