#!/bin/bash
# EPAAlphaTrendV1 Backtest Suite
# ===============================
# Multi-period backtesting for comprehensive strategy validation

STRATEGY="EPAAlphaTrendV1"
CONFIG="user_data/config_alphatrend_2h.json"
RESULTS_DIR="user_data/backtest_results"

echo "=================================================="
echo "EPAAlphaTrendV1 Backtest Suite"
echo "=================================================="
echo ""

# Create results directory if not exists
mkdir -p $RESULTS_DIR

# T1: Bull Run (Q1 2024)
echo "[T1] Bull Run: 2024-01-01 ~ 2024-03-31"
echo "--------------------------------------------------"
docker compose run --rm freqtrade backtesting \
    --strategy $STRATEGY \
    -c $CONFIG \
    --timerange 20240101-20240331 \
    --export trades \
    --export-filename $RESULTS_DIR/at_t1_bull.json

echo ""

# T2: Correction (Q2 2024)
echo "[T2] Correction: 2024-04-01 ~ 2024-06-30"
echo "--------------------------------------------------"
docker compose run --rm freqtrade backtesting \
    --strategy $STRATEGY \
    -c $CONFIG \
    --timerange 20240401-20240630 \
    --export trades \
    --export-filename $RESULTS_DIR/at_t2_correction.json

echo ""

# T3: Recovery (H2 2024)
echo "[T3] Recovery: 2024-07-01 ~ 2024-12-31"
echo "--------------------------------------------------"
docker compose run --rm freqtrade backtesting \
    --strategy $STRATEGY \
    -c $CONFIG \
    --timerange 20240701-20241231 \
    --export trades \
    --export-filename $RESULTS_DIR/at_t3_recovery.json

echo ""

# T4: Full 2024
echo "[T4] Full 2024: 2024-01-01 ~ 2024-12-31"
echo "--------------------------------------------------"
docker compose run --rm freqtrade backtesting \
    --strategy $STRATEGY \
    -c $CONFIG \
    --timerange 20240101-20241231 \
    --export trades \
    --export-filename $RESULTS_DIR/at_t4_full.json

echo ""
echo "=================================================="
echo "Backtest Suite Complete"
echo "Results saved to: $RESULTS_DIR/at_*.json"
echo "=================================================="
