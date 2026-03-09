param(
    [int]$Epochs = 150,
    [string]$Timerange = "20220101-20260301"
)

docker compose run --rm bot1_btceth hyperopt `
  --config user_data/config_production.json `
  --strategy KivancSupertrendedMovingAverages1D `
  --timeframe 1d `
  --timerange $Timerange `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT `
  --data-format-ohlcv feather `
  --hyperopt-loss ProfitDrawDownHyperOptLoss `
  --spaces buy `
  --epochs $Epochs `
  --min-trades 20 `
  --random-state 42
