# Freqtrade Operations

This folder contains the runtime layer for the single supported strategy:
`KivancSupertrendedMovingAverages1D`.

## What Is Kept

- one Docker service
- one strategy and one hyperopt export
- one paper/live-safe config
- one backtest config
- one production profile and one 4H research profile
- one separate futures research config and strategy path
- one profile-safe script runner for research automation

## Commands

```powershell
cd "c:\Users\Emre\Desktop\Buy-sell Algorithm\freqtrade"

# Refresh 1D candles
.\scripts\download_kivanc_1d.ps1

# Full-period backtest
.\scripts\backtest_kivanc_1d.ps1

# Hyperopt the entry space
.\scripts\hyperopt_kivanc_1d.ps1

# Refresh 4H candles for research
.\scripts\download_kivanc_4h.ps1

# Validate the 4H risk profile
.\scripts\backtest_kivanc_4h_risk.ps1

# Compare production-vs-risk profiles on 4H
.\scripts\compare_kivanc_profiles.ps1

# Hyperopt only the 4H risk layer
.\scripts\hyperopt_kivanc_4h_risk.ps1

# Refresh 1D Binance futures candles for long/short research
.\scripts\download_kivanc_futures_1d.ps1

# Full-period futures backtest
.\scripts\backtest_kivanc_futures_1d.ps1

# Regime matrix for futures long/short research
.\scripts\backtest_kivanc_futures_regimes.ps1

# Start the bot
docker compose up -d
```

## Service Name

The compose service remains `bot1_btceth` so existing `docker compose run --rm bot1_btceth ...`
commands still work.

## Files

- Strategy: `user_data/strategies/KivancSupertrendedMovingAverages1D.py`
- Hyperopt params: `user_data/strategies/KivancSupertrendedMovingAverages1D.json`
- Profiles: `user_data/profiles/production_1d.json`, `user_data/profiles/risk_validation_4h.json`
- Runtime config: `user_data/config.json`
- Research config: `user_data/config_production.json`
- Futures research config: `user_data/config_futures_research.json`
- Script runner: `scripts/kivanc_profile_runner.py`
- Futures strategy path: `user_data/strategies_research/KivancSupertrendedMovingAveragesFutures1D.py`

## Profile Rules

- `production_1d` is the default live/paper profile and should match the strategy JSON.
- `risk_validation_4h` is research-only and is applied temporarily by scripts.
- The scripts always back up and restore `user_data/strategies/KivancSupertrendedMovingAverages1D.json`.
- Futures research uses a separate strategy class with `can_short=True` and never replaces the spot production strategy.
