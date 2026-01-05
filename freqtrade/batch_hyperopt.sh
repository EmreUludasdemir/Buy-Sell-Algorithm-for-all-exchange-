#!/bin/bash
# Batch Hyperopt Script - Run overnight
# Optimizes all 8 losing strategies

STRATEGIES=(
    "EPAAlphaTrend"
    "EPAUltimateV3_Balanced"
    "EPAUltimateV3_Optimized"
    "EPAUltimateV3"
    "EPAAlphaTrendV1"
    "AlphaTrendBaseline"
    "EPAUltimateV4"
    "AlphaTrendAdaptive"
)

TIMERANGE="20230101-20241001"
CONFIG="user_data/config.json"
EPOCHS=100
LOSS="SortinoHyperOptLoss"

echo "=== BATCH HYPEROPT START ==="
echo "Date: $(date)"
echo "Strategies: ${#STRATEGIES[@]}"
echo ""

for STRATEGY in "${STRATEGIES[@]}"; do
    echo "========================================"
    echo "Optimizing: $STRATEGY"
    echo "Started: $(date)"
    echo "========================================"
    
    freqtrade hyperopt \
        --strategy "$STRATEGY" \
        --hyperopt-loss "$LOSS" \
        --spaces roi stoploss \
        --epochs $EPOCHS \
        --timerange $TIMERANGE \
        -c $CONFIG \
        --timeframe 2h \
        -j 1 \
        2>&1 | tee -a "user_data/hyperopt_${STRATEGY}.log"
    
    echo ""
    echo "Completed: $STRATEGY at $(date)"
    echo ""
done

echo "=== BATCH HYPEROPT COMPLETE ==="
echo "Finished: $(date)"
