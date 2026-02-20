from datetime import datetime

from EPASimpleTrend import EPASimpleTrend


class EPASimpleTrendTimeStop(EPASimpleTrend):
    """
    A/B variant: baseline EPASimpleTrend + only time-stop exit.
    """

    time_stop_hours = 96
    time_stop_min_profit = 0.008
    hard_time_stop_hours = 144

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

