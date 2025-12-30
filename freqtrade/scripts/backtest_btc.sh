#!/bin/bash
# ============================================================================
# EPA Ultimate V3 Backtest Script
# ============================================================================
# Backtest EPAUltimateV3 on BTC/USDT with monthly breakdown
#
# Usage:
#   ./backtest_btc.sh
#
# Requirements:
#   - Docker and Docker Compose installed
#   - Freqtrade docker image available
#   - Historical data downloaded (will download if missing)
# ============================================================================

set -e  # Exit on error

echo "============================================"
echo "EPA Ultimate V3 - BTC/USDT Backtest"
echo "============================================"
echo ""

# Configuration
STRATEGY="EPAUltimateV3"
CONFIG="user_data/strategies/config_btc_backtest.json"
TIMEFRAME="4h"
TIMERANGE="20230101-20251230"
PAIRS="BTC/USDT"

echo "Strategy: $STRATEGY"
echo "Timeframe: $TIMEFRAME"
echo "Period: $TIMERANGE"
echo "Pair: $PAIRS"
echo ""

# Download data if needed
echo "Downloading/updating historical data..."
docker compose run --rm freqtrade download-data \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --pairs "$PAIRS" \
    --trading-mode spot \
    --exchange binance

echo ""
echo "Starting backtest..."
echo ""

# Run backtest
docker compose run --rm freqtrade backtesting \
    --strategy "$STRATEGY" \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --pairs "$PAIRS" \
    --breakdown month \
    --export trades

echo ""
echo "============================================"
echo "Backtest Complete!"
echo "============================================"
echo ""
echo "Results saved to:"
echo "  - user_data/backtest_results/"
echo ""
echo "To view detailed results:"
echo "  docker compose run --rm freqtrade backtesting-show"
echo ""
