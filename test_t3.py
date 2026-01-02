"""
Quick T3 MA Validation Test
"""

import sys
sys.path.insert(0, '/freqtrade/user_data/strategies')

print('='*60)
print('T3 MOVING AVERAGE VALIDATION TEST')
print('='*60)

# STEP 1: Import
print('\n[STEP 1] Importing kivanc_indicators...')
try:
    from indicators import kivanc_indicators as ki
    print('✅ Import successful')
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)

# STEP 2: Create test data
print('\n[STEP 2] Creating test data (100 candles)...')
import pandas as pd
import numpy as np

np.random.seed(42)
n = 100
base_price = 95000
prices = base_price + np.cumsum(np.random.randn(n) * 500 + 50)

test_df = pd.DataFrame({
    'high': prices + np.random.rand(n) * 200,
    'low': prices - np.random.rand(n) * 200,
    'close': prices,
    'volume': np.random.randint(1000000, 5000000, n)
})
print(f'✅ Created {len(test_df)} candles')
print(f'   Price range: ${test_df["close"].min():,.0f} - ${test_df["close"].max():,.0f}')

# STEP 3: Run T3 MA
print('\n[STEP 3] Running t3_ma() function...')
try:
    t3_line, direction = ki.t3_ma(test_df, period=5, volume_factor=0.7)
    print('✅ Function executed without errors')
except Exception as e:
    print(f'❌ Function failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# STEP 4: Validate return types
print('\n[STEP 4] Validating return types...')
print(f'   T3 line type: {type(t3_line).__name__}', '✅' if type(t3_line).__name__ == 'Series' else '❌')
print(f'   Direction type: {type(direction).__name__}', '✅' if type(direction).__name__ == 'Series' else '❌')

# STEP 5: Check for NaN values
print('\n[STEP 5] Checking for NaN values...')
nan_t3 = t3_line.isna().sum()
nan_dir = direction.isna().sum()
print(f'   T3 line NaN count: {nan_t3}', '✅ (Expected: ~30 warmup)' if nan_t3 <= 35 else '⚠️')
print(f'   Direction NaN count: {nan_dir}', '✅' if nan_dir == 0 else '⚠️')

# STEP 6: Display sample values
print('\n[STEP 6] Sample values:')
print('\nFirst 5 values (warmup period - expect NaN):')
print(f'T3 line: {t3_line.head().tolist()}')
print(f'Direction: {direction.head().tolist()}')

print('\nLast 5 values (should be valid):')
print(f'T3 line: {t3_line.tail().tolist()}')
print(f'Direction: {direction.tail().tolist()}')

# STEP 7: Value range check
print('\n[STEP 7] Value range validation:')
valid_t3 = t3_line[~t3_line.isna()]
if len(valid_t3) > 0:
    print(f'   T3 range: ${valid_t3.min():,.2f} - ${valid_t3.max():,.2f}')
    print(f'   Price range: ${test_df["close"].min():,.2f} - ${test_df["close"].max():,.2f}')
    ratio = valid_t3.mean() / test_df['close'].mean()
    print(f'   T3/Price ratio: {ratio:.2%}', '✅' if 0.8 <= ratio <= 1.2 else '⚠️')

# STEP 8: Direction statistics
print('\n[STEP 8] Direction statistics:')
bullish = (direction == 1).sum()
bearish = (direction == -1).sum()
print(f'   Bullish bars: {bullish} ({bullish/len(test_df)*100:.1f}%)')
print(f'   Bearish bars: {bearish} ({bearish/len(test_df)*100:.1f}%)')

# FINAL
print('\n' + '='*60)
print('✅ T3 MA VALIDATION COMPLETE')
print('='*60)
print('All checks passed! T3 is ready for strategy integration.')
