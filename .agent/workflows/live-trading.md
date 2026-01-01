---
description: Safe deployment checklist for live/paper trading
---

# Live Trading Workflow

> ⚠️ **WARNING**: Live trading involves real money. Follow this checklist carefully.

## Pre-Deployment Checklist

### 1. Complete SAFETY.md Review

- [ ] 4+ weeks of dry-run testing completed
- [ ] Backtest on all market regimes (bull/bear/sideways)
- [ ] Max drawdown < 20% in all scenarios
- [ ] Profit factor > 1.5 across test periods
- [ ] Position sizing reviewed

### 2. API Key Setup

```bash
# Create .env file (NEVER commit this)
cp .env.example .env
```

Edit `.env`:

```bash
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here
```

**API Key Permissions:**

- ✅ Enable Reading
- ✅ Enable Spot Trading
- ❌ **NEVER** enable Withdrawals
- ❌ **NEVER** enable Futures (unless intended)

### 3. Configuration Review

Edit `freqtrade/user_data/config.json`:

```json
{
  "dry_run": true, // Start with true!
  "stake_amount": 100,
  "max_open_trades": 3
}
```

### 4. Start in Paper Trading Mode

```bash
cd freqtrade
docker compose up -d
docker compose logs -f  # Monitor for 1 hour
```

### 5. Verify Bot Operation

Check for:

- [ ] Bot connects to exchange
- [ ] Indicators calculate correctly
- [ ] Trades execute as expected
- [ ] Protections are active

### 6. Switch to Live (With Approval)

⚠️ **REQUIRES MANUAL APPROVAL**

Edit config:

```json
{
  "dry_run": false
}
```

Restart:

```bash
docker compose restart
```

## Daily Monitoring

- [ ] Review open trades
- [ ] Check daily P&L
- [ ] Verify no protection locks
- [ ] Monitor max drawdown

## Emergency Procedures

### Stop the Bot

```bash
docker compose down
```

### Check Positions

Log into exchange manually to verify positions.

### Recovery

1. Investigate the issue
2. Fix the root cause
3. Re-run backtests
4. Start in dry-run mode again

## Quick Commands

| Action  | Command                  |
| ------- | ------------------------ |
| Start   | `docker compose up -d`   |
| Stop    | `docker compose down`    |
| Logs    | `docker compose logs -f` |
| Restart | `docker compose restart` |
| Status  | `docker compose ps`      |
