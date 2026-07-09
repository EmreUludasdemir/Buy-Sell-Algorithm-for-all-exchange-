from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATEGY_FILE = (
    ROOT / "freqtrade" / "user_data" / "strategies_momentum" / "MomentumVolumeCompound4H.py"
)
LIVE_CONFIG = ROOT / "freqtrade" / "user_data" / "config_momentum_4h.json"
BACKTEST_CONFIG = ROOT / "freqtrade" / "user_data" / "config_momentum_4h_backtest.json"
SCRIPT_DIR = ROOT / "freqtrade" / "scripts"


def _load_class_node() -> ast.ClassDef:
    tree = ast.parse(STRATEGY_FILE.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MomentumVolumeCompound4H"
    )


def _class_assignments(class_node: ast.ClassDef) -> dict:
    return {
        target.id: node.value
        for node in class_node.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def test_momentum_files_exist() -> None:
    assert STRATEGY_FILE.exists()
    assert LIVE_CONFIG.exists()
    assert BACKTEST_CONFIG.exists()


def test_strategy_uses_4h_execution_and_1d_regime() -> None:
    assignments = _class_assignments(_load_class_node())

    assert isinstance(assignments["timeframe"], ast.Constant)
    assert assignments["timeframe"].value == "4h"
    assert isinstance(assignments["informative_timeframe"], ast.Constant)
    assert assignments["informative_timeframe"].value == "1d"

    source = STRATEGY_FILE.read_text(encoding="utf-8")
    assert "merge_informative_pair" in source
    assert "informative_pairs" in source
    assert "bull_regime" in source


def test_strategy_is_spot_long_only_with_short_term_risk_layer() -> None:
    assignments = _class_assignments(_load_class_node())

    assert isinstance(assignments["can_short"], ast.Constant)
    assert assignments["can_short"].value is False
    assert isinstance(assignments["trailing_stop"], ast.Constant)
    assert assignments["trailing_stop"].value is True

    source = STRATEGY_FILE.read_text(encoding="utf-8")
    assert "minimal_roi" in source
    assert "stoploss" in source


def test_strategy_compounds_profit_into_next_position() -> None:
    source = STRATEGY_FILE.read_text(encoding="utf-8")
    assert "custom_stake_amount" in source
    assert "compound_stake_fraction" in source
    assert "win_streak_boost" in source
    assert "get_total_stake_amount" in source


def test_strategy_filters_on_volume_and_momentum() -> None:
    source = STRATEGY_FILE.read_text(encoding="utf-8")
    assert "volume_surge_mult" in source
    assert "volume_ratio" in source
    assert "adx" in source
    assert "breakout" in source


def test_live_config_targets_high_volume_pairs_dynamically() -> None:
    data = json.loads(LIVE_CONFIG.read_text(encoding="utf-8"))
    assert data["strategy"] == "MomentumVolumeCompound4H"
    assert data["strategy_path"] == "user_data/strategies_momentum"
    assert data["timeframe"] == "4h"
    assert data["dry_run"] is True

    methods = [entry["method"] for entry in data["pairlists"]]
    assert methods[0] == "VolumePairList"
    volume_pairlist = data["pairlists"][0]
    assert volume_pairlist["sort_key"] == "quoteVolume"
    assert volume_pairlist["number_assets"] >= 5


def test_backtest_config_uses_static_high_volume_majors() -> None:
    data = json.loads(BACKTEST_CONFIG.read_text(encoding="utf-8"))
    assert data["strategy"] == "MomentumVolumeCompound4H"
    assert data["pairlists"] == [{"method": "StaticPairList"}]
    whitelist = data["exchange"]["pair_whitelist"]
    assert "BTC/USDT" in whitelist
    assert "ETH/USDT" in whitelist
    assert len(whitelist) >= 5


def test_momentum_scripts_exist_and_cover_both_timeframes() -> None:
    expected = {
        "download_momentum_4h.ps1",
        "backtest_momentum_4h.ps1",
        "hyperopt_momentum_4h.ps1",
    }
    assert expected.issubset({path.name for path in SCRIPT_DIR.iterdir() if path.is_file()})

    download_source = (SCRIPT_DIR / "download_momentum_4h.ps1").read_text(encoding="utf-8")
    assert "--timeframe 4h 1d" in download_source

    backtest_source = (SCRIPT_DIR / "backtest_momentum_4h.ps1").read_text(encoding="utf-8")
    assert "MomentumVolumeCompound4H" in backtest_source
    assert "user_data/strategies_momentum" in backtest_source
