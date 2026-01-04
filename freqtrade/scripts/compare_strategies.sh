#!/bin/bash
# Strategy Comparison: EPAUltimateV3 vs EPAAlphaTrendV1
# ======================================================
# Runs both strategies on the same config for fair comparison

CONFIG="user_data/config_alphatrend_2h.json"
TIMERANGE="20240101-20241231"

echo "=================================================="
echo "Strategy Comparison: EPAUltimateV3 vs EPAAlphaTrendV1"
echo "Timerange: $TIMERANGE"
echo "Config: $CONFIG"
echo "=================================================="
echo ""

# Baseline: EPAUltimateV3
echo "[BASELINE] EPAUltimateV3"
echo "--------------------------------------------------"
docker compose run --rm freqtrade backtesting \
    --strategy EPAUltimateV3 \
    -c $CONFIG \
    --timeframe 2h \
    --timerange $TIMERANGE

echo ""
echo "=================================================="
echo ""

# New: EPAAlphaTrendV1
echo "[NEW] EPAAlphaTrendV1"
echo "--------------------------------------------------"
docker compose run --rm freqtrade backtesting \
    --strategy EPAAlphaTrendV1 \
    -c $CONFIG \
    --timerange $TIMERANGE

echo ""
echo "=================================================="
echo "Comparison Complete"
echo "=================================================="
