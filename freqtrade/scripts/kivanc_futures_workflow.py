from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
HYPEROPT_RESULTS_DIR = ROOT / "user_data" / "hyperopt_results"
BACKTEST_RESULTS_DIR = ROOT / "user_data" / "backtest_results"
FUTURES_PARAM_PATH = ROOT / "user_data" / "strategies_research" / "KivancSupertrendedMovingAveragesFutures1D.json"

STRATEGY_NAME = "KivancSupertrendedMovingAveragesFutures1D"
VARIANTS = {
    "futures": {
        "config_path": ROOT / "user_data" / "config_futures_research.json",
        "pairs": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "BNB/USDT:USDT",
            "SOL/USDT:USDT",
            "XRP/USDT:USDT",
        ],
        "pair_files": [
            "BTC_USDT_USDT-1d-futures.feather",
            "ETH_USDT_USDT-1d-futures.feather",
            "BNB_USDT_USDT-1d-futures.feather",
            "SOL_USDT_USDT-1d-futures.feather",
            "XRP_USDT_USDT-1d-futures.feather",
        ],
    },
    "filtered_futures": {
        "config_path": ROOT / "user_data" / "config_futures_filtered_research.json",
        "pairs": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "BNB/USDT:USDT",
            "XRP/USDT:USDT",
        ],
        "pair_files": [
            "BTC_USDT_USDT-1d-futures.feather",
            "ETH_USDT_USDT-1d-futures.feather",
            "BNB_USDT_USDT-1d-futures.feather",
            "XRP_USDT_USDT-1d-futures.feather",
        ],
    },
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


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
    return sorted(
        [path for path in directory.glob(pattern) if path not in before],
        key=lambda item: item.stat().st_mtime,
    )


def variant_spec(name: str) -> dict:
    if name not in VARIANTS:
        raise ValueError(f"Unsupported variant: {name}")
    return VARIANTS[name]


def config_cli_path(config_path: Path) -> str:
    return config_path.relative_to(ROOT).as_posix()


def variant_title(name: str) -> str:
    return name.replace("_", " ").title()


def ensure_futures_data(spec: dict) -> None:
    data_dir = ROOT / "user_data" / "data" / "binance" / "futures"
    missing = [name for name in spec["pair_files"] if not (data_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing futures data files: "
            + ", ".join(missing)
            + ". Run .\\scripts\\download_kivanc_futures_1d.ps1 first."
        )


@contextmanager
def applied_futures_params(param_path: Path):
    backup_path = FUTURES_PARAM_PATH.with_suffix(".json.bak")
    shutil.copy2(FUTURES_PARAM_PATH, backup_path)
    try:
        shutil.copy2(param_path, FUTURES_PARAM_PATH)
        yield
    finally:
        if not backup_path.exists():
            raise RuntimeError(f"Backup restore failed for {FUTURES_PARAM_PATH}.")
        shutil.copy2(backup_path, FUTURES_PARAM_PATH)
        backup_path.unlink()


def docker_backtest_full(spec: dict) -> Path:
    before = set(BACKTEST_RESULTS_DIR.glob("backtest-result-*.zip"))
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "backtesting",
        "--config",
        config_cli_path(spec["config_path"]),
        "--strategy",
        STRATEGY_NAME,
        "--strategy-path",
        "user_data/strategies_research",
        "--timeframe",
        "1d",
        "--timerange",
        "20220101-20260301",
        "--pairs",
        *spec["pairs"],
        "--data-format-ohlcv",
        "feather",
        "--cache",
        "none",
        "--enable-protections",
        "--export",
        "trades",
    ]
    run_command(command)
    created = new_files(BACKTEST_RESULTS_DIR, "backtest-result-*.zip", before)
    if not created:
        latest_marker = BACKTEST_RESULTS_DIR / ".last_result.json"
        if latest_marker.exists():
            latest_name = json.loads(latest_marker.read_text(encoding="utf-8")).get("latest_backtest")
            if latest_name:
                fallback = BACKTEST_RESULTS_DIR / latest_name
                if fallback.exists():
                    return fallback
        raise RuntimeError("No new futures backtest zip was produced.")
    return created[-1]


