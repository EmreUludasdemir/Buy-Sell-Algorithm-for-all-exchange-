# 🤝 Contributing to EPA Trading Bot

Thank you for your interest in contributing! This document explains how to set up your development environment and contribute effectively.

---

## 📋 Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

---

## 🚀 Quick Setup

```bash
# Clone the repository
git clone https://github.com/EmreUludasdemir/Buy-Sell-Algorithm-for-all-exchange-.git
cd Buy-Sell-Algorithm-for-all-exchange-

# Install dependencies
make install

# Verify setup
make verify
```

---

## 🛠️ Development Commands

All commands are available via `make`. Run `make help` to see all options.

### Code Quality

```bash
# Run linter
make lint

# Run linter and fix issues
make lint-fix

# Format code
make format

# Check formatting without changes
make format-check

# Run type checker (optional)
make typecheck
```

### Testing

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run tests with coverage
make test-cov
```

### Backtesting

```bash
# Download historical data
make download-data

# Run backtest (default strategy)
make backtest

# Run backtest with custom params
make backtest STRATEGY=EPAFuturesPro TIMERANGE=20240101-20241231

# Run hyperopt
make hyperopt STRATEGY=EPAUltimateV3 EPOCHS=200
```

### Docker

```bash
# Start bot (paper trading)
make docker-up

# View logs
make docker-logs

# Stop bot
make docker-down
```

---

## 📁 Project Structure

```
├── freqtrade/user_data/strategies/  # Add new strategies here
├── tests/                           # Add tests here
├── docs/                            # Documentation
└── .github/workflows/               # CI/CD
```

---

## ✅ Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code passes linting: `make lint`
- [ ] Code is formatted: `make format`
- [ ] Tests pass: `make test`
- [ ] New code has tests (if applicable)
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages are clear and descriptive

---

## 🧪 Adding a New Strategy

1. Create strategy file in `freqtrade/user_data/strategies/`:

```python
# freqtrade/user_data/strategies/MyNewStrategy.py

from freqtrade.strategy import IStrategy
from pandas import DataFrame

class MyNewStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '4h'
    can_short = False  # Set True for futures

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add your indicators here
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add entry conditions
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add exit conditions
        return dataframe
```

2. Add tests in `tests/test_my_strategy.py`:

```python
import pytest

class TestMyNewStrategy:
    @pytest.mark.unit
    def test_populate_indicators(self, sample_ohlcv_data):
        from MyNewStrategy import MyNewStrategy
        strategy = MyNewStrategy({})
        result = strategy.populate_indicators(sample_ohlcv_data.copy(), {"pair": "BTC/USDT"})
        assert result is not None
```

3. Run backtest:

```bash
make backtest STRATEGY=MyNewStrategy TIMERANGE=20240101-20241231
```

---

## 🧪 Adding Tests

Tests are located in `tests/` directory. We use pytest.

### Test Categories

- **Unit tests** (`@pytest.mark.unit`): Fast, isolated tests
- **Integration tests** (`@pytest.mark.integration`): Tests with dependencies
- **Slow tests** (`@pytest.mark.slow`): Long-running tests

### Available Fixtures (conftest.py)

- `sample_ohlcv_data`: 100 candles of realistic BTC data
- `empty_ohlcv_data`: Empty DataFrame for edge cases
- `short_ohlcv_data`: 5 candles for edge cases
- `trending_up_data`: Strong uptrend data
- `trending_down_data`: Strong downtrend data

### Example Test

```python
@pytest.mark.unit
def test_my_indicator(sample_ohlcv_data):
    result = my_indicator(sample_ohlcv_data)
    assert result is not None
    assert len(result) == len(sample_ohlcv_data)
```

---

## 📝 Commit Message Format

Use clear, descriptive commit messages:

```
feat: Add new indicator X
fix: Correct look-ahead bias in Y
test: Add tests for Z strategy
docs: Update README with new commands
refactor: Simplify entry logic
```

---

## 🔒 Security

- **Never commit API keys or secrets**
- Use `.env` file for sensitive data (it's gitignored)
- Report security issues privately to the maintainers

---

## ❓ Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Include relevant logs and backtest results when reporting issues

---

## 📜 License

By contributing, you agree that your contributions will be licensed under MPL-2.0.
