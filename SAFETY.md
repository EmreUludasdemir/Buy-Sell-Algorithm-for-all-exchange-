# 🛡️ SAFETY.md - Trading Bot Security Guardrails

> **⚠️ WARNING**: Trading involves significant financial risk. This document outlines mandatory safety procedures before live trading.

---

## 📋 Pre-Live Trading Checklist

### ✅ Required Before ANY Live Trade

- [ ] **4+ weeks of dry-run testing** completed
- [ ] Backtest on **all market regimes** (bull/bear/sideways)
- [ ] Max drawdown < 20% in all scenarios
- [ ] Profit factor > 1.5 across test periods
- [ ] Position sizing reviewed and appropriate
- [ ] Stoploss and trailing stop logic verified
- [ ] API key permissions reviewed (read + trade ONLY)

### ✅ Configuration Review

- [ ] `dry_run: false` set intentionally (not accidentally)
- [ ] `stake_amount` appropriate for account size
- [ ] `max_open_trades` reasonable (4 or less recommended)
- [ ] All protections enabled (CooldownPeriod, StoplossGuard, MaxDrawdown)

---

## 🔐 API Key Security

### Golden Rules

1. **NEVER commit API keys to Git**
   - Use environment variables
   - Use `.env` files (gitignored)
2. **Minimize permissions**

   - ✅ Enable Reading
   - ✅ Enable Spot Trading
   - ❌ **NEVER** enable Withdrawals
   - ❌ **NEVER** enable Futures (unless intended)

3. **IP Whitelist**

   - Always set IP whitelist on exchange
   - Only allow your server's IP

4. **Rotate regularly**
   - Change API keys every 3-6 months
   - Immediately rotate if exposed

### .env Template

```bash
# .env (NEVER COMMIT THIS FILE)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here
```

---

## 🚫 Dangerous Commands (NEVER RUN)

### Destructive Git Commands

```bash
# ❌ NEVER run these
git push --force
git reset --hard origin/main
rm -rf .git
```

### Exposing Secrets

```bash
# ❌ NEVER do this
echo $BINANCE_SECRET
cat .env
printenv | grep KEY
```

### Unreviewed Deployments

```bash
# ❌ NEVER deploy without review
docker compose up -d  # Without checking config first
```

---

## 🤖 AI Assistant (Antigravity/Claude) Guidelines

### ⚠️ CRITICAL: Turbo Mode Warning

> **NEVER use Turbo/Auto mode for trading strategy code.**
>
> Always:
>
> - Review every diff before approval
> - Check parameter changes carefully
> - Verify no secrets are exposed
> - Test changes in dry-run first

### Safe Prompting

```markdown
✅ GOOD: "Show me the diff and explain the changes"
✅ GOOD: "Run backtest before implementing"
✅ GOOD: "What are the risks of this change?"

❌ BAD: "Just do it automatically"
❌ BAD: "Push directly to main"
❌ BAD: "Deploy to production immediately"
```

### Required Constraints for AI

Always include these in prompts:

- `.env` dokunma (don't touch .env)
- Secrets yazdırma (don't print secrets)
- Destructive komut yok (no destructive commands)
- PR küçük (keep PRs small)

---

## 📊 Monitoring Requirements

### Daily Checks

- [ ] Review open trades
- [ ] Check daily P&L
- [ ] Verify no protection locks
- [ ] Monitor max drawdown

### Weekly Checks

- [ ] Run `daily_report.py` for metrics
- [ ] Review rolling Sharpe/Sortino
- [ ] Check consecutive loss streaks
- [ ] Verify strategy is trading as expected

### Emergency Procedures

1. **Stop the bot**: `docker compose down`
2. **Review logs**: `docker compose logs -f`
3. **Check positions**: Manual exchange login
4. **Investigate**: Don't restart until issue understood

---

## 🔄 Safe Deployment Process

```bash
# 1. Run verification
./scripts/verify.sh

# 2. Start in dry-run mode
docker compose up -d
docker compose logs -f  # Monitor for 1h

# 3. If stable, switch to live
# Edit config: dry_run: false
docker compose restart
```

---

## 📞 Emergency Contacts

- **Exchange Support**: (your exchange support link)
- **Bot Issues**: Check GitHub Issues
- **Critical Bug**: Stop bot immediately, investigate

---

_Last updated: 2025-12-28_
_Version: 1.0_
