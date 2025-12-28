import json

with open(r'c:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade\user_data\backtest_results\temp_extract\backtest-result-2025-12-28_23-14-31.json','r',encoding='utf-8') as f:
    d=json.load(f)

s=d.get('strategy',{}).get('EPAStrategyV2',{})

print('='*50)
print('BACKTEST RESULTS - EPAStrategyV2 (4H)')
print('='*50)
print('Total Trades:', s.get('total_trades'))
print('Win Rate:', round(s.get('winrate',0)*100,2), '%')
print('Profit Factor:', s.get('profit_factor'))
print('Total Profit:', round(s.get('profit_total',0)*100,2), '%')
print('Total Profit USDT:', round(s.get('profit_total_abs',0),2))
print('CAGR:', round(s.get('cagr',0)*100,2), '%')
print('Sharpe Ratio:', s.get('sharpe'))
print('Sortino Ratio:', s.get('sortino'))
print('Calmar Ratio:', s.get('calmar'))
print('Max Drawdown:', round(s.get('max_drawdown_account',0)*100,2), '%')
print('Expectancy:', round(s.get('expectancy',0),4))
print('Avg Holding:', s.get('holding_avg'))
print('='*50)
