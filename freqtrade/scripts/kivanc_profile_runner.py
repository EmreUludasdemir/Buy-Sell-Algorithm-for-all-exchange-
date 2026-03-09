from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "user_data" / "config_production.json"
PROFILES_DIR = ROOT / "user_data" / "profiles"
STRATEGY_PARAM_PATH = ROOT / "user_data" / "strategies" / "KivancSupertrendedMovingAverages1D.json"
BACKTEST_RESULTS_DIR = ROOT / "user_data" / "backtest_results"
HYPEROPT_RESULTS_DIR = ROOT / "user_data" / "hyperopt_results"
REPORTS_DIR = ROOT / "reports"

STRATEGY_NAME = "KivancSupertrendedMovingAverages1D"
PAIRS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
PAIR_FILES = [pair.replace("/", "_") for pair in PAIRS]
SCENARIOS = [
    ("bear_2022", "20220501-20221231"),
    ("recovery_2023", "20230101-20231231"),
    ("bull_2024", "20240101-20241231"),
    ("choppy_2025", "20250101-20251231"),
    ("ytd_2026", "20260101-20260301"),
    ("full_2022_2026", "20220101-20260301"),
]
REQUIRED_PROFILE_KEYS = {"buy", "roi", "stoploss", "trailing", "max_open_trades"}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_profile(profile_name: str) -> tuple[Path, dict]:
    path = PROFILES_DIR / f"{profile_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    params = data.get("params", {})
    missing = sorted(REQUIRED_PROFILE_KEYS - set(params.keys()))
    if data.get("strategy_name") != STRATEGY_NAME:
        raise ValueError(f"{path.name} must target {STRATEGY_NAME}.")
    if missing:
        raise ValueError(f"{path.name} is missing params keys: {', '.join(missing)}")
    return path, data


def ensure_ohlcv_data(timeframe: str) -> None:
    missing = []
    data_dir = ROOT / "user_data" / "data" / "binance"
    for pair_file in PAIR_FILES:
        target = data_dir / f"{pair_file}-{timeframe}.feather"
        if not target.exists():
            missing.append(target.name)
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing {timeframe} data files: {joined}. Run .\\scripts\\download_kivanc_{timeframe}.ps1 first."
        )


def run_command(args: list[str], capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() if result.stderr else result.stdout.strip()
        raise RuntimeError(detail or f"Command failed: {' '.join(args)}")
    return result


def new_files(directory: Path, pattern: str, before: set[Path]) -> list[Path]:
    return sorted([path for path in directory.glob(pattern) if path not in before], key=lambda item: item.stat().st_mtime)


@contextmanager
def applied_profile(profile_path: Path) -> Iterable[None]:
    backup_path = STRATEGY_PARAM_PATH.with_suffix(".json.bak")
    shutil.copy2(STRATEGY_PARAM_PATH, backup_path)
    try:
        shutil.copy2(profile_path, STRATEGY_PARAM_PATH)
        yield
    finally:
        if not backup_path.exists():
            raise RuntimeError(f"Backup restore failed for {STRATEGY_PARAM_PATH}.")
        shutil.copy2(backup_path, STRATEGY_PARAM_PATH)
        backup_path.unlink()


def docker_backtest(timerange: str, timeframe: str) -> Path:
    before = set(BACKTEST_RESULTS_DIR.glob("backtest-result-*.zip"))
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "backtesting",
        "--config",
        "user_data/config_production.json",
        "--strategy",
        STRATEGY_NAME,
        "--timeframe",
        timeframe,
        "--timerange",
        timerange,
        "--pairs",
        *PAIRS,
        "--data-format-ohlcv",
        "feather",
        "--enable-protections",
        "--export",
        "trades",
    ]
    run_command(command)
    created = new_files(BACKTEST_RESULTS_DIR, "backtest-result-*.zip", before)
    if not created:
        raise RuntimeError("No new backtest zip was produced.")
    return created[-1]


def docker_hyperopt(timeframe: str) -> tuple[Path, str]:
    before = set(HYPEROPT_RESULTS_DIR.glob("*.fthypt"))
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "hyperopt",
        "--config",
        "user_data/config_production.json",
        "--strategy",
        STRATEGY_NAME,
        "--timeframe",
        timeframe,
        "--timerange",
        "20220101-20251231",
        "--pairs",
        *PAIRS,
        "--data-format-ohlcv",
        "feather",
        "--hyperopt-loss",
        "ProfitDrawDownHyperOptLoss",
        "--spaces",
        "roi",
        "stoploss",
        "trailing",
        "--epochs",
        "250",
        "--min-trades",
        "30",
        "--random-state",
        "42",
        "--disable-param-export",
        "--early-stop",
        "80",
        "-j",
        "8",
    ]
    stdout = run_command(command, capture_output=True).stdout
    created = new_files(HYPEROPT_RESULTS_DIR, "*.fthypt", before)
    if not created:
        raise RuntimeError("No new hyperopt result file was produced.")
    return created[-1], stdout


