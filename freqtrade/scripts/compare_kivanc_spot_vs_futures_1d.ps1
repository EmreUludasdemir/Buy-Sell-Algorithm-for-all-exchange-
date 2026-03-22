param(
    [string]$SpotReportDir = "",
    [string]$FuturesReportDir = "",
    [string]$FilteredFuturesReportDir = ""
)

$reportRoot = Join-Path (Split-Path $PSScriptRoot -Parent) "reports"

if (-not $SpotReportDir) {
    $SpotReportDir = (Get-ChildItem $reportRoot | Where-Object { $_.PSIsContainer -and $_.Name -like "kivanc_spot_1d_regimes_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName)
}

if (-not $FuturesReportDir) {
    $FuturesReportDir = (Get-ChildItem $reportRoot | Where-Object { $_.PSIsContainer -and $_.Name -like "kivanc_futures_1d_regimes_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName)
}

if (-not $FilteredFuturesReportDir) {
    $FilteredFuturesReportDir = (Get-ChildItem $reportRoot | Where-Object { $_.PSIsContainer -and $_.Name -like "kivanc_futures_filtered_1d_regimes_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName)
}

@'
import json
import pathlib
import sys
from datetime import datetime, timezone

spot_dir = pathlib.Path(sys.argv[1])
futures_dir = pathlib.Path(sys.argv[2])
filtered_dir = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
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

def resolve_summary_path(directory: pathlib.Path, *preferred_names: str) -> pathlib.Path:
    for name in preferred_names:
        candidate = directory / name
        if candidate.exists():
            return candidate
    summaries = sorted(directory.glob("*summary.json"))
    if summaries:
        return summaries[0]
    raise FileNotFoundError(f"No summary json found in {directory}")


spot_rows = json.loads(resolve_summary_path(spot_dir, "kivanc_spot_1d_regimes_summary.json").read_text(encoding="utf-8"))
futures_rows = json.loads(resolve_summary_path(futures_dir, "kivanc_futures_1d_regimes_summary.json").read_text(encoding="utf-8"))
filtered_rows = []
if filtered_dir:
    filtered_rows = json.loads(
        resolve_summary_path(
            filtered_dir,
            "kivanc_futures_filtered_1d_regimes_summary.json",
            "asym60_regimes_summary.json",
        ).read_text(encoding="utf-8")
    )
spot_by = {row["scenario"]: row for row in spot_rows}
futures_by = {row["scenario"]: row for row in futures_rows}
filtered_by = {row["scenario"]: row for row in filtered_rows}


def choose_mode(candidates):
    active = [candidate for candidate in candidates if candidate["trades"] > 0 or candidate["profit_pct"] != 0]
    if not active:
        return "none", "No trades in any mode."

    active_sorted = sorted(active, key=lambda item: (item["profit_pct"], -item["max_dd_pct"]), reverse=True)
    leader = active_sorted[0]
    if len(active_sorted) == 1:
        return leader["mode"], "Only one mode produced trades."

    runner_up = active_sorted[1]
    if leader["profit_pct"] >= runner_up["profit_pct"] and leader["max_dd_pct"] <= runner_up["max_dd_pct"] + 5:
        return leader["mode"], "Highest return with acceptable drawdown."

    near_leaders = [candidate for candidate in active_sorted if candidate["profit_pct"] >= leader["profit_pct"] - 15]
    risk_leader = min(near_leaders, key=lambda item: item["max_dd_pct"])
    if risk_leader["mode"] != leader["mode"]:
        return risk_leader["mode"], "Return gap did not justify the extra drawdown."

    return leader["mode"], "Highest return remained the best tradeoff."

comparison = []
decision_rows = []


def fmt_pct(value):
    if value is None:
        return ""
    return f"{value:.2f}%"


for scenario_id in scenario_ids:
    spot = spot_by[scenario_id]
    fut = futures_by[scenario_id]
    filtered = filtered_by.get(scenario_id)
    row = {
        "scenario": scenario_id,
        "spot_profit_pct": spot["profit_pct"],
        "futures_profit_pct": fut["profit_pct"],
        "filtered_futures_profit_pct": filtered["profit_pct"] if filtered else None,
        "profit_delta_pct": round(fut["profit_pct"] - spot["profit_pct"], 2),
        "spot_dd_pct": spot["max_dd_pct"],
        "futures_dd_pct": fut["max_dd_pct"],
        "filtered_futures_dd_pct": filtered["max_dd_pct"] if filtered else None,
        "drawdown_delta_pct": round(fut["max_dd_pct"] - spot["max_dd_pct"], 2),
    }
    comparison.append(row)

    candidates = [
        {"mode": "spot_1d", "profit_pct": spot["profit_pct"], "max_dd_pct": spot["max_dd_pct"], "trades": spot["trades"]},
        {"mode": "futures_1d", "profit_pct": fut["profit_pct"], "max_dd_pct": fut["max_dd_pct"], "trades": fut["trades"]},
    ]
    if filtered:
        candidates.append({
            "mode": "filtered_futures_1d",
            "profit_pct": filtered["profit_pct"],
            "max_dd_pct": filtered["max_dd_pct"],
            "trades": filtered["trades"],
        })

    preferred, reason = choose_mode(candidates)

    decision_rows.append({
        "scenario": scenario_id,
        "preferred": preferred,
        "reason": reason,
    })

summary = {
    "spot_report_dir": str(spot_dir),
    "futures_report_dir": str(futures_dir),
    "filtered_futures_report_dir": str(filtered_dir) if filtered_dir else "",
    "comparison": comparison,
    "decision_rows": decision_rows,
}
(report_dir / "comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

lines = [
    "# Spot 1D vs Futures Modes Decision Table",
    "",
    f"Spot source: `{spot_dir.name}`",
    f"Futures source: `{futures_dir.name}`",
    f"Filtered futures source: `{filtered_dir.name}`" if filtered_dir else "Filtered futures source: `not provided`",
    "",
    "## Comparison",
    "",
    "| Scenario | Spot Profit | Futures Profit | Filtered Futures Profit | Spot MaxDD | Futures MaxDD | Filtered Futures MaxDD |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for row in comparison:
    lines.append(
        f"| {row['scenario']} | {fmt_pct(row['spot_profit_pct'])} | {fmt_pct(row['futures_profit_pct'])} | "
        f"{fmt_pct(row['filtered_futures_profit_pct'])} | {fmt_pct(row['spot_dd_pct'])} | {fmt_pct(row['futures_dd_pct'])} | "
        f"{fmt_pct(row['filtered_futures_dd_pct'])} |"
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
'@ | python - $SpotReportDir $FuturesReportDir $FilteredFuturesReportDir
