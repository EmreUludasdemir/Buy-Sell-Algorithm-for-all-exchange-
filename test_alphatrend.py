"""
AlphaTrend Indicator Validation Script
======================================
Tests the alphatrend() function from kivanc_indicators.py

Usage (inside Freqtrade Docker):
    python3 test_alphatrend.py

Or from host (if Docker is running):
    docker compose exec freqtrade python3 /freqtrade/test_alphatrend.py
"""

import sys
import os

# Add user_data/strategies to path for imports
sys.path.insert(0, '/freqtrade/user_data/strategies')

print('='*60)
print('ALPHATREND INDICATOR VALIDATION TEST')
print('='*60)

# === STEP 1: Import the indicator ===
print('\n[STEP 1] Importing kivanc_indicators module...')
try:
    from indicators import kivanc_indicators as ki
    print('✅ Import successful')
    print(f'   Module version: {ki.__doc__.split("Version:")[1].split()[0].strip() if "Version:" in ki.__doc__ else "Unknown"}')
except Exception as e:
    print(f'❌ IMPORT FAILED: {e}')
    print('\nWhat this means:')
    print('  - The module file might have syntax errors')
    print('  - Or the path is incorrect')
    print('  - Check: /freqtrade/user_data/strategies/indicators/kivanc_indicators.py')
    sys.exit(1)

# === STEP 2: Create test data ===
print('\n[STEP 2] Creating test dataframe (100 candles, uptrend simulation)...')
try:
    import pandas as pd
    import numpy as np
    
    # Seed for reproducibility
    np.random.seed(42)
    n = 100
    base_price = 95000
    
    # Simulate realistic BTC uptrend with noise
    trend = np.cumsum(np.random.randn(n) * 500 + 50)  # Random walk with upward drift
    prices = base_price + trend
    
    test_df = pd.DataFrame({
        'high': prices + np.random.rand(n) * 200,      # High slightly above close
        'low': prices - np.random.rand(n) * 200,       # Low slightly below close
        'close': prices,                                # Close price
        'volume': np.random.randint(1000000, 5000000, n)  # Random volume
    })
    
    print('✅ Test data created')
    print(f'   Rows: {len(test_df)}')
    print(f'   Price range: ${test_df["close"].min():,.0f} - ${test_df["close"].max():,.0f}')
    print(f'   Volume range: {test_df["volume"].min():,} - {test_df["volume"].max():,}')
    print(f'   Overall trend: {"UPTREND" if test_df["close"].iloc[-1] > test_df["close"].iloc[0] else "DOWNTREND"}')
    
except Exception as e:
    print(f'❌ DATA CREATION FAILED: {e}')
    sys.exit(1)

# === STEP 3: Run alphatrend() ===
print('\n[STEP 3] Running alphatrend() function...')
try:
    at_line, at_trend, buy_sig, sell_sig = ki.alphatrend(
        test_df,
        atr_period=14,
        atr_multiplier=1.0,
        mfi_period=14
    )
    print('✅ Function executed without errors')
    
except Exception as e:
    print(f'❌ FUNCTION EXECUTION FAILED: {e}')
    print('\nFull error traceback:')
    import traceback
    traceback.print_exc()
    
    print('\n📚 WHAT THIS ERROR TEACHES YOU:')
    error_str = str(e).lower()
    if 'keyerror' in error_str:
        print('  → KeyError means a required column is missing from dataframe')
        print('  → Check: Does test_df have high, low, close, volume columns?')
    elif 'typeerror' in error_str:
        print('  → TypeError means wrong data type passed to function')
        print('  → TA-Lib expects specific types (usually numpy arrays or pandas Series)')
    elif 'valueerror' in error_str:
        print('  → ValueError means data shape/size is wrong')
        print('  → Check: Does dataframe have enough rows? (need >14 for ATR/MFI)')
    else:
        print('  → Unexpected error - review the full traceback above')
    
    sys.exit(1)

# === STEP 4: Validate return types ===
print('\n[STEP 4] Validating return types...')
print(f'   AlphaTrend line: {type(at_line).__name__}', end='')
print(' ✅' if type(at_line).__name__ == 'Series' else ' ❌')

print(f'   Trend direction: {type(at_trend).__name__}', end='')
print(' ✅' if type(at_trend).__name__ == 'Series' else ' ❌')

print(f'   Buy signals: {type(buy_sig).__name__}', end='')
print(' ✅' if type(buy_sig).__name__ == 'Series' else ' ❌')

print(f'   Sell signals: {type(sell_sig).__name__}', end='')
print(' ✅' if type(sell_sig).__name__ == 'Series' else ' ❌')

# === STEP 5: Check for NaN values ===
print('\n[STEP 5] Checking for NaN (missing) values...')
nan_line = at_line.isna().sum()
nan_trend = at_trend.isna().sum()
nan_buy = buy_sig.isna().sum()
nan_sell = sell_sig.isna().sum()

print(f'   AlphaTrend line NaN count: {nan_line}', end='')
if nan_line <= 14:
    print(' ✅ (Expected: ~14 warmup period)')
else:
    print(f' ⚠️  (Too many! Expected ~14)')

print(f'   Trend direction NaN count: {nan_trend}', end='')
print(' ✅' if nan_trend == 0 else ' ⚠️')

print(f'   Buy signals NaN count: {nan_buy}', end='')
print(' ✅' if nan_buy == 0 else ' ⚠️')

print(f'   Sell signals NaN count: {nan_sell}', end='')
print(' ✅' if nan_sell == 0 else ' ⚠️')