def docker_hyperopt_show(result_file: Path) -> str:
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "hyperopt-show",
        "--config",
        "user_data/config_production.json",
        "--best",
        "--print-json",
        "--disable-param-export",
        "--hyperopt-filename",
        result_file.name,
    ]
    return run_command(command, capture_output=True).stdout


def parse_hyperopt_params(output: str) -> dict:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise RuntimeError("Could not find hyperopt params JSON in hyperopt-show output.")


def parse_backtest_zip(zip_path: Path, scenario_id: str) -> dict:
    with ZipFile(zip_path) as archive:
        payload_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".json") and "_config" not in name and f"_{STRATEGY_NAME}.json" not in name
        )
        payload = json.loads(archive.read(payload_name))

    strategy = payload["strategy"][STRATEGY_NAME]
    return {
        "scenario": scenario_id,
        "date_range": f"{strategy['backtest_start']} -> {strategy['backtest_end']}",
        "profit_pct": round(strategy["profit_total"] * 100, 2),
        "final_balance": round(strategy["final_balance"], 2),
        "trades": strategy["total_trades"],
        "win_rate_pct": round((strategy["wins"] / strategy["total_trades"] * 100) if strategy["total_trades"] else 0.0, 2),
        "profit_factor": round(strategy["profit_factor"], 2),
        "max_dd_pct": round(strategy["max_drawdown_account"] * 100, 2),
        "market_change_pct": round(strategy["market_change"] * 100, 2),
        "avg_holding": strategy["holding_avg"],
        "best_pair": strategy["best_pair"]["key"],
        "best_pair_profit_pct": round(strategy["best_pair"]["profit_total_pct"], 2),
        "zip_file": zip_path.name,
    }


