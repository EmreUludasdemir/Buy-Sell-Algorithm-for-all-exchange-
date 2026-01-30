#!/bin/bash
# ============================================================================
# EMA Breakout Volume Strategy Backtest Script
# ============================================================================
# EGM (Earnings Growth Momentum) metodolojisinden ilham alan
# EMA Ribbon + Volume Breakout stratejisi
#
# Usage:
#   ./backtest_ema_breakout.sh [timerange]
#
# Examples:
#   ./backtest_ema_breakout.sh                    # Default: Bull Market
#   ./backtest_ema_breakout.sh 20230101-20231231  # Mixed Market
# ============================================================================

set -e

echo "============================================"
echo "EMA Breakout Volume Strategy"
echo "LoneStockTrader EGM Methodology"
echo "============================================"
echo ""

# Configuration
STRATEGY="EMABreakoutVolume"
CONFIG="user_data/config.json"
TIMEFRAME="4h"
TIMERANGE="${1:-20240601-20241231}"
PAIRS="BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT"

echo "Strategy: $STRATEGY"
echo "Timeframe: $TIMEFRAME"
echo "Period: $TIMERANGE"
echo "Pairs: $PAIRS"
echo ""

# Download data
echo "📥 Downloading historical data..."
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
    --export-filename "user_data/backtest_results/ema_breakout_${TIMERANGE}.json"

echo ""
echo "============================================"
echo "✅ EMA Breakout Backtest Complete!"
echo "============================================"
echo ""
echo "📊 Strategy based on:"
echo "  - LoneStockTrader EGM Methodology"
echo "  - CANSLIM Breakout Principles"
echo "  - EMA Ribbon + Volume Confirmation"
echo ""
