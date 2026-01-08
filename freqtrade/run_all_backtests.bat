@echo off
setlocal enabledelayedexpansion

echo ============================================
echo EPA Multi-Strategy Backtest
echo Timerange: 2023-01-01 to 2026-01-01
echo ============================================
echo.

set STRATEGIES=EPAUltimateV3 EPASuperTrend EPASuperTrendOptimized EPAMomentum EPASimpleEMA EPAHoldDCA EPASuperTrendAggressive

for %%s in (%STRATEGIES%) do (
    echo Testing: %%s
    docker run --rm -v "%cd%/user_data:/freqtrade/user_data" freqtradeorg/freqtrade:stable backtesting --strategy %%s --config /freqtrade/user_data/config.json --timerange 20230101-20260101 --timeframe 4h --export trades
    echo.
)

echo All backtests completed!
echo Check user_data/backtest_results for results
