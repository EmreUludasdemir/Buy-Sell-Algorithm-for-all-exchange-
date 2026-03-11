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
  $before = @(
    Get-ChildItem "user_data/backtest_results" -Filter "backtest-result-*.zip" |
      Select-Object -ExpandProperty FullName
  )

  docker compose run --rm bot1_btceth backtesting `
    --config user_data/config_futures_research.json `
    --strategy KivancSupertrendedMovingAveragesFutures1D `
    --strategy-path user_data/strategies_research `
    --timeframe 1d `
    --timerange $sc.tr `
    --pairs BTC/USDT:USDT ETH/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT XRP/USDT:USDT `
    --data-format-ohlcv feather `
    --enable-protections `
    --export trades

  $created = Get-ChildItem "user_data/backtest_results" -Filter "backtest-result-*.zip" |
    Where-Object { $before -notcontains $_.FullName } |
    Sort-Object LastWriteTime

  if (-not $created) {
    throw "No new backtest zip was created for $($sc.id)."
  }

  Copy-Item $created[-1].FullName "$out/$($sc.id).zip" -Force
}

@'
import json
import pathlib
from zipfile import ZipFile

root = pathlib.Path("reports")
latest = sorted([p for p in root.iterdir() if p.is_dir() and p.name.startswith("kivanc_futures_1d_regimes_")], key=lambda p: p.stat().st_mtime)[-1]
scenario_ids = [
    "bear_2022",
    "recovery_2023",
    "bull_2024",
    "choppy_2025",
    "ytd_2026",
    "full_2022_2026",
]
rows = []

for scenario_id in scenario_ids:
    fp = latest / f"{scenario_id}.zip"
    if not fp.exists():
        continue
    with ZipFile(fp) as zf:
        payload_name = next(
            name for name in zf.namelist()
            if name.endswith(".json")
            and "_config" not in name
            and "_market_change.feather" not in name
            and "_signals.pkl" not in name
            and "_rejected.pkl" not in name
            and "_exited.pkl" not in name
        )
        payload = json.loads(zf.read(payload_name))
    strategy = next(iter(payload["strategy"].values()))
    rows.append({
        "scenario": scenario_id,
        "date_range": f"{strategy['backtest_start']} -> {strategy['backtest_end']}",
        "profit_pct": round((strategy.get("profit_total", 0) or 0) * 100, 2),
        "final_balance": round(strategy.get("final_balance", 0) or 0, 2),
        "trades": strategy.get("total_trades", 0),
        "win_rate_pct": round((strategy.get("wins", 0) / strategy.get("total_trades", 1) * 100) if strategy.get("total_trades", 0) else 0.0, 2),
        "profit_factor": round(strategy.get("profit_factor", 0) or 0, 2),
        "max_dd_pct": round((strategy.get("max_drawdown_account", 0) or 0) * 100, 2),
        "market_change_pct": round((strategy.get("market_change", 0) or 0) * 100, 2),
        "longs": strategy.get("trade_count_long", 0),
        "shorts": strategy.get("trade_count_short", 0),
        "long_profit_pct": round((strategy.get("profit_total_long", 0) or 0) * 100, 2),
        "short_profit_pct": round((strategy.get("profit_total_short", 0) or 0) * 100, 2),
    })

summary_path = latest / "kivanc_futures_1d_regimes_summary.json"
summary_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

lines = [
    "# Kivanc STMA Futures 1D Long/Short Research",
    "",
    "Research config: `user_data/config_futures_research.json`",
    "Strategy: `KivancSupertrendedMovingAveragesFutures1D`",
    "",
    "| Scenario | Date | Profit | 1000 USDT Result | Trades | Longs | Shorts | Long PnL | Short PnL | Win Rate | PF | MaxDD | Market |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]

for row in rows:
    lines.append(
        f"| {row['scenario']} | {row['date_range']} | {row['profit_pct']:.2f}% | {row['final_balance']:.2f} | "
        f"{row['trades']} | {row['longs']} | {row['shorts']} | {row['long_profit_pct']:.2f}% | {row['short_profit_pct']:.2f}% | {row['win_rate_pct']:.2f}% | "
        f"{row['profit_factor']:.2f} | {row['max_dd_pct']:.2f}% | {row['market_change_pct']:.2f}% |"
    )

(latest / "kivanc_futures_1d_regimes_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(latest)
'@ | python -
