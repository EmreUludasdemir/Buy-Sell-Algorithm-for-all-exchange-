"""
Download and backtest NASDAQ/S&P 500 indices with scanner strategy engine.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scanner.providers import YahooProvider
from src.scanner.strategy import BacktestConfig, StrategyParams, run_backtest
from src.scanner.walkforward import WalkForwardConfig, walk_forward_oos


INDEX_MAP = {
    "NASDAQ": "^IXIC",
    "SP500": "^GSPC",
}


def buy_hold_return(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    start = float(df["Close"].iloc[0])
    end = float(df["Close"].iloc[-1])
    if start <= 0:
        return 0.0
    return (end / start) - 1.0


def main() -> int:
    provider = YahooProvider()
    bt_cfg = BacktestConfig()
    wf_cfg = WalkForwardConfig()
    params = StrategyParams()

    reports_dir = Path("reports")
    data_dir = reports_dir / "us_indices_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for name, ticker in INDEX_MAP.items():
        df = provider.fetch(ticker, period="10y")
        if df.empty:
            results.append(
                {
                    "index": name,
                    "ticker": ticker,
                    "status": "no_data",
                }
            )
            continue

        csv_path = data_dir / f"{name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_path, index=True)

        bt = run_backtest(df, bt_cfg, params)
        wf = walk_forward_oos(df, bt_cfg, wf_cfg)
        bh = buy_hold_return(df)

        results.append(
            {
                "index": name,
                "ticker": ticker,
                "status": "ok",
                "rows": int(len(df)),
                "start": str(df.index.min().date()),
                "end": str(df.index.max().date()),
                "buy_hold_return": float(bh),
                "strategy_backtest": bt,
                "walk_forward_oos": {
                    "oos_return": float(wf.get("oos_return", 0.0)),
                    "oos_max_drawdown": float(wf.get("oos_max_drawdown", 0.0)),
                    "oos_trades": float(wf.get("oos_trades", 0.0)),
                    "oos_winrate": float(wf.get("oos_winrate", 0.0)),
                    "windows": float(wf.get("windows", 0.0)),
                },
                "data_csv": str(csv_path),
            }
        )

    json_path = reports_dir / "us_indices_backtest.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    md_lines = [
        "# US Indices Backtest",
        "",
        f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- Strategy params: `{asdict(params)}`",
        f"- Backtest config: `{asdict(bt_cfg)}`",
        f"- Walk-forward config: `{asdict(wf_cfg)}`",
        "",
        "| Index | Ticker | Data Range | Rows | Buy&Hold % | Strategy % | OOS % | OOS MaxDD % | OOS Trades | Windows |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for r in results:
        if r["status"] != "ok":
            md_lines.append(f"| {r['index']} | {r['ticker']} | - | 0 | - | - | - | - | - | - |")
            continue
        bt = r["strategy_backtest"]
        wf = r["walk_forward_oos"]
        md_lines.append(
            "| {index} | {ticker} | {start} -> {end} | {rows} | {bh:.2f} | {btret:.2f} | {oos:.2f} | {dd:.2f} | {trades:.0f} | {windows:.0f} |".format(
                index=r["index"],
                ticker=r["ticker"],
                start=r["start"],
                end=r["end"],
                rows=r["rows"],
                bh=r["buy_hold_return"] * 100.0,
                btret=bt["total_return"] * 100.0,
                oos=wf["oos_return"] * 100.0,
                dd=wf["oos_max_drawdown"] * 100.0,
                trades=wf["oos_trades"],
                windows=wf["windows"],
            )
        )

    md_path = reports_dir / "us_indices_backtest.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    for r in results:
        if r["status"] != "ok":
            print(f"{r['index']} ({r['ticker']}): no data")
            continue
        bt = r["strategy_backtest"]
        wf = r["walk_forward_oos"]
        print(
            f"{r['index']} ({r['ticker']}) | "
            f"Buy&Hold={r['buy_hold_return']*100:.2f}% | "
            f"Strategy={bt['total_return']*100:.2f}% | "
            f"OOS={wf['oos_return']*100:.2f}% | "
            f"OOS DD={wf['oos_max_drawdown']*100:.2f}%"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
