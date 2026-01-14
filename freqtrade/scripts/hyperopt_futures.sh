#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# EPA Futures Pro - Hyperopt Optimization Script
# ═══════════════════════════════════════════════════════════════════════════
# Author: Emre Uludaşdemir
# Usage: ./hyperopt_futures.sh [epochs] [timerange]
# Example: ./hyperopt_futures.sh 500 20240101-20241231
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
EPOCHS="${1:-300}"
TIMERANGE="${2:-20240101-20241231}"
LOSS_FUNCTION="SharpeHyperOptLoss"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}    EPA Futures Pro - Hyperopt Optimization${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Strategy:${NC}    $STRATEGY"
echo -e "${YELLOW}Config:${NC}      $CONFIG"
echo -e "${YELLOW}Timeframe:${NC}   $TIMEFRAME"
echo -e "${YELLOW}Epochs:${NC}      $EPOCHS"
echo -e "${YELLOW}Timerange:${NC}   $TIMERANGE"
echo -e "${YELLOW}Loss:${NC}        $LOSS_FUNCTION"
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

# Run hyperopt
echo -e "${BLUE}[2/3] Running hyperopt (this may take a while)...${NC}"
docker compose run --rm freqtrade hyperopt \
    --strategy $STRATEGY \
    --config $CONFIG \
    --timeframe $TIMEFRAME \
    --timerange $TIMERANGE \
    --hyperopt-loss $LOSS_FUNCTION \
    --epochs $EPOCHS \
    --spaces buy sell \
    --enable-protections \
    -j 4

# Show results
echo -e "${BLUE}[3/3] Hyperopt complete!${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}    Apply best parameters with:${NC}"
echo -e "${GREEN}    freqtrade hyperopt-show --best${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
