param(
    [string]$SpotReportDir = "",
    [string]$FuturesReportDir = ""
)

if (-not $SpotReportDir) {
    $SpotReportDir = (Get-ChildItem ".\reports" | Where-Object { $_.PSIsContainer -and $_.Name -like "kivanc_spot_1d_regimes_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName)
}

if (-not $FuturesReportDir) {
    $FuturesReportDir = (Get-ChildItem ".\reports" | Where-Object { $_.PSIsContainer -and $_.Name -like "kivanc_futures_1d_regimes_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName)
}

@'
import json
import pathlib
import sys
from datetime import datetime, timezone

spot_dir = pathlib.Path(sys.argv[1])
futures_dir = pathlib.Path(sys.argv[2])
report_root = spot_dir.parents[0]
report_dir = report_root / f"kivanc_spot_vs_futures_1d_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
report_dir.mkdir(parents=True, exist_ok=True)

scenario_ids = [
    "bear_2022",
    "recovery_2023",
    "bull_2024",
    "choppy_2025",
    "ytd_2026",
    "full_2022_2026",
]

spot_rows = json.loads((spot_dir / "kivanc_spot_1d_regimes_summary.json").read_text(encoding="utf-8"))
futures_rows = json.loads((futures_dir / "kivanc_futures_1d_regimes_summary.json").read_text(encoding="utf-8"))
spot_by = {row["scenario"]: row for row in spot_rows}
futures_by = {row["scenario"]: row for row in futures_rows}

comparison = []
decision_rows = []
for scenario_id in scenario_ids:
    spot = spot_by[scenario_id]
    fut = futures_by[scenario_id]
    comparison.append({
        "scenario": scenario_id,
        "spot_profit_pct": spot["profit_pct"],
        "futures_profit_pct": fut["profit_pct"],
        "profit_delta_pct": round(fut["profit_pct"] - spot["profit_pct"], 2),
        "spot_dd_pct": spot["max_dd_pct"],
        "futures_dd_pct": fut["max_dd_pct"],
        "drawdown_delta_pct": round(fut["max_dd_pct"] - spot["max_dd_pct"], 2),
    })

    if scenario_id == "ytd_2026":
        preferred = "none"
        reason = "No trades in either mode."
    elif fut["profit_pct"] > spot["profit_pct"] and fut["max_dd_pct"] <= spot["max_dd_pct"] + 5:
        preferred = "futures_1d"
        reason = "Higher return with acceptable drawdown increase."
    elif spot["profit_pct"] > fut["profit_pct"] and spot["max_dd_pct"] <= fut["max_dd_pct"]:
        preferred = "spot_1d"
        reason = "Better return with lower or equal drawdown."
    elif spot["profit_pct"] >= fut["profit_pct"]:
        preferred = "spot_1d"
        reason = "Higher return or meaningfully cleaner risk profile."
    else:
        preferred = "futures_1d"
        reason = "Higher return outweighs moderate drawdown cost."

    decision_rows.append({
        "scenario": scenario_id,
        "preferred": preferred,
        "reason": reason,
    })

summary = {
    "spot_report_dir": str(spot_dir),
    "futures_report_dir": str(futures_dir),
    "comparison": comparison,
    "decision_rows": decision_rows,
}
(report_dir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

lines = [
    "# Spot 1D vs Futures 1D Decision Table",
    "",
    f"Spot source: `{spot_dir.name}`",
    f"Futures source: `{futures_dir.name}`",
    "",
    "## Comparison",
    "",
    "| Scenario | Spot Profit | Futures Profit | Delta | Spot MaxDD | Futures MaxDD | Delta |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for row in comparison:
    lines.append(
        f"| {row['scenario']} | {row['spot_profit_pct']:.2f}% | {row['futures_profit_pct']:.2f}% | {row['profit_delta_pct']:.2f}% | {row['spot_dd_pct']:.2f}% | {row['futures_dd_pct']:.2f}% | {row['drawdown_delta_pct']:.2f}% |"
    )

lines.extend([
    "",
    "## Decision Table",
    "",
    "| Scenario | Preferred Mode | Reason |",
    "|---|---|---|",
])
for row in decision_rows:
    lines.append(f"| {row['scenario']} | {row['preferred']} | {row['reason']} |")

(report_dir / "spot_vs_futures_decision_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(report_dir)
'@ | python - $SpotReportDir $FuturesReportDir
