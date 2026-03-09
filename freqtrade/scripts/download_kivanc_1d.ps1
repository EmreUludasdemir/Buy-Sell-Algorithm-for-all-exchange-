param(
    [string]$Timerange = "20200101-20260301"
)

docker compose run --rm bot1_btceth download-data `
  --config user_data/config_production.json `
  --timeframe 1d `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT `
  --timerange $Timerange `
  --data-format-ohlcv feather `
  --prepend
