# 🚀 EPA Paper Trading Setup Guide
**Strategy:** EPAUltimateV3  
**Duration:** 7 Days  
**Capital:** $2000 (virtual)

---

## 📋 Pre-Flight Checklist

### ✅ Safety Confirmations
- [x] `dry_run = true` in config ✅
- [x] No real API keys (empty strings) ✅
- [x] Virtual wallet: $2000 ✅
- [x] Strategy: EPAUltimateV3 (baseline) ✅
- [x] 5 pairs only (BTC/ETH/BNB/SOL/XRP) ✅

### 📁 Files Created
- `config_paper_trading.json` - Paper trading configuration
- `paper_trading_log.md` - Daily tracking log
- `monitor_paper_trading.ps1` - Monitoring script

---

## 🔧 STEP 1: Telegram Setup (Optional but Recommended)

### A. Create Telegram Bot

1. **Open Telegram app**
2. **Search for:** @BotFather
3. **Send:** `/newbot`
4. **Choose name:** EPA Paper Trading Bot
5. **Choose username:** epa_paper_trading_bot (or similar)
6. **Copy token:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` (example)

### B. Get Your Chat ID

1. **Search for:** @userinfobot
2. **Start chat:** `/start`
3. **Copy ID:** `987654321` (example)

### C. Update Config

Edit `config_paper_trading.json`:
```json
"telegram": {
    "enabled": true,
    "token": "YOUR_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID_HERE",
    ...
}
```

**⚠️ If you skip Telegram:** You'll need to check the web UI manually

---

## 🎯 STEP 2: Smoke Test (1 Hour)

Before running 7 days, test for 1 hour:

### Start Bot
```powershell
cd "c:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade"

# Stop any running instance
docker-compose down

# Start with paper trading config
docker-compose run --rm freqtrade trade \
  --strategy EPAUltimateV3 \
  -c /freqtrade/user_data/config_paper_trading.json
```

### Monitor (Wait 5 minutes)
```powershell
# In a new PowerShell window
cd "c:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade"

.\monitor_paper_trading.ps1
```

### Check for Issues

✅ **Good signs:**
- Bot starts without errors
- "Searching for BTC/USDT buy signals" in logs
- No Python exceptions
- Web UI accessible at http://localhost:8080

❌ **Bad signs:**
- "Could not load strategy" error
- "API authentication failed" (should not happen in dry-run)
- Bot crashes immediately
- No pairs being analyzed

### Stop After 1 Hour
```powershell
docker-compose down
```

**Decision:**
- ✅ No issues → Proceed to 7-day trial
- ❌ Issues found → Debug before continuing

---

## 🏃 STEP 3: Start 7-Day Trial

### Start Bot in Background
```powershell
cd "c:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade"

# Start as daemon (background)
docker-compose up -d

# Verify it's running
docker ps
```

### Access Monitoring

**Web UI:**
- URL: http://localhost:8080
- Username: `freqtrade`
- Password: `EPAPaperTrade2026!`

**PowerShell Monitor:**
```powershell
.\monitor_paper_trading.ps1          # Quick check
.\monitor_paper_trading.ps1 -Detailed # Full stats
.\monitor_paper_trading.ps1 -Status  # Logs & health
```

**Telegram:**
- Should receive alerts for each trade (if enabled)

---

## 📊 STEP 4: Daily Monitoring Routine

### Morning Check (9:00 AM)

```powershell
cd freqtrade
.\monitor_paper_trading.ps1 -Detailed
```

Record in `paper_trading_log.md`:
- Total P/L
- Open trades
- Win rate

### Evening Check (9:00 PM)

```powershell
.\monitor_paper_trading.ps1 -Detailed
```

Record:
- Total P/L (end of day)
- New trades today
- Any issues

### What to Watch For

🚨 **Immediate Action Required:**
- Bot stopped (container down)
- Loss > -$100 in 24h
- Zero trades for 48h
- Win rate < 40%

⚠️ **Monitor Closely:**
- Drawdown > 5%
- Win rate < 55%
- Unusual trade patterns

✅ **Healthy Signals:**
- Steady small profits
- Win rate 55-70%
- 1-3 trades per day
- Drawdown < 5%

---

## 🎬 STEP 5: Day 7 Review

### Generate Final Report

```powershell
cd freqtrade

