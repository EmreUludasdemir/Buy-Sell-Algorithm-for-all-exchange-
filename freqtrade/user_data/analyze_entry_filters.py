"""
Diagnostic Script for EPAAlphaTrendV1 Entry Analysis
Analyzes which entry layer is filtering the most signals.
"""
import sys
sys.path.insert(0, '/freqtrade/user_data/strategies')

import pandas as pd
import numpy as np
import talib.abstract as ta
from freqtrade.data.btanalysis import load_backtest_data
from freqtrade.data.history import load_pair_history
from pathlib import Path

# Load BTC/USDT 2h data for 2024
data_dir = Path('/freqtrade/user_data/data/binance')
pair = 'BTC_USDT'  # Use underscore format for file path
timeframe = '2h'

print("Loading data...")
# Try direct file loading
import json
data_file = data_dir / f'{pair}-{timeframe}.json'
print(f"Looking for: {data_file}")

if data_file.exists():
    with open(data_file, 'r') as f:
        data = json.load(f)
    dataframe = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    dataframe['date'] = pd.to_datetime(dataframe['date'], unit='ms')
    # Filter to 2024
    dataframe = dataframe[(dataframe['date'] >= '2024-01-01') & (dataframe['date'] < '2025-01-01')]
else:
    print(f"ERROR: File not found: {data_file}")
    import os
    print(f"Available files in {data_dir}:")
    try:
        for f in os.listdir(data_dir):
            print(f"  - {f}")
    except:
        print(f"  Cannot list directory")
    sys.exit(1)

if dataframe.empty:
    print("ERROR: No data loaded!")
    sys.exit(1)

print(f"Loaded {len(dataframe)} bars for {pair} {timeframe}")

# Import indicators
from alphatrend_indicators import alphatrend, squeeze_momentum, wavetrend, choppiness_index
from smc_indicators import calculate_swing_highs_lows, calculate_bos_choch
from kivanc_indicators import supertrend

# Parameters (defaults)
alphatrend_period = 14
alphatrend_coeff = 1.0
adx_threshold = 28
chop_threshold = 50
squeeze_length = 20
wavetrend_channel = 10
wavetrend_average = 21
swing_length = 25
volume_factor = 0.8
confluence_required = 2

print("Calculating indicators...")

# AlphaTrend
at_line, at_signal = alphatrend(dataframe, period=alphatrend_period, coeff=alphatrend_coeff)
dataframe['alphatrend'] = at_line
dataframe['alphatrend_signal'] = at_signal
dataframe['alphatrend_bullish'] = (at_line > at_signal).astype(int)
dataframe['alphatrend_cross_up'] = (
    (dataframe['alphatrend'] > dataframe['alphatrend_signal']) &
    (dataframe['alphatrend'].shift(1) <= dataframe['alphatrend_signal'].shift(1))
).astype(int)

# ADX
dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)

# Choppiness
dataframe['choppiness'] = choppiness_index(dataframe, period=14)

# Squeeze Momentum
squeeze_mom, squeeze_on = squeeze_momentum(dataframe, bb_length=squeeze_length, kc_length=squeeze_length)
dataframe['squeeze_momentum'] = squeeze_mom

# WaveTrend
wt1, wt2 = wavetrend(dataframe, channel_length=wavetrend_channel, average_length=wavetrend_average)
dataframe['wavetrend_bullish'] = (wt1 > wt2).astype(int)

# SuperTrend
st_dir, st_line = supertrend(dataframe, period=10, multiplier=3.0)
dataframe['supertrend_direction'] = st_dir

# BOS/CHoCH
try:
    swings = calculate_swing_highs_lows(dataframe, swing_length=swing_length)
    bos_choch = calculate_bos_choch(dataframe, swings)
    dataframe['bullish_bos'] = (bos_choch['BOS'] == 1).astype(int)
    dataframe['bullish_choch'] = (bos_choch['CHOCH'] == 1).astype(int)
except:
    dataframe['bullish_bos'] = 0
    dataframe['bullish_choch'] = 0

# Volume
dataframe['volume_sma_20'] = dataframe['volume'].rolling(20).mean()

# EMA for HTF filter simulation
dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)

# Now calculate layers
total_bars = len(dataframe)

# LAYER 1 components
at_bullish_count = (dataframe['alphatrend_bullish'] == 1).sum()
adx_pass = (dataframe['adx'] > adx_threshold).sum()
chop_pass = (dataframe['choppiness'] < chop_threshold).sum()

