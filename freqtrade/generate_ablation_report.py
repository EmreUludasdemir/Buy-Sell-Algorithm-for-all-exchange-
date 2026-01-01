#!/usr/bin/env python3
"""
Generate Stop Mechanism Ablation Study Report
Analyzes 4 variants to identify the true culprit of trailing_stop_loss exits
"""

# Summary data from backtests
variants = {
    'A': {
        'name': 'Trailing ON, Custom OFF',
        'trailing': True,
        'custom': False,
        'trades': 81,
        'profit_usdt': -34.84,
        'profit_pct': -1.74,
        'win_rate': 69.1,
        'drawdown': 9.03,
        'exit_reasons': {
            'roi': {'count': 41, 'pnl': 520.41, 'win_rate': 100},
            'trailing_stop_loss': {'count': 15, 'pnl': 81.23, 'win_rate': 100},
            'stop_loss': {'count': 14, 'pnl': -252.58, 'win_rate': 0},
            'exit_signal': {'count': 11, 'pnl': -383.91, 'win_rate': 0}
        }
    },
    'B': {
        'name': 'Trailing OFF, Custom ON',
        'trailing': False,
        'custom': True,
        'trades': 84,
        'profit_usdt': 113.61,
        'profit_pct': 5.68,
        'win_rate': 57.1,
        'drawdown': 7.65,
        'exit_reasons': {
            'roi': {'count': 45, 'pnl': 642.58, 'win_rate': 100},
            'tiered_tp_8pct': {'count': 1, 'pnl': 49.73, 'win_rate': 100},
            'trailing_stop_loss': {'count': 34, 'pnl': -494.58, 'win_rate': 5.9},  # MISLABELED!
            'stop_loss': {'count': 2, 'pnl': -20.76, 'win_rate': 0},
            'exit_signal': {'count': 2, 'pnl': -63.35, 'win_rate': 0}
        }
    },
    'C': {
        'name': 'Both ON (Baseline)',
        'trailing': True,
        'custom': True,
        'trades': 92,
        'profit_usdt': -54.43,
        'profit_pct': -2.72,
        'win_rate': 51.1,
        'drawdown': 8.19,
        'exit_reasons': {
            'roi': {'count': 40, 'pnl': 539.43, 'win_rate': 100},
            'trailing_stop_loss': {'count': 48, 'pnl': -514.80, 'win_rate': 14.6},
            'stop_loss': {'count': 2, 'pnl': -19.67, 'win_rate': 0},
            'exit_signal': {'count': 2, 'pnl': -59.40, 'win_rate': 0}
        }
    },
    'D': {
        'name': 'Both OFF (Fixed Stoploss)',
        'trailing': False,
        'custom': False,
        'trades': 72,
        'profit_usdt': 116.75,
        'profit_pct': 5.84,
        'win_rate': 70.8,
        'drawdown': 8.10,
        'exit_reasons': {
            'roi': {'count': 49, 'pnl': 673.22, 'win_rate': 100},
            'tiered_tp_8pct': {'count': 2, 'pnl': 56.17, 'win_rate': 100},
            'stop_loss': {'count': 10, 'pnl': -219.68, 'win_rate': 0},
            'exit_signal': {'count': 11, 'pnl': -392.96, 'win_rate': 0}
        }
    }
}

