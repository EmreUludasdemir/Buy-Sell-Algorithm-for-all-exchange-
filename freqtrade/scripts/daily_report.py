#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Daily Report Generator with JSON Save
===============================================
"""

import json
import os
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configuration
API_URL = "http://127.0.0.1:8080/api/v1"
USERNAME = "freqtrade"
PASSWORD = "EPAv2$Secure#2024!Trade"
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def get_token():
    try:
        response = requests.post(f"{API_URL}/token/login", 
            data={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return response.json().get("access_token") if response.status_code == 200 else None
    except: return None


def api_get(endpoint, token):
    try:
        return requests.get(f"{API_URL}/{endpoint}", 
            headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
    except: return {}


def generate_report():
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
    
    wins = draws = losses = 0
    total_pnl = 0.0
    closed_today = 0
    
    for trade in trades_data.get("trades", []):
        if trade.get("close_date"):
            try:
                close_date = datetime.fromisoformat(trade["close_date"].replace("Z", ""))
                if close_date >= past_24h:
                    closed_today += 1
                    p = trade.get("profit_abs", 0) or 0
                    total_pnl += p
                    if p > 0.01: wins += 1
                    elif p < -0.01: losses += 1
                    else: draws += 1
            except: pass
    
    cooldown = stoploss = maxdd = 0
    for lock in locks.get("locks", []):
        reason = lock.get("reason", "").lower()
        if "cooldown" in reason: cooldown += 1
        elif "stoploss" in reason: stoploss += 1
        elif "drawdown" in reason: maxdd += 1
    
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "strategy": show_config.get("strategy", "EPAStrategyV2"),
        "timeframe": show_config.get("timeframe", "15m"),
        "pairs": show_config.get("exchange", {}).get("pair_whitelist", []),
        "total_trades": profit.get("trade_count", 0),
        "trades_today": closed_today,
        "open_trades": len(status),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": round(wins / closed_today * 100, 1) if closed_today else 0,
        "total_pnl_usdt": round(total_pnl, 2),
        "cumulative_pnl_usdt": round(profit.get("profit_closed_coin", 0), 2),
        "cumulative_pnl_pct": round(profit.get("profit_closed_percent", 0), 2),
        "max_drawdown": round(profit.get("max_drawdown", 0) * 100, 2) if profit.get("max_drawdown") else 0,
        "protections_triggered": {
            "CooldownPeriod": cooldown,
            "StoplossGuard": stoploss,
            "MaxDrawdown": maxdd
        }
    }
    return report


def print_table(r):
    print("\n" + "=" * 55)
    print("[DAILY REPORT]", r.get("date", "N/A"))
    print("=" * 55)
    print(f"Strategy: {r.get('strategy')} | TF: {r.get('timeframe')}")
    print(f"Pairs: {', '.join(r.get('pairs', []))}")
    print("-" * 55)
    print(f"Trades Today: {r.get('trades_today')} | Open: {r.get('open_trades')}")
    print(f"W/D/L: {r.get('wins')}/{r.get('draws')}/{r.get('losses')} ({r.get('win_rate'):.1f}%)")
    print(f"PnL Today: {r.get('total_pnl_usdt'):+.2f} USDT")
    print(f"Cumulative: {r.get('cumulative_pnl_usdt'):+.2f} USDT ({r.get('cumulative_pnl_pct'):+.2f}%)")
    print("-" * 55)
    prots = r.get("protections_triggered", {})
    print(f"Protections: CD={prots.get('CooldownPeriod',0)} | SG={prots.get('StoplossGuard',0)} | MD={prots.get('MaxDrawdown',0)}")
    print("=" * 55)


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    report = generate_report()
    
    if "error" in report:
        print(f"[ERROR] {report['error']}")
        sys.exit(1)
    
    filename = REPORTS_DIR / f"{report['date']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[OK] Report saved: {filename}")
    
    print("\n[JSON OUTPUT]")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    print_table(report)


if __name__ == "__main__":
    main()
