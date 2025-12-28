#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Daily Report Generator
================================
Generates comprehensive trading report with advanced metrics:
- Rolling Sharpe/Sortino (7-day)
- Consecutive loss streak
- Signal quality score
- Standardized JSON + Markdown output
"""

import json
import math
import os
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configuration
API_URL = "http://127.0.0.1:8080/api/v1"
USERNAME = "freqtrade"
PASSWORD = "EPAv2$Secure#2024!Trade"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
RISK_FREE_RATE = 0.0  # Annualized risk-free rate (0% for crypto)


def get_token() -> Optional[str]:
    try:
        response = requests.post(f"{API_URL}/token/login", 
            data={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return response.json().get("access_token") if response.status_code == 200 else None
    except: 
        return None


def api_get(endpoint: str, token: str) -> dict:
    try:
        return requests.get(f"{API_URL}/{endpoint}", 
            headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
    except: 
        return {}


# ============================================================================
#                       ENHANCED METRICS CALCULATIONS
# ============================================================================

def calculate_rolling_sharpe(returns: List[float], window_days: int = 7) -> Optional[float]:
    """Calculate rolling Sharpe ratio over specified window."""
    if len(returns) < 2:
        return None
    
    # Filter to window (assuming daily returns)
    window_returns = returns[-window_days:] if len(returns) >= window_days else returns
    
    if len(window_returns) < 2:
        return None
    
    mean_return = sum(window_returns) / len(window_returns)
    variance = sum((r - mean_return) ** 2 for r in window_returns) / len(window_returns)
    std_return = math.sqrt(variance) if variance > 0 else 0.0001
    
    # Annualize (assuming daily returns)
    annualized_return = mean_return * 365
    annualized_std = std_return * math.sqrt(365)
    
    sharpe = (annualized_return - RISK_FREE_RATE) / annualized_std if annualized_std > 0 else 0
    return round(sharpe, 2)


def calculate_rolling_sortino(returns: List[float], window_days: int = 7) -> Optional[float]:
    """Calculate rolling Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return None
    
    window_returns = returns[-window_days:] if len(returns) >= window_days else returns
    
    if len(window_returns) < 2:
        return None
    
    mean_return = sum(window_returns) / len(window_returns)
    
    # Downside deviation: only negative returns
    negative_returns = [r for r in window_returns if r < 0]
    if not negative_returns:
        return 10.0  # Very good - no downside
    
    downside_variance = sum(r ** 2 for r in negative_returns) / len(window_returns)
    downside_std = math.sqrt(downside_variance) if downside_variance > 0 else 0.0001
    
    # Annualize
    annualized_return = mean_return * 365
    annualized_downside = downside_std * math.sqrt(365)
    
    sortino = (annualized_return - RISK_FREE_RATE) / annualized_downside if annualized_downside > 0 else 0
    return round(min(sortino, 10.0), 2)  # Cap at 10


def calculate_consecutive_loss_streak(trades: List[dict]) -> int:
    """Calculate maximum consecutive losing trades."""
    if not trades:
        return 0
    
    max_streak = 0
    current_streak = 0
    
    for trade in trades:
        profit = trade.get("profit_abs", 0) or 0
        if profit < -0.01:  # Loss
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return max_streak


def calculate_signal_quality(trades: List[dict]) -> float:
    """Calculate signal quality: winning signals / total signals."""
    if not trades:
        return 0.0
    
    winners = sum(1 for t in trades if (t.get("profit_abs", 0) or 0) > 0.01)
    return round(winners / len(trades) * 100, 1) if trades else 0.0


# ============================================================================
#                           REPORT GENERATION
# ============================================================================

def generate_report() -> dict:
    token = get_token()
    if not token:
        return {"error": "Failed to connect to bot API"}
    
    show_config = api_get("show_config", token) or {}
    trades_data = api_get("trades", token) or {"trades": []}
    profit = api_get("profit", token) or {}
    locks = api_get("locks", token) or {"locks": []}
    status = api_get("status", token) or []
    
    now = datetime.utcnow()
    past_24h = now - timedelta(hours=24)
    past_7d = now - timedelta(days=7)
    
    wins = draws = losses = 0
    total_pnl = 0.0
    closed_today = 0
    daily_returns = []
    all_trades = []
    
    for trade in trades_data.get("trades", []):
        if trade.get("close_date"):
            try:
                close_date = datetime.fromisoformat(trade["close_date"].replace("Z", ""))
                p = trade.get("profit_abs", 0) or 0
                pct = trade.get("profit_ratio", 0) or 0
                
                all_trades.append(trade)
                
                # 7-day window for rolling metrics
                if close_date >= past_7d:
                    daily_returns.append(pct)
                
                # 24h window for daily stats
                if close_date >= past_24h:
                    closed_today += 1
                    total_pnl += p
                    if p > 0.01: wins += 1
                    elif p < -0.01: losses += 1
                    else: draws += 1
            except: 
                pass
    
    # Protection locks
    cooldown = stoploss = maxdd = 0
    for lock in locks.get("locks", []):
        reason = lock.get("reason", "").lower()
        if "cooldown" in reason: cooldown += 1
        elif "stoploss" in reason: stoploss += 1
        elif "drawdown" in reason: maxdd += 1
    
    # Calculate enhanced metrics
    rolling_sharpe = calculate_rolling_sharpe(daily_returns)
    rolling_sortino = calculate_rolling_sortino(daily_returns)
    loss_streak = calculate_consecutive_loss_streak(all_trades)
    signal_quality = calculate_signal_quality(all_trades)
    
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "strategy": show_config.get("strategy", "EPAStrategyV2"),
        "timeframe": show_config.get("timeframe", "4h"),
        "pairs": show_config.get("exchange", {}).get("pair_whitelist", []),
        
        # Basic stats
        "total_trades": profit.get("trade_count", 0),
        "trades_today": closed_today,
        "open_trades": len(status),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": round(wins / closed_today * 100, 1) if closed_today else 0,
        
        # P&L
        "total_pnl_usdt": round(total_pnl, 2),
        "cumulative_pnl_usdt": round(profit.get("profit_closed_coin", 0), 2),
        "cumulative_pnl_pct": round(profit.get("profit_closed_percent", 0), 2),
        "max_drawdown": round(profit.get("max_drawdown", 0) * 100, 2) if profit.get("max_drawdown") else 0,
        
        # Enhanced metrics (NEW)
        "metrics": {
            "rolling_sharpe_7d": rolling_sharpe,
            "rolling_sortino_7d": rolling_sortino,
            "consecutive_loss_streak": loss_streak,
            "signal_quality_pct": signal_quality
        },
        
        # Protections
        "protections_triggered": {
            "CooldownPeriod": cooldown,
            "StoplossGuard": stoploss,
            "MaxDrawdown": maxdd
        }
    }
    return report