def write_matrix_report(report_path: Path, title: str, intro: list[str], rows: list[dict]) -> None:
    lines = [f"# {title}", ""]
    lines.extend(intro)
    if intro:
        lines.append("")
    lines.append("| Scenario | Date | Profit | 1000 USDT Result | Trades | Win Rate | PF | MaxDD | Market | Avg Hold | Best Pair |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for row in rows:
        lines.append(
            f"| {row['scenario']} | {row['date_range']} | {row['profit_pct']:.2f}% | "
            f"{row['final_balance']:.2f} | {row['trades']} | {row['win_rate_pct']:.2f}% | "
            f"{row['profit_factor']:.2f} | {row['max_dd_pct']:.2f}% | {row['market_change_pct']:.2f}% | "
            f"{row['avg_holding']} | {row['best_pair']} ({row['best_pair_profit_pct']:.2f}%) |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def backtest_matrix(profile_name: str, label: str, timeframe: str) -> Path:
    ensure_ohlcv_data(timeframe)
    profile_path, _ = load_profile(profile_name)
    report_dir = REPORTS_DIR / f"{label}_{utc_timestamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with applied_profile(profile_path):
        for scenario_id, timerange in SCENARIOS:
            zip_path = docker_backtest(timerange, timeframe)
            rows.append(parse_backtest_zip(zip_path, scenario_id))

    summary_path = report_dir / f"{label}_summary.json"
    summary_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_matrix_report(
        report_dir / f"{label}.md",
        "Kivanc STMA 4H Risk Validation",
        [
            f"Profile: `{profile_name}`",
            f"Timeframe: `{timeframe}`",
            "This report applies the selected profile temporarily and restores the production JSON after each run.",
        ],
        rows,
    )
    return report_dir


def compare_profiles(baseline_name: str, candidate_name: str, label: str, timeframe: str) -> Path:
    ensure_ohlcv_data(timeframe)
    baseline_path, _ = load_profile(baseline_name)
    candidate_path, _ = load_profile(candidate_name)
    report_dir = REPORTS_DIR / f"{label}_{utc_timestamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)

    def collect(profile_path: Path) -> list[dict]:
        rows = []
        with applied_profile(profile_path):
            for scenario_id, timerange in SCENARIOS:
                zip_path = docker_backtest(timerange, timeframe)
                rows.append(parse_backtest_zip(zip_path, scenario_id))
        return rows

    baseline_rows = collect(baseline_path)
    candidate_rows = collect(candidate_path)

    baseline_by_scenario = {row["scenario"]: row for row in baseline_rows}
    comparison_rows = []
    for candidate in candidate_rows:
        baseline = baseline_by_scenario[candidate["scenario"]]
        comparison_rows.append(
            {
                "scenario": candidate["scenario"],
                "baseline_profit_pct": baseline["profit_pct"],
                "candidate_profit_pct": candidate["profit_pct"],
                "profit_delta_pct": round(candidate["profit_pct"] - baseline["profit_pct"], 2),
                "baseline_dd_pct": baseline["max_dd_pct"],
                "candidate_dd_pct": candidate["max_dd_pct"],
                "drawdown_delta_pct": round(candidate["max_dd_pct"] - baseline["max_dd_pct"], 2),
            }
        )

    (report_dir / "baseline_4h_summary.json").write_text(json.dumps(baseline_rows, indent=2), encoding="utf-8")
    (report_dir / "risk_4h_summary.json").write_text(json.dumps(candidate_rows, indent=2), encoding="utf-8")
    (report_dir / "comparison_summary.json").write_text(json.dumps(comparison_rows, indent=2), encoding="utf-8")

    lines = [
        "# Kivanc Profile Comparison",
        "",
        f"Baseline profile: `{baseline_name}` on `{timeframe}`",
        f"Candidate profile: `{candidate_name}` on `{timeframe}`",
        "",
        "## Delta",
        "",
        "| Scenario | Baseline Profit | Candidate Profit | Delta | Baseline MaxDD | Candidate MaxDD | Delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in comparison_rows:
        lines.append(
            f"| {row['scenario']} | {row['baseline_profit_pct']:.2f}% | {row['candidate_profit_pct']:.2f}% | "
            f"{row['profit_delta_pct']:.2f}% | {row['baseline_dd_pct']:.2f}% | {row['candidate_dd_pct']:.2f}% | "
            f"{row['drawdown_delta_pct']:.2f}% |"
        )

    (report_dir / f"{label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_dir


def hyperopt_risk(base_profile_name: str, label: str, timeframe: str) -> Path:
    ensure_ohlcv_data(timeframe)
    profile_path, _ = load_profile(base_profile_name)
    report_dir = REPORTS_DIR / f"{label}_{utc_timestamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)

    with applied_profile(profile_path):
        result_file, hyperopt_output = docker_hyperopt(timeframe)
        show_output = docker_hyperopt_show(result_file)

    best_params = parse_hyperopt_params(show_output)
    match = re.search(
        r"Total profit\s+(-?\d+\.\d+)\s+USDT\s+\(\s*(-?\d+\.\d+)%\).*?Max Drawdown \(Acct\)\s+(\d+\.\d+)\s+USDT\s+\(\s*(\d+\.\d+)%",
        show_output,
        re.DOTALL,
    )
    summary = {
        "base_profile": base_profile_name,
        "timeframe": timeframe,
        "hyperopt_file": result_file.name,
        "best_params": best_params,
    }
    if match:
        summary["reported_profit_usdt"] = float(match.group(1))
        summary["reported_profit_pct"] = float(match.group(2))
        summary["reported_drawdown_usdt"] = float(match.group(3))
        summary["reported_drawdown_pct"] = float(match.group(4))

    (report_dir / "hyperopt_best_params.json").write_text(json.dumps(best_params, indent=2), encoding="utf-8")
    (report_dir / "hyperopt_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (report_dir / "hyperopt_stdout.txt").write_text(hyperopt_output, encoding="utf-8")
    (report_dir / "hyperopt_show.txt").write_text(show_output, encoding="utf-8")

    markdown = [
        "# Kivanc STMA 4H Risk Hyperopt",
        "",
        f"Base profile: `{base_profile_name}`",
        f"Timeframe: `{timeframe}`",
        f"Result file: `{result_file.name}`",
        "",
        "## Best Params",
        "",
        "```json",
        json.dumps(best_params, indent=2),
        "```",
    ]
    if "reported_profit_pct" in summary:
        markdown.extend(
            [
                "",
                "## Reported Best Result",
                "",
                f"- Profit: `{summary['reported_profit_pct']:.2f}%`",
                f"- Profit USDT: `{summary['reported_profit_usdt']:.3f}`",
                f"- MaxDD: `{summary['reported_drawdown_pct']:.2f}%`",
            ]
        )
    (report_dir / f"{label}.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return report_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile-safe helper for Kivanc STMA operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest_parser = subparsers.add_parser("backtest-matrix")
    backtest_parser.add_argument("--profile", required=True)
    backtest_parser.add_argument("--label", required=True)
    backtest_parser.add_argument("--timeframe", default="4h")

    compare_parser = subparsers.add_parser("compare-profiles")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--candidate", required=True)
    compare_parser.add_argument("--label", required=True)
    compare_parser.add_argument("--timeframe", default="4h")

    hyperopt_parser = subparsers.add_parser("hyperopt-risk")
    hyperopt_parser.add_argument("--base-profile", required=True)
    hyperopt_parser.add_argument("--label", required=True)
    hyperopt_parser.add_argument("--timeframe", default="4h")

    args = parser.parse_args()
    if args.command == "backtest-matrix":
        report_dir = backtest_matrix(args.profile, args.label, args.timeframe)
    elif args.command == "compare-profiles":
        report_dir = compare_profiles(args.baseline, args.candidate, args.label, args.timeframe)
    else:
        report_dir = hyperopt_risk(args.base_profile, args.label, args.timeframe)

    print(report_dir)


if __name__ == "__main__":
    main()
