import json
import sys

with open('user_data/backtest_results/.last_result.json', 'r') as f:
    data = json.load(f)

strategy_name = list(data.get('strategy', {}).keys())[0] if data.get('strategy') else None
if not strategy_name:
    print("No strategy found")
    sys.exit(1)

r = data['strategy'][strategy_name]

print(f"""
{'='*60}
BACKTEST SONUCLARI: {strategy_name}
{'='*60}
Timeframe: {r.get('timeframe', '?')}
Timerange: {r.get('timerange', '?')}

GENEL PERFORMANS:
- Toplam Trade: {r.get('total_trades', 0)}
- Win Rate: {r.get('winrate', 0)*100:.1f}%
- Profit Mean: {r.get('profit_mean', 0)*100:.2f}%
- Profit Total: {r.get('profit_total_abs', 0):.2f} USDT ({r.get('profit_total', 0)*100:.2f}%)
- Max Drawdown: {r.get('max_drawdown_abs', 0):.2f} USDT ({r.get('max_drawdown', 0)*100:.2f}%)
- Sharpe Ratio: {r.get('sharpe', 0):.2f}
- Sortino Ratio: {r.get('sortino', 0):.2f}
- Profit Factor: {r.get('profit_factor', 0):.2f}
- Expectancy: {r.get('expectancy', 0):.4f}

TRADE BILGILERI:
""")

trades = r.get('trades', [])
if trades:
    wins = sum(1 for t in trades if t.get('profit_ratio', 0) > 0)
    losses = sum(1 for t in trades if t.get('profit_ratio', 0) <= 0)
    print(f"- Kazanan: {wins}")
    print(f"- Kaybeden: {losses}")
    print(f"\nTRADE DETAYLARI:")
    print("-"*80)
    for i, t in enumerate(trades, 1):
        print(f"  {i}. {t.get('pair', '?')} | "
              f"Giris: {t.get('open_date', '?')[:16]} | "
              f"Cikis: {t.get('close_date', '?')[:16]} | "
              f"Profit: {t.get('profit_ratio', 0)*100:.2f}% | "
              f"Tag: {t.get('enter_tag', '-')}")
else:
    print("  Trade yok")

print("="*60)