def parse_backtest_zip(zip_path: Path) -> dict:
    with ZipFile(zip_path) as archive:
        payload_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".json")
            and "_config" not in name
            and "_market_change.feather" not in name
            and "_signals.pkl" not in name
            and "_rejected.pkl" not in name
            and "_exited.pkl" not in name
        )
        payload = json.loads(archive.read(payload_name))

    strategy = payload["strategy"][STRATEGY_NAME]
    return {
        "date_range": f"{strategy['backtest_start']} -> {strategy['backtest_end']}",
        "profit_pct": round((strategy.get("profit_total", 0) or 0) * 100, 2),
        "final_balance": round(strategy.get("final_balance", 0) or 0, 2),
        "trades": strategy.get("total_trades", 0),
        "win_rate_pct": round(
            (strategy.get("wins", 0) / strategy.get("total_trades", 1) * 100)
            if strategy.get("total_trades", 0)
            else 0.0,
            2,
        ),
        "profit_factor": round(strategy.get("profit_factor", 0) or 0, 2),
        "max_dd_pct": round((strategy.get("max_drawdown_account", 0) or 0) * 100, 2),
        "market_change_pct": round((strategy.get("market_change", 0) or 0) * 100, 2),
        "longs": strategy.get("trade_count_long", 0),
        "shorts": strategy.get("trade_count_short", 0),
        "long_profit_pct": round((strategy.get("profit_total_long", 0) or 0) * 100, 2),
        "short_profit_pct": round((strategy.get("profit_total_short", 0) or 0) * 100, 2),
        "zip_file": zip_path.name,
    }


def docker_hyperopt_risk(spec: dict, epochs: int) -> tuple[Path, str]:
    return docker_hyperopt_generic(spec, ["roi", "stoploss", "trailing"], epochs)


def docker_hyperopt_buy(spec: dict, epochs: int) -> tuple[Path, str]:
    return docker_hyperopt_generic(spec, ["buy"], epochs)


def docker_hyperopt_generic(spec: dict, spaces: list[str], epochs: int) -> tuple[Path, str]:
    before = set(HYPEROPT_RESULTS_DIR.glob("*.fthypt"))
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "hyperopt",
        "--config",
        config_cli_path(spec["config_path"]),
        "--strategy",
        STRATEGY_NAME,
        "--strategy-path",
        "user_data/strategies_research",
        "--timeframe",
        "1d",
        "--timerange",
        "20220101-20260301",
        "--pairs",
        *spec["pairs"],
        "--data-format-ohlcv",
        "feather",
        "--hyperopt-loss",
        "ProfitDrawDownHyperOptLoss",
        "--spaces",
        *spaces,
        "--epochs",
        str(epochs),
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
        raise RuntimeError("No new futures hyperopt result file was produced.")
    return created[-1], stdout


def docker_hyperopt_show(spec: dict, result_file: Path) -> tuple[str, dict]:
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "hyperopt-show",
        "--config",
        config_cli_path(spec["config_path"]),
        "--best",
        "--print-json",
        "--disable-param-export",
        "--hyperopt-filename",
        result_file.name,
    ]
    stdout = run_command(command, capture_output=True).stdout
    best_json = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            best_json = json.loads(line)
    if best_json is None:
        raise RuntimeError("Could not extract best params JSON from futures hyperopt-show output.")
    return stdout, best_json


def build_candidate_params(current_payload: dict, best_json: dict) -> dict:
    return {
        "strategy_name": STRATEGY_NAME,
        "params": {
            "roi": best_json["minimal_roi"],
            "stoploss": {"stoploss": best_json["stoploss"]},
            "trailing": {
                "trailing_stop": best_json["trailing_stop"],
                "trailing_stop_positive": best_json["trailing_stop_positive"],
                "trailing_stop_positive_offset": best_json["trailing_stop_positive_offset"],
                "trailing_only_offset_is_reached": best_json["trailing_only_offset_is_reached"],
            },
            "max_open_trades": {"max_open_trades": best_json["max_open_trades"]},
            "buy": current_payload["params"]["buy"],
        },
        "ft_stratparam_v": current_payload["ft_stratparam_v"],
        "export_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
    }


