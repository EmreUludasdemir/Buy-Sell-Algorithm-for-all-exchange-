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
- one filtered-futures research config for the validated 4-pair subset
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

# Full-period filtered futures backtest
.\scripts\backtest_kivanc_futures_filtered_1d.ps1

# Regime matrix for the validated filtered-futures subset
.\scripts\backtest_kivanc_futures_filtered_regimes.ps1

# Hyperopt only the futures risk layer, with safe keep-or-reject logic
.\scripts\hyperopt_kivanc_futures_1d_risk.ps1

# Hyperopt only the futures buy layer, with the same keep-or-reject validation
.\scripts\hyperopt_kivanc_futures_1d_buy.ps1

# Build a spot-vs-futures decision table from the latest regime reports
.\scripts\compare_kivanc_spot_vs_futures_1d.ps1

# Ask the latest decision table which mode should be preferred
.\scripts\select_kivanc_runtime_mode.ps1
.\scripts\select_kivanc_runtime_mode.ps1 -Scenario bull_2024
.\scripts\select_kivanc_runtime_mode.ps1 -Date 2025-07-15

# Use the selector output to launch the matching spot or futures backtest
.\scripts\run_kivanc_selected_backtest.ps1 -Scenario bull_2024

# Scan 3-5 pair futures subsets with the current baseline params
.\scripts\backtest_kivanc_futures_pairsets.ps1

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
- Filtered futures config: `user_data/config_futures_filtered_research.json`
- Script runner: `scripts/kivanc_profile_runner.py`
- Futures strategy path: `user_data/strategies_research/KivancSupertrendedMovingAveragesFutures1D.py`
- Futures workflow helper: `scripts/kivanc_futures_workflow.py`
- Runtime selector: `scripts/kivanc_runtime_selector.py`
- Runtime launcher: `scripts/run_kivanc_selected_backtest.ps1`
- Futures pairset scan: `scripts/kivanc_futures_pairset_scan.py`

## Profile Rules

- `production_1d` is the default live/paper profile and should match the strategy JSON.
- `risk_validation_4h` is research-only and is applied temporarily by scripts.
- The scripts always back up and restore `user_data/strategies/KivancSupertrendedMovingAverages1D.json`.
- Futures research uses a separate strategy class with `can_short=True` and never replaces the spot production strategy.
- Filtered futures research uses the same strategy class but a tighter whitelist: `BTC/USDT:USDT ETH/USDT:USDT BNB/USDT:USDT XRP/USDT:USDT`.
- Futures risk hyperopt only writes `user_data/strategies_research/KivancSupertrendedMovingAveragesFutures1D.json` if the validated candidate improves on the current futures baseline.
- Futures buy hyperopt follows the same validation rule and also leaves the current params untouched when the candidate is worse.
- The runtime selector is advisory only. It reads the latest comparison report and returns a recommended mode; it does not reconfigure the bot by itself.
- The runtime launcher is execution-oriented. It uses the selector output to run the correct spot or futures backtest for the selected scenario.
- The pairset scan is research-only. It does not change the futures params file and is used to test whether a smaller whitelist improves the current baseline.
