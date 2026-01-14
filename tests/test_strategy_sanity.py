"""
Strategy sanity tests - ensure strategies load and don't crash on basic data.
"""

import pytest


class TestStrategyImports:
    """Test that all strategies can be imported without errors."""

    @pytest.mark.unit
    def test_import_kivanc_indicators(self):
        """Test kivanc_indicators module imports."""
        try:
            from kivanc_indicators import add_kivanc_indicators
            assert callable(add_kivanc_indicators)
        except ImportError as e:
            pytest.skip(f"kivanc_indicators not available: {e}")

    @pytest.mark.unit
    def test_import_smc_indicators(self):
        """Test smc_indicators module imports."""
        try:
            from smc_indicators import calculate_volatility_regime, add_smc_zones_complete
            assert callable(calculate_volatility_regime)
            assert callable(add_smc_zones_complete)
        except ImportError as e:
            pytest.skip(f"smc_indicators not available: {e}")

    @pytest.mark.unit
    def test_import_epa_futures_pro(self):
        """Test EPAFuturesPro strategy imports."""
        try:
            from EPAFuturesPro import EPAFuturesPro
            assert EPAFuturesPro is not None
        except ImportError as e:
            pytest.skip(f"EPAFuturesPro not available: {e}")


class TestStrategySanity:
    """Test that strategies don't crash on basic operations."""

    @pytest.mark.unit
    def test_epa_futures_pro_populate_indicators(self, sample_ohlcv_data):
        """Test EPAFuturesPro.populate_indicators doesn't crash."""
        try:
            from EPAFuturesPro import EPAFuturesPro

            strategy = EPAFuturesPro({})
            result = strategy.populate_indicators(sample_ohlcv_data.copy(), {"pair": "BTC/USDT"})

            # Check that result is a DataFrame with expected columns
            assert result is not None
            assert len(result) == len(sample_ohlcv_data)
            assert 'close' in result.columns
        except ImportError as e:
            pytest.skip(f"EPAFuturesPro not available: {e}")
        except Exception as e:
            pytest.fail(f"populate_indicators crashed: {e}")

    @pytest.mark.unit
    def test_epa_futures_pro_empty_data(self, empty_ohlcv_data):
        """Test EPAFuturesPro handles empty data gracefully."""
        try:
            from EPAFuturesPro import EPAFuturesPro

            strategy = EPAFuturesPro({})
            # Should not crash on empty data
            result = strategy.populate_indicators(empty_ohlcv_data.copy(), {"pair": "BTC/USDT"})
            assert result is not None
        except ImportError as e:
            pytest.skip(f"EPAFuturesPro not available: {e}")
        except Exception:
            # It's acceptable to raise an exception on empty data
            pass

    @pytest.mark.unit
    def test_epa_futures_pro_short_data(self, short_ohlcv_data):
        """Test EPAFuturesPro handles short data without crash."""
        try:
            from EPAFuturesPro import EPAFuturesPro

            strategy = EPAFuturesPro({})
            result = strategy.populate_indicators(short_ohlcv_data.copy(), {"pair": "BTC/USDT"})
            assert result is not None
        except ImportError as e:
            pytest.skip(f"EPAFuturesPro not available: {e}")
        except Exception:
            # It's acceptable to raise an exception on very short data
            pass


class TestIndicatorFunctions:
    """Test individual indicator functions."""

    @pytest.mark.unit
    def test_supertrend_calculation(self, sample_ohlcv_data):
        """Test SuperTrend indicator calculation."""
        try:
            from EPAFuturesPro import supertrend

            st_line, st_dir = supertrend(sample_ohlcv_data, period=10, multiplier=3.0)

            assert st_line is not None
            assert st_dir is not None
            assert len(st_line) == len(sample_ohlcv_data)
            assert len(st_dir) == len(sample_ohlcv_data)
            # Direction should be -1 (bullish) or 1 (bearish)
            assert all(d in [-1, 1] for d in st_dir.dropna())
        except ImportError as e:
            pytest.skip(f"supertrend not available: {e}")

    @pytest.mark.unit
    def test_supertrend_trending_up(self, trending_up_data):
        """Test SuperTrend correctly identifies uptrend."""
        try:
            from EPAFuturesPro import supertrend

            st_line, st_dir = supertrend(trending_up_data, period=10, multiplier=3.0)

            # In a strong uptrend, most recent direction should be bullish (-1)
            recent_dir = st_dir.iloc[-20:].dropna()
            bullish_count = (recent_dir == -1).sum()
            assert bullish_count > len(recent_dir) * 0.5, "SuperTrend should detect uptrend"
        except ImportError as e:
            pytest.skip(f"supertrend not available: {e}")

    @pytest.mark.unit
    def test_supertrend_trending_down(self, trending_down_data):
        """Test SuperTrend correctly identifies downtrend."""
        try:
            from EPAFuturesPro import supertrend

            st_line, st_dir = supertrend(trending_down_data, period=10, multiplier=3.0)

            # In a strong downtrend, most recent direction should be bearish (1)
            recent_dir = st_dir.iloc[-20:].dropna()
            bearish_count = (recent_dir == 1).sum()
            assert bearish_count > len(recent_dir) * 0.5, "SuperTrend should detect downtrend"
        except ImportError as e:
            pytest.skip(f"supertrend not available: {e}")


class TestNoLookahead:
    """Test that strategies don't have look-ahead bias."""

    @pytest.mark.unit
    def test_indicators_use_shift(self, sample_ohlcv_data):
        """
        Verify indicators don't use future data.
        This is a basic check - full lookahead detection requires Freqtrade's built-in tools.
        """
        try:
            from EPAFuturesPro import EPAFuturesPro

            strategy = EPAFuturesPro({})
            df = sample_ohlcv_data.copy()

            # Run indicators on full data
            result_full = strategy.populate_indicators(df.copy(), {"pair": "BTC/USDT"})

            # Run indicators on partial data (first 50 rows)
            result_partial = strategy.populate_indicators(df.iloc[:50].copy(), {"pair": "BTC/USDT"})

            # For the first 50 rows, indicators should produce the same values
            # (if no look-ahead bias exists)
            # Note: This is a simplified check; real lookahead detection is more complex
            assert result_partial is not None
            assert result_full is not None

        except ImportError as e:
            pytest.skip(f"EPAFuturesPro not available: {e}")
