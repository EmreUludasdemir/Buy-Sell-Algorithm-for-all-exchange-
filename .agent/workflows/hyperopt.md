---
description: How to run hyperparameter optimization for trading strategies
---

# Hyperopt Workflow

## Overview

Hyperopt finds optimal strategy parameters by testing thousands of combinations.

## Steps

### 1. Navigate to freqtrade directory

```bash
cd freqtrade
```

### 2. Quick Hyperopt (EPAUltimateV3)

```bash
./scripts/hyperopt_btc.sh
```

> ⚠️ Takes several hours with 300 epochs

### 3. Custom Hyperopt

```bash
docker compose run --rm freqtrade hyperopt \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --hyperopt-loss SortinoHyperOptLoss \
    --spaces buy sell roi stoploss \
    --epochs 150 \
    --timerange 20230101-20241231 \
    --timeframe 4h \
    --min-trades 20
```

### 4. View Best Results

// turbo

```bash
docker compose run --rm freqtrade hyperopt-show -n 10
```

### 5. Export Parameters to JSON

// turbo

```bash
docker compose run --rm freqtrade hyperopt-show --best --print-json --no-header > user_data/strategies/EPAStrategyV2.json
```

### 6. Validate with Backtest

Run a backtest with the new parameters to verify improvement.

## Loss Functions

| Function                     | Optimizes For               |
| ---------------------------- | --------------------------- |
| `SortinoHyperOptLoss`        | Sortino ratio (recommended) |
| `SharpeHyperOptLoss`         | Sharpe ratio                |
| `MaxDrawDownHyperOptLoss`    | Minimize drawdown           |
| `CalmarHyperOptLoss`         | Calmar ratio                |
| `ProfitDrawDownHyperOptLoss` | Profit with DD constraint   |

## Search Spaces

| Space      | What it Optimizes       |
| ---------- | ----------------------- |
| `buy`      | Entry signal parameters |
| `sell`     | Exit signal parameters  |
| `roi`      | ROI table targets       |
| `stoploss` | Stop loss percentage    |
| `trailing` | Trailing stop settings  |

## Tips

1. **Start with fewer epochs** (50-100) to find promising ranges
2. **Use `--random-state 42`** for reproducible results
3. **Set `--min-trades 20`** to avoid overfitting on few trades
4. **Walk-forward validate**: Test on out-of-sample data after optimization
