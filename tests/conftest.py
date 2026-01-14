"""
Pytest configuration and fixtures for EPA Trading Bot tests.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest


# Add project paths to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
STRATEGIES_PATH = PROJECT_ROOT / "freqtrade" / "user_data" / "strategies"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(STRATEGIES_PATH))


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """
    Generate sample OHLCV data for testing.
    Returns a DataFrame with 100 candles of realistic BTC-like data.
    """
    import numpy as np

    np.random.seed(42)
    n = 100

    # Generate random walk for close prices
    returns = np.random.randn(n) * 0.02  # 2% daily volatility
    close = 50000 * np.exp(np.cumsum(returns))

    # Generate OHLC from close
    high = close * (1 + np.abs(np.random.randn(n) * 0.01))
    low = close * (1 - np.abs(np.random.randn(n) * 0.01))
    open_price = low + (high - low) * np.random.rand(n)

    # Generate volume
    volume = np.random.uniform(100, 1000, n) * 1e6

    # Create DataFrame
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })

    # Add date index
    df['date'] = pd.date_range(start='2024-01-01', periods=n, freq='4h')
    df = df.set_index('date')

    return df


@pytest.fixture
def empty_ohlcv_data() -> pd.DataFrame:
    """
    Generate empty OHLCV DataFrame for edge case testing.
    """
    return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])


@pytest.fixture
def short_ohlcv_data() -> pd.DataFrame:
    """
    Generate short OHLCV data (5 candles) for edge case testing.
    """
    return pd.DataFrame({
        'open': [50000, 50100, 50050, 50200, 50150],
        'high': [50200, 50300, 50150, 50400, 50250],
        'low': [49900, 50000, 49950, 50100, 50050],
        'close': [50100, 50050, 50200, 50150, 50200],
        'volume': [1e9, 1.1e9, 0.9e9, 1.2e9, 1e9],
    })


@pytest.fixture
def trending_up_data() -> pd.DataFrame:
    """
    Generate strongly trending up OHLCV data for testing trend indicators.
    """
    import numpy as np

    n = 100
    trend = np.linspace(50000, 60000, n)  # 20% up
    noise = np.random.randn(n) * 200
    close = trend + noise

    df = pd.DataFrame({
        'open': close - np.abs(np.random.randn(n) * 100),
        'high': close + np.abs(np.random.randn(n) * 200),
        'low': close - np.abs(np.random.randn(n) * 200),
        'close': close,
        'volume': np.random.uniform(100, 1000, n) * 1e6,
    })

    return df


@pytest.fixture
def trending_down_data() -> pd.DataFrame:
    """
    Generate strongly trending down OHLCV data for testing trend indicators.
    """
    import numpy as np

    n = 100
    trend = np.linspace(60000, 50000, n)  # 20% down
    noise = np.random.randn(n) * 200
    close = trend + noise

    df = pd.DataFrame({
        'open': close + np.abs(np.random.randn(n) * 100),
        'high': close + np.abs(np.random.randn(n) * 200),
        'low': close - np.abs(np.random.randn(n) * 200),
        'close': close,
        'volume': np.random.uniform(100, 1000, n) * 1e6,
    })

    return df
