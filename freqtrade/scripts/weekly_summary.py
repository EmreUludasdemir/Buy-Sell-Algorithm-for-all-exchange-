#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weekly Summary Generator
========================
Reads all daily JSON reports and creates summary.md
"""

import json
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def load_reports():
    reports = []
    for f in sorted(REPORTS_DIR.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                reports.append(json.load(fp))
        except: pass
    return reports


def generate_summary(reports):
    if not reports:
        return "# Weekly Summary\n\nNo reports found.\n"
    
    # Totals
    total_trades = sum(r.get("trades_today", 0) for r in reports)
    total_wins = sum(r.get("wins", 0) for r in reports)
    total_draws = sum(r.get("draws", 0) for r in reports)
    total_losses = sum(r.get("losses", 0) for r in reports)
    total_pnl = sum(r.get("total_pnl_usdt", 0) for r in reports)
    max_dd = max(r.get("max_drawdown", 0) for r in reports)
    
    # Protection counts
    all_cd = sum(r.get("protections_triggered", {}).get("CooldownPeriod", 0) for r in reports)
    all_sg = sum(r.get("protections_triggered", {}).get("StoplossGuard", 0) for r in reports)
    all_md = sum(r.get("protections_triggered", {}).get("MaxDrawdown", 0) for r in reports)
    
    # Alerts
    alerts = []
    if all_md >= 3:
        alerts.append("> **ALERT:** MaxDrawdown triggered 3+ times in 7 days!")
    
    # Check consecutive StoplossGuard
    sg_streak = 0
    max_streak = 0
    for r in reports:
        if r.get("protections_triggered", {}).get("StoplossGuard", 0) > 0:
            sg_streak += 1
            max_streak = max(max_streak, sg_streak)
        else:
            sg_streak = 0
    if max_streak >= 3:
        alerts.append("> **ALERT:** StoplossGuard triggered 3+ consecutive days!")
    
    # Draw ratio
    if total_trades > 0 and (total_draws / total_trades) > 0.55:
        alerts.append(f"> **ALERT:** Draw ratio is {total_draws/total_trades*100:.1f}% (>55%)")
    
    # Build markdown
    md = f"""# Weekly Summary Report

**Period:** {reports[0].get('date', 'N/A')} to {reports[-1].get('date', 'N/A')}
**Strategy:** {reports[0].get('strategy', 'EPAStrategyV2')}
**Days:** {len(reports)}

## Overall Totals

| Metric | Value |
|--------|-------|
| Total Trades | {total_trades} |
| Wins | {total_wins} |
| Draws | {total_draws} |
| Losses | {total_losses} |
| Win Rate | {(total_wins/total_trades*100) if total_trades else 0:.1f}% |
| Total PnL | {total_pnl:+.2f} USDT |
| Max Drawdown | {max_dd:.2f}% |
| Cooldown Triggers | {all_cd} |
| StoplossGuard Triggers | {all_sg} |
| MaxDrawdown Triggers | {all_md} |

## Daily Breakdown

| Date | Trades | Win | Draw | Loss | PnL | Max DD | CD | SG | MD |
|------|--------|-----|------|------|-----|--------|----|----|-----|
"""
    
    for r in reports:
        p = r.get("protections_triggered", {})
        md += f"| {r.get('date','-')} | {r.get('trades_today',0)} | {r.get('wins',0)} | {r.get('draws',0)} | {r.get('losses',0)} | {r.get('total_pnl_usdt',0):+.2f} | {r.get('max_drawdown',0):.1f}% | {p.get('CooldownPeriod',0)} | {p.get('StoplossGuard',0)} | {p.get('MaxDrawdown',0)} |\n"
    
    if alerts:
        md += "\n## Alerts\n\n" + "\n".join(alerts) + "\n"
    
    return md


def main():
    reports = load_reports()
    summary = generate_summary(reports)
    
    out_file = REPORTS_DIR / "summary.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"[OK] Summary saved: {out_file}")
    print("\n" + summary)


if __name__ == "__main__":
    main()
