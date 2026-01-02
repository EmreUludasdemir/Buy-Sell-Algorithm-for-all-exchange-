---
description: How to create a new trading strategy for Freqtrade
---

# Strategy Development Workflow

> [!IMPORTANT] > **Key Rules:**
>
> - Always use `kivanc_indicators.py` for custom indicators
> - Test on T1 (20240601-20241231) and T2 (20230101-20231231) timeranges
> - Never optimize without baseline comparison

## Steps

### 1. Create Strategy File

Copy the base template:

```bash
cp freqtrade/user_data/strategies/EPAStrategyV2.py \
   freqtrade/user_data/strategies/NewStrategyName.py
```

### 2. Strategy Structure

```python
class NewStrategyName(IStrategy):
    INTERFACE_VERSION = 3

    # Timeframe
    timeframe = '4h'

    # Risk parameters
    stoploss = -0.15
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03

    # ROI table
    minimal_roi = {
        "0": 0.10,
        "60": 0.06,
        "120": 0.03,
        "240": 0.02
    }

    # Hyperopt parameters
    buy_adx = IntParameter(20, 50, default=30, space='buy')
    buy_chop = IntParameter(40, 70, default=50, space='buy')

    def populate_indicators(self, dataframe, metadata):
        # Add your indicators
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        # Entry conditions
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        # Exit conditions
        return dataframe
```

### 3. Add Indicators

Import from existing indicator modules:

```python
from kivanc_indicators import add_kivanc_indicators
from smc_indicators import calculate_volatility_regime

def populate_indicators(self, dataframe, metadata):
    # Kıvanç indicators (Supertrend, HalfTrend, QQE, WAE)
    dataframe = add_kivanc_indicators(dataframe)

    # SMC indicators
    dataframe = calculate_volatility_regime(dataframe)

    return dataframe
```

### 4. Implement Entry Logic

```python
def populate_entry_trend(self, dataframe, metadata):
    conditions = []

    # Regime filter
    conditions.append(dataframe['adx'] > self.buy_adx.value)
    conditions.append(dataframe['choppiness'] < self.buy_chop.value)

    # Signal conditions
    conditions.append(dataframe['supertrend_direction'] == 1)
    conditions.append(dataframe['volume'] > dataframe['volume_sma'])

    if conditions:
        dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1

    return dataframe
```

### 5. Add Risk Management

```python
def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
    # ATR-based dynamic stop
    if current_profit > 0.05:
        return -0.02  # Tighten to 2%
    elif current_profit > 0.03:
        return -0.05  # Tighten to 5%
    return -0.15  # Default 15%
```

### 6. Run Backtest

```bash
./scripts/backtest_btc.sh
```

### 7. Hyperopt (if needed)

Optimize parameters if initial results are not satisfactory.

## Checklist

- [ ] Strategy file created
- [ ] Indicators implemented (vectorized, no loops)
- [ ] Entry conditions defined
- [ ] Exit conditions defined
- [ ] Risk management added
- [ ] Backtest passed
- [ ] No repainting or look-ahead bias
- [ ] Type hints added
- [ ] Docstrings added
