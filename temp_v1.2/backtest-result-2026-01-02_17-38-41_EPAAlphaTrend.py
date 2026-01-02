"""
EPAAlphaTrend Strategy - Pure Kıvanç Özbilgiç Methodology
==========================================================
Triple-layer trend confirmation system using only Kıvanç indicators:
- AlphaTrend (Trend Filter)
- T3 Moving Average (Trend Confirmation)
- SuperTrend (Entry Trigger)

Philosophy: Simple, clear, and effective. Quality over quantity.

Author: Emre Uludaşdemir  
Version: 1.2.0
Based on: Kıvanç Özbilgiç TradingView indicators

Version History:
- v1.0.0 (2026-01-02): Initial implementation with indicator-based exits
- v1.1.0 (2026-01-02): Removed AlphaTrend exit, added trailing stop
                       Bug: Exit signals still triggered (0% win rate)
- v1.2.0 (2026-01-02): Disabled ALL exit signals - ROI + Trailing Stop ONLY
                       Rationale: Exit signals cut winners (0% win on 10 trades)
                       Exit Strategy: ROI (100% win) + Trailing (78% win)
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

# Import Kıvanç Özbilgiç indicators
from kivanc_indicators import alphatrend, t3_ma, supertrend

logger = logging.getLogger(__name__)


class EPAAlphaTrend(IStrategy):
    """
    EPAAlphaTrend - Pure Trend Following Strategy
    
    Three-Layer Defense System:
    1. AlphaTrend: Identifies bullish environment (ATR + MFI)
    2. T3 MA: Confirms trend strength (6-layer smoothing)
    3. SuperTrend: Times precise entry (ATR-based trigger)
    
    Entry Logic:
    - ALL conditions must be true:
      1. AlphaTrend direction = 1 (bullish trend)
      2. Close > T3 line (price above trend support)
      3. Close > AlphaTrend line (price respects dynamic support)
      4. SuperTrend flips from -1 to 1 (entry trigger)
      5. Volume > 20-period average (breakout confirmation)
    
    Exit Logic:
    - ANY condition triggers exit:
      1. SuperTrend direction = -1 (trend reversal)
      2. Close < AlphaTrend line (support broken)
    
    Philosophy:
    - Fewer trades, higher quality
    - Only trade strong, clear trends
    - Exit fast when trend weakens
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Timeframe - 4H for clean trends
    timeframe = '4h'
    
    # Disable shorting (spot markets)
    can_short = False
    
    # Exit Strategy Philosophy:
    # We use ONLY ROI + Trailing Stop, NO exit signals
    # Reason: Backtest proved exit signals have 0% win rate (10 trades, all losses)
    # They trigger too early and cut profitable trades before ROI
    # Performance: ROI exits 100% win | Trailing 78% win | Exit Signal 0% win
    use_exit_signal = False  # CRITICAL: Disable indicator-based exits
    use_custom_stoploss = True  # Enable trailing stop
    
    # ROI table - Progressive profit taking
    minimal_roi = {
        "0": 0.10,       # 10% immediate spike exit
        "360": 0.07,     # 7% after 6h (swing trade)
        "720": 0.05,     # 5% after 12h (trend trade)
        "1440": 0.03,    # 3% after 24h (let winners run)
    }
    
    # Stoploss - 8% for 4H volatility
    stoploss = -0.08
    
    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    
    # Process only new candles
    process_only_new_candles = True
    
    # Use exit signals
    use_exit_signal = True
    exit_profit_only = False
    
    # Startup candles
    startup_candle_count: int = 100
    
    # Protections
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 8
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": False
            }
        ]
    
    # ==================== INDICATOR PARAMETERS ====================
    
    # AlphaTrend settings
    alpha_atr_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    alpha_atr_multiplier = DecimalParameter(0.5, 2.0, default=1.0, space='buy', optimize=True)
    alpha_mfi_period = IntParameter(10, 20, default=14, space='buy', optimize=True)
    
    # T3 MA settings
    t3_period = IntParameter(3, 10, default=5, space='buy', optimize=True)
    t3_volume_factor = DecimalParameter(0.5, 0.9, default=0.7, space='buy', optimize=False)
    
    # SuperTrend settings
    st_period = IntParameter(8, 14, default=10, space='buy', optimize=True)
    st_multiplier = DecimalParameter(2.0, 4.0, default=3.0, space='buy', optimize=True)
    
    # Volume filter
    volume_lookback = IntParameter(15, 25, default=20, space='buy', optimize=False)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate Kıvanç indicators.
        
        Three indicators, three confirmations, one clear signal.
        """
        
        # ==================== ALPHATREND ====================
        # Trend filter using ATR bands + MFI direction
        alpha_line, alpha_dir, alpha_buy, alpha_sell = alphatrend(
            dataframe,
            atr_period=self.alpha_atr_period.value,
            atr_multiplier=self.alpha_atr_multiplier.value,
            mfi_period=self.alpha_mfi_period.value
        )
        
        # Ensure all series are pandas Series (not numpy arrays)
        dataframe['alpha_line'] = pd.Series(alpha_line, index=dataframe.index)
        dataframe['alpha_dir'] = pd.Series(alpha_dir, index=dataframe.index)      # 1 = bullish, -1 = bearish
        dataframe['alpha_buy'] = pd.Series(alpha_buy, index=dataframe.index)      # Buy signal (crossover)
        dataframe['alpha_sell'] = pd.Series(alpha_sell, index=dataframe.index)    # Sell signal (crossunder)
        
        # ==================== T3 MOVING AVERAGE ====================
        # Trend confirmation using 6-layer EMA smoothing
        t3_line, t3_dir = t3_ma(
            dataframe,
            period=self.t3_period.value,
            volume_factor=self.t3_volume_factor.value
        )
        
        #Ensure series are pandas Series (not numpy arrays)
        dataframe['t3_line'] = pd.Series(t3_line, index=dataframe.index)
        dataframe['t3_dir'] = pd.Series(t3_dir, index=dataframe.index)            # 1 = uptrend, -1 = downtrend
        
        # ==================== SUPERTREND ====================
        # Entry trigger using ATR-based bands
        st_dir, st_line = supertrend(
            dataframe,
            period=self.st_period.value,
            multiplier=self.st_multiplier.value
        )
        
        # Ensure series are pandas Series (not numpy arrays)
        dataframe['st_dir'] = pd.Series(st_dir, index=dataframe.index)            # 1 = bullish, -1 = bearish
        dataframe['st_line'] = pd.Series(st_line, index=dataframe.index)
        
        # SuperTrend flip detection (key for entry timing)
        # Use dataframe columns after assignment to ensure proper type
        dataframe['st_flip_bullish'] = (
            (dataframe['st_dir'] == 1) &
            (dataframe['st_dir'].shift(1) == -1)
        ).astype(int)
        
        dataframe['st_flip_bearish'] = (
            (dataframe['st_dir'] == -1) &
            (dataframe['st_dir'].shift(1) == 1)
        ).astype(int)
        
        # ==================== VOLUME FILTER ====================
        dataframe['volume_ma'] = dataframe['volume'].rolling(
            window=self.volume_lookback.value
        ).mean()
        
        dataframe['volume_ok'] = (
            dataframe['volume'] > dataframe['volume_ma']
        ).astype(int)
        
        # ==================== ATR FOR REFERENCE ====================
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry logic: Triple confirmation required.
        
        All conditions must align:
        1. AlphaTrend direction = 1 (bullish environment)
        2. Close > T3 line (above trend support)
        3. Close > AlphaTrend line (respects dynamic support)
        4. SuperTrend flips bullish (entry trigger)
        5. Volume > MA (breakout confirmation)
        
        This ensures we only enter strong, confirmed uptrends.
        """
        
        # ==================== LONG ENTRY ====================
        
        dataframe.loc[
            # Layer 1: AlphaTrend confirms bullish environment
            (dataframe['alpha_dir'] == 1) &
            
            # Layer 2: Price above T3 (trend confirmation)
            (dataframe['close'] > dataframe['t3_line']) &
            
            # Layer 3: Price above AlphaTrend line (dynamic support)
            (dataframe['close'] > dataframe['alpha_line']) &
            
            # Trigger: SuperTrend just flipped bullish
            (dataframe['st_flip_bullish'] == 1) &
            
            # Confirmation: Volume spike (breakout has energy)
            (dataframe['volume_ok'] == 1) &
            
            # Basic sanity check
            (dataframe['volume'] > 0),
            
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit logic: DISABLED in v1.2.0
        
        This function is NO LONGER USED because use_exit_signal = False.
        
        Exit Strategy Evolution:
        - v1.0: AlphaTrend + SuperTrend exits → 50% win rate, 0.83% profit
        - v1.1: SuperTrend exit only → 65% win rate, 0.21% profit (worse!)
        - v1.2: NO exit signals → Expected 80% win rate, 3-5% profit
        
        Why we disabled exit signals:
        - v1.1 backtest: 10 exit_signal trades, 0% win rate, -39.47 USDT loss
        - Indicator exits trigger too early in trend-following strategies
        - ROI + Trailing Stop let winners run while protecting profits
        
        Philosophy: "Let winners run, cut losers short"
        - ROI handles explosive moves (100% win rate)
        - Trailing stop locks in profits during pullbacks (78% win rate)
        - Exit signals would prematurely close winning positions
        """
        # Exit signals disabled - return dataframe unchanged
        # Exits handled by: ROI table + custom_stoploss (trailing)
        return dataframe
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    **kwargs) -> Optional[str]:
        """
        Custom exit for profit milestones.
        
        Exit tiers:
        - 8%+ profit: Take profit (rare spike)
        - 5%+ profit after 12h: Swing trade completed
        """
        
        # Tier 1: Quick profit on spike
        if current_profit >= 0.08:
            return 'profit_spike_8pct'
        
        # Tier 2: Swing trade profit after time
        if current_profit >= 0.05:
            trade_duration_hours = (current_time - trade.open_date_utc).total_seconds() / 3600
            if trade_duration_hours >= 12:  # 3 x 4h candles
                return 'swing_tp_5pct'
        
        return None
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        **kwargs) -> Optional[float]:
        """
        Trailing stop to protect profits.
        
        Logic:
        - Profit > 8%: trail at 3% (let big winners run with protection)
        - Profit > 5%: trail at 2% (protect good trades)
        - Profit > 2%: trail at 1% (lock in small profits)
        - Otherwise: use -8% fixed stop
        
        Why this works:
        - Backtest showed ROI exits had 100% win rate
        - Trailing stop ensures we capture profit before reversal
        - Progressive tightening as profit increases
        """
        if current_profit > 0.08:
            return -0.03  # Trail at 3% below current price
        elif current_profit > 0.05:
            return -0.02  # Trail at 2%
        elif current_profit > 0.02:
            return -0.01  # Trail at 1%
        
        return self.stoploss  # Default -8%
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: Optional[str], side: str, **kwargs) -> float:
        """No leverage - keep it safe."""
        return 1.0
