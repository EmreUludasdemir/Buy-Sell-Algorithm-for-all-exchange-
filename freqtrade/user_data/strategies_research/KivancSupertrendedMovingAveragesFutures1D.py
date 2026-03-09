from pathlib import Path
import sys


BASE_STRATEGY_DIR = Path(__file__).resolve().parents[1] / "strategies"
if str(BASE_STRATEGY_DIR) not in sys.path:
    sys.path.append(str(BASE_STRATEGY_DIR))

from KivancSupertrendedMovingAverages1D import KivancSupertrendedMovingAverages1D


class KivancSupertrendedMovingAveragesFutures1D(KivancSupertrendedMovingAverages1D):
    """
    Futures research variant of the production Kivanc STMA strategy.

    This class reuses the daily logic and enables short execution for
    Binance USDT-margined futures backtests. It is not the production bot.
    """

    can_short = True
