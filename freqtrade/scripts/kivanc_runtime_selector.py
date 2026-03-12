from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"

SCENARIO_WINDOWS = {
    "bear_2022": ("2022-05-01", "2022-12-31"),
    "recovery_2023": ("2023-01-01", "2023-12-31"),
    "bull_2024": ("2024-01-01", "2024-12-31"),
    "choppy_2025": ("2025-01-01", "2025-12-31"),
    "ytd_2026": ("2026-01-01", "2026-03-01"),
    "full_2022_2026": ("2022-01-01", "2026-03-01"),
}


def scenario_timerange(scenario: str) -> str:
    start_s, end_s = SCENARIO_WINDOWS[scenario]
    return start_s.replace("-", "") + "-" + end_s.replace("-", "")


def latest_compare_summary() -> Path:
    candidates = sorted(
        [p for p in REPORTS_DIR.iterdir() if p.is_dir() and p.name.startswith("kivanc_spot_vs_futures_1d_")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No spot-vs-futures comparison reports found.")
    summary_path = candidates[0] / "comparison_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Comparison summary missing: {summary_path}")
    return summary_path


def resolve_scenario(target_date: datetime) -> tuple[str, str]:
    for scenario_id, (start_s, end_s) in SCENARIO_WINDOWS.items():
        start = datetime.fromisoformat(start_s)
        end = datetime.fromisoformat(end_s)
        if start <= target_date <= end:
            return scenario_id, "date_window_match"

    if target_date > datetime.fromisoformat(SCENARIO_WINDOWS["ytd_2026"][1]):
        return "ytd_2026", "nearest_recent_window"
    return "full_2022_2026", "fallback_full_window"


def main() -> None:
    parser = argparse.ArgumentParser(description="Recommend spot or futures mode from the latest Kivanc decision table.")
    parser.add_argument("--scenario", default="")
    parser.add_argument("--date", default="")
    args = parser.parse_args()

    summary_path = latest_compare_summary()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    decision_rows = {row["scenario"]: row for row in summary["decision_rows"]}
    comparison_rows = {row["scenario"]: row for row in summary["comparison"]}

    if args.scenario:
        scenario = args.scenario
        source = "manual_scenario"
    else:
        target_date = datetime.now()
        if args.date:
            target_date = datetime.fromisoformat(args.date)
        scenario, source = resolve_scenario(target_date)

    if scenario not in decision_rows:
        raise ValueError(f"Scenario not found in latest decision table: {scenario}")

    decision = decision_rows[scenario]
    comparison = comparison_rows[scenario]
    output = {
        "scenario": scenario,
        "selection_source": source,
        "preferred_mode": decision["preferred"],
        "reason": decision["reason"],
        "timerange": scenario_timerange(scenario),
        "spot_profit_pct": comparison["spot_profit_pct"],
        "futures_profit_pct": comparison["futures_profit_pct"],
        "filtered_futures_profit_pct": comparison.get("filtered_futures_profit_pct"),
        "spot_max_dd_pct": comparison["spot_dd_pct"],
        "futures_max_dd_pct": comparison["futures_dd_pct"],
        "filtered_futures_max_dd_pct": comparison.get("filtered_futures_dd_pct"),
        "spot_backtest_script": str(ROOT / "scripts" / "backtest_kivanc_1d.ps1"),
        "futures_backtest_script": str(ROOT / "scripts" / "backtest_kivanc_futures_1d.ps1"),
        "filtered_futures_backtest_script": str(ROOT / "scripts" / "backtest_kivanc_futures_filtered_1d.ps1"),
        "comparison_report": str(summary_path.parent),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
