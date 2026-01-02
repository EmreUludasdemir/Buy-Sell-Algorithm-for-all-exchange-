---
description: How to implement new indicators using kivanc_indicators.py
---

# Indicator Implementation Workflow

> [!IMPORTANT] > **Always explain WHY we need each indicator before implementing it.**

## Steps

### 1. Identify the Purpose

Before adding any indicator, answer:

- What market condition does this indicator detect?
- How will it improve entry/exit timing?
- Does it complement existing indicators?

### 2. Check Existing Indicators

Review `kivanc_indicators.py` for available indicators:

```python
# Available in kivanc_indicators.py:
# - Supertrend: Trend direction and dynamic support/resistance
# - HalfTrend: Trend confirmation with less noise
# - QQE (Qualitative Quantitative Estimation): Momentum with smoothing
# - WAE (Waddah Attar Explosion): Trend strength and momentum
```

// turbo

```bash
# View available indicator functions
grep "^def " freqtrade/user_data/strategies/kivanc_indicators.py
```

### 3. Implement New Indicator

Add to `kivanc_indicators.py` with:

```python
def calculate_new_indicator(dataframe: DataFrame, period: int = 14) -> DataFrame:
    """
    Calculate [Indicator Name].

    WHY: [Explain the purpose - e.g., "Detects momentum divergence"]

    Args:
        dataframe: OHLCV DataFrame
        period: Lookback period

    Returns:
        DataFrame with new indicator columns
    """
    # Use vectorized operations (NO Python loops!)
    dataframe['indicator_name'] = ta.SMA(dataframe['close'], timeperiod=period)

    return dataframe
```

### 4. Naming Convention

```python
# Column naming pattern
dataframe['indicator_value']     # Raw indicator value
dataframe['indicator_signal']    # Signal line
dataframe['indicator_direction'] # Direction: 1 (up), -1 (down), 0 (neutral)
dataframe['indicator_cross']     # Crossover: 1 (bullish), -1 (bearish)
```

### 5. Avoid Look-Ahead Bias

```python
# ❌ WRONG - Uses future data
dataframe['signal'] = dataframe['close'].shift(-1)

# ✅ CORRECT - Only uses past data
dataframe['signal'] = dataframe['close'].shift(1)
```

### 6. Test the Indicator

// turbo

```bash
# Run syntax check
python -m py_compile freqtrade/user_data/strategies/kivanc_indicators.py
```

```bash
# Run backtest with new indicator
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3 --config user_data/config.json --timerange 20240601-20241231
```

## Checklist

- [ ] Indicator purpose explained
- [ ] Added to `kivanc_indicators.py`
- [ ] Uses vectorized operations (no loops)
- [ ] No look-ahead bias
- [ ] Type hints included
- [ ] Docstring with WHY explanation
- [ ] Syntax check passed
- [ ] Backtest completed on T1/T2
