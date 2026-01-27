#!/bin/bash
# ============================================================================
# MACD-V Strategy Backtest Script
# ============================================================================
# MACD-V (Volatility Normalized MACD) backtest on multiple pairs
#
# MACD-V Formülü:
#   MACD-V = [(12-EMA - 26-EMA) / ATR(26)] × 100
#
# Usage:
#   ./backtest_macdv.sh [timerange]
#
# Examples:
#   ./backtest_macdv.sh                    # Default: 20240601-20241231 (Bull Market)
#   ./backtest_macdv.sh 20230101-20231231  # Custom range (Mixed Market)
#
# Requirements:
#   - Docker and Docker Compose installed
#   - Freqtrade docker image available
# ============================================================================

set -e  # Exit on error

echo "============================================"
echo "MACD-V Strategy Backtest"
echo "Volatility Normalized Momentum"
echo "============================================"
echo ""

# Configuration
STRATEGY="MACDVStrategy"
CONFIG="user_data/config.json"
TIMEFRAME="4h"
TIMERANGE="${1:-20240601-20241231}"  # Default: Bull Market benchmark (T1)
PAIRS="BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT"

echo "Strategy: $STRATEGY"
echo "Timeframe: $TIMEFRAME"
echo "Period: $TIMERANGE"
echo "Pairs: $PAIRS"
echo ""

# Download data if needed
echo "📥 Downloading/updating historical data..."
docker compose run --rm freqtrade download-data \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --pairs $PAIRS \
    --trading-mode spot \
    --exchange binance

echo ""
echo "🚀 Starting backtest..."
echo ""

# Run backtest
docker compose run --rm freqtrade backtesting \
    --strategy "$STRATEGY" \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe "$TIMEFRAME" \
    --breakdown month \
    --export trades \
    --export-filename "user_data/backtest_results/macdv_${TIMERANGE}.json"

echo ""
echo "============================================"
echo "✅ MACD-V Backtest Complete!"
echo "============================================"
echo ""
echo "📊 Results saved to:"
echo "  - user_data/backtest_results/"
echo ""
echo "📈 To view detailed results:"
echo "  docker compose run --rm freqtrade backtesting-show"
echo ""
echo "🔄 To run on Mixed Market period (T2):"
echo "  ./backtest_macdv.sh 20230101-20231231"
echo ""