# Get full statistics
docker exec freqtrade freqtrade profit --show-days 7 -c /freqtrade/user_data/config_paper_trading.json

# Export trade history
docker exec freqtrade freqtrade export-trades --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite --export-filename paper_trade_history.csv
```

### Complete Decision Matrix

Fill out in `paper_trading_log.md`:

**Metrics Checklist:**
- [ ] Total profit %: ______
- [ ] Total trades: ______
- [ ] Win rate: ______
- [ ] Max drawdown: ______
- [ ] Bot stability: ______

**Decision:**
- ✅ **Proceed to Live:** Profit > 0%, WR > 55%, DD < 10%
- ⚠️ **Extend Paper:** Profit -2% to 0%, need more data
- ❌ **Stop & Debug:** Profit < -5%, something wrong

---

## 🛠️ Troubleshooting

### Bot Won't Start

```powershell
# Check logs
docker logs freqtrade

# Common issues:
# 1. Port 8080 already in use
# 2. Strategy file missing
# 3. Config syntax error

# Fix: Check config with
docker exec freqtrade freqtrade show-config -c /freqtrade/user_data/config_paper_trading.json
```

### No Trades Happening

**Possible causes:**
1. Market conditions (no signals)
2. Protection locks active
3. Timeframe mismatch
4. Strategy logic issue

**Check:**
```powershell
# See protection status
docker exec freqtrade freqtrade show_trades --open

# Check strategy is loaded
docker exec freqtrade freqtrade list-strategies
```

### Telegram Not Working

1. Check bot token is correct
2. Verify chat ID is correct
3. Start conversation with bot first
4. Check `"enabled": true`

---

## 📚 Quick Reference

### Essential Commands

```powershell
# Start bot
docker-compose up -d

# Stop bot
docker-compose down

# View logs (live)
docker logs -f freqtrade

# Check status
.\monitor_paper_trading.ps1

# Full performance report
docker exec freqtrade freqtrade profit -c /freqtrade/user_data/config_paper_trading.json

# Current trades
docker exec freqtrade freqtrade show_trades --open -c /freqtrade/user_data/config_paper_trading.json

# Force exit all (emergency)
docker exec freqtrade freqtrade force_exit all -c /freqtrade/user_data/config_paper_trading.json
```

### API Endpoints

**Web UI:** http://localhost:8080

**REST API:**
```
GET /api/v1/status
GET /api/v1/profit
GET /api/v1/trades
GET /api/v1/performance
```

---

## 🎓 Expected Results

### Realistic 7-Day Targets

| Metric | Conservative | Realistic | Optimistic |
|--------|-------------|-----------|------------|
| **Profit** | +0.5% | +1.5% | +2.5% |
| **Trades** | 5 | 8-12 | 15+ |
| **Win Rate** | 50% | 60% | 70% |
| **Max DD** | 3% | 2% | 1% |

**Remember:** 
- Backtest was 13.87% / 6 months = 2.31% per week
- Paper trading is optimistic (no real slippage)
- Crypto is volatile - daily swings normal

---

## ⚠️ Critical Reminders

1. **This is PRACTICE** - No real money at risk
2. **dry_run = true** - Always verify before changing
3. **Don't force trades** - Let strategy work naturally
4. **Document everything** - Use paper_trading_log.md
5. **Be patient** - 7 days = small sample size

---

## 📞 When to Ask for Help

❌ **Stop immediately if:**
- Bot trading with real money (check config!)
- Unexplained large losses (-10%+)
- Bot crashes repeatedly
- Cannot access web UI or logs

✅ **Normal behavior:**
- No trades for 24h (market conditions)
- Small losses -2% to 0% (variance)
- Occasional protection locks
- Strategy waiting for signals

---

## 🚀 Next Steps After Success

1. **Analyze results** - Compare to backtest
2. **Identify issues** - What worked/didn't work?
3. **Plan live trial** - Start with $100 real capital
4. **Set risk limits** - Max loss per day/week
5. **Monitor closely** - First week of live is critical

**Good luck! 🍀**

---

*Created: 2026-01-02*
*Strategy: EPAUltimateV3*
*Backtest Performance: 13.87% / 6 months*
