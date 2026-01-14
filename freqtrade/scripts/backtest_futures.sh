#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# EPA Futures Pro - Backtest Script
# ═══════════════════════════════════════════════════════════════════════════
# Author: Emre Uludaşdemir
# Usage: ./backtest_futures.sh [timerange]
# Example: ./backtest_futures.sh 20240101-20241231
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
STRATEGY="EPAFuturesPro"
CONFIG="user_data/strategies/config_futures.json"
TIMEFRAME="1h"
TIMERANGE="${1:-20240101-20241231}"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}    EPA Futures Pro - Backtest${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Strategy:${NC}  $STRATEGY"
echo -e "${YELLOW}Config:${NC}    $CONFIG"
echo -e "${YELLOW}Timeframe:${NC} $TIMEFRAME"
echo -e "${YELLOW}Timerange:${NC} $TIMERANGE"
echo ""

# Change to freqtrade directory
cd "$(dirname "$0")/.."

# Download data if needed
echo -e "${BLUE}[1/3] Downloading data...${NC}"
docker compose run --rm freqtrade download-data \
    --config $CONFIG \
    --timeframe $TIMEFRAME \
    --timerange $TIMERANGE \
    --trading-mode futures

# Run backtest
echo -e "${BLUE}[2/3] Running backtest...${NC}"
docker compose run --rm freqtrade backtesting \
    --strategy $STRATEGY \
    --config $CONFIG \
    --timeframe $TIMEFRAME \
    --timerange $TIMERANGE \
    --enable-protections \
    --export trades \
    --export-filename user_data/backtest_results/futures_${TIMERANGE}.json

# Show results
echo -e "${BLUE}[3/3] Backtest complete!${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Results saved to: user_data/backtest_results/futures_${TIMERANGE}.json${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
