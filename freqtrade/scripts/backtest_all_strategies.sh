#!/bin/bash
# =============================================================================
# Backtest All Research-Based Strategies
# =============================================================================
# This script runs backtests on all 5 research-based strategies
# across multiple pairs and timeframes to find the top performers.
#
# Usage: ./backtest_all_strategies.sh
# =============================================================================

set -e

# Configuration
STRATEGIES=("RSI2Strategy" "MACDRSICombo" "SuperTrendADX" "TripleConfluence" "EMADynamicATR")
PAIRS="BTC/USDT ETH/USDT"
TIMEFRAMES=("4h" "1d")
TIMERANGE="20220101-20250101"  # Last 3 years

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Results directory
RESULTS_DIR="../user_data/backtest_results/comparison_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}       EPA Trading Bot - Strategy Comparison Backtest       ${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "Strategies: ${YELLOW}${STRATEGIES[*]}${NC}"
echo -e "Timeframes: ${YELLOW}${TIMEFRAMES[*]}${NC}"
echo -e "Timerange:  ${YELLOW}${TIMERANGE}${NC}"
echo -e "Results:    ${YELLOW}${RESULTS_DIR}${NC}"
echo ""

# Summary file
SUMMARY_FILE="$RESULTS_DIR/summary.txt"
echo "Strategy Comparison Summary - $(date)" > "$SUMMARY_FILE"
echo "========================================" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# Function to run backtest
run_backtest() {
    local strategy=$1
    local timeframe=$2
    local output_file="$RESULTS_DIR/${strategy}_${timeframe}.json"

    echo -e "${YELLOW}Testing: ${strategy} on ${timeframe}...${NC}"

    docker compose run --rm freqtrade backtesting \
        --strategy "$strategy" \
        --config user_data/config.json \
        --timerange "$TIMERANGE" \
        --timeframe "$timeframe" \
        --export trades \
        --export-filename "$output_file" \
        2>&1 | tee "$RESULTS_DIR/${strategy}_${timeframe}.log"

    # Extract key metrics from log
    local log_file="$RESULTS_DIR/${strategy}_${timeframe}.log"

    # Parse results (these patterns match Freqtrade output)
    local total_profit=$(grep -oP "Total profit\s+\K[\d.-]+" "$log_file" 2>/dev/null || echo "N/A")
    local win_rate=$(grep -oP "Win Rate\s+\[\s*\K[\d.]+%" "$log_file" 2>/dev/null || echo "N/A")
    local profit_factor=$(grep -oP "Profit factor\s+\K[\d.]+" "$log_file" 2>/dev/null || echo "N/A")
    local max_dd=$(grep -oP "Max\. Drawdown\s+\K[\d.-]+%" "$log_file" 2>/dev/null || echo "N/A")
    local trades=$(grep -oP "Total/Daily Avg Trades\s+\K\d+" "$log_file" 2>/dev/null || echo "N/A")

    echo "${strategy},${timeframe},${total_profit},${win_rate},${profit_factor},${max_dd},${trades}" >> "$RESULTS_DIR/results.csv"

    echo "" >> "$SUMMARY_FILE"
    echo "Strategy: $strategy | Timeframe: $timeframe" >> "$SUMMARY_FILE"
    echo "  Total Profit: $total_profit%" >> "$SUMMARY_FILE"
    echo "  Win Rate: $win_rate" >> "$SUMMARY_FILE"
    echo "  Profit Factor: $profit_factor" >> "$SUMMARY_FILE"
    echo "  Max Drawdown: $max_dd" >> "$SUMMARY_FILE"
    echo "  Total Trades: $trades" >> "$SUMMARY_FILE"

    if [[ "$total_profit" != "N/A" ]]; then
        echo -e "${GREEN}✓ Completed: ${strategy} on ${timeframe}${NC}"
    else
        echo -e "${RED}⚠ Warning: Could not parse results for ${strategy} on ${timeframe}${NC}"
    fi
}

# Create CSV header
echo "strategy,timeframe,total_profit,win_rate,profit_factor,max_drawdown,trades" > "$RESULTS_DIR/results.csv"

# Run all backtests
echo -e "${BLUE}Starting backtests...${NC}"
echo ""

for timeframe in "${TIMEFRAMES[@]}"; do
    echo -e "${BLUE}=== Timeframe: ${timeframe} ===${NC}"
    for strategy in "${STRATEGIES[@]}"; do
        run_backtest "$strategy" "$timeframe"
        echo ""
    done
done

# Generate final report
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}                    BACKTEST RESULTS                        ${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Display CSV results
echo -e "${YELLOW}Results Summary:${NC}"
column -t -s ',' "$RESULTS_DIR/results.csv"
echo ""

# Find top 3 performers (by total profit)
echo -e "${GREEN}Top 3 Performers (by Total Profit):${NC}"
tail -n +2 "$RESULTS_DIR/results.csv" | sort -t',' -k3 -rn | head -3 | column -t -s ','
echo ""

echo -e "${BLUE}Full results saved to: ${RESULTS_DIR}${NC}"
echo ""
echo -e "${GREEN}Backtest comparison complete!${NC}"