def generate_report():
    lines = [
        "# Stop Mechanism Ablation Study - EPAUltimateV3",
        "",
        "**Goal**: Prove whether losses labeled `trailing_stop_loss` are caused by trailing_stop settings or custom_stoploss logic.",
        "",
        "**Test Period**: 2024-06-01 to 2024-12-31 (213 days)",
        "**Timeframe**: 4h",
        "**Pairs**: BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT",
        "**Base Stoploss**: -8% (fixed)",
        "**Trailing Settings**: positive=3%, offset=5%, only_offset_is_reached=True",
        "**Custom Stoploss**: ATR-based (max of -8% or 3 ATR)",
        "",
        "---",
        "",
        "## Variant Summary",
        "",
        "| Variant | Trailing | Custom | Trades | Profit USDT | Profit % | Win Rate | Drawdown | Trailing Exits |",
        "|---------|----------|--------|--------|-------------|----------|----------|----------|----------------|"
    ]
    
    for var_id in ['A', 'B', 'C', 'D']:
        v = variants[var_id]
        trailing_exits = v['exit_reasons'].get('trailing_stop_loss', {}).get('count', 0)
        lines.append(
            f"| **{var_id}** | {'Ô£à' if v['trailing'] else 'ÔØî'} | "
            f"{'Ô£à' if v['custom'] else 'ÔØî'} | {v['trades']} | "
            f"{v['profit_usdt']:.2f} | {v['profit_pct']:.2f}% | "
            f"{v['win_rate']:.1f}% | {v['drawdown']:.2f}% | {trailing_exits} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## Detailed Analysis",
        ""
    ])
    
    for var_id in ['A', 'B', 'C', 'D']:
        v = variants[var_id]
        lines.extend([
            f"### Variant {var_id}: {v['name']}",
            "",
            f"**Configuration**:",
            f"- `trailing_stop = {v['trailing']}`",
            f"- `use_custom_stoploss = {v['custom']}`",
            "",
            f"**Results**:",
            f"- Total Trades: {v['trades']}",
            f"- Profit: {v['profit_usdt']:.2f} USDT ({v['profit_pct']:.2f}%)",
            f"- Win Rate: {v['win_rate']:.1f}%",
            f"- Max Drawdown: {v['drawdown']:.2f}%",
            "",
            "**Exit Reason Distribution**:",
            "",
            "| Exit Reason | Count | Total PnL (USDT) | Win Rate |",
            "|------------|-------|------------------|----------|"
        ])
        
        for reason, data in v['exit_reasons'].items():
            lines.append(
                f"| {reason} | {data['count']} | {data['pnl']:.2f} | {data['win_rate']:.1f}% |"
            )
        
        # Special analysis for trailing_stop_loss
        if 'trailing_stop_loss' in v['exit_reasons']:
            tsl_data = v['exit_reasons']['trailing_stop_loss']
            lines.extend([
                "",
                "**Trailing Stop Loss Analysis**:",
                f"- Count: {tsl_data['count']} trades",
                f"- Total Impact: {tsl_data['pnl']:.2f} USDT",
                f"- Win Rate: {tsl_data['win_rate']:.1f}%",
                f"- Average: {tsl_data['pnl']/tsl_data['count']:.2f} USDT per trade",
                ""
            ])
            
            # Critical finding for Variant B
            if var_id == 'B':
                lines.extend([
                    "**­şÜ¿ CRITICAL FINDING ­şÜ¿**:",
                    "",
                    "This variant has `trailing_stop = False`, yet 34 trades are labeled as `trailing_stop_loss`!",
                    "",
                    "**Proof that custom_stoploss is mislabeling its exits as trailing_stop_loss.**",
                    ""
                ])
        
        lines.extend(["", "---", ""])
    
    # Conclusions
    lines.extend([
        "## Conclusion",
        "",
        "### ­şÄ» Root Cause Identified",
        "",
        "The `trailing_stop_loss` exit reason is triggered by **BOTH mechanisms**, and they interfere with each other:",
        "",
        "1. **When `trailing_stop = True` and `use_custom_stoploss = False` (Variant A)**:",
        "   - 15 trailing_stop_loss exits with **100% win rate** (+81 USDT)",
        "   - This is TRUE trailing stops working correctly",
        "   - They lock in profits after +5% threshold",
        "",
        "2. **When `trailing_stop = False` and `use_custom_stoploss = True` (Variant B)**:",
        "   - 34 trailing_stop_loss exits with **5.9% win rate** (-495 USDT) ÔåÉ MISLABELED!",
        "   - Trailing is OFF but exits still labeled as trailing_stop_loss",
        "   - **Proof: custom_stoploss mislabels its ATR-based exits**",
        "",
        "3. **When both are ON (Variant C - Original)**:",
        "   - 48 trailing_stop_loss exits with **14.6% win rate** (-515 USDT)",
        "   - Worst of both worlds: interference between mechanisms",
        "   - Custom stoploss overrides trailing logic unpredictably",
        "",
        "4. **When both are OFF (Variant D - Winner)**:",
        "   - **0 trailing_stop_loss exits**",
        "   - Fixed -8% stoploss only: 10 exits, -220 USDT",
        "   - **+117 USDT profit (+5.84%), 70.8% win rate**",
        "   - Clean, predictable exit behavior",
        "",
        "---",
        "",
        "## Recommendation for 4H Timeframe",
        "",
        "### Ô£à Use Variant D: Both OFF (Fixed Stoploss Only)",
        "",
        "```python",
        "stoploss = -0.08  # -8% fixed stop",
        "use_custom_stoploss = False  # Disable ATR-based logic",
        "trailing_stop = False  # Disable trailing stops",
        "```",
        "",
        "### Justification:",
        "",
        "| Metric | Variant D (Winner) | Variant C (Current) | Improvement |",
        "|--------|-------------------|---------------------|-------------|",
        "| Profit | **+117 USDT** | -54 USDT | **+171 USDT** |",
        "| Profit % | **+5.84%** | -2.72% | **+8.56%** |",
        "| Win Rate | **70.8%** | 51.1% | **+19.7%** |",
        "| Trades | 72 | 92 | -20 (more selective) |",
        "| Drawdown | 8.10% | 8.19% | Similar |",
        "| Trailing Exits | **0** | 48 (-515 USDT) | **Eliminated problem** |",
        "",
        "### Why Fixed Stoploss Works Best for 4H:",
        "",
        "1. **Predictability**: -8% stop is clear, no interference from ATR or trailing logic",
        "2. **Fewer Trades**: 72 vs 92 = more selective, higher quality entries",
        "3. **Higher Win Rate**: 70.8% vs 51.1% = better entry/exit timing",
        "4. **ROI Table Dominates**: 49 ROI exits with 100% win rate (+673 USDT)",
        "5. **Clean Exit Reasons**: Only 4 types (roi, stop_loss, exit_signal, tiered_tp)",
        "",
        "### Alternative: Variant B (If You Want Dynamic Stops)",
        "",
        "If you prefer ATR-based dynamic stops:",
        "",
        "```python",
        "stoploss = -0.08",
        "use_custom_stoploss = True  # ATR-based logic",
        "trailing_stop = False  # Must disable to avoid mislabeling",
        "```",
        "",
        "- Also profitable: +114 USDT (+5.68%)",
        "- But: 34 exits mislabeled as trailing_stop_loss (confusing)",
        "- And: Only 57.1% win rate vs 70.8% for Variant D",
        "",
        "---",
        "",
        "## Implementation Steps",
        "",
        "1. **Open** `user_data/strategies/EPAUltimateV3.py`",
        "",
        "2. **Find** the stop configuration section (around line 86-95)",
        "",
        "3. **Replace** with:",
        "```python",
        "# Base stoploss - fixed for 4H timeframe",
        "stoploss = -0.08",
        "",
        "# Disable dynamic mechanisms for clean behavior",
        "use_custom_stoploss = False",
        "",
        "# Disable trailing stops",
        "trailing_stop = False",
        "trailing_stop_positive = 0.03  # Not used",
        "trailing_stop_positive_offset = 0.05  # Not used",
        "trailing_only_offset_is_reached = True  # Not used",
        "```",
        "",
        "4. **Commit** changes:",
        "```bash",
        "git add user_data/strategies/EPAUltimateV3.py",
        "git commit -m 'Apply Variant D: Fixed stoploss only - Best performance for 4H'",
        "```",
        "",
        "5. **Run final validation backtest**:",
        "```bash",
        "docker compose run --rm freqtrade backtesting \\",
        "    --strategy EPAUltimateV3 \\",
        "    --config user_data/config.json \\",
        "    --timerange 20240601-20241231 \\",
        "    --timeframe 4h",
        "```",
        "",
        "Expected: +117 USDT, 72 trades, 70.8% win rate, 0 trailing_stop_loss exits",
        "",
        "---",
        "",
        "## Key Insights",
        "",
        "1. **Mislabeling Confirmed**: `custom_stoploss` returns values that get labeled as `trailing_stop_loss` even when trailing is OFF",
        "",
        "2. **Interference Effect**: When both mechanisms are ON, they conflict and produce worst results",
        "",
        "3. **Simplicity Wins**: Fixed stoploss outperforms complex dynamic logic for 4H timeframe",
        "",
        "4. **ROI Table is King**: All variants show ROI exits have 100% win rate - let it do the work",
        "",
        "5. **4H Volatility**: -8% fixed stop is wide enough for 4H candle noise, no need for dynamic ATR",
        "",
        "---",
        "",
        "**Report Generated**: 2026-01-01",
        "**Strategy**: EPAUltimateV3",
        "**Test Period**: 2024-06-01 to 2024-12-31 (213 days)",
        "**Conclusion**: Use Variant D (both OFF) for optimal 4H performance"
    ])
    
    return '\n'.join(lines)

if __name__ == "__main__":
    from pathlib import Path
    
    report = generate_report()
    report_path = Path('reports/stop_mechanism_ablation.md')
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report, encoding='utf-8')
    
    print(f"Ô£à Ablation study report generated: {report_path}")
    print(f"\n­şôè Summary:")
    print(f"   Variant A (Trailing ON, Custom OFF):  -35 USDT,  81 trades")
    print(f"   Variant B (Trailing OFF, Custom ON):  +114 USDT, 84 trades Ô¡É PROFITABLE")
    print(f"   Variant C (Both ON - Baseline):       -54 USDT,  92 trades")
    print(f"   Variant D (Both OFF - WINNER):        +117 USDT, 72 trades Ô¡ÉÔ¡É BEST")
    print(f"\n­şÄ» Recommendation: Use Variant D (fixed stoploss only)")
    print(f"   - No interference, clean exits, highest win rate (70.8%)")
    print(f"   - Zero trailing_stop_loss exits (problem eliminated)")
