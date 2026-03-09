from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRATEGY_FILE = ROOT / "freqtrade" / "user_data" / "strategies" / "KivancSupertrendedMovingAverages1D.py"
PARAM_FILE = ROOT / "freqtrade" / "user_data" / "strategies" / "KivancSupertrendedMovingAverages1D.json"
PROFILE_DIR = ROOT / "freqtrade" / "user_data" / "profiles"
PRODUCTION_PROFILE = PROFILE_DIR / "production_1d.json"
RISK_PROFILE = PROFILE_DIR / "risk_validation_4h.json"
SCRIPT_DIR = ROOT / "freqtrade" / "scripts"
FUTURES_STRATEGY_FILE = (
    ROOT / "freqtrade" / "user_data" / "strategies_research" / "KivancSupertrendedMovingAveragesFutures1D.py"
)
FUTURES_PARAM_FILE = (
    ROOT / "freqtrade" / "user_data" / "strategies_research" / "KivancSupertrendedMovingAveragesFutures1D.json"
)
FUTURES_CONFIG = ROOT / "freqtrade" / "user_data" / "config_futures_research.json"


def _load_tree() -> ast.Module:
    return ast.parse(STRATEGY_FILE.read_text(encoding="utf-8"))


def test_strategy_files_exist() -> None:
    assert STRATEGY_FILE.exists()
    assert PARAM_FILE.exists()
    assert PRODUCTION_PROFILE.exists()
    assert RISK_PROFILE.exists()
    assert FUTURES_STRATEGY_FILE.exists()
    assert FUTURES_PARAM_FILE.exists()
    assert FUTURES_CONFIG.exists()


def test_strategy_declares_expected_class_and_timeframe() -> None:
    tree = _load_tree()
    class_node = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "KivancSupertrendedMovingAverages1D"
    )
    timeframe_assign = next(
        node
        for node in class_node.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "timeframe" for target in node.targets)
    )
    assert isinstance(timeframe_assign.value, ast.Constant)
    assert timeframe_assign.value.value == "1d"


def test_strategy_directory_contains_only_kivanc_strategy() -> None:
    strategy_dir = STRATEGY_FILE.parent
    files = sorted(path.name for path in strategy_dir.iterdir() if path.is_file())
    assert files == [
        "KivancSupertrendedMovingAverages1D.json",
        "KivancSupertrendedMovingAverages1D.py",
    ]


def test_exported_hyperopt_params_match_expected_keys() -> None:
    data = json.loads(PARAM_FILE.read_text(encoding="utf-8"))
    keys = sorted(data["params"]["buy"].keys())
    assert keys == [
        "adx_threshold",
        "atr_multiplier",
        "atr_period",
        "ma_length",
        "ma_type",
        "regime_ema_length",
        "regime_slope_lookback",
        "regime_slope_min",
        "t3_volume_factor",
        "use_adx_filter",
        "use_builtin_atr",
        "use_regime_filter",
    ]


def test_profiles_have_required_keys_and_are_distinct() -> None:
    strategy_params = json.loads(PARAM_FILE.read_text(encoding="utf-8"))
    production = json.loads(PRODUCTION_PROFILE.read_text(encoding="utf-8"))
    risk = json.loads(RISK_PROFILE.read_text(encoding="utf-8"))

    for payload in [production, risk]:
        assert payload["strategy_name"] == "KivancSupertrendedMovingAverages1D"
        assert sorted(payload["params"].keys()) == ["buy", "max_open_trades", "roi", "stoploss", "trailing"]

    assert strategy_params == production
    assert production != risk


def test_4h_profile_keeps_same_buy_layer_but_changes_risk_layer() -> None:
    production = json.loads(PRODUCTION_PROFILE.read_text(encoding="utf-8"))
    risk = json.loads(RISK_PROFILE.read_text(encoding="utf-8"))

    assert production["params"]["buy"] == risk["params"]["buy"]
    assert production["params"]["roi"] != risk["params"]["roi"]
    assert production["params"]["stoploss"] != risk["params"]["stoploss"]
    assert production["params"]["trailing"] != risk["params"]["trailing"]


def test_strategy_remains_daily_and_spot_safe_while_exposing_research_hooks() -> None:
    tree = _load_tree()
    class_node = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "KivancSupertrendedMovingAverages1D"
    )
    assignments = {
        target.id: node.value
        for node in class_node.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    assert isinstance(assignments["can_short"], ast.Constant)
    assert assignments["can_short"].value is False

    source = STRATEGY_FILE.read_text(encoding="utf-8")
    assert "research_short_signal" in source
    assert "use_regime_filter" in source


def test_profile_scripts_exist() -> None:
    expected = {
        "backtest_kivanc_1d.ps1",
        "backtest_kivanc_4h_risk.ps1",
        "backtest_kivanc_futures_1d.ps1",
        "backtest_kivanc_futures_regimes.ps1",
        "compare_kivanc_profiles.ps1",
        "download_kivanc_1d.ps1",
        "download_kivanc_4h.ps1",
        "download_kivanc_futures_1d.ps1",
        "hyperopt_kivanc_1d.ps1",
        "hyperopt_kivanc_4h_risk.ps1",
        "kivanc_profile_runner.py",
    }
    assert expected.issubset({path.name for path in SCRIPT_DIR.iterdir() if path.is_file()})


def test_futures_research_strategy_enables_shorting() -> None:
    tree = ast.parse(FUTURES_STRATEGY_FILE.read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "KivancSupertrendedMovingAveragesFutures1D"
    )
    can_short_assign = next(
        node
        for node in class_node.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "can_short" for target in node.targets)
    )
    assert isinstance(can_short_assign.value, ast.Constant)
    assert can_short_assign.value.value is True


def test_futures_config_uses_binance_futures_pairs() -> None:
    data = json.loads(FUTURES_CONFIG.read_text(encoding="utf-8"))
    assert data["trading_mode"] == "futures"
    assert data["margin_mode"] == "isolated"
    assert all(pair.endswith(":USDT") for pair in data["exchange"]["pair_whitelist"])
