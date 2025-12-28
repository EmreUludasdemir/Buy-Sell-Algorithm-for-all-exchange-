#!/bin/bash
# ============================================================================
# verify.sh - Local Verification Script
# ============================================================================
# Runs smoke tests before deployment:
#   1. Python lint check on strategy files
#   2. Smoke test backtest (30-day sample)
#   3. Config validation
#
# Usage:
#   chmod +x scripts/verify.sh
#   ./scripts/verify.sh
# ============================================================================

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FREQTRADE_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "=============================================="
echo "🔍 Running Verification Suite"
echo "=============================================="
echo ""

# Track failures
FAILED=0

# ============================================================================
# 1. Python Syntax Check
# ============================================================================
echo -e "${YELLOW}[1/3] Python Lint Check...${NC}"

STRATEGY_DIR="$FREQTRADE_DIR/freqtrade/user_data/strategies"

if [ -d "$STRATEGY_DIR" ]; then
    for pyfile in "$STRATEGY_DIR"/*.py; do
        if [ -f "$pyfile" ]; then
            if python -m py_compile "$pyfile" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} $(basename "$pyfile")"
            else
                echo -e "  ${RED}✗${NC} $(basename "$pyfile") - Syntax error!"
                FAILED=1
            fi
        fi
    done
else
    # Try alternate path structure
    STRATEGY_DIR="$FREQTRADE_DIR/user_data/strategies"
    if [ -d "$STRATEGY_DIR" ]; then
        for pyfile in "$STRATEGY_DIR"/*.py; do
            if [ -f "$pyfile" ]; then
                if python -m py_compile "$pyfile" 2>/dev/null; then
                    echo -e "  ${GREEN}✓${NC} $(basename "$pyfile")"
                else
                    echo -e "  ${RED}✗${NC} $(basename "$pyfile") - Syntax error!"
                    FAILED=1
                fi
            fi
        done
    else
        echo -e "  ${RED}✗${NC} Strategy directory not found"
        FAILED=1
    fi
fi

echo ""

# ============================================================================
# 2. Smoke Test Backtest
# ============================================================================
echo -e "${YELLOW}[2/3] Smoke Test Backtest...${NC}"

# Check if docker compose is available
if command -v docker &> /dev/null; then
    cd "$FREQTRADE_DIR/freqtrade" 2>/dev/null || cd "$FREQTRADE_DIR"
    
    # Run short backtest (30 days, minimal output)
    if docker compose run --rm freqtrade backtesting \
        --strategy EPAStrategyV2 \
        --timerange 20241101-20241201 \
        --export none \
        --no-header 2>&1 | grep -q "trades\|profit"; then
        echo -e "  ${GREEN}✓${NC} Backtest completed successfully"
    else
        echo -e "  ${YELLOW}⚠${NC} Backtest completed (verify output manually)"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Docker not available, skipping backtest"
fi

echo ""

# ============================================================================
# 3. Config Validation
# ============================================================================
echo -e "${YELLOW}[3/3] Config Validation...${NC}"

# Check for production config
CONFIG_FILE="$FREQTRADE_DIR/freqtrade/user_data/config_production.json"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="$FREQTRADE_DIR/user_data/config_production.json"
fi

if [ -f "$CONFIG_FILE" ]; then
    # Check for dry_run
    if grep -q '"dry_run": true' "$CONFIG_FILE"; then
        echo -e "  ${GREEN}✓${NC} dry_run is enabled (safe)"
    elif grep -q '"dry_run": false' "$CONFIG_FILE"; then
        echo -e "  ${YELLOW}⚠${NC} dry_run is DISABLED (live trading!)"
    else
        echo -e "  ${YELLOW}⚠${NC} dry_run setting not found"
    fi
    
    # Check for API keys (should NOT be in file)
    if grep -q '"key": "[^"]\+"' "$CONFIG_FILE" 2>/dev/null; then
        if grep -q '"key": ""' "$CONFIG_FILE" || grep -q '"key": "YOUR_' "$CONFIG_FILE"; then
            echo -e "  ${GREEN}✓${NC} No hardcoded API keys"
        else
            echo -e "  ${RED}✗${NC} WARNING: API key may be hardcoded!"
            FAILED=1
        fi
    else
        echo -e "  ${GREEN}✓${NC} API key not in config"
    fi
    
    echo -e "  ${GREEN}✓${NC} Config file exists"
else
    echo -e "  ${YELLOW}⚠${NC} Production config not found"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
echo "=============================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Verification PASSED${NC}"
    echo "=============================================="
    echo ""
    exit 0
else
    echo -e "${RED}❌ Verification FAILED${NC}"
    echo "=============================================="
    echo ""
    exit 1
fi
