#!/bin/bash
# ============================================================================
# MACD-V Strategy Hyperopt Script
# ============================================================================
# Optimize MACD-V parameters using Sortino ratio
#
# Optimizes:
#   - Fast/Slow EMA periods (8-15 / 20-30)
#   - Signal EMA period (7-12)
#   - ATR period (20-30)
#   - Overbought/Oversold levels (120-180 / -180 to -120)
#   - Neutral zone bounds (30-70 / -70 to -30)
#
# Usage:
#   ./hyperopt_macdv.sh [epochs]
#
# Examples:
#   ./hyperopt_macdv.sh       # Default: 200 epochs
#   ./hyperopt_macdv.sh 500   # Custom: 500 epochs
# ============================================================================

set -e

echo "============================================"
echo "MACD-V Strategy Hyperopt"
echo "Parameter Optimization"
echo "============================================"
echo ""

# Configuration
STRATEGY="MACDVStrategy"
CONFIG="user_data/config.json"
TIMEFRAME="4h"
TIMERANGE="20240101-20241231"
EPOCHS="${1:-200}"
LOSS_FUNCTION="SortinoHyperOptLoss"

echo "Strategy: $STRATEGY"
echo "Timeframe: $TIMEFRAME"
echo "Period: $TIMERANGE"
echo "Epochs: $EPOCHS"
echo "Loss Function: $LOSS_FUNCTION"
echo ""

# Download data first
echo "📥 Downloading/updating historical data..."
docker compose run --rm freqtrade download-data \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --trading-mode spot \
    --exchange binance

echo ""
echo "🔧 Starting hyperopt optimization..."
echo ""

# Run hyperopt
docker compose run --rm freqtrade hyperopt \
    --strategy "$STRATEGY" \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --hyperopt-loss "$LOSS_FUNCTION" \
    --epochs "$EPOCHS" \
    --spaces buy \
    --random-state 42 \
    --min-trades 20

echo ""
echo "============================================"
echo "✅ Hyperopt Complete!"
echo "============================================"
echo ""
echo "📊 To apply best parameters:"
echo "  1. Check the output above for best parameters"
echo "  2. Update MACDVStrategy.py with optimized values"
echo "  3. Run backtest to verify: ./backtest_macdv.sh"
echo ""
