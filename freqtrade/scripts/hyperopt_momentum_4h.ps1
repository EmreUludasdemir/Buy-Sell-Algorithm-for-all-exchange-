param(
    [string]$Timerange = "20220101-20260301",
    [int]$Epochs = 200
)

docker compose run --rm bot1_btceth hyperopt `
  --config user_data/config_momentum_4h_backtest.json `
  --strategy MomentumVolumeCompound4H `
  --strategy-path user_data/strategies_momentum `
  --timeframe 4h `
  --timerange $Timerange `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT DOGE/USDT ADA/USDT LINK/USDT `
  --data-format-ohlcv feather `
  --hyperopt-loss SharpeHyperOptLoss `
  --spaces buy sell `
  --epochs $Epochs `
  --job-workers 1
