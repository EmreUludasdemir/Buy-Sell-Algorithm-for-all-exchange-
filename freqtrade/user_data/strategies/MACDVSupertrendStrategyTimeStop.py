from datetime import datetime

from MACDVSupertrendStrategy import MACDVSupertrendStrategy


class MACDVSupertrendStrategyTimeStop(MACDVSupertrendStrategy):
    """
    A/B variant: baseline MACDVSupertrendStrategy + only time-stop exit.
    """

    time_stop_hours = 120
    time_stop_min_profit = 0.010
    hard_time_stop_hours = 168

    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        open_hours = (current_time - trade.open_date_utc).total_seconds() / 3600.0

        if open_hours >= self.hard_time_stop_hours and current_profit < 0:
            return "time_stop_hard"

        if open_hours >= self.time_stop_hours and current_profit < self.time_stop_min_profit:
            return "time_stop_soft"

        return None

