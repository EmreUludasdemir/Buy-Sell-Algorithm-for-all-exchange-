$run = "kivanc_futures_1d_regimes_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")
$out = "reports/$run"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$scenarios = @(
  @{ id = "bear_2022"; tr = "20220501-20221231" },
  @{ id = "recovery_2023"; tr = "20230101-20231231" },
  @{ id = "bull_2024"; tr = "20240101-20241231" },
  @{ id = "choppy_2025"; tr = "20250101-20251231" },
  @{ id = "ytd_2026"; tr = "20260101-20260301" },
  @{ id = "full_2022_2026"; tr = "20220101-20260301" }
)

foreach ($sc in $scenarios) {
  docker compose run --rm bot1_btceth backtesting `
    --config user_data/config_futures_research.json `
    --strategy KivancSupertrendedMovingAveragesFutures1D `
    --strategy-path user_data/strategies_research `
    --timeframe 1d `
    --timerange $sc.tr `
    --pairs BTC/USDT:USDT ETH/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT XRP/USDT:USDT `
    --data-format-ohlcv feather `
    --enable-protections `
    --export trades `
    --export-filename "$out/$($sc.id).json"
}

@'
import json
import pathlib

root = pathlib.Path("reports")
latest = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("kivanc_futures_1d_regimes_")], key=lambda p: p.stat().st_mtime)[-1]
rows = []

for fp in sorted(latest.glob("*.json")):
    payload = json.loads(fp.read_text(encoding="utf-8"))
    strategy = next(iter(payload["strategy"].values()))
    rows.append({
        "scenario": fp.stem,
        "date_range": f"{strategy['backtest_start']} -> {strategy['backtest_end']}",
        "profit_pct": round((strategy.get("profit_total", 0) or 0) * 100, 2),
        "final_balance": round(strategy.get("final_balance", 0) or 0, 2),
        "trades": strategy.get("total_trades", 0),
        "win_rate_pct": round((strategy.get("wins", 0) / strategy.get("total_trades", 1) * 100) if strategy.get("total_trades", 0) else 0.0, 2),
        "profit_factor": round(strategy.get("profit_factor", 0) or 0, 2),
        "max_dd_pct": round((strategy.get("max_drawdown_account", 0) or 0) * 100, 2),
        "market_change_pct": round((strategy.get("market_change", 0) or 0) * 100, 2),
        "longs": strategy.get("long_trades", 0),
        "shorts": strategy.get("short_trades", 0),
    })

summary_path = latest / "kivanc_futures_1d_regimes_summary.json"
summary_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

lines = [
    "# Kivanc STMA Futures 1D Long/Short Research",
    "",
    "Research config: `user_data/config_futures_research.json`",
    "Strategy: `KivancSupertrendedMovingAveragesFutures1D`",
    "",
    "| Scenario | Date | Profit | 1000 USDT Result | Trades | Longs | Shorts | Win Rate | PF | MaxDD | Market |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]

for row in rows:
    lines.append(
        f"| {row['scenario']} | {row['date_range']} | {row['profit_pct']:.2f}% | {row['final_balance']:.2f} | "
        f"{row['trades']} | {row['longs']} | {row['shorts']} | {row['win_rate_pct']:.2f}% | "
        f"{row['profit_factor']:.2f} | {row['max_dd_pct']:.2f}% | {row['market_change_pct']:.2f}% |"
    )

(latest / "kivanc_futures_1d_regimes_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(latest)
'@ | python -
