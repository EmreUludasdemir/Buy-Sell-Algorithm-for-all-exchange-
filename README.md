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

_Backtest period: Jan 2023 - Dec 2024 | Pairs: BTC/USDT, ETH/USDT, SOL/USDT | Timeframe: 4h_

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
│   │   │   ├── EPAStrategyV2.py      # EPA Strategy V2
│   │   │   ├── EPAStrategyV2.json    # Optimized params
│   │   │   ├── EPAUltimateV3.py      # 🆕 Ultimate V3 (EPA + Kıvanç)
│   │   │   ├── kivanc_indicators.py  # 🆕 Kıvanç Özbilgiç indicators
│   │   │   ├── smc_indicators.py     # Smart Money Concepts
│   │   │   └── config_btc_backtest.json  # 🆕 BTC backtest config
│   │   └── config.json               # Bot configuration
│   ├── scripts/
│   │   ├── daily_report.py           # Daily performance
│   │   ├── weekly_summary.py         # Weekly summary
│   │   ├── backtest_btc.sh           # 🆕 BTC backtest script
│   │   └── hyperopt_btc.sh           # 🆕 Hyperopt script
│   └── docker-compose.yml
├── EfloudPriceAction_Strategy_v7.pine  # TradingView indicator
└── README.md
```

---

## ⚙️ Strategy Configuration

### 🆕 EPAUltimateV3 - Maximum Confluence Strategy

**The latest and most advanced strategy combining EPA methodology with Kıvanç Özbilgiç's proven indicators.**

#### Key Features

- **📊 EPA Base Filters**: ADX regime, Choppiness Index, EMA system, Volume confirmation
- **🎯 Kıvanç Indicators**: Supertrend, Half Trend, QQE, Waddah Attar Explosion
- **🔄 Multi-Indicator Confluence**: Requires agreement from multiple indicators
- **⚡ Dynamic Risk Management**: Position sizing based on volatility regime
- **🌐 HTF Trend Filter**: 1D timeframe for macro trend alignment
- **🛡️ Advanced Exits**: Multiple reversal signals + Chandelier Exit stops

#### Trading Logic

**Entry Requirements (ALL must be true):**
1. ✅ Trending market (ADX > 30, Choppiness < 50)
2. ✅ EMA alignment (Fast > Slow > Trend EMA)
3. ✅ At least 3 Kıvanç indicators bullish (Supertrend, HalfTrend, QQE)
4. ✅ Waddah Attar shows momentum explosion
5. ✅ Volume confirmation
6. ✅ Daily trend aligned

**Exit Signals:**
- Supertrend or QQE reversal
- EMA cross reversal
- ROI targets (10% → 6% → 4% → 2.5%)
- ATR-based Chandelier Exit stop

#### Performance Targets

| Metric             | Target  |
| ------------------ | ------- |
| Sharpe Ratio       | > 1.0   |
| Win Rate           | > 45%   |
| Max Drawdown       | < 20%   |
| Profit Factor      | > 1.5   |

#### Usage

```bash
# Backtest on BTC/USDT (2023-2025)
cd freqtrade/scripts
./backtest_btc.sh

# Hyperopt parameter optimization
./hyperopt_btc.sh

# Live trading (after backtesting)
docker compose up -d
# Edit config.json to use EPAUltimateV3 strategy
```

#### Hyperopt Parameters

The strategy includes optimizable parameters:

- **EMA**: Fast (8-15), Slow (25-40), Trend (80-120)
- **Regime Filters**: ADX threshold (25-45), Chop threshold (45-65)
- **Supertrend**: Period (7-15), Multiplier (2.0-4.0)
- **Half Trend**: Amplitude (1-4), Deviation (1.5-3.0)
- **QQE**: RSI period (10-20), Factor (3.0-5.0)
- **Risk**: ATR multiplier (2.0-4.0)

---

## ⚙️ EPAStrategyV2 Configuration

### EPAStrategyV2 Parameters

| Parameter      | Value  | Description           |
| -------------- | ------ | --------------------- |
| Timeframe      | 4h     | Trading timeframe     |
| Stoploss       | -20%   | Base stop loss        |
| Trailing Stop  | +31.4% | Activate after profit |
| ADX Threshold  | 32     | Trend strength filter |
| Chop Threshold | 45     | Choppy market filter  |

### Trading Pairs

- ✅ BTC/USDT
- ✅ ETH/USDT
- ✅ SOL/USDT
- ✅ XRP/USDT
- ✅ BNB/USDT
- ✅ ADA/USDT

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

---

## 🎯 Kıvanç Özbilgiç Indicators

The EPAUltimateV3 strategy integrates popular TradingView indicators by **Kıvanç Özbilgiç**, a renowned technical analyst and indicator developer.

### Supertrend
- **Purpose**: Primary trend direction identification
- **Method**: ATR-based dynamic bands
- **Signal**: 1 = Bullish trend, -1 = Bearish trend
- **Parameters**: Period (10), Multiplier (3.0)

### Half Trend
- **Purpose**: Smooth trend detection with reduced whipsaw
- **Method**: ATR channels with amplitude filtering
- **Signal**: Clear trend direction with support/resistance levels
- **Parameters**: Amplitude (2), Channel Deviation (2.0)

### QQE (Quantitative Qualitative Estimation)
- **Purpose**: RSI-based momentum confirmation
- **Method**: Smoothed RSI with dynamic bands
- **Signal**: Excellent for trend confirmation
- **Parameters**: RSI Period (14), Smoothing (5), QQ Factor (4.238)

### Waddah Attar Explosion
- **Purpose**: Volatility and momentum timing
- **Method**: MACD + Bollinger Bands analysis
- **Signal**: Shows "explosion" (high momentum) vs "dead zone" (low momentum)
- **Usage**: Enter during explosions, avoid dead zones
- **Parameters**: Sensitivity (150), Fast (20), Slow (40)

### Why These Indicators?

1. **Proven Track Record**: Used by thousands of traders on TradingView
2. **Complementary Signals**: Each indicator measures different market aspects
3. **Reduced False Signals**: Multi-indicator confluence filters out noise
4. **Adaptable**: Work well across different market conditions

---

## 📈 Backtesting

```bash
# Run backtest
docker compose run --rm freqtrade backtesting \
    --strategy EPAStrategyV2 \
    --config user_data/config.json \
    --timerange 20230101-20241222 \
    --timeframe 4h

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

### Multi-Scenario Backtest

```bash
cd freqtrade/scripts
python run_backtests.py
# Output: reports/multi_scenario_backtest_<timestamp>.json
# Tests: Bull (2023-Q4), Bear (2022-H2), Sideways (2024-Q2) markets
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
