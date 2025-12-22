# 🚀 EPA Trading Bot - Algorithmic Crypto Trading

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Freqtrade](https://img.shields.io/badge/Freqtrade-2025.11-green.svg)](https://www.freqtrade.io/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL%202.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![Trading](https://img.shields.io/badge/Trading-Spot-orange.svg)](https://www.binance.com/)

**High-performance algorithmic trading bot** based on Efloud Price Action methodology with Smart Money Concepts. Built for Freqtrade with optimized parameters for BTC/USDT and BNB/USDT pairs.

---

## 📊 Performance Metrics (2-Year Backtest)

| Metric            | Value   |
| ----------------- | ------- |
| **Total Profit**  | +90.05% |
| **CAGR**          | 38.73%  |
| **Profit Factor** | 1.65    |
| **Win Rate**      | 49.1%   |
| **Max Drawdown**  | 24.04%  |
| **Sharpe Ratio**  | 0.54    |
| **Calmar Ratio**  | 10.00   |

_Backtest period: Jan 2023 - Dec 2024 | Pairs: BTC/USDT, BNB/USDT | Timeframe: 1h_

---

## ✨ Features

- 🎯 **Smart Money Concepts** - ADX regime filtering, Choppiness Index
- 📈 **Price Action Signals** - EMA crossovers, breakouts, SFP patterns
- 🛡️ **Risk Management** - ATR-based stops, trailing protection
- ⚡ **Optimized Parameters** - Hyperopt tuned for maximum Sortino
- 🔒 **Built-in Protections** - Cooldown, StoplossGuard, MaxDrawdown

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Binance API keys (for live trading)

### Installation

```bash
# Clone repository
git clone https://github.com/EmreUludasdemir/Buy-Sell-Algorithm-for-all-exchange-.git
cd Buy-Sell-Algorithm-for-all-exchange-/freqtrade

# Start bot (paper trading)
docker compose up -d

# Check logs
docker compose logs -f
```

### Web UI Access

```
URL: http://127.0.0.1:8080
Username: freqtrade
Password: (see config.json)
```

---

## 📁 Project Structure

```
├── freqtrade/
│   ├── user_data/
│   │   ├── strategies/
│   │   │   ├── EPAStrategyV2.py      # Main strategy
│   │   │   ├── EPAStrategyV2.json    # Optimized params
│   │   │   └── smc_indicators.py     # Shared indicators
│   │   └── config.json               # Bot configuration
│   ├── scripts/
│   │   ├── daily_report.py           # Daily performance
│   │   └── weekly_summary.py         # Weekly summary
│   └── docker-compose.yml
├── EfloudPriceAction_Strategy_v7.pine  # TradingView indicator
└── README.md
```

---

## ⚙️ Strategy Configuration

### EPAStrategyV2 Parameters

| Parameter      | Value  | Description           |
| -------------- | ------ | --------------------- |
| Timeframe      | 15m    | Trading timeframe     |
| Stoploss       | -20%   | Base stop loss        |
| Trailing Stop  | +31.4% | Activate after profit |
| ADX Threshold  | 32     | Trend strength filter |
| Chop Threshold | 45     | Choppy market filter  |

### Trading Pairs

- ✅ BTC/USDT (+66.71%)
- ✅ BNB/USDT (+23.34%)
- ❌ ETH/USDT (removed - underperformed)

---

## 🛡️ Risk Management

### Built-in Protections

```python
protections = [
    {"method": "CooldownPeriod", "stop_duration_candles": 12},
    {"method": "StoplossGuard", "trade_limit": 2, "stop_duration_candles": 24},
    {"method": "MaxDrawdown", "max_allowed_drawdown": 0.12}
]
```

### Risk Philosophy

> _"NEVER go all in. It could be a trap, project could fail, BTC could dump."_
> — @EfloudTheSurfer

---

## 📈 Backtesting

```bash
# Run backtest
docker compose run --rm freqtrade backtesting \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --timerange 20230101-20241222 \
    --timeframe 1h

# Hyperopt optimization
docker compose run --rm freqtrade hyperopt \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --hyperopt-loss SortinoHyperOptLoss \
    --epochs 150
```

---

## 🔧 Development

### Daily Report Generation

```bash
python scripts/daily_report.py
# Output: reports/YYYY-MM-DD.json
```

### Weekly Summary

```bash
python scripts/weekly_summary.py
# Output: reports/summary.md
```

---

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Past performance does not guarantee future results
- Cryptocurrency trading involves substantial risk of loss
- Never trade with money you cannot afford to lose
- The authors are not responsible for any financial losses

---

## 📜 License

Mozilla Public License 2.0

---

## 🙏 Credits

- **Methodology**: [@EfloudTheSurfer](https://twitter.com/EfloudTheSurfer)
- **Framework**: [Freqtrade](https://www.freqtrade.io/)
- **Concepts**: ICT Smart Money Concepts

---

<p align="center">
  <b>⭐ Star this repo if you find it useful! ⭐</b>
</p>
