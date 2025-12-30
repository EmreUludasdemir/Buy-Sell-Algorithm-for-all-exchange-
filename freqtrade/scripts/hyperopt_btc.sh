#!/bin/bash
# ============================================================================
# EPA Ultimate V3 Hyperopt Script
# ============================================================================
# Hyperopt optimization for EPAUltimateV3 on BTC/USDT
#
# Usage:
#   ./hyperopt_btc.sh
#
# Parameters to optimize:
#   - Buy signals: EMA periods, ADX/Chop thresholds, Kıvanç parameters
#   - Sell signals: Exit conditions
#   - ROI: Return on Investment targets
#   - Stoploss: Stop loss percentage
#
# Loss function: SortinoHyperOptLoss (optimizes Sortino ratio)
# ============================================================================

set -e  # Exit on error

echo "============================================"
echo "EPA Ultimate V3 - Hyperopt Optimization"
echo "============================================"
echo ""

# Configuration
STRATEGY="EPAUltimateV3"
CONFIG="user_data/strategies/config_btc_backtest.json"
TIMEFRAME="4h"
TIMERANGE="20230101-20241231"
PAIRS="BTC/USDT"
EPOCHS=300
LOSS="SortinoHyperOptLoss"
SPACES="buy sell roi stoploss"

echo "Strategy: $STRATEGY"
echo "Timeframe: $TIMEFRAME"
echo "Period: $TIMERANGE"
echo "Pair: $PAIRS"
echo "Epochs: $EPOCHS"
echo "Loss Function: $LOSS"
echo "Spaces: $SPACES"
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
echo "Starting hyperopt optimization..."
echo "This may take several hours depending on your hardware."
echo ""

# Run hyperopt
docker compose run --rm freqtrade hyperopt \
    --strategy "$STRATEGY" \
    --config "$CONFIG" \
    --hyperopt-loss "$LOSS" \
    --spaces $SPACES \
    --epochs "$EPOCHS" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --pairs "$PAIRS" \
    --random-state 42 \
    --min-trades 20

echo ""
echo "============================================"
echo "Hyperopt Complete!"
echo "============================================"
echo ""
echo "Results saved to:"
echo "  - user_data/hyperopt_results/"
echo ""
echo "To view best results:"
echo "  docker compose run --rm freqtrade hyperopt-show -n 10"
echo ""
echo "To export best parameters:"
echo "  docker compose run --rm freqtrade hyperopt-show --best --print-json --no-header"
echo ""
