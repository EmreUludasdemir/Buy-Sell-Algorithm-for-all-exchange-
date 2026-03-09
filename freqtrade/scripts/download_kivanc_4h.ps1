docker compose run --rm bot1_btceth download-data `
  --config user_data/config_production.json `
  --timeframe 4h `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT `
  --timerange 20200101-20260301 `
  --data-format-ohlcv feather
