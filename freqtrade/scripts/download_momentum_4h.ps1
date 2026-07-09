param(
    [string]$Timerange = "20200101-20260301"
)

# The strategy consumes both 4h (execution) and 1d (regime) candles,
# so both timeframes are downloaded for the high-volume backtest pair set.
docker compose run --rm bot1_btceth download-data `
  --config user_data/config_momentum_4h_backtest.json `
  --timeframe 4h 1d `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT DOGE/USDT ADA/USDT LINK/USDT `
  --timerange $Timerange `
  --data-format-ohlcv feather