# === STEP 6: Display first 5 values ===
print('\n[STEP 6] First 5 values (warmup period - expect NaN):')
print('\nAlphaTrend Line:')
print(at_line.head())
print('\nTrend Direction (1=bullish, -1=bearish):')
print(at_trend.head())
print('\nBuy Signals (True=buy signal):')
print(buy_sig.head())

# === STEP 7: Display last 5 values ===
print('\n[STEP 7] Last 5 values (should be valid):')
print('\nAlphaTrend Line:')
print(at_line.tail())
print('\nTrend Direction:')
print(at_trend.tail())
print('\nSell Signals (True=sell signal):')
print(sell_sig.tail())

# === STEP 8: Signal statistics ===
print('\n[STEP 8] Signal statistics:')
buy_count = buy_sig.sum()
sell_count = sell_sig.sum()
bullish_bars = (at_trend == 1).sum()
bearish_bars = (at_trend == -1).sum()

print(f'   Total buy signals: {buy_count}', end='')
if buy_count > 0:
    print(' ✅')
else:
    print(' ⚠️  (No buy signals - might be OK depending on trend)')

print(f'   Total sell signals: {sell_count}', end='')
if sell_count > 0:
    print(' ✅')
else:
    print(' ⚠️  (No sell signals - might be OK if pure uptrend)')

print(f'   Bullish bars: {bullish_bars} ({bullish_bars/len(test_df)*100:.1f}%)')
print(f'   Bearish bars: {bearish_bars} ({bearish_bars/len(test_df)*100:.1f}%)')

# === STEP 9: Value range validation ===
print('\n[STEP 9] Value range validation:')
valid_at = at_line[~at_line.isna()]

if len(valid_at) > 0:
    at_min, at_max = valid_at.min(), valid_at.max()
    price_min, price_max = test_df['close'].min(), test_df['close'].max()
    
    print(f'   AlphaTrend range: ${at_min:.2f} - ${at_max:.2f}')
    print(f'   Price range: ${price_min:.2f} - ${price_max:.2f}')
    
    # AlphaTrend should be within reasonable range of prices (±20%)
    ratio = valid_at.mean() / test_df['close'].mean()
    print(f'   AlphaTrend/Price ratio: {ratio:.2%}', end='')
    if 0.8 <= ratio <= 1.2:
        print(' ✅ (Within expected range)')
    else:
        print(' ⚠️  (Outside expected range - might indicate calculation error)')

# === STEP 10: Visual pattern check ===
print('\n[STEP 10] Visual pattern check (sample):')
print('Candle | Close Price | AlphaTrend | Trend | Signal')
print('-' * 60)
for i in [15, 30, 50, 70, 90]:  # Sample candles
    close = test_df['close'].iloc[i]
    at = at_line.iloc[i]
    trend = at_trend.iloc[i]
    signal = 'BUY' if buy_sig.iloc[i] else ('SELL' if sell_sig.iloc[i] else '-')
    
    trend_symbol = '↑' if trend == 1 else '↓'
    print(f'  {i:3d}  | ${close:8.0f}   | ${at:8.0f}  | {trend:2d} {trend_symbol} | {signal:4s}')

# === FINAL SUMMARY ===
print('\n' + '='*60)
print('VALIDATION SUMMARY')
print('='*60)

all_checks_passed = True

# Check 1: No import errors
print('✅ Import: Module loaded successfully')

# Check 2: Function executed
print('✅ Execution: Function ran without crashing')

# Check 3: Return types
types_ok = (type(at_line).__name__ == 'Series' and 
            type(at_trend).__name__ == 'Series' and
            type(buy_sig).__name__ == 'Series' and 
            type(sell_sig).__name__ == 'Series')
if types_ok:
    print('✅ Types: All return values are pandas Series')
else:
    print('❌ Types: Some return values are not pandas Series')
    all_checks_passed = False

# Check 4: NaN handling
if nan_line <= 14 and nan_trend == 0:
    print('✅ NaN handling: Warmup period handled correctly')
else:
    print(f'⚠️  NaN handling: Unexpected NaN counts')
    all_checks_passed = False

# Check 5: Signals present
if buy_count > 0 or sell_count > 0:
    print(f'✅ Signals: Generated {buy_count} buy, {sell_count} sell signals')
else:
    print('⚠️  Signals: No signals generated (might be OK, but verify)')

# Check 6: Value ranges
if len(valid_at) > 0 and 0.8 <= ratio <= 1.2:
    print('✅ Values: AlphaTrend values in reasonable range')
else:
    print('⚠️  Values: AlphaTrend values outside expected range')

print('\n' + '='*60)
if all_checks_passed:
    print('🎉 ALL CRITICAL CHECKS PASSED!')
    print('AlphaTrend indicator is ready for strategy integration.')
else:
    print('⚠️  SOME CHECKS FAILED - Review output above')
    print('Fix issues before using in live strategy.')
print('='*60)

print('\n📚 WHAT YOU LEARNED:')
print('  1. Indicators need warmup period (~14 candles for ATR/MFI)')
print('  2. AlphaTrend combines ATR bands with MFI direction')
print('  3. Return values are pandas Series (Freqtrade standard)')
print('  4. Buy/sell signals are boolean Series, not integers')
print('  5. Validation prevents bugs in live trading!')

print('\nNext steps:')
print('  → Integrate into strategy: use at_line, at_trend in populate_indicators()')
print('  → Test with real BTC data: download-data then re-run test')
print('  → Backtest minimal strategy with only AlphaTrend signals')
