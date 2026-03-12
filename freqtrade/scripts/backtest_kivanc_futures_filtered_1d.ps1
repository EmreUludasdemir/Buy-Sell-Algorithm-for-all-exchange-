param(
    [string]$Timerange = "20220101-20260301"
)

docker compose run --rm bot1_btceth backtesting `
  --config user_data/config_futures_filtered_research.json `
  --strategy KivancSupertrendedMovingAveragesFutures1D `
  --strategy-path user_data/strategies_research `
  --timeframe 1d `
  --timerange $Timerange `
  --pairs BTC/USDT:USDT ETH/USDT:USDT BNB/USDT:USDT XRP/USDT:USDT `
  --data-format-ohlcv feather `
  --enable-protections `
  --export trades