def print_table(r: dict):
    """Print formatted report to console."""
    print("\n" + "=" * 60)
    print(f"📊 DAILY REPORT | {r.get('date', 'N/A')}")
    print("=" * 60)
    print(f"Strategy: {r.get('strategy')} | TF: {r.get('timeframe')}")
    print(f"Pairs: {', '.join(r.get('pairs', []))}")
    print("-" * 60)
    print(f"Trades Today: {r.get('trades_today')} | Open: {r.get('open_trades')}")
    print(f"W/D/L: {r.get('wins')}/{r.get('draws')}/{r.get('losses')} ({r.get('win_rate'):.1f}%)")
    print(f"PnL Today: {r.get('total_pnl_usdt'):+.2f} USDT")
    print(f"Cumulative: {r.get('cumulative_pnl_usdt'):+.2f} USDT ({r.get('cumulative_pnl_pct'):+.2f}%)")
    print("-" * 60)
    
    # Enhanced metrics
    m = r.get("metrics", {})
    print("📈 QUALITY METRICS:")
    print(f"  Rolling Sharpe (7d): {m.get('rolling_sharpe_7d', 'N/A')}")
    print(f"  Rolling Sortino (7d): {m.get('rolling_sortino_7d', 'N/A')}")
    print(f"  Max Loss Streak: {m.get('consecutive_loss_streak', 0)}")
    print(f"  Signal Quality: {m.get('signal_quality_pct', 0):.1f}%")
    print("-" * 60)
    
    prots = r.get("protections_triggered", {})
    print(f"Protections: CD={prots.get('CooldownPeriod',0)} | SG={prots.get('StoplossGuard',0)} | MD={prots.get('MaxDrawdown',0)}")
    print("=" * 60)


def generate_markdown(r: dict) -> str:
    """Generate standardized markdown report."""
    m = r.get("metrics", {})
    prots = r.get("protections_triggered", {})
    
    md = f"""# 📊 Daily Report - {r.get('date', 'N/A')}

## Strategy Info
- **Strategy**: {r.get('strategy')}
- **Timeframe**: {r.get('timeframe')}
- **Pairs**: {', '.join(r.get('pairs', []))}

## Performance (24h)
| Metric | Value |
|--------|-------|
| Trades Today | {r.get('trades_today')} |
| Open Trades | {r.get('open_trades')} |
| Win Rate | {r.get('win_rate'):.1f}% |
| PnL Today | {r.get('total_pnl_usdt'):+.2f} USDT |
| Cumulative PnL | {r.get('cumulative_pnl_usdt'):+.2f} USDT ({r.get('cumulative_pnl_pct'):+.2f}%) |
| Max Drawdown | {r.get('max_drawdown'):.2f}% |

## Quality Metrics (7-day rolling)
| Metric | Value | Status |
|--------|-------|--------|
| Sharpe Ratio | {m.get('rolling_sharpe_7d', 'N/A')} | {'✅' if (m.get('rolling_sharpe_7d') or 0) > 1 else '⚠️'} |
| Sortino Ratio | {m.get('rolling_sortino_7d', 'N/A')} | {'✅' if (m.get('rolling_sortino_7d') or 0) > 1.5 else '⚠️'} |
| Max Loss Streak | {m.get('consecutive_loss_streak', 0)} | {'✅' if m.get('consecutive_loss_streak', 0) < 4 else '⚠️'} |
| Signal Quality | {m.get('signal_quality_pct', 0):.1f}% | {'✅' if m.get('signal_quality_pct', 0) > 50 else '⚠️'} |

## Protections Triggered
- CooldownPeriod: {prots.get('CooldownPeriod', 0)}
- StoplossGuard: {prots.get('StoplossGuard', 0)}
- MaxDrawdown: {prots.get('MaxDrawdown', 0)}

---
*Generated: {r.get('timestamp')}*
"""
    return md


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    report = generate_report()
    
    if "error" in report:
        print(f"[ERROR] {report['error']}")
        sys.exit(1)
    
    # Save JSON
    json_file = REPORTS_DIR / f"{report['date']}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[OK] JSON saved: {json_file}")
    
    # Save Markdown
    md_file = REPORTS_DIR / f"{report['date']}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(generate_markdown(report))
    print(f"[OK] Markdown saved: {md_file}")
    
    # Console output
    print("\n[JSON OUTPUT]")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print_table(report)


if __name__ == "__main__":
    main()
