"""
Scanner - Ana Tarama Modülü

Lone Stock Trader'ın tüm kurallarını uygular:
A) Eleme: ADR/ATR/Likidite
B) Tema/Basket: Grup rüzgârı
C) Lider seçimi: RS
D) Yapı: Base/Squeeze/Breakout
E) Walk-forward: OOS test
F) Skor ve sırala
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import logging

from .indicators import (
    adr_pct, atr_pct, avg_volume,
    rs_series, slope_last, rs_above_ma, relative_performance,
    ma_squeeze_value, ma_stack_bullish, ma_slopes_positive,
    weekly_base_score, weekly_volatility_contracting,
    is_breakout, volume_breakout, up_down_volume_ratio,
    near_52w_high, pct_from_52w_high
)
from .providers import DataProvider, YahooProvider
from .strategy import BacktestConfig
from .walkforward import (
    WalkForwardConfig, walk_forward_oos, 
    is_valid_wf_result, calculate_wf_score
)


logger = logging.getLogger(__name__)


@dataclass
class ScanConfig:
    """
    Tarama filtreleri - Thread'deki kurallar.
    
    Her değer "ölçülebilir kural" karşılığı.
    
    PRESET'ler:
    - aggressive: Orijinal thread değerleri (küçük hisseler için)
    - balanced: Büyük+küçük karışık  
    - conservative: Sadece likid, büyük hisseler
    """
    # A) Volatilite filtreleri
    adr_min: float = 1.5           # ADR% >= 1.5 (daha geniş)
    atr_min: float = 1.5           # ATR% >= 1.5 (daha geniş)
    avg_vol_min: float = 500_000   # Likidite (ABD için 500K)
    
    # B) Relative Strength
    rs_slope_min: float = -0.005   # RS eğimi (negatif kabul, piyasa düzeltmesi için)
    rs_above_50ma: bool = False    # RS line 50MA üstünde (relaxed)
    outperform_days: int = 60      # Son N günde benchmark'ı geç
    
    # C) Yapı filtreleri
    squeeze_max: float = 0.15      # MA squeeze <= %15 (çok relaxed)
    base_score_min: float = 0.2    # Haftalık base kalitesi (relaxed)
    require_ma_stack: bool = False # Bullish MA stack şart mı? (relaxed)
    
    # D) Opsiyonel sıkı filtreler
    require_breakout: bool = False     # Bugün breakout mu?
    require_volume_breakout: bool = False  # Hacim spike?
    near_52w_high_threshold: float = 0.15  # %15 içinde
    
    # E) Skor ağırlıkları
    weight_rs: float = 30.0
    weight_adr: float = 15.0
    weight_squeeze: float = 20.0
    weight_base: float = 15.0
    weight_wf: float = 20.0  # Walk-forward sonucu


@dataclass
class ScanResult:
    """Tek hisse için tarama sonucu"""
    ticker: str
    passed: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    fail_reason: str = ""
    wf_result: Optional[Dict] = None


def passes_filters(
    df: pd.DataFrame,
    bench_df: pd.DataFrame,
    cfg: ScanConfig
) -> Tuple[bool, Dict[str, float], str]:
    """
    Tüm filtreleri uygula.
    
    Returns:
        (passed, metrics_dict, fail_reason)
    """
    metrics: Dict[str, float] = {}
    
    # Minimum veri kontrolü
    if df.empty or len(df) < 250:
        return False, metrics, "yetersiz_veri"
    
    if bench_df.empty or len(bench_df) < 250:
        return False, metrics, "benchmark_verisi_yok"
    
    # =====================
    # A) VOLATİLİTE + LİKİDİTE
    # =====================
    
    adr = adr_pct(df, 20)
    metrics["adr_pct"] = adr
    if adr < cfg.adr_min:
        return False, metrics, f"adr_düşük_{adr:.1f}"
    
    atrp = atr_pct(df, 14)
    metrics["atr_pct"] = atrp
    if atrp < cfg.atr_min:
        return False, metrics, f"atr_düşük_{atrp:.1f}"
    
    vol = avg_volume(df, 20)
    metrics["avg_volume"] = vol
    if vol < cfg.avg_vol_min:
        return False, metrics, f"likidite_düşük"
    
    # =====================
    # B) RELATIVE STRENGTH (LİDERLİK)
    # =====================
    
    rs = rs_series(df["Close"], bench_df["Close"])
    rs_s = slope_last(rs, 20)
    metrics["rs_slope"] = rs_s if not np.isnan(rs_s) else 0.0
    
    if np.isnan(rs_s) or rs_s <= cfg.rs_slope_min:
        return False, metrics, "rs_zayıf"
    
    if cfg.rs_above_50ma:
        if not rs_above_ma(df["Close"], bench_df["Close"], 50):
            return False, metrics, "rs_50ma_altı"
    
    rel_perf = relative_performance(df, bench_df, cfg.outperform_days)
    metrics["relative_perf_60d"] = rel_perf if not np.isnan(rel_perf) else 0.0
    
    # =====================
    # C) YAPI (SQUEEZE + BASE)
    # =====================
    
    sq = ma_squeeze_value(df)
    metrics["ma_squeeze"] = sq if not np.isnan(sq) else 1.0
    
    if np.isnan(sq) or sq > cfg.squeeze_max:
        return False, metrics, f"squeeze_yok_{sq:.2f}"
    
    if cfg.require_ma_stack:
        if not ma_stack_bullish(df):
            return False, metrics, "ma_stack_bearish"
    
    base = weekly_base_score(df)
    metrics["base_score"] = base if not np.isnan(base) else 0.0
    
    if np.isnan(base) or base < cfg.base_score_min:
        return False, metrics, f"base_zayıf_{base:.2f}"
    
    # =====================
    # D) OPSİYONEL SIKIT FİLTRELER
    # =====================
    
    if cfg.require_breakout:
        if not is_breakout(df, 20):
            return False, metrics, "breakout_yok"
    
    if cfg.require_volume_breakout:
        if not volume_breakout(df, 1.5):
            return False, metrics, "hacim_breakout_yok"
    
    # 52w high proximity
    pct_52w = pct_from_52w_high(df)
    metrics["pct_from_52w_high"] = pct_52w if not np.isnan(pct_52w) else -100.0
    
    # =====================
    # EK METRİKLER (skor için)
    # =====================
    
    metrics["up_down_vol_ratio"] = up_down_volume_ratio(df, 20)
    metrics["ma_slopes_positive"] = 1.0 if ma_slopes_positive(df, 5) else 0.0
    metrics["vol_contracting"] = 1.0 if weekly_volatility_contracting(df, 8) else 0.0
    
    return True, metrics, ""


def calculate_score(metrics: Dict[str, float], cfg: ScanConfig) -> float:
    """
    Skor hesapla (sıralama için).
    
    Yüksek skor = daha iyi aday.
    """
    score = 0.0
    
    # RS (liderlik)
    rs_slope = metrics.get("rs_slope", 0.0)
    score += rs_slope * 1000 * cfg.weight_rs / 30
    
    # ADR (volatilite)
    adr = metrics.get("adr_pct", 0.0)
    score += adr * cfg.weight_adr / 15
    
    # Squeeze (düşük = iyi)
    squeeze = metrics.get("ma_squeeze", 1.0)
    squeeze_score = max(0, (cfg.squeeze_max - squeeze) * 100)
    score += squeeze_score * cfg.weight_squeeze / 20
    
    # Base (yüksek = iyi)
    base = metrics.get("base_score", 0.0)
    score += base * 10 * cfg.weight_base / 15
    
    # Relative performance bonus
    rel_perf = metrics.get("relative_perf_60d", 0.0)
    if rel_perf > 0:
        score += rel_perf * 5
    
    # Volume pattern bonus
    up_down = metrics.get("up_down_vol_ratio", 1.0)
    if up_down > 1.2:
        score += 2.0
    
    return score


def scan_single(
    ticker: str,
    df: pd.DataFrame,
    bench_df: pd.DataFrame,
    scan_cfg: ScanConfig,
    bt_cfg: Optional[BacktestConfig] = None,
    wf_cfg: Optional[WalkForwardConfig] = None,
    run_walkforward: bool = True
) -> ScanResult:
    """
    Tek hisse tara + (opsiyonel) walk-forward test.
    """
    # Filtreleme
    passed, metrics, fail_reason = passes_filters(df, bench_df, scan_cfg)
    
    if not passed:
        return ScanResult(
            ticker=ticker,
            passed=False,
            metrics=metrics,
            score=0.0,
            fail_reason=fail_reason
        )
    
    # Skor (filtre sonrası)
    score = calculate_score(metrics, scan_cfg)
    
    # Walk-forward (opsiyonel)
    wf_result = None
    if run_walkforward and bt_cfg is not None:
        if wf_cfg is None:
            wf_cfg = WalkForwardConfig()
        
        wf_result = walk_forward_oos(df, bt_cfg, wf_cfg)
        
        if is_valid_wf_result(wf_result):
            wf_score = calculate_wf_score(wf_result)
            score += wf_score * scan_cfg.weight_wf / 20
            metrics["wf_oos_return"] = wf_result["oos_return"]
            metrics["wf_max_dd"] = wf_result["oos_max_drawdown"]
            metrics["wf_trades"] = wf_result["oos_trades"]
        else:
            # Walk-forward başarısız = düş
            passed = False
            fail_reason = "wf_yetersiz"
    
    return ScanResult(
        ticker=ticker,
        passed=passed,
        metrics=metrics,
        score=score,
        fail_reason=fail_reason,
        wf_result=wf_result
    )


def run_scan(
    tickers: List[str],
    benchmark: str,
    provider: DataProvider,
    scan_cfg: Optional[ScanConfig] = None,
    bt_cfg: Optional[BacktestConfig] = None,
    wf_cfg: Optional[WalkForwardConfig] = None,
    run_walkforward: bool = True,
    top_n: int = 20,
    verbose: bool = True
) -> List[str]:
    """
    Tam tarama: filtre + walk-forward + sıralama.
    
    Returns:
        Top N ticker listesi (sadece semboller).
    """
    if scan_cfg is None:
        scan_cfg = ScanConfig()
    
    if bt_cfg is None:
        bt_cfg = BacktestConfig()
    
    # Benchmark verisi
    if verbose:
        logger.info(f"Benchmark çekiliyor: {benchmark}")
    bench_df = provider.fetch(benchmark)
    
    if bench_df.empty:
        logger.error(f"Benchmark verisi alınamadı: {benchmark}")
        return []
    
    # Tüm hisseleri tara
    results: List[ScanResult] = []
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        if verbose:
            logger.info(f"[{i+1}/{total}] {ticker}")
        
        df = provider.fetch(ticker)
        
        if df.empty:
            continue
        
        result = scan_single(
            ticker=ticker,
            df=df,
            bench_df=bench_df,
            scan_cfg=scan_cfg,
            bt_cfg=bt_cfg,
            wf_cfg=wf_cfg,
            run_walkforward=run_walkforward
        )
        
        results.append(result)
        
        if verbose and result.passed:
            logger.info(f"  ✓ PASSED - Score: {result.score:.2f}")
        elif verbose:
            logger.debug(f"  ✗ Failed: {result.fail_reason}")
    
    # Geçenleri filtrele ve sırala
    passed = [r for r in results if r.passed]
    passed.sort(key=lambda x: x.score, reverse=True)
    
    # Top N ticker döndür
    return [r.ticker for r in passed[:top_n]]


def run_scan_detailed(
    tickers: List[str],
    benchmark: str,
    provider: DataProvider,
    scan_cfg: Optional[ScanConfig] = None,
    bt_cfg: Optional[BacktestConfig] = None,
    wf_cfg: Optional[WalkForwardConfig] = None,
    run_walkforward: bool = True,
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Detaylı tarama sonucu (DataFrame olarak).
    
    Metrikleri de görmek isteyenler için.
    """
    if scan_cfg is None:
        scan_cfg = ScanConfig()
    
    if bt_cfg is None:
        bt_cfg = BacktestConfig()
    
    bench_df = provider.fetch(benchmark)
    
    if bench_df.empty:
        return pd.DataFrame()
    
    rows = []
    
    for ticker in tickers:
        df = provider.fetch(ticker)
        
        if df.empty:
            continue
        
        result = scan_single(
            ticker=ticker,
            df=df,
            bench_df=bench_df,
            scan_cfg=scan_cfg,
            bt_cfg=bt_cfg,
            wf_cfg=wf_cfg,
            run_walkforward=run_walkforward
        )
        
        row = {"ticker": ticker, "passed": result.passed, "score": result.score}
        row.update(result.metrics)
        row["fail_reason"] = result.fail_reason
        rows.append(row)
    
    df_out = pd.DataFrame(rows)
    
    if not df_out.empty:
        df_out = df_out.sort_values("score", ascending=False)
    
    return df_out.head(top_n) if top_n > 0 else df_out
