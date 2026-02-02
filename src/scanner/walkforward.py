"""
Walk-Forward Backtester

"Geçmişte şov yapıp gelecekte ağlatan sistemleri" elemek için:
- Rolling out-of-sample (OOS) test
- Train/test split her pencerede
- Sadece OOS performansı say

Overfit'in panzehiri budur.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from .strategy import (
    StrategyParams, BacktestConfig, 
    run_backtest, DEFAULT_PARAM_GRID, build_signals
)


@dataclass
class WalkForwardConfig:
    """Walk-forward ayarları"""
    train_days: int = 200      # ~10 ay train (kısaltıldı)
    test_days: int = 50        # ~2 ay test (OOS)
    step_days: int = 50        # Kaydırma
    warmup_days: int = 60      # İlk N gün = indicator hesabı için
    min_windows: int = 2       # Minimum pencere sayısı (gevşetildi)
    min_trades: int = 2        # Minimum toplam trade (gevşetildi)


def run_backtest_with_params(
    df: pd.DataFrame,
    config: BacktestConfig,
    params: StrategyParams
) -> Dict[str, float]:
    """Parametre ile backtest (strategy.py'deki wrapper)"""
    return run_backtest(df, config, params)


def walk_forward_oos(
    df: pd.DataFrame,
    bt_config: BacktestConfig,
    wf_config: Optional[WalkForwardConfig] = None,
    param_grid: Optional[List[StrategyParams]] = None,
) -> Dict[str, float]:
    """
    Rolling Walk-Forward Out-of-Sample Test.
    
    Her pencerede:
    1. Train periyodunda param seç (basit grid)
    2. Test periyodunda backtest yap (OOS)
    3. OOS sonuçlarını biriktir
    
    Neden önemli?
    - Tek seferlik full backtest = overfit riski yüksek
    - Walk-forward = "görülmemiş veri" performansı
    
    Returns:
        Dict with OOS metrics
    """
    if wf_config is None:
        wf_config = WalkForwardConfig()
    
    if param_grid is None:
        param_grid = DEFAULT_PARAM_GRID
    
    total_required = wf_config.warmup_days + wf_config.train_days + wf_config.test_days
    
    if df.empty or len(df) < total_required:
        return _empty_wf_result()
    
    # Sorted index
    df = df.sort_index()
    
    # Starting point
    start = wf_config.warmup_days
    end = len(df)
    
    # Cumulative OOS tracking
    oos_equity = bt_config.initial_capital
    oos_peak = oos_equity
    oos_dd = 0.0
    oos_trades = 0.0
    oos_wins = 0.0
    windows = 0
    
    window_results: List[Dict] = []
    
    i = start
    while i + wf_config.train_days + wf_config.test_days <= end:
        train_start = i
        train_end = i + wf_config.train_days
        test_start = train_end
        test_end = test_start + wf_config.test_days
        
        train_df = df.iloc[train_start:train_end].copy()
        test_df = df.iloc[test_start:test_end].copy()
        
        # =====================
        # TRAIN: Param selection
        # =====================
        best_params = param_grid[0]
        best_score = -1e9
        
        for p in param_grid:
            stats = run_backtest_with_params(train_df, bt_config, p)
            
            # Minimum trade şartı
            if stats["trades"] < 2:
                continue
            
            # Score: return - DD penalty
            score = stats["total_return"] - (abs(stats["max_drawdown"]) * 0.7)
            
            if score > best_score:
                best_score = score
                best_params = p
        
        # =====================
        # TEST: Out-of-sample
        # =====================
        oos_stats = run_backtest_with_params(test_df, bt_config, best_params)
        
        # Compound OOS equity
        oos_equity *= (1.0 + oos_stats["total_return"])
        oos_peak = max(oos_peak, oos_equity)
        oos_dd = min(oos_dd, (oos_equity / oos_peak) - 1.0)
        
        oos_trades += oos_stats["trades"]
        oos_wins += oos_stats["trades"] * oos_stats["winrate"]
        
        window_results.append({
            "window": windows + 1,
            "train_start": df.index[train_start],
            "test_start": df.index[test_start],
            "test_end": df.index[test_end - 1],
            "params": best_params,
            "oos_return": oos_stats["total_return"],
            "oos_trades": oos_stats["trades"],
        })
        
        windows += 1
        i += wf_config.step_days
    
    # Final metrics
    total_oos_return = (oos_equity / bt_config.initial_capital) - 1.0
    overall_winrate = (oos_wins / oos_trades) if oos_trades > 0 else 0.0
    
    return {
        "oos_return": float(total_oos_return),
        "oos_max_drawdown": float(oos_dd),
        "oos_trades": float(oos_trades),
        "oos_winrate": float(overall_winrate),
        "windows": float(windows),
        "final_equity": float(oos_equity),
        "window_details": window_results,
    }


def _empty_wf_result() -> Dict:
    """Boş walk-forward sonucu"""
    return {
        "oos_return": 0.0,
        "oos_max_drawdown": 0.0,
        "oos_trades": 0.0,
        "oos_winrate": 0.0,
        "windows": 0.0,
        "final_equity": 0.0,
        "window_details": [],
    }


def is_valid_wf_result(result: Dict, min_windows: int = 3, min_trades: int = 4) -> bool:
    """Walk-forward sonucu geçerli mi?"""
    return (
        result["windows"] >= min_windows and
        result["oos_trades"] >= min_trades
    )


def calculate_wf_score(result: Dict) -> float:
    """
    Walk-forward score hesapla.
    
    Sıralama için kullanılır:
    - OOS return yüksek = iyi
    - Max drawdown düşük = iyi
    - Winrate yüksek = bonus
    """
    if not is_valid_wf_result(result):
        return -1e9
    
    return (
        result["oos_return"] * 100  # Return ağırlık
        - abs(result["oos_max_drawdown"]) * 80  # DD ceza
        + result["oos_winrate"] * 10  # Winrate bonus
    )
