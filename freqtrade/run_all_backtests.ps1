# Multi-Strategy Backtest Script
# Timerange: 2023-01-01 to 2026-01-01 (Full Market Conditions)

$strategies = @(
    "EPAUltimateV3",
    "EPASuperTrend",
    "EPASuperTrendOptimized",
    "EPASuperTrendAggressive",
    "EPAMomentum",
    "EPASimpleEMA",
    "EPAHoldDCA"
)

$resultsDir = "user_data/backtest_results"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$summaryFile = "$resultsDir/backtest_summary_$timestamp.txt"

Write-Host "========================================"
Write-Host "EPA Multi-Strategy Backtest"
Write-Host "Timerange: 2023-01-01 to 2026-01-01"
Write-Host "========================================"
Write-Host ""

"EPA Multi-Strategy Backtest Results" | Out-File $summaryFile
"Timerange: 2023-01-01 to 2026-01-01" | Add-Content $summaryFile
"Generated: $timestamp" | Add-Content $summaryFile
"========================================" | Add-Content $summaryFile
"" | Add-Content $summaryFile

foreach ($strategy in $strategies) {
    Write-Host "Testing: $strategy..."
    "Strategy: $strategy" | Add-Content $summaryFile
    "----------------------------------------" | Add-Content $summaryFile
    
    $output = docker run --rm -v "${PWD}/user_data:/freqtrade/user_data" freqtradeorg/freqtrade:stable backtesting --strategy $strategy --config /freqtrade/user_data/config.json --timerange 20230101-20260101 --timeframe 4h 2>&1
    
    $output | Add-Content $summaryFile
    "" | Add-Content $summaryFile
    
    Write-Host "  Done!"
}

Write-Host ""
Write-Host "All backtests completed!"
Write-Host "Results saved to: $summaryFile"
