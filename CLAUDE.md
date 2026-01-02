# EPA Trading Bot - Claude Instructions

## User Context

> [!IMPORTANT]
> The user is not a professional quant/programmer. Follow these guidelines:

### Communication Rules

- **Explain Freqtrade concepts simply** with analogies when possible
- **Always show backtest commands clearly** - full command, not just snippets
- **Explain why we need each indicator** before implementation

### Standard Test Timeranges

Always test on these benchmark periods:

- **T1 (Bull Market)**: `20240601-20241231` - Primary benchmark
- **T2 (Mixed Market)**: `20230101-20231231` - Validation period

### Git Workflow

```bash
# Commit message format
git commit -m "feat: add new RSI divergence indicator"
git commit -m "fix: correct look-ahead bias in entry signal"
git commit -m "test: add backtest for aggressive ROI"
```

### Baseline Comparison Rule

> **NEVER optimize without baseline comparison.** Always run:
>
> 1. Baseline strategy backtest first
> 2. New/modified strategy backtest second
> 3. Compare metrics side-by-side

---

## Project Structure

```text
├── freqtrade/
│   ├── user_data/
│   │   ├── strategies/
│   │   │   ├── EPAStrategyV2.py      # Base EPA strategy
│   │   │   ├── EPAUltimateV3.py      # Kıvanç integration
│   │   │   ├── kivanc_indicators.py  # Supertrend, HalfTrend, QQE, WAE
│   │   │   └── smc_indicators.py     # Smart Money Concepts
│   │   └── config.json               # Bot configuration
│   ├── scripts/
│   │   ├── daily_report.py           # Performance reporting
│   │   ├── run_backtests.py          # Multi-scenario tests
│   │   ├── backtest_btc.sh           # BTC backtest
│   │   └── hyperopt_btc.sh           # Hyperopt optimization
│   └── docker-compose.yml
├── src/                               # Utilities, AI, analysis modules
├── SAFETY.md                          # Security guardrails
└── README.md
```

## Commands

### Lint & Format

```bash
ruff check .
ruff format .
```

### Backtesting

```bash
cd freqtrade
docker compose run --rm freqtrade backtesting \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --timerange 20230101-20241231 \
    --timeframe 4h
```

### Hyperopt

```bash
docker compose run --rm freqtrade hyperopt \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --hyperopt-loss SortinoHyperOptLoss \
    --epochs 300
```

### Docker Controls

```bash
docker compose up -d      # Start bot
docker compose down       # Stop bot
docker compose logs -f    # View logs
```

## Trading Rules

### Risk Management

- **Max Risk**: 2% of wallet per trade
- **Max Leverage**: 3x (conservative)
- **Max Drawdown**: 20% (protection enabled)
- **Position Sizing**: ATR-based dynamic sizing

### Code Quality

1. **Type hints** are mandatory
2. Use **vectorized operations** (no Python loops in indicators)
3. Add **docstrings** to all functions
4. No **magic numbers** - use config parameters

### Indicator Safety

```python
# ❌ REPAINTING - Uses future data
df['signal'] = df['close'].shift(-1)  # NEVER do this

# ✅ CORRECT - Only uses past data
df['signal'] = df['close'].shift(1)
```

### Look-Ahead Bias Check

- Always use `.shift(1)` for indicator signals
- Entry signals cannot use same-candle close prices
- Verify in backtest: `--enable-protections`

## AI Assistant Guidelines

### Safe Commands

```markdown
✅ Run backtest and show results
✅ Analyze strategy performance
✅ Create new indicator file
✅ Explain code changes
```

### Forbidden Actions

```markdown
❌ Edit .env or expose secrets
❌ Run git push --force
❌ Set dry_run: false without review
❌ Deploy to production automatically
```

### PR Guidelines

- Keep changes small and focused
- One feature per commit
- Run backtest before submit
- Update documentation

## Patterns

### Strategy Template

```python
class NewStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    stoploss = -0.15

    # Parameters
    buy_adx = IntParameter(20, 45, default=30, space='buy')

    def populate_indicators(self, dataframe, metadata):
        # Add indicators here
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        # Entry logic here
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        # Exit logic here
        return dataframe
```

### Indicator Convention

```python
# Column naming
dataframe['ema_fast']        # EMA fast line
dataframe['supertrend_dir']  # Supertrend direction (1/-1)
dataframe['qqe_signal']      # QQE signal line
dataframe['volume_sma']      # Volume moving average
```

## Quick Reference

| Action    | Command                     |
| --------- | --------------------------- |
| Backtest  | `./scripts/backtest_btc.sh` |
| Hyperopt  | `./scripts/hyperopt_btc.sh` |
| Start Bot | `docker compose up -d`      |
| View Logs | `docker compose logs -f`    |
| Stop Bot  | `docker compose down`       |
