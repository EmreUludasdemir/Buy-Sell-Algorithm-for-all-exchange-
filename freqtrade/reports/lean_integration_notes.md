# LEAN to Freqtrade Adaptation Notes

This repo now includes a LEAN-inspired upgrade in:

- `freqtrade/user_data/strategies/MACDVSupertrendStrategy.py`

## What was added

1. Market regime filter
- Uses BTC 1d EMA200 as a global gate.
- New entries are blocked when macro regime is bearish.

2. Volatility-targeted position sizing
- Implemented in `custom_stake_amount`.
- Uses ATR/close ratio to scale stake size.
- Lower volatility -> can allocate larger stake (within caps).
- Higher volatility -> stake is reduced.

3. Time-based risk exits
- Implemented in `custom_exit`.
- Adds `lean_time_stop` and `lean_hard_time_stop` exits to prevent dead capital.

4. Profit-locking stoploss tiers
- Implemented in `custom_stoploss`.
- Uses tighter stoploss as trade profit grows.

## Operational impact

- `use_custom_stoploss = True` is enabled in the strategy.
- The strategy remains `spot` compatible (`can_short = False`).

## Recommended next step

Re-run hyperopt because strategy logic changed:

```powershell
docker compose run --rm bot1_btceth hyperopt `
  --config user_data/config_production.json `
  --strategy MACDVSupertrendStrategy `
  --strategy-path user_data/strategies `
  --timeframe 4h `
  --timerange 20220101-20251231 `
  --pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT `
  --data-format-ohlcv feather `
  --spaces buy roi stoploss trailing `
  --hyperopt-loss SharpeHyperOptLossDaily `
  --epochs 120 `
  --job-workers 1
```

