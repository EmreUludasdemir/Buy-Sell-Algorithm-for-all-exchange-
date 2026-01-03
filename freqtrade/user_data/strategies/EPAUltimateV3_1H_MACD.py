"""
1H MACD Crossover Strategy

Why MACD vs RSI?
- MACD crosses happen MORE frequently than RSI in bull markets
- Momentum-based (trend following) vs oversold/overbought
- Works better on 1H timeframe

Expected: 50-100 trades (vs 5 with RSI)
"""

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta
from pandas import DataFrame
from functools import reduce


class EPAUltimateV3_1H_MACD(IStrategy):
    """
    1H MACD Crossover Strategy
    
    Entry: MACD bullish crossover + EMA200 trend + Volume
    Exit: MACD bearish crossover
    
    Target: 50-100 trades (vs RSI's 5 trades)
    """
    
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    
    # Hyperopt spaces
    buy_macd_fast = IntParameter(8, 16, default=12, space='buy', optimize=True)
    buy_macd_slow = IntParameter(20, 30, default=26, space='buy', optimize=True)
    buy_macd_signal = IntParameter(7, 12, default=9, space='buy', optimize=True)
    
    sell_macd_signal = IntParameter(7, 12, default=9, space='sell', optimize=True)
    
    # Risk management
    minimal_roi = {
        "0": 0.03,    # 3%
        "240": 0.02,  # 2% after 4h
        "480": 0.01   # 1% after 8h
    }
    
    stoploss = -0.03
    trailing_stop = False
    
    max_open_trades = 4
    stake_amount = 100
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # Startup candles
    startup_candle_count = 200
    
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {"method": "MaxDrawdown", "lookback_period_candles": 48, 
             "trade_limit": 10, "stop_duration_candles": 12, 
             "max_allowed_drawdown": 0.12}
        ]
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Indicators:
        - MACD (12, 26, 9) - Dynamic crossover signal
        - EMA 50, 200 - Trend filter  
        - Volume MA - Confirmation
        """
        
        # MACD with hyperopt-optimizable parameters
        macd = ta.MACD(dataframe, 
                       fastperiod=self.buy_macd_fast.value,
                       slowperiod=self.buy_macd_slow.value,
                       signalperiod=self.buy_macd_signal.value)
        
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Trend filters (EMA)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Volume
        dataframe['volume_ma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        
        # RSI (for reference)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        MACD Bullish Crossover Entry (NO FILTERS)
        
        Logic: MACD crosses above signal only
        """
        conditions = []
        
        # MACD bullish crossover (DYNAMIC!)
        macd_crossover = (
            (dataframe['macd'] > dataframe['macdsignal']) &
            (dataframe['macd'].shift(1) <= dataframe['macdsignal'].shift(1))
        )
        conditions.append(macd_crossover)
        
        # Volume not zero
        conditions.append(dataframe['volume'] > 0)
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        MACD Bearish Crossover Exit
        """
        conditions = []
        
        # MACD bearish crossover
        macd_bearish = (
            (dataframe['macd'] < dataframe['macdsignal']) &
            (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1))
        )
        conditions.append(macd_bearish)
        
        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), 'exit_long'] = 1
        
        return dataframe
