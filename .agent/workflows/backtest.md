---
description: How to run backtests for EPA Trading Bot strategies
---

# Backtest Workflow

## Prerequisites

- Docker and Docker Compose installed
- Historical data available (will auto-download if missing)

## Steps

### 1. Navigate to freqtrade directory

```bash
cd freqtrade
```

### 2. Quick Backtest (Standard T1 Timerange)

// turbo

```bash
# T1: Bull Market (Primary Benchmark)
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3 --config user_data/config.json --timerange 20240601-20241231 --timeframe 4h
```

### 2b. Validation Backtest (T2 Timerange)

```bash
# T2: Mixed Market (Validation)
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3 --config user_data/config.json --timerange 20230101-20231231 --timeframe 4h
```

### 3. Custom Backtest

```bash
docker compose run --rm freqtrade backtesting \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --timerange 20230101-20241231 \
    --timeframe 4h \
    --pairs BTC/USDT ETH/USDT \
    --breakdown month \
    --export trades
```

### 4. View Results

// turbo

```bash
docker compose run --rm freqtrade backtesting-show
```

### 5. Multi-Scenario Test

```bash
python scripts/run_backtests.py
```

Results saved to: `reports/multi_scenario_backtest_<timestamp>.json`

## Key Parameters

| Parameter     | Description         | Example             |
| ------------- | ------------------- | ------------------- |
| `--strategy`  | Strategy class name | `EPAStrategyV2`     |
| `--timerange` | Date range          | `20230101-20241231` |
| `--timeframe` | Candle timeframe    | `4h`                |
| `--pairs`     | Trading pairs       | `BTC/USDT ETH/USDT` |
| `--breakdown` | Results breakdown   | `month` or `day`    |
| `--export`    | Export trades       | `trades`            |

## Interpreting Results

| Metric        | Good  | Warning |
| ------------- | ----- | ------- |
| Profit Factor | > 1.5 | < 1.2   |
| Win Rate      | > 45% | < 40%   |
| Max Drawdown  | < 20% | > 25%   |
| Sharpe Ratio  | > 0.8 | < 0.5   |
