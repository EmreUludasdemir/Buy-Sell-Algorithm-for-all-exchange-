"""
Trading Sinyalleri - NE ZAMAN AL, NE ZAMAN SAT

Bu modül net sinyaller üretir:
- BUY: Şu an al
- SELL: Şu an sat
- HOLD: Bekle
- WATCH: İzle (henüz sinyal yok)

Her sinyal için:
- Entry fiyatı
- Stop loss seviyesi
- Take profit seviyeleri
- Risk/Reward oranı
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime

from .indicators import (
    sma, ema, atr, atr_pct, adr_pct,
    donchian_high, donchian_low,
    ma_stack_bullish, ma_squeeze_value,
    rs_series, slope_last, avg_volume,
    volume_breakout, weekly_base_score,
    pct_from_52w_high
)


class SignalType(Enum):
    """Sinyal türleri"""
    BUY = "🟢 AL"
    SELL = "🔴 SAT"
    HOLD = "🟡 TUT"
    WATCH = "👀 İZLE"
    NO_SIGNAL = "⚪ SİNYAL YOK"


@dataclass
class TradingSignal:
    """Tek bir trading sinyali"""
    ticker: str
    signal: SignalType
    price: float
    date: datetime
    
    # Entry/Exit seviyeleri
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None  # İlk hedef (1R)
    take_profit_2: Optional[float] = None  # İkinci hedef (2R)
    take_profit_3: Optional[float] = None  # Üçüncü hedef (3R)
    
    # Risk metrikleri
    risk_pct: Optional[float] = None       # Stop'a uzaklık %
    reward_risk_ratio: Optional[float] = None
    
    # Sinyal gücü ve nedeni
    strength: int = 0                       # 1-5 arası
    reasons: List[str] = None
    
    # Ek bilgiler
    atr_value: Optional[float] = None
    volume_ratio: Optional[float] = None
    rs_slope: Optional[float] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


def calculate_levels(
    entry: float, 
    stop: float, 
    risk_reward_targets: List[float] = [1.0, 2.0, 3.0]
) -> Tuple[float, float, float]:
    """
    Risk/Reward'a göre take profit seviyeleri hesapla.
    
    Args:
        entry: Giriş fiyatı
        stop: Stop loss fiyatı
        risk_reward_targets: R katları [1R, 2R, 3R]
    
    Returns:
        (TP1, TP2, TP3)
    """
    risk = abs(entry - stop)
    direction = 1 if entry > stop else -1  # Long vs Short
    
    tp1 = entry + (risk * risk_reward_targets[0] * direction)
    tp2 = entry + (risk * risk_reward_targets[1] * direction)
    tp3 = entry + (risk * risk_reward_targets[2] * direction)
    
    return tp1, tp2, tp3


def generate_buy_signal(
    df: pd.DataFrame,
    ticker: str,
    bench_df: Optional[pd.DataFrame] = None
) -> Optional[TradingSignal]:
    """
    AL sinyali üret - Breakout + Trend + Momentum birleşimi.
    
    Entry Koşulları:
    1. Fiyat Donchian(20) High kırılımı
    2. MA Stack bullish (10 > 20 > 50)
    3. Hacim ortalamanın üstünde
    4. ATR ile volatilite doğrulaması
    
    Stop Loss: 
    - 2 ATR altı veya
    - Son swing low veya
    - 20 MA altı (hangisi yakınsa)
    """
    if df.empty or len(df) < 60:
        return None
    
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    current_price = float(c.iloc[-1])
    current_date = df.index[-1]
    
    # ATR hesapla
    atr_val = float(atr(df, 14).iloc[-1])
    atr_pct_val = atr_pct(df, 14)
    
    # Göstergeler
    dc_high = donchian_high(df, 20)
    dc_low = donchian_low(df, 20)
    ma20 = sma(c, 20)
    ma50 = sma(c, 50)
    
    # Son değerler
    prev_dc_high = float(dc_high.iloc[-2])
    current_ma20 = float(ma20.iloc[-1])
    current_ma50 = float(ma50.iloc[-1])
    
    # Hacim analizi
    vol_avg = avg_volume(df, 20)
    current_vol = float(df["Volume"].iloc[-1])
    vol_ratio = current_vol / vol_avg if vol_avg > 0 else 1.0
    
    # RS slope (benchmark varsa)
    rs_s = None
    if bench_df is not None and not bench_df.empty:
        rs = rs_series(c, bench_df["Close"])
        rs_s = slope_last(rs, 20)
    
    # =============================
    # ENTRY KOŞULLARI
    # =============================
    reasons = []
    strength = 0
    
    # 1. Donchian Breakout
    breakout = current_price > prev_dc_high
    if breakout:
        reasons.append("✓ Donchian(20) kırılımı")
        strength += 1
    
    # 2. MA Stack
    ma_stack = (current_price > current_ma20 > current_ma50)
    if ma_stack:
        reasons.append("✓ MA stack bullish (P>20>50)")
        strength += 1
    
    # 3. Hacim doğrulaması
    vol_confirm = vol_ratio > 1.2
    if vol_confirm:
        reasons.append(f"✓ Hacim spike ({vol_ratio:.1f}x)")
        strength += 1
    
    # 4. MA'lar yükseliyor
    ma20_rising = float(ma20.iloc[-1]) > float(ma20.iloc[-5])
    if ma20_rising:
        reasons.append("✓ 20MA yükseliyor")
        strength += 1
    
    # 5. RS güçlü (opsiyonel)
    if rs_s is not None and rs_s > 0:
        reasons.append("✓ Relative strength pozitif")
        strength += 1
    
    # =============================
    # SİNYAL KARARI
    # =============================
    
    # BUY sinyali için minimum 3 koşul
    if breakout and strength >= 3:
        signal_type = SignalType.BUY
    elif ma_stack and strength >= 2:
        signal_type = SignalType.WATCH
        reasons.insert(0, "⏳ Setup oluşuyor, breakout bekle")
    else:
        return None  # Sinyal yok
    
    # =============================
    # STOP LOSS HESAPLA
    # =============================
    
    # Yöntem 1: 2 ATR altı
    stop_atr = current_price - (2 * atr_val)
    
    # Yöntem 2: Son 10 günün en düşüğü
    stop_swing = float(l.tail(10).min())
    
    # Yöntem 3: 20 MA altı
    stop_ma = current_ma20 * 0.98  # MA'nın %2 altı
    
    # En yakın olanı seç (riski sınırla)
    stop_loss = max(stop_atr, stop_swing, stop_ma)
    
    # Risk hesapla
    risk_pct = ((current_price - stop_loss) / current_price) * 100
    
    # Risk çok yüksekse (%8'den fazla) sinyal verme
    if risk_pct > 8:
        reasons.append(f"⚠️ Risk yüksek ({risk_pct:.1f}%)")
        if signal_type == SignalType.BUY:
            signal_type = SignalType.WATCH
    
    # =============================
    # TAKE PROFIT SEVİYELERİ
    # =============================
    
    entry_price = current_price
    tp1, tp2, tp3 = calculate_levels(entry_price, stop_loss)
    
    # R/R oranı
    reward = tp2 - entry_price
    risk = entry_price - stop_loss
    rr_ratio = reward / risk if risk > 0 else 0
    
    return TradingSignal(
        ticker=ticker,
        signal=signal_type,
        price=current_price,
        date=current_date,
        entry_price=entry_price,
        stop_loss=round(stop_loss, 2),
        take_profit_1=round(tp1, 2),
        take_profit_2=round(tp2, 2),
        take_profit_3=round(tp3, 2),
        risk_pct=round(risk_pct, 2),
        reward_risk_ratio=round(rr_ratio, 2),
        strength=strength,
        reasons=reasons,
        atr_value=round(atr_val, 2),
        volume_ratio=round(vol_ratio, 2),
        rs_slope=round(rs_s, 6) if rs_s else None
    )


def generate_sell_signal(
    df: pd.DataFrame,
    ticker: str,
    entry_price: Optional[float] = None
) -> Optional[TradingSignal]:
    """
    SAT sinyali üret - Trend bozulması + Zayıflık.
    
    Exit Koşulları:
    1. Fiyat 20MA altına kapandı
    2. MA stack bozuldu (20 < 50)
    3. Lower high + lower low oluştu
    4. Hacim artışıyla satış
    """
    if df.empty or len(df) < 60:
        return None
    
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    current_price = float(c.iloc[-1])
    current_date = df.index[-1]
    
    ma20 = sma(c, 20)
    ma50 = sma(c, 50)
    
    current_ma20 = float(ma20.iloc[-1])
    current_ma50 = float(ma50.iloc[-1])
    
    reasons = []
    strength = 0
    
    # 1. Fiyat 20MA altında
    below_ma20 = current_price < current_ma20
    if below_ma20:
        reasons.append("✗ Fiyat 20MA altında")
        strength += 1
    
    # 2. MA stack bozuldu
    ma_bearish = current_ma20 < current_ma50
    if ma_bearish:
        reasons.append("✗ MA stack bearish (20 < 50)")
        strength += 1
    
    # 3. Son 2 gün ardarda düşüş
    consecutive_down = (
        float(c.iloc[-1]) < float(c.iloc[-2]) < float(c.iloc[-3])
    )
    if consecutive_down:
        reasons.append("✗ 3 gün ardarda düşüş")
        strength += 1
    
    # 4. 20MA aşağı dönüyor
    ma20_falling = float(ma20.iloc[-1]) < float(ma20.iloc[-5])
    if ma20_falling:
        reasons.append("✗ 20MA düşüyor")
        strength += 1
    
    # 5. Dün breakout var ama bugün geri döndü (false breakout)
    dc_high = donchian_high(df, 20)
    prev_close = float(c.iloc[-2])
    prev_dc = float(dc_high.iloc[-3])
    false_breakout = prev_close > prev_dc and current_price < prev_dc
    if false_breakout:
        reasons.append("✗ False breakout!")
        strength += 2  # Ciddi uyarı
    
    # =============================
    # SİNYAL KARARI
    # =============================
    
    if strength >= 3:
        signal_type = SignalType.SELL
    elif strength >= 2:
        signal_type = SignalType.HOLD
        reasons.insert(0, "⚠️ Dikkatli ol, stop sıkılaştır")
    else:
        return None
    
    # P&L hesapla (entry varsa)
    pnl_pct = None
    if entry_price:
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        reasons.append(f"P/L: {pnl_pct:+.1f}%")
    
    return TradingSignal(
        ticker=ticker,
        signal=signal_type,
        price=current_price,
        date=current_date,
        strength=strength,
        reasons=reasons
    )


def scan_for_signals(
    df: pd.DataFrame,
    ticker: str,
    bench_df: Optional[pd.DataFrame] = None,
    position_held: bool = False,
    entry_price: Optional[float] = None
) -> TradingSignal:
    """
    Tam sinyal taraması - AL/SAT/TUT/İZLE.
    
    Args:
        df: Hisse verisi
        ticker: Sembol
        bench_df: Benchmark verisi (SPY/XU100)
        position_held: Pozisyon var mı?
        entry_price: Giriş fiyatı (varsa)
    """
    if df.empty or len(df) < 60:
        return TradingSignal(
            ticker=ticker,
            signal=SignalType.NO_SIGNAL,
            price=0,
            date=datetime.now(),
            reasons=["Yetersiz veri"]
        )
    
    current_price = float(df["Close"].iloc[-1])
    current_date = df.index[-1]
    
    # Pozisyon yoksa: AL sinyali ara
    if not position_held:
        buy_signal = generate_buy_signal(df, ticker, bench_df)
        if buy_signal:
            return buy_signal
    
    # Pozisyon varsa: SAT sinyali ara
    else:
        sell_signal = generate_sell_signal(df, ticker, entry_price)
        if sell_signal:
            return sell_signal
        
        # Satış sinyali yoksa TUT
        return TradingSignal(
            ticker=ticker,
            signal=SignalType.HOLD,
            price=current_price,
            date=current_date,
            reasons=["Trend devam ediyor, pozisyonu tut"]
        )
    
    # Hiçbir sinyal yoksa
    return TradingSignal(
        ticker=ticker,
        signal=SignalType.NO_SIGNAL,
        price=current_price,
        date=current_date,
        reasons=["Setup oluşmadı"]
    )


def format_signal(signal: TradingSignal) -> str:
    """Sinyali güzel formatlı string olarak döndür"""
    lines = [
        f"\n{'='*50}",
        f"📊 {signal.ticker} - {signal.signal.value}",
        f"{'='*50}",
        f"Fiyat: ${signal.price:.2f}",
        f"Tarih: {signal.date.strftime('%Y-%m-%d')}",
    ]
    
    if signal.signal == SignalType.BUY:
        lines.extend([
            f"\n📍 ENTRY SEVİYELERİ:",
            f"   Giriş: ${signal.entry_price:.2f}",
            f"   Stop Loss: ${signal.stop_loss:.2f} ({signal.risk_pct:.1f}% risk)",
            f"\n🎯 HEDEFLER:",
            f"   TP1 (1R): ${signal.take_profit_1:.2f}",
            f"   TP2 (2R): ${signal.take_profit_2:.2f}",
            f"   TP3 (3R): ${signal.take_profit_3:.2f}",
            f"\n📈 R/R Oranı: {signal.reward_risk_ratio:.1f}",
        ])
    
    lines.append(f"\n💡 NEDENLER:")
    for reason in signal.reasons:
        lines.append(f"   {reason}")
    
    if signal.strength:
        lines.append(f"\n⭐ Sinyal Gücü: {'★' * signal.strength}{'☆' * (5-signal.strength)}")
    
    lines.append(f"{'='*50}\n")
    
    return "\n".join(lines)
