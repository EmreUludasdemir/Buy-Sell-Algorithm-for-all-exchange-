import json
import zipfile

# Read from zip file using Windows relative path
z = zipfile.ZipFile('user_data/backtest_results/backtest-result-2026-01-03_10-05-10.zip')
data = json.loads(z.read(z.namelist()[0]))
    
s = data['strategy']['EPAUltimateV3']
print(f"""
📊 4H BASELINE (2024 Full Year):
================================
💰 Profit: {s.get('profit_total_abs', 0):.2f} USDT
📈 Profit %: {s.get('profit_total', 0)*100:.2f}%
🔢 Trades: {s.get('total_trades', 0)}
✅ Wins: {s.get('wins', 0)}
❌ Losses: {s.get('losses', 0)}
🎯 Win Rate: {s.get('wins', 0)/max(s.get('total_trades', 1), 1)*100:.1f}%
📉 Max DD: {s.get('max_drawdown', 0)*100:.2f}%
💵 Avg/Trade: {s.get('profit_total_abs', 0)/max(s.get('total_trades', 1), 1):.2f} USDT
================================
""")
