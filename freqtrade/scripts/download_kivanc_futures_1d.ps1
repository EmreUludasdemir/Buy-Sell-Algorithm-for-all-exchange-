docker compose run --rm bot1_btceth download-data `
  --config user_data/config_futures_research.json `
  --trading-mode futures `
  --timeframe 1d `
  --pairs BTC/USDT:USDT ETH/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT XRP/USDT:USDT `
  --timerange 20200101-20260301 `
  --prepend `
  --data-format-ohlcv feather
