"""
SMC Strategy - Smart Money Concepts Trading Strategy
=====================================================
Freqtrade strategy based on ICT/Smart Money Concepts methodology.

Entry logic:
- Market structure confirmation (BOS/CHOCH)
- Order Block entry zones
- Fair Value Gap confirmation
- Liquidity sweep triggers

Exit logic:
- Opposite FVG targets
- Trailing on structure break
- ATR-based stop loss
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

# Import our SMC indicators
from smc_indicators import (
    calculate_swing_highs_lows,
    calculate_bos_choch,
    calculate_order_blocks,
    calculate_fvg,
    calculate_liquidity,
    get_entry_zones
)

logger = logging.getLogger(__name__)


class SMCStrategy(IStrategy):
    """
    Smart Money Concepts (SMC) Trading Strategy
    
    This strategy uses institutional trading concepts:
    - Order Blocks for entry zones
    - Fair Value Gaps for targets
    - BOS/CHOCH for trend confirmation
    - Liquidity sweeps as entry triggers
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Optimal timeframe for the strategy
    timeframe = '15m'
    
    # Can this strategy go short?
    can_short = False  # Set to True for futures
    
    # Minimal ROI designed for the strategy
    minimal_roi = {
        "0": 0.05,      # 5% initial target
        "30": 0.03,     # 3% after 30 mins
        "60": 0.02,     # 2% after 60 mins
        "120": 0.01,    # 1% after 120 mins
    }
    
    # Optimal stoploss
    stoploss = -0.03  # 3% stop loss
    
    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01  # Trail after 1% profit
    trailing_stop_positive_offset = 0.015  # Start trailing at 1.5%
    trailing_only_offset_is_reached = True
    
    # Run "populate_indicators()" only for new candle
    process_only_new_candles = True
    
    # Use exit signal
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # Number of candles startup requires
    startup_candle_count: int = 100
    
    # ==================== HYPEROPT PARAMETERS ====================
    
    # Swing detection
    swing_length = IntParameter(5, 30, default=10, space='buy', optimize=True)
    
    # Order Block settings
    ob_lookback = IntParameter(20, 100, default=50, space='buy', optimize=True)
    ob_threshold = DecimalParameter(0.3, 0.8, default=0.5, space='buy', optimize=True)
    
    # FVG settings
    fvg_min_size = DecimalParameter(0.001, 0.01, default=0.003, space='buy', optimize=True)
    
    # Risk settings
    risk_reward = DecimalParameter(1.0, 3.0, default=1.5, space='sell', optimize=True)
    
    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations for analysis.
        Higher timeframes for trend confirmation.
        """
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        
        # Add higher timeframes for trend confirmation
        for pair in pairs:
            informative_pairs.append((pair, '1h'))  # 1 hour for structure
            informative_pairs.append((pair, '4h'))  # 4 hour for bias
        
        return informative_pairs
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate all SMC indicators.
        """
        # ATR for volatility-based stops
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # EMA for additional trend filter
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Volume analysis
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # ==================== SMC INDICATORS ====================
        
        # Swing Highs and Lows
        swing_length = self.swing_length.value
        swings = calculate_swing_highs_lows(dataframe, swing_length)
        dataframe['swing_hl'] = swings['HighLow']
        dataframe['swing_level'] = swings['Level']
        
        # Break of Structure / Change of Character
        structure = calculate_bos_choch(dataframe, swings)
        dataframe['bos'] = structure['BOS']
        dataframe['choch'] = structure['CHOCH']
        dataframe['structure_level'] = structure['Level']
        
        # Order Blocks
        order_blocks = calculate_order_blocks(dataframe, swings)
        dataframe['ob'] = order_blocks['OB']
        dataframe['ob_top'] = order_blocks['Top']
        dataframe['ob_bottom'] = order_blocks['Bottom']
        
        # Fair Value Gaps
        fvg = calculate_fvg(dataframe)
        dataframe['fvg'] = fvg['FVG']
        dataframe['fvg_top'] = fvg['Top']
        dataframe['fvg_bottom'] = fvg['Bottom']
        
        # Liquidity
        liquidity = calculate_liquidity(dataframe, swings)
        dataframe['liquidity'] = liquidity['Liquidity']
        dataframe['liquidity_level'] = liquidity['Level']
        dataframe['liquidity_swept'] = liquidity['Swept']
        
        # Entry Zones (combined OB + FVG)
        zones = get_entry_zones(dataframe, swing_length)
        dataframe['bullish_zone'] = zones['bullish_zone']
        dataframe['bullish_zone_top'] = zones['bullish_top']
        dataframe['bullish_zone_bottom'] = zones['bullish_bottom']
        dataframe['bearish_zone'] = zones['bearish_zone']
        dataframe['bearish_zone_top'] = zones['bearish_top']
        dataframe['bearish_zone_bottom'] = zones['bearish_bottom']
        
        # ==================== DERIVED SIGNALS ====================
        
        # Trend determination
        dataframe['trend'] = np.where(
            dataframe['ema_50'] > dataframe['ema_200'], 1,
            np.where(dataframe['ema_50'] < dataframe['ema_200'], -1, 0)
        )
        
        # Recent BOS/CHOCH (within last N candles)
        lookback = 20
        dataframe['recent_bullish_bos'] = (
            dataframe['bos'].rolling(window=lookback).apply(
                lambda x: 1 if (x == 1).any() else 0
            )
        )
        dataframe['recent_bearish_bos'] = (
            dataframe['bos'].rolling(window=lookback).apply(
                lambda x: 1 if (x == -1).any() else 0
            )
        )
        dataframe['recent_bullish_choch'] = (
            dataframe['choch'].rolling(window=lookback).apply(
                lambda x: 1 if (x == 1).any() else 0
            )
        )
        dataframe['recent_bearish_choch'] = (
            dataframe['choch'].rolling(window=lookback).apply(
                lambda x: 1 if (x == -1).any() else 0
            )
        )
        
        # Price in zone detection
        dataframe['price_in_bullish_ob'] = (
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['ob'].ffill() == 1)
        ).astype(int)
        
        dataframe['price_in_bearish_ob'] = (
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['ob'].ffill() == -1)
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry conditions based on SMC.
        
        Long Entry:
        1. Bullish market structure (recent BOS or CHOCH)
        2. Price in bullish Order Block OR at bullish FVG
        3. Trend filter (EMA 50 > EMA 200)
        4. Volume confirmation
        """
        
        dataframe.loc[
            (
                # Trend filter
                (dataframe['trend'] == 1) &
                
                # Market structure confirmation
                (
                    (dataframe['recent_bullish_bos'] == 1) |
                    (dataframe['recent_bullish_choch'] == 1)
                ) &
                
                # Entry zone: in bullish OB or FVG
                (
                    (dataframe['price_in_bullish_ob'] == 1) |
                    (dataframe['fvg'] == 1)
                ) &
                
                # Volume filter: above average
                (dataframe['volume_ratio'] > 0.8) &
                
                # Make sure we have valid data
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        # Short entries (if enabled)
        if self.can_short:
            dataframe.loc[
                (
                    # Trend filter
                    (dataframe['trend'] == -1) &
                    
                    # Market structure confirmation
                    (
                        (dataframe['recent_bearish_bos'] == 1) |
                        (dataframe['recent_bearish_choch'] == 1)
                    ) &
                    
                    # Entry zone: in bearish OB or FVG
                    (
                        (dataframe['price_in_bearish_ob'] == 1) |
                        (dataframe['fvg'] == -1)
                    ) &
                    
                    # Volume filter
                    (dataframe['volume_ratio'] > 0.8) &
                    
                    # Valid data
                    (dataframe['volume'] > 0)
                ),
                'enter_short'
            ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit conditions based on SMC.
        
        Exit Long:
        1. Bearish CHOCH (trend reversal)
        2. Price reaches bearish FVG (resistance)
        3. Bearish Order Block rejection
        """
        
        dataframe.loc[
            (
                # Structure break against position
                (dataframe['choch'] == -1) |
                
                # Hit resistance (bearish FVG)
                (dataframe['fvg'] == -1) |
                
                # Price rejected from bearish OB
                (dataframe['price_in_bearish_ob'] == 1)
            ),
            'exit_long'
        ] = 1
        
        # Short exits
        if self.can_short:
            dataframe.loc[
                (
                    # Structure break against position
                    (dataframe['choch'] == 1) |
                    
                    # Hit support (bullish FVG)
                    (dataframe['fvg'] == 1) |
                    
                    # Price bouncing from bullish OB
                    (dataframe['price_in_bullish_ob'] == 1)
                ),
                'exit_short'
            ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Dynamic stop loss based on Order Block levels.
        
        For longs: Stop below the Order Block bottom
        For shorts: Stop above the Order Block top
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        
        if trade.is_short:
            # Short stop: above entry + 1.5 ATR
            stop_price = trade.open_rate + (atr * 1.5)
            return (stop_price / current_rate) - 1
        else:
            # Long stop: below entry - 1.5 ATR
            stop_price = trade.open_rate - (atr * 1.5)
            return (stop_price / current_rate) - 1
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """
        Custom exit logic for partial profits.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
        
        last_candle = dataframe.iloc[-1]
        
        # Exit if we hit a CHOCH against our position
        if not trade.is_short:
            if last_candle['choch'] == -1:
                return 'smc_choch_reversal'
        else:
            if last_candle['choch'] == 1:
                return 'smc_choch_reversal'
        
        return None
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        Customize leverage for each new trade.
        
        Using conservative leverage for safety.
        """
        return 1.0  # No leverage for spot trading


class SMCStrategyV2(SMCStrategy):
    """
    SMC Strategy V2 - More aggressive version with liquidity sweeps.
    
    Additional entry condition: Liquidity sweep confirmation
    """
    
    # Slightly higher targets
    minimal_roi = {
        "0": 0.08,
        "30": 0.05,
        "60": 0.03,
        "120": 0.02,
    }
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        More aggressive entries with liquidity confirmation.
        """
        
        # Bullish liquidity sweep detection
        dataframe['liquidity_sweep_bull'] = (
            (dataframe['liquidity_swept'].notna()) &
            (dataframe['liquidity'] == 1)
        ).astype(int)
        
        dataframe['liquidity_sweep_bear'] = (
            (dataframe['liquidity_swept'].notna()) &
            (dataframe['liquidity'] == -1)
        ).astype(int)
        
        dataframe.loc[
            (
                # Trend filter
                (dataframe['trend'] == 1) &
                
                # Market structure
                (
                    (dataframe['recent_bullish_bos'] == 1) |
                    (dataframe['recent_bullish_choch'] == 1)
                ) &
                
                # Entry zone + Liquidity sweep
                (
                    (dataframe['price_in_bullish_ob'] == 1) |
                    (dataframe['liquidity_sweep_bull'].rolling(5).max() == 1)
                ) &
                
                # Volume
                (dataframe['volume_ratio'] > 1.0) &  # Higher volume requirement
                
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
