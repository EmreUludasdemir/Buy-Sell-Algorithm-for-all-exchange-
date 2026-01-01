# EPAStrategyV4 Development Roadmap

> **Goal**: Next-generation trading strategy combining Smart Money Concepts, Machine Learning, and proven Kıvanç indicators.

---

## 🎯 Target Metrics

| Metric             | Current (V2/V3) | Target (V4) |
| ------------------ | --------------- | ----------- |
| Sharpe Ratio       | 0.54            | > 1.0       |
| Win Rate           | 49%             | > 55%       |
| Max Drawdown       | 24%             | < 15%       |
| Profit Factor      | 1.65            | > 2.0       |
| Avg Trade Duration | 18h             | 12-16h      |

---

## Phase 1: Enhanced SMC Indicators (Week 1-2)

### Order Block Detection

```python
# Bullish Order Block: Last bearish candle before strong bullish move
# Bearish Order Block: Last bullish candle before strong bearish move
def detect_order_blocks(dataframe, swing_lookback=10, min_move_atr=2.0):
    # Implementation: Mark candles where price reversed strongly
    pass
```

### Fair Value Gap (FVG)

```python
# Bullish FVG: When candle[i] low > candle[i-2] high
# Price tends to fill these gaps
def detect_fvg(dataframe):
    pass
```

### Liquidity Grab

```python
# Identify false breakouts that sweep stops before reversing
def detect_liquidity_grab(dataframe, lookback=20):
    pass
```

**Deliverables:**

- [ ] `smc_indicators_v2.py` with Order Blocks, FVG, Liquidity Grabs
- [ ] Unit tests for each indicator
- [ ] Integration with EPAStrategyV4

---

## Phase 2: ML Signal Validation (Week 3-4)

### Feature Engineering

| Feature              | Source            | Purpose                |
| -------------------- | ----------------- | ---------------------- |
| `kivanc_agreement`   | Kıvanç indicators | Confluence score (0-4) |
| `ob_distance_atr`    | Order Blocks      | Distance to nearest OB |
| `fvg_present`        | FVG               | Entry at gap fill      |
| `vol_regime`         | ATR Z-score       | Volatility context     |
| `htf_trend_strength` | Daily ADX         | Macro trend confidence |

### Model Options

1. **XGBoost Classifier** - Fast, interpretable, good for tabular data
2. **LightGBM** - Better for larger datasets
3. **Simple Ensemble** - Combine multiple weak classifiers

### Training Pipeline

```bash
# 1. Extract features from historical trades
python scripts/extract_ml_features.py --strategy EPAUltimateV3 --period 2023-2024

# 2. Train model
python scripts/train_ml_model.py --model xgboost --target win_loss

# 3. Validate with walk-forward
python scripts/validate_ml.py --splits 5 --test_size 0.2
```

**Deliverables:**

- [ ] `ml_signals.py` with feature extraction
- [ ] `ml_models/` directory with trained models
- [ ] Integration hook in EPAStrategyV4

---

## Phase 3: Multi-Timeframe Confirmation (Week 5)

### MTF Architecture

```
1D  → Macro trend direction (EMA-based)
4H  → Primary entry timeframe
1H  → Confirmation and precision timing
15m → (Optional) Scalp entries in strong trends
```

### Implementation

```python
def informative_pairs(self):
    pairs = self.dp.current_whitelist()
    return [
        (pair, '1d') for pair in pairs
    ] + [
        (pair, '1h') for pair in pairs
    ]
```

**Deliverables:**

- [ ] 1H confirmation logic
- [ ] MTF trend agreement scoring
- [ ] Adjusted position sizing based on MTF confluence

---

## Phase 4: Multi-Exchange Support (Week 6)

### Target Exchanges

1. **Bybit Perpetual Futures** - 2x leverage, funding rate consideration
2. **OKX Spot** - Backup exchange
3. **Kraken** - Fiat on/off ramp

### Adaptation Requirements

| Feature     | Spot | Futures           |
| ----------- | ---- | ----------------- |
| Short       | ❌   | ✅                |
| Leverage    | 1x   | 2-3x              |
| Funding     | N/A  | Hourly check      |
| Liquidation | N/A  | Calculate & avoid |

**Deliverables:**

- [ ] `config_bybit.json` with futures settings
- [ ] Funding rate integration
- [ ] Liquidation price calculator

---

## Phase 5: Performance Optimization (Week 7-8)

### Vectorization

```python
# Convert loop-based to vectorized
# Before: for i in range(period, len(dataframe))
# After: Use numpy operations with shift()
```

### Caching

```python
# Cache indicator calculations across pairs
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_supertrend(pair, timeframe, period, multiplier):
    pass
```

### Profiling

```bash
python -m cProfile -o profile.out scripts/backtest_btc.sh
snakeviz profile.out
```

---

## File Structure (Final)

```
freqtrade/user_data/strategies/
├── EPAStrategyV4.py              # Main strategy
├── EPAStrategyV4.json            # Hyperopt parameters
├── indicators/
│   ├── kivanc_indicators_v2.py   # Optimized Kıvanç
│   ├── smc_indicators_v2.py      # Enhanced SMC
│   └── ml_signals.py             # ML predictions
├── ml_models/
│   ├── xgb_signal_validator.pkl  # Trained model
│   └── feature_scaler.pkl        # Feature normalization
└── configs/
    ├── config_binance_spot.json
    ├── config_bybit_futures.json
    └── config_btc_only.json
```

---

## Risk Considerations

> [!CAUTION]
>
> - **Overfitting**: Use walk-forward validation for ML models
> - **Repainting**: All indicators must use `.shift(1)` for signals
> - **Leverage**: Max 3x, prefer 2x for safety
> - **Paper Trade**: Minimum 4 weeks before any live capital

---

## Timeline Summary

| Phase               | Duration | Status         |
| ------------------- | -------- | -------------- |
| 1. SMC Indicators   | 2 weeks  | ⏳ Not started |
| 2. ML Validation    | 2 weeks  | ⏳ Not started |
| 3. MTF Confirmation | 1 week   | ⏳ Not started |
| 4. Multi-Exchange   | 1 week   | ⏳ Not started |
| 5. Optimization     | 2 weeks  | ⏳ Not started |

**Total: ~8 weeks to production-ready V4**
