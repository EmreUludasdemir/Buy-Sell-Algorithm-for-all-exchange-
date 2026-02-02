"""
Strateji ve Backtest Engine

Lone Stock Trader kuralları:
- Entry: Donchian breakout + MA stack bullish + squeeze açılımı
- Exit: Close < MA20 (trailing stop gibi çalışır)
- Risk: Stop = base altı veya 2*ATR
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from .indicators import (
    sma, atr, donchian_high, donchian_low,
    ma_stack_bullish_series
)


@dataclass(frozen=True)
class StrategyParams:
    """
    Strateji parametreleri.
    
    Walk-forward'da küçük grid ile optimize edilebilir,
    ama overfit'e kaçmamak için sınırlı tutuyoruz.
    """
    donchian_w: int = 20      # Breakout penceresi
    exit_ma: int = 20         # Çıkış MA'sı
    ma_fast: int = 10         # Hızlı MA
    ma_mid: int = 20          # Orta MA  
    ma_slow: int = 50         # Yavaş MA
    atr_stop_mult: float = 2.0  # ATR çarpanı (stop için)
    use_trailing: bool = True   # Trailing stop kullan


@dataclass
class BacktestConfig:
    """Backtest ayarları"""
    fee_bps: float = 10.0        # Komisyon (0.10% = 10 bps)
    slippage_bps: float = 5.0    # Kayma (0.05%)
    initial_capital: float = 100_000.0
    position_size_pct: float = 1.0  # Sermayenin %'si (1.0 = full)


def build_signals(
    df: pd.DataFrame, 
    params: StrategyParams
) -> Tuple[pd.Series, pd.Series]:
    """
    Entry/Exit sinyalleri üret.
    
    Entry: 
        - Close, önceki Donchian High'ı kırsın
        - MA stack bullish olsun (10>20>50 ve fiyat 20 üstü)
    
    Exit:
        - Close < MA(exit_ma)
    """
    c = df["Close"]
    
    # Donchian Channel
    dc_high = donchian_high(df, params.donchian_w)
    
    # Exit MA
    exit_ma = sma(c, params.exit_ma)
    
    # MA Stack
    ma_fast = sma(c, params.ma_fast)
    ma_mid = sma(c, params.ma_mid)
    ma_slow = sma(c, params.ma_slow)
    
    bullish_stack = (ma_fast > ma_mid) & (ma_mid > ma_slow) & (c > ma_mid)
    
    # Entry: Breakout + Bullish
    entry = (c > dc_high.shift(1)) & bullish_stack
    
    # Exit: Close < exit MA
    exit_ = (c < exit_ma)
    
    return entry.fillna(False), exit_.fillna(False)


def run_backtest(
    df: pd.DataFrame,
    config: BacktestConfig,
    params: Optional[StrategyParams] = None
) -> Dict[str, float]:
    """
    Basit long-only backtest.
    
    - Tek pozisyon (bir seferde 1 trade)
    - Komisyon ve slippage dahil
    - Drawdown takibi
    
    Returns:
        Dict with metrics: total_return, max_drawdown, trades, winrate, avg_trade
    """
    if params is None:
        params = StrategyParams()
    
    entry, exit_ = build_signals(df, params)
    c = df["Close"]
    
    if c.empty:
        return _empty_result()
    
    in_pos = False
    entry_price = 0.0
    equity = config.initial_capital
    peak = equity
    dd = 0.0
    
    trades = 0
    wins = 0
    pnl_list: List[float] = []
    
    fee = config.fee_bps / 10_000.0
    slip = config.slippage_bps / 10_000.0
    
    for i in range(len(df)):
        price = float(c.iloc[i])
        
        # Entry
        if (not in_pos) and entry.iloc[i]:
            in_pos = True
            entry_price = price * (1 + slip)  # Kötü dolum
            equity *= (1 - fee)
            trades += 1
        
        # Exit
        elif in_pos and exit_.iloc[i]:
            exit_price = price * (1 - slip)  # Kötü dolum
            trade_return = exit_price / entry_price
            equity *= trade_return
            equity *= (1 - fee)
            
            pnl = trade_return - 1
            pnl_list.append(pnl)
            if pnl > 0:
                wins += 1
            
            in_pos = False
        
        # Drawdown tracking
        peak = max(peak, equity)
        dd = min(dd, (equity / peak) - 1)
    
    # Pozisyon açıksa kapat
    if in_pos:
        exit_price = float(c.iloc[-1]) * (1 - slip)
        trade_return = exit_price / entry_price
        equity *= trade_return
        equity *= (1 - fee)
        
        pnl = trade_return - 1
        pnl_list.append(pnl)
        if pnl > 0:
            wins += 1
    
    total_return = (equity / config.initial_capital) - 1
    winrate = (wins / trades) if trades > 0 else 0.0
    avg_trade = float(np.mean(pnl_list)) if pnl_list else 0.0
    
    return {
        "total_return": float(total_return),
        "max_drawdown": float(dd),
        "trades": float(trades),
        "winrate": float(winrate),
        "avg_trade": float(avg_trade),
        "final_equity": float(equity),
    }


def _empty_result() -> Dict[str, float]:
    """Boş sonuç (veri yoksa)"""
    return {
        "total_return": 0.0,
        "max_drawdown": 0.0,
        "trades": 0.0,
        "winrate": 0.0,
        "avg_trade": 0.0,
        "final_equity": 0.0,
    }


# ============================================================================
# PARAM GRID (Walk-forward için)
# ============================================================================

DEFAULT_PARAM_GRID = [
    StrategyParams(20, 20, 10, 20, 50),  # Default
    StrategyParams(20, 30, 10, 20, 50),  # Daha geç çıkış
    StrategyParams(15, 20, 10, 20, 50),  # Daha erken breakout
    StrategyParams(20, 20, 8, 21, 55),   # Alternatif MA'lar
    StrategyParams(25, 20, 10, 20, 50),  # Daha geç breakout
    StrategyParams(20, 15, 10, 20, 50),  # Daha erken çıkış (agresif)
]
