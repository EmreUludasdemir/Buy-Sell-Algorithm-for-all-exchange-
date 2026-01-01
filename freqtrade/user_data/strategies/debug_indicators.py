"""
Debug script to check Kıvanç indicator values and diagnose why strategies produce few trades.
Run from freqtrade directory:
    docker compose run --rm freqtrade python user_data/strategies/debug_indicators.py
"""

import sys
import os
sys.path.insert(0, 'user_data/strategies')

import pandas as pd
import numpy as np

# Load data directly
from pathlib import Path

def load_data():
    """Load BTC/USDT 4h data from feather file."""
    data_path = Path('user_data/data/binance/BTC_USDT-4h.feather')
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        return None
    
    df = pd.read_feather(data_path)
    print(f"Loaded {len(df)} candles from {data_path}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    return df


def test_supertrend(df):
    """Test Supertrend indicator."""
    print("\n" + "="*60)
    print("=== SUPERTREND TEST ===")
    print("="*60)
    
    from kivanc_indicators import supertrend
    
    direction, line = supertrend(df, period=10, multiplier=3.0)
    
    print(f"Type of direction: {type(direction)}")
    print(f"Length: {len(direction)}")
    print(f"NaN count: {pd.isna(direction).sum()} / {len(direction)}")
    print(f"Unique values: {pd.Series(direction).dropna().unique()}")
    
    # Count direction values
    dir_series = pd.Series(direction)
    bull_count = (dir_series == 1).sum()
    bear_count = (dir_series == -1).sum()
    print(f"Bullish (1): {bull_count}")
    print(f"Bearish (-1): {bear_count}")
    
    # Direction changes
    changes = (dir_series != dir_series.shift(1)).sum()
    print(f"Direction changes: {changes}")
    
    print(f"\nLast 20 values:\n{dir_series.tail(20).to_string()}")
    
    return direction


def test_halftrend(df):
    """Test HalfTrend indicator."""
    print("\n" + "="*60)
    print("=== HALFTREND TEST ===")
    print("="*60)
    
    from kivanc_indicators import halftrend
    
    direction, up_line, down_line = halftrend(df, amplitude=2, channel_deviation=2.0)
    
    print(f"Type of direction: {type(direction)}")
    print(f"Length: {len(direction)}")
    print(f"NaN count: {pd.isna(direction).sum()} / {len(direction)}")
    print(f"Unique values: {pd.Series(direction).dropna().unique()}")
    
    # Count direction values
    dir_series = pd.Series(direction)
    bull_count = (dir_series == 1).sum()
    bear_count = (dir_series == -1).sum()
    print(f"Bullish (1): {bull_count}")
    print(f"Bearish (-1): {bear_count}")
    
    # Direction changes
    changes = (dir_series != dir_series.shift(1)).sum()
    print(f"Direction changes: {changes}")
    
    print(f"\nLast 20 values:\n{dir_series.tail(20).to_string()}")
    
    return direction


def test_qqe(df):
    """Test QQE indicator."""
    print("\n" + "="*60)
    print("=== QQE TEST ===")
    print("="*60)
    
    from kivanc_indicators import qqe
    
    trend, rsi_ma, qqe_line = qqe(df, rsi_period=14, sf=5, qq_factor=4.238)
    
    print(f"Type of trend: {type(trend)}")
    print(f"Length: {len(trend)}")
    print(f"NaN count: {pd.isna(trend).sum()} / {len(trend)}")
    print(f"Unique values: {pd.Series(trend).dropna().unique()}")
    
    # Count trend values
    trend_series = pd.Series(trend)
    bull_count = (trend_series == 1).sum()
    bear_count = (trend_series == -1).sum()
    print(f"Bullish (1): {bull_count}")
    print(f"Bearish (-1): {bear_count}")
    
    # Trend changes
    changes = (trend_series != trend_series.shift(1)).sum()
    print(f"Trend changes: {changes}")
    
    # Check RSI MA values
    print(f"\nRSI MA stats:")
    print(f"  Min: {rsi_ma.min():.2f}")
    print(f"  Max: {rsi_ma.max():.2f}")
    print(f"  Mean: {rsi_ma.mean():.2f}")
    
    print(f"\nLast 20 trend values:\n{trend_series.tail(20).to_string()}")
    
    return trend


def test_wae(df):
    """Test Waddah Attar Explosion indicator."""
    print("\n" + "="*60)
    print("=== WAE TEST ===")
    print("="*60)
    
    from kivanc_indicators import waddah_attar_explosion
    
    wae = waddah_attar_explosion(df, sensitivity=150)
    
    print(f"Columns: {wae.columns.tolist()}")
    print(f"Length: {len(wae)}")
    
    print(f"\nWAE Signal stats:")
    print(f"  Bullish explosion: {(wae['wae_signal'] == 1).sum()}")
    print(f"  Bearish explosion: {(wae['wae_signal'] == -1).sum()}")
    print(f"  Dead zone: {(wae['wae_signal'] == 0).sum()}")
    
    print(f"\nWAE in explosion: {wae['wae_in_explosion'].sum()} candles")
    
    return wae


def test_confluence(df):
    """Test combined Kıvanç confluence."""
    print("\n" + "="*60)
    print("=== CONFLUENCE TEST ===")
    print("="*60)
    
    from kivanc_indicators import add_kivanc_indicators
    
    result = add_kivanc_indicators(df)
    
    # Check confluence counts
    bull_count = result['kivanc_bull_count']
    bear_count = result['kivanc_bear_count']
    
    print(f"Bullish confluence distribution:")
    print(f"  0/3: {(bull_count == 0).sum()}")
    print(f"  1/3: {(bull_count == 1).sum()}")
    print(f"  2/3: {(bull_count == 2).sum()}")
    print(f"  3/3: {(bull_count == 3).sum()}")
    
    print(f"\nBearish confluence distribution:")
    print(f"  0/3: {(bear_count == 0).sum()}")
    print(f"  1/3: {(bear_count == 1).sum()}")
    print(f"  2/3: {(bear_count == 2).sum()}")
    print(f"  3/3: {(bear_count == 3).sum()}")
    
    # Count candles where at least 1 bullish signal
    at_least_1_bull = (bull_count >= 1).sum()
    at_least_2_bull = (bull_count >= 2).sum()
    print(f"\nCandles with >= 1 bullish: {at_least_1_bull}")
    print(f"Candles with >= 2 bullish: {at_least_2_bull}")
    
    return result


def main():
    print("="*60)
    print("KΙVANÇ INDICATORS DEBUG SCRIPT")
    print("="*60)
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Test each indicator
    try:
        st_dir = test_supertrend(df)
    except Exception as e:
        print(f"SUPERTREND ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        ht_dir = test_halftrend(df)
    except Exception as e:
        print(f"HALFTREND ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        qqe_trend = test_qqe(df)
    except Exception as e:
        print(f"QQE ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        wae = test_wae(df)
    except Exception as e:
        print(f"WAE ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        confluence = test_confluence(df)
    except Exception as e:
        print(f"CONFLUENCE ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