# LAYER 1 combined
trend_ok = (
    (dataframe['alphatrend_bullish'] == 1) &
    (dataframe['adx'] > adx_threshold) &
    (dataframe['choppiness'] < chop_threshold)
)
layer1_count = trend_ok.sum()

# LAYER 2 components
at_cross_count = (dataframe['alphatrend_cross_up'] == 1).sum()
bos_pass = (dataframe['bullish_bos'].rolling(10).max() == 1).sum()
choch_pass = (dataframe['bullish_choch'].rolling(10).max() == 1).sum()

# LAYER 2 combined
trigger_alphatrend = dataframe['alphatrend_cross_up'] == 1
trigger_structure = (
    (dataframe['bullish_bos'].rolling(10).max() == 1) |
    (dataframe['bullish_choch'].rolling(10).max() == 1)
)
entry_trigger = trigger_alphatrend | trigger_structure
layer2_count = entry_trigger.sum()

# LAYER 3 components
confirm_momentum = (dataframe['squeeze_momentum'] > 0).astype(int)
confirm_wavetrend = dataframe['wavetrend_bullish']
confirm_supertrend = (dataframe['supertrend_direction'] == 1).astype(int)
confluence_count = confirm_momentum + confirm_wavetrend + confirm_supertrend
confluence_ok = confluence_count >= confluence_required
layer3_count = confluence_ok.sum()

# LAYER 4
volume_ok = dataframe['volume'] > (dataframe['volume_sma_20'] * volume_factor)
layer4_count = volume_ok.sum()

# Cumulative filtering
after_l1 = trend_ok.sum()
after_l2 = (trend_ok & entry_trigger).sum()
after_l3 = (trend_ok & entry_trigger & confluence_ok).sum()
after_l4 = (trend_ok & entry_trigger & confluence_ok & volume_ok).sum()

# Print results
print(f"""
===============================================================
DIAGNOSTIC - BTC/USDT 2H (2024)
===============================================================
Total bars: {total_bars}

LAYER 1 COMPONENTS (Trend Filter):
- AlphaTrend Bullish: {at_bullish_count:4d} ({at_bullish_count/total_bars*100:5.1f}%)
- ADX > {adx_threshold}:           {adx_pass:4d} ({adx_pass/total_bars*100:5.1f}%)
- Choppiness < {chop_threshold}:      {chop_pass:4d} ({chop_pass/total_bars*100:5.1f}%)

LAYER 2 COMPONENTS (Entry Trigger):
- AT Crossover:       {at_cross_count:4d} ({at_cross_count/total_bars*100:5.1f}%)
- BOS (10 bar):       {bos_pass:4d} ({bos_pass/total_bars*100:5.1f}%)
- CHoCH (10 bar):     {choch_pass:4d} ({choch_pass/total_bars*100:5.1f}%)

LAYER PASS RATES (individual):
- L1 Trend OK:        {layer1_count:4d} ({layer1_count/total_bars*100:5.1f}%)
- L2 Trigger:         {layer2_count:4d} ({layer2_count/total_bars*100:5.1f}%)
- L3 Confluence:      {layer3_count:4d} ({layer3_count/total_bars*100:5.1f}%)
- L4 Volume:          {layer4_count:4d} ({layer4_count/total_bars*100:5.1f}%)

CUMULATIVE FILTERING:
- After L1:           {after_l1:4d} bars remain  (-{total_bars - after_l1} filtered by L1)
- After L1+L2:        {after_l2:4d} bars remain  (-{after_l1 - after_l2} filtered by L2)
- After L1+L2+L3:     {after_l3:4d} bars remain  (-{after_l2 - after_l3} filtered by L3)
- After ALL:          {after_l4:4d} potential entries (-{after_l3 - after_l4} filtered by L4)

BOTTLENECK ANALYSIS:
- L1 filters: {(1 - layer1_count/total_bars)*100:.1f}% of bars
- L2 filters: {(1 - after_l2/max(after_l1, 1))*100:.1f}% of L1-passed bars
- L3 filters: {(1 - after_l3/max(after_l2, 1))*100:.1f}% of L1+L2-passed bars
- L4 filters: {(1 - after_l4/max(after_l3, 1))*100:.1f}% of L1+L2+L3-passed bars
===============================================================
""")
