# 🏗️ EPA Trading Bot - Architecture

## Overview

The EPA Trading Bot is a **Freqtrade-based algorithmic trading system** implementing Efloud Price Action methodology with Smart Money Concepts (SMC).

```
┌─────────────────────────────────────────────────────────────┐
│                    EPA Trading Bot                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │  Strategies │    │  Indicators │    │   Configs   │    │
│  │             │    │             │    │             │    │
│  │ EPAUltimate │    │   Kıvanç    │    │   Binance   │    │
│  │ EPAFutures  │    │    SMC      │    │   Bybit     │    │
│  │ EPASimple   │    │  AlphaTrend │    │   Futures   │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            ▼                               │
│                  ┌─────────────────┐                       │
│                  │    Freqtrade    │                       │
│                  │     Engine      │                       │
│                  └────────┬────────┘                       │
│                           │                                │
│         ┌─────────────────┼─────────────────┐             │
│         ▼                 ▼                 ▼             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Backtesting │  │   Paper    │  │    Live     │       │
│  │              │  │  Trading   │  │   Trading   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
Buy-Sell-Algorithm-for-all-exchange-/
├── freqtrade/                      # Main Freqtrade bot
│   ├── user_data/
│   │   ├── strategies/             # Trading strategies
│   │   │   ├── EPAFuturesPro.py   # Futures strategy (Long+Short)
│   │   │   ├── EPAUltimateV3.py   # Main spot strategy
│   │   │   ├── kivanc_indicators.py  # Kıvanç Özbilgiç indicators
│   │   │   ├── smc_indicators.py     # Smart Money Concepts
│   │   │   └── config_*.json      # Strategy configs
│   │   ├── data/                  # Historical data (gitignored)
│   │   ├── backtest_results/      # Backtest outputs (gitignored)
│   │   └── config.json            # Main bot config
│   ├── scripts/                   # Automation scripts
│   │   ├── backtest_futures.sh
│   │   ├── hyperopt_futures.sh
│   │   └── daily_report.py
│   └── docker-compose.yml         # Docker setup
│
├── src/                           # AI trading signals (experimental)
│   ├── ai/                        # ML models
│   ├── analysis/                  # Technical analysis
│   ├── data/                      # Data fetching
│   └── signals/                   # Signal generation
│
├── tests/                         # Test suite
│   ├── conftest.py               # Pytest fixtures
│   └── test_strategy_sanity.py   # Strategy tests
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md           # This file
│   └── CONTRIBUTING.md           # Contribution guide
│
├── .github/workflows/             # CI/CD
│   └── ci.yml                    # GitHub Actions
│
├── *.pine                         # TradingView indicators
├── Makefile                       # Build commands
├── pyproject.toml                 # Project config
└── requirements.txt               # Python dependencies
```

---

## Strategy Architecture

### EPAFuturesPro (Recommended for Futures)

```
Entry Logic:
┌─────────────────────────────────────────────────────────────┐
│  1. TRIPLE SUPERTREND (2/3 must agree)                     │
│     ST1: Period 10, Mult 1.5 (Fast)                        │
│     ST2: Period 11, Mult 2.0 (Medium)                      │
│     ST3: Period 12, Mult 3.0 (Slow)                        │
├─────────────────────────────────────────────────────────────┤
│  2. TREND FILTERS                                          │
│     • ADX > 25 (Strong trend)                              │
│     • EMA 200 (Major trend direction)                      │
│     • RSI (Momentum, 30-70 range)                          │
├─────────────────────────────────────────────────────────────┤
│  3. SCORING SYSTEM (4/6 required)                          │
│     • SuperTrend bullish/bearish                           │
│     • ADX + DI confirmation                                │
│     • RSI momentum                                         │
│     • EMA 200 position                                     │
│     • MACD signal                                          │
│     • EMA crossover                                        │
├─────────────────────────────────────────────────────────────┤
│  4. RISK MANAGEMENT                                        │
│     • ATR-based Stop Loss (1.5x ATR)                       │
│     • ATR-based Take Profit (3x ATR)                       │
│     • Trailing Stop (2% offset)                            │
└─────────────────────────────────────────────────────────────┘
```

### EPAUltimateV3 (Recommended for Spot)

Combines EPA methodology with Kıvanç Özbilgiç indicators:
- **SuperTrend**: Primary trend direction
- **Half Trend**: Smooth trend with reduced whipsaw
- **QQE**: RSI-based momentum confirmation
- **Waddah Attar Explosion**: Volatility timing

---

## Indicator Modules

### kivanc_indicators.py

Implements popular TradingView indicators by Kıvanç Özbilgiç:

| Indicator | Purpose | Key Parameters |
|-----------|---------|----------------|
| SuperTrend | Trend direction | Period: 10, Mult: 3.0 |
| Half Trend | Smooth trends | Amplitude: 2, Dev: 2.0 |
| QQE | Momentum | RSI: 14, Factor: 4.238 |
| WAE | Volatility | Sensitivity: 150 |

### smc_indicators.py

Smart Money Concepts implementation:

| Indicator | Purpose |
|-----------|---------|
| Order Blocks | Institutional zones |
| Fair Value Gaps | Imbalance detection |
| Break of Structure | Trend change signals |
| Liquidity Grabs | Stop hunt detection |

---

## Data Flow

```
Exchange API → Freqtrade Engine → Strategy
                    │
                    ├─→ populate_indicators() → Technical Analysis
                    │
                    ├─→ populate_entry_trend() → Entry Signals
                    │
                    ├─→ populate_exit_trend() → Exit Signals
                    │
                    └─→ custom_stoploss() → Risk Management
```

---

## Configuration

### Environment Variables

```bash
# .env file (never commit!)
FREQTRADE__EXCHANGE__KEY=your_api_key
FREQTRADE__EXCHANGE__SECRET=your_api_secret
FREQTRADE__TELEGRAM__TOKEN=telegram_bot_token
FREQTRADE__TELEGRAM__CHAT_ID=your_chat_id
```

### Exchange Configs

| Exchange | Config File | Trading Mode |
|----------|-------------|--------------|
| Binance | config.json | Spot |
| Binance Futures | config_futures.json | Futures |

---

## Testing Strategy

1. **Unit Tests**: Indicator calculations
2. **Sanity Tests**: Strategy doesn't crash
3. **Lookahead Tests**: No future data usage
4. **Backtests**: Historical performance
5. **Paper Trading**: Live simulation

---

## Performance Targets

| Metric | Target | Warning |
|--------|--------|---------|
| Win Rate | > 45% | < 35% |
| Profit Factor | > 1.5 | < 1.2 |
| Max Drawdown | < 25% | > 35% |
| Sharpe Ratio | > 1.0 | < 0.5 |

---

## Safety Guidelines

⚠️ **Always:**
- Paper trade first (minimum 2 weeks)
- Start with small position sizes
- Enable all protections (StoplossGuard, MaxDrawdown)
- Monitor live trading closely

❌ **Never:**
- Trade with money you can't afford to lose
- Disable risk protections
- Use excessive leverage (max 3x recommended)
- Trust backtest results blindly
