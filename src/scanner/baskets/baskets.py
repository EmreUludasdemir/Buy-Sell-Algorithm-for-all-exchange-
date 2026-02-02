"""
Basket/Tema Yönetimi

"Hisseler yalnız koşmaz, tema iter."

Basket momentum kontrolü:
- %members_above_50MA >= 60%
- Median RS slope pozitif
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import yaml
import os

from ..indicators import sma, rs_series, slope_last
from ..providers import DataProvider


@dataclass
class BasketMetrics:
    """Basket momentum metrikleri"""
    name: str
    members: List[str]
    pct_above_50ma: float
    median_rs_slope: float
    median_return_20d: float
    is_strong: bool


def load_baskets(filepath: str) -> Dict[str, List[str]]:
    """YAML'dan basket yükle"""
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_baskets(baskets: Dict[str, List[str]], filepath: str):
    """Basket'leri YAML'a kaydet"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(baskets, f, default_flow_style=False, allow_unicode=True)


def calculate_basket_metrics(
    basket_name: str,
    members: List[str],
    provider: DataProvider,
    benchmark: str = "SPY"
) -> Optional[BasketMetrics]:
    """
    Basket momentum hesapla.
    
    Güçlü basket kriterleri:
    - %60+ üye 50MA üstünde
    - Median RS slope pozitif
    """
    if not members:
        return None
    
    bench_df = provider.fetch(benchmark)
    if bench_df.empty:
        return None
    
    above_50ma_count = 0
    rs_slopes = []
    returns_20d = []
    valid_members = 0
    
    for ticker in members:
        df = provider.fetch(ticker)
        if df.empty or len(df) < 60:
            continue
        
        valid_members += 1
        c = df["Close"]
        
        # 50MA kontrolü
        ma50 = sma(c, 50)
        if not pd.isna(ma50.iloc[-1]) and c.iloc[-1] > ma50.iloc[-1]:
            above_50ma_count += 1
        
        # RS slope
        rs = rs_series(c, bench_df["Close"])
        rs_s = slope_last(rs, 20)
        if not np.isnan(rs_s):
            rs_slopes.append(rs_s)
        
        # 20 günlük return
        if len(c) >= 20:
            ret = (c.iloc[-1] / c.iloc[-20]) - 1
            returns_20d.append(ret)
    
    if valid_members == 0:
        return None
    
    pct_above = above_50ma_count / valid_members
    median_rs = float(np.median(rs_slopes)) if rs_slopes else 0.0
    median_ret = float(np.median(returns_20d)) if returns_20d else 0.0
    
    # Güçlü basket: %60+ above 50MA VE RS slope pozitif
    is_strong = (pct_above >= 0.6) and (median_rs > 0)
    
    return BasketMetrics(
        name=basket_name,
        members=members,
        pct_above_50ma=pct_above,
        median_rs_slope=median_rs,
        median_return_20d=median_ret,
        is_strong=is_strong
    )


def get_strong_baskets(
    baskets: Dict[str, List[str]],
    provider: DataProvider,
    benchmark: str = "SPY"
) -> List[BasketMetrics]:
    """Güçlü basket'leri döndür"""
    strong = []
    
    for name, members in baskets.items():
        metrics = calculate_basket_metrics(name, members, provider, benchmark)
        if metrics and metrics.is_strong:
            strong.append(metrics)
    
    return strong


def get_leaders_from_basket(
    basket: BasketMetrics,
    provider: DataProvider,
    benchmark: str = "SPY",
    top_n: int = 3
) -> List[str]:
    """
    Basket'in liderlerini döndür (RS en yüksek).
    
    "Sen lideri al" kuralı.
    """
    bench_df = provider.fetch(benchmark)
    if bench_df.empty:
        return []
    
    scores = []
    
    for ticker in basket.members:
        df = provider.fetch(ticker)
        if df.empty or len(df) < 60:
            continue
        
        rs = rs_series(df["Close"], bench_df["Close"])
        rs_s = slope_last(rs, 20)
        
        if not np.isnan(rs_s):
            scores.append((ticker, rs_s))
    
    # RS'e göre sırala
    scores.sort(key=lambda x: x[1], reverse=True)
    
    return [t for t, _ in scores[:top_n]]


# ============================================================================
# DEFAULT BASKETS
# ============================================================================

DEFAULT_US_BASKETS = {
    "quantum_computing": ["RGTI", "IONQ", "QBTS", "QUBT"],
    "crypto_miners": ["MARA", "RIOT", "CLSK", "HUT", "BTBT"],
    "ai_chips": ["NVDA", "AMD", "SMCI", "AVGO", "MRVL"],
    "ev_auto": ["TSLA", "RIVN", "LCID", "NIO", "XPEV"],
    "cybersecurity": ["CRWD", "PANW", "ZS", "FTNT", "S"],
    "biotech": ["MRNA", "BNTX", "NVAX", "REGN", "VRTX"],
    "fintech": ["COIN", "SQ", "PYPL", "AFRM", "SOFI"],
    "cloud": ["SNOW", "DDOG", "NET", "MDB", "PLTR"],
}

DEFAULT_BIST_BASKETS = {
    "savunma": ["ASELS.IS", "ASELSAN.IS"],
    "bankalar": ["AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "GARAN.IS", "VAKBN.IS"],
    "holding": ["KCHOL.IS", "SAHOL.IS", "DOHOL.IS", "SISE.IS"],
    "havayolu": ["THYAO.IS", "PGSUS.IS"],
    "perakende": ["BIMAS.IS", "MGROS.IS", "BIZIM.IS"],
    "enerji": ["TUPRS.IS", "PETKM.IS", "AYGAZ.IS"],
}


def create_default_baskets_file(filepath: str, market: str = "us"):
    """Default basket dosyası oluştur"""
    baskets = DEFAULT_US_BASKETS if market.lower() == "us" else DEFAULT_BIST_BASKETS
    save_baskets(baskets, filepath)
