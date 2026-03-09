param(
    [string]$Timerange = "20220101-20260301"
)

docker compose run --rm bot1_btceth backtesting `
  --config user_data/config_production.json `
  --strategy KivancSupertrendedMovingAverages1D `
  --timeframe 1d `
  --timerange $Timerange `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT `
  --data-format-ohlcv feather `
  --enable-protections `
  --export trades