def build_buy_candidate_params(current_payload: dict, best_json: dict) -> dict:
    return {
        "strategy_name": STRATEGY_NAME,
        "params": {
            "roi": current_payload["params"]["roi"],
            "stoploss": current_payload["params"]["stoploss"],
            "trailing": current_payload["params"]["trailing"],
            "max_open_trades": {"max_open_trades": best_json["max_open_trades"]},
            "buy": best_json["params"],
        },
        "ft_stratparam_v": current_payload["ft_stratparam_v"],
        "export_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
    }


def candidate_beats_baseline(candidate: dict, baseline: dict) -> bool:
    if candidate["profit_pct"] > baseline["profit_pct"]:
        return True
    if candidate["profit_pct"] == baseline["profit_pct"] and candidate["max_dd_pct"] < baseline["max_dd_pct"]:
        return True
    return False


def risk_hyperopt_validate(epochs: int, label: str, variant: str = "futures") -> Path:
    spec = variant_spec(variant)
    ensure_futures_data(spec)
    report_dir = REPORTS_DIR / f"{label}_{utc_timestamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)

    current_payload = json.loads(FUTURES_PARAM_PATH.read_text(encoding="utf-8"))
    baseline_zip = docker_backtest_full(spec)
    baseline_metrics = parse_backtest_zip(baseline_zip)

    result_file, hyperopt_stdout = docker_hyperopt_risk(spec, epochs)
    hyperopt_show, best_json = docker_hyperopt_show(spec, result_file)
    candidate_payload = build_candidate_params(current_payload, best_json)
    candidate_path = report_dir / "candidate_futures_params.json"
    candidate_path.write_text(json.dumps(candidate_payload, indent=2), encoding="utf-8")

    with applied_futures_params(candidate_path):
        candidate_zip = docker_backtest_full(spec)
        candidate_metrics = parse_backtest_zip(candidate_zip)

    accepted = candidate_beats_baseline(candidate_metrics, baseline_metrics)
    if accepted:
        FUTURES_PARAM_PATH.write_text(json.dumps(candidate_payload, indent=2), encoding="utf-8")
        decision = "accepted"
    else:
        decision = "rejected_no_improvement"

    summary = {
        "decision": decision,
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "hyperopt_file": result_file.name,
        "candidate_params": best_json,
    }

    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (report_dir / "hyperopt_stdout.txt").write_text(hyperopt_stdout, encoding="utf-8")
    (report_dir / "hyperopt_show.txt").write_text(hyperopt_show, encoding="utf-8")

    lines = [
        f"# Kivanc {variant_title(variant)} 1D Risk Hyperopt Validation",
        "",
        f"Decision: `{decision}`",
        f"Hyperopt file: `{result_file.name}`",
        "",
        "## Baseline",
        "",
        f"- Profit: `{baseline_metrics['profit_pct']:.2f}%`",
        f"- Final balance: `{baseline_metrics['final_balance']:.2f}`",
        f"- Trades: `{baseline_metrics['trades']}`",
        f"- Profit factor: `{baseline_metrics['profit_factor']:.2f}`",
        f"- MaxDD: `{baseline_metrics['max_dd_pct']:.2f}%`",
        "",
        "## Candidate",
        "",
        f"- Profit: `{candidate_metrics['profit_pct']:.2f}%`",
        f"- Final balance: `{candidate_metrics['final_balance']:.2f}`",
        f"- Trades: `{candidate_metrics['trades']}`",
        f"- Profit factor: `{candidate_metrics['profit_factor']:.2f}`",
        f"- MaxDD: `{candidate_metrics['max_dd_pct']:.2f}%`",
        "",
        "## Candidate Params",
        "",
        "```json",
        json.dumps(best_json, indent=2),
        "```",
    ]
    (report_dir / "risk_hyperopt_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_dir


def buy_hyperopt_validate(epochs: int, label: str, variant: str = "futures") -> Path:
    spec = variant_spec(variant)
    ensure_futures_data(spec)
    report_dir = REPORTS_DIR / f"{label}_{utc_timestamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)

    current_payload = json.loads(FUTURES_PARAM_PATH.read_text(encoding="utf-8"))
    baseline_zip = docker_backtest_full(spec)
    baseline_metrics = parse_backtest_zip(baseline_zip)

    result_file, hyperopt_stdout = docker_hyperopt_buy(spec, epochs)
    hyperopt_show, best_json = docker_hyperopt_show(spec, result_file)
    candidate_payload = build_buy_candidate_params(current_payload, best_json)
    candidate_path = report_dir / "candidate_futures_params.json"
    candidate_path.write_text(json.dumps(candidate_payload, indent=2), encoding="utf-8")

    with applied_futures_params(candidate_path):
        candidate_zip = docker_backtest_full(spec)
        candidate_metrics = parse_backtest_zip(candidate_zip)

    accepted = candidate_beats_baseline(candidate_metrics, baseline_metrics)
    if accepted:
        FUTURES_PARAM_PATH.write_text(json.dumps(candidate_payload, indent=2), encoding="utf-8")
        decision = "accepted"
    else:
        decision = "rejected_no_improvement"

    summary = {
        "decision": decision,
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "hyperopt_file": result_file.name,
        "candidate_params": best_json,
    }

    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (report_dir / "hyperopt_stdout.txt").write_text(hyperopt_stdout, encoding="utf-8")
    (report_dir / "hyperopt_show.txt").write_text(hyperopt_show, encoding="utf-8")

    lines = [
        f"# Kivanc {variant_title(variant)} 1D Buy Hyperopt Validation",
        "",
        f"Decision: `{decision}`",
        f"Hyperopt file: `{result_file.name}`",
        "",
        "## Baseline",
        "",
        f"- Profit: `{baseline_metrics['profit_pct']:.2f}%`",
        f"- Final balance: `{baseline_metrics['final_balance']:.2f}`",
        f"- Trades: `{baseline_metrics['trades']}`",
        f"- Profit factor: `{baseline_metrics['profit_factor']:.2f}`",
        f"- MaxDD: `{baseline_metrics['max_dd_pct']:.2f}%`",
        "",
        "## Candidate",
        "",
        f"- Profit: `{candidate_metrics['profit_pct']:.2f}%`",
        f"- Final balance: `{candidate_metrics['final_balance']:.2f}`",
        f"- Trades: `{candidate_metrics['trades']}`",
        f"- Profit factor: `{candidate_metrics['profit_factor']:.2f}`",
        f"- MaxDD: `{candidate_metrics['max_dd_pct']:.2f}%`",
        "",
        "## Candidate Params",
        "",
        "```json",
        json.dumps(best_json, indent=2),
        "```",
    ]
    (report_dir / "buy_hyperopt_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe futures workflow helper for Kivanc STMA.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    risk_parser = subparsers.add_parser("risk-hyperopt-validate")
    risk_parser.add_argument("--epochs", type=int, default=250)
    risk_parser.add_argument("--label", default="kivanc_futures_1d_risk_hyperopt")
    risk_parser.add_argument("--variant", choices=sorted(VARIANTS.keys()), default="futures")

    buy_parser = subparsers.add_parser("buy-hyperopt-validate")
    buy_parser.add_argument("--epochs", type=int, default=250)
    buy_parser.add_argument("--label", default="kivanc_futures_1d_buy_hyperopt")
    buy_parser.add_argument("--variant", choices=sorted(VARIANTS.keys()), default="futures")

    args = parser.parse_args()
    if args.command == "risk-hyperopt-validate":
        report_dir = risk_hyperopt_validate(args.epochs, args.label, args.variant)
    elif args.command == "buy-hyperopt-validate":
        report_dir = buy_hyperopt_validate(args.epochs, args.label, args.variant)
    print(report_dir)


if __name__ == "__main__":
    main()
