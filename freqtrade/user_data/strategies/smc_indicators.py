"""
Smart Money Concepts Indicators for Freqtrade
==============================================
Wrapper module integrating smartmoneyconcepts library with Freqtrade.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from smartmoneyconcepts import smc
    SMC_AVAILABLE = True
except ImportError:
    SMC_AVAILABLE = False
    logger.warning("smartmoneyconcepts not installed. Run: pip install smartmoneyconcepts")


def prepare_ohlc(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare OHLC data for SMC library.
    
    SMC expects lowercase column names: open, high, low, close, volume
    """
    df = dataframe.copy()
    
    # Ensure lowercase columns
    df.columns = [col.lower() for col in df.columns]
    
    # Ensure required columns exist
    required = ['open', 'high', 'low', 'close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    return df


def calculate_swing_highs_lows(
    dataframe: pd.DataFrame, 
    swing_length: int = 10
) -> pd.DataFrame:
    """
    Calculate swing highs and lows.
    
    Returns DataFrame with:
    - HighLow: 1 for swing high, -1 for swing low
    - Level: price level of the swing
    """
    if not SMC_AVAILABLE:
        return _fallback_swing_highs_lows(dataframe, swing_length)
    
    ohlc = prepare_ohlc(dataframe)
    return smc.swing_highs_lows(ohlc, swing_length=swing_length)


def _fallback_swing_highs_lows(df: pd.DataFrame, swing_length: int) -> pd.DataFrame:
    """Fallback swing detection without SMC library."""
    result = pd.DataFrame(index=df.index)
    result['HighLow'] = 0
    result['Level'] = np.nan
    
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(swing_length, len(df) - swing_length):
        # Check swing high
        if highs[i] == max(highs[i-swing_length:i+swing_length+1]):
            result.iloc[i, result.columns.get_loc('HighLow')] = 1
            result.iloc[i, result.columns.get_loc('Level')] = highs[i]
        
        # Check swing low
        if lows[i] == min(lows[i-swing_length:i+swing_length+1]):
            result.iloc[i, result.columns.get_loc('HighLow')] = -1
            result.iloc[i, result.columns.get_loc('Level')] = lows[i]
    
    return result


def calculate_bos_choch(
    dataframe: pd.DataFrame,
    swing_highs_lows: pd.DataFrame,
    close_break: bool = True
) -> pd.DataFrame:
    """
    Calculate Break of Structure (BOS) and Change of Character (CHOCH).
    
    Returns DataFrame with:
    - BOS: 1 for bullish, -1 for bearish, 0 otherwise
    - CHOCH: 1 for bullish, -1 for bearish, 0 otherwise
    - Level: the price level broken
    - BrokenIndex: index where the break occurred
    """
    if not SMC_AVAILABLE:
        return _fallback_bos_choch(dataframe, swing_highs_lows)
    
    ohlc = prepare_ohlc(dataframe)
    return smc.bos_choch(ohlc, swing_highs_lows, close_break=close_break)


def _fallback_bos_choch(df: pd.DataFrame, swings: pd.DataFrame) -> pd.DataFrame:
    """Fallback BOS/CHOCH detection."""
    result = pd.DataFrame(index=df.index)
    result['BOS'] = 0
    result['CHOCH'] = 0
    result['Level'] = np.nan
    result['BrokenIndex'] = np.nan
    
    # Simple implementation: detect when close breaks previous swing
    swing_highs = swings[swings['HighLow'] == 1]['Level'].dropna()
    swing_lows = swings[swings['HighLow'] == -1]['Level'].dropna()
    
    last_swing_high = None
    last_swing_low = None
    trend = 0  # 1 = bullish, -1 = bearish
    
    for i in range(len(df)):
        idx = df.index[i]
        
        # Update last swings
        if idx in swing_highs.index:
            last_swing_high = swing_highs[idx]
        if idx in swing_lows.index:
            last_swing_low = swing_lows[idx]
        
        if last_swing_high is None or last_swing_low is None:
            continue
        
        close = df['close'].iloc[i]
        
        # Bullish break
        if close > last_swing_high:
            if trend == -1:
                result.iloc[i, result.columns.get_loc('CHOCH')] = 1
            else:
                result.iloc[i, result.columns.get_loc('BOS')] = 1
            result.iloc[i, result.columns.get_loc('Level')] = last_swing_high
            trend = 1
        
        # Bearish break
        elif close < last_swing_low:
            if trend == 1:
                result.iloc[i, result.columns.get_loc('CHOCH')] = -1
            else:
                result.iloc[i, result.columns.get_loc('BOS')] = -1
            result.iloc[i, result.columns.get_loc('Level')] = last_swing_low
            trend = -1
    
    return result


def calculate_order_blocks(
    dataframe: pd.DataFrame,
    swing_highs_lows: pd.DataFrame,
    close_mitigation: bool = False
) -> pd.DataFrame:
    """
    Calculate Order Blocks.
    
    Returns DataFrame with:
    - OB: 1 for bullish OB, -1 for bearish OB
    - Top: top of the order block
    - Bottom: bottom of the order block
    - OBVolume: volume indicator
    - Percentage: strength of OB
    """
    if not SMC_AVAILABLE:
        return _fallback_order_blocks(dataframe, swing_highs_lows)
    
    ohlc = prepare_ohlc(dataframe)
    return smc.ob(ohlc, swing_highs_lows, close_mitigation=close_mitigation)


def _fallback_order_blocks(df: pd.DataFrame, swings: pd.DataFrame) -> pd.DataFrame:
    """Fallback Order Block detection."""
    result = pd.DataFrame(index=df.index)
    result['OB'] = 0
    result['Top'] = np.nan
    result['Bottom'] = np.nan
    result['OBVolume'] = np.nan
    result['Percentage'] = np.nan
    
    # Simple implementation: last opposite candle before impulsive move
    for i in range(3, len(df)):
        current_range = df['high'].iloc[i] - df['low'].iloc[i]
        avg_range = (df['high'] - df['low']).iloc[i-5:i].mean()
        
        # Check for impulsive move (1.5x average range)
        if current_range < avg_range * 1.5:
            continue
        
        # Bullish OB: bearish candle before bullish impulse
        if df['close'].iloc[i] > df['open'].iloc[i]:  # Bullish candle
            if df['close'].iloc[i-1] < df['open'].iloc[i-1]:  # Previous bearish
                result.iloc[i-1, result.columns.get_loc('OB')] = 1
                result.iloc[i-1, result.columns.get_loc('Top')] = df['high'].iloc[i-1]
                result.iloc[i-1, result.columns.get_loc('Bottom')] = df['low'].iloc[i-1]
                if 'volume' in df.columns:
                    result.iloc[i-1, result.columns.get_loc('OBVolume')] = df['volume'].iloc[i-1]
        
        # Bearish OB: bullish candle before bearish impulse
        elif df['close'].iloc[i] < df['open'].iloc[i]:  # Bearish candle
            if df['close'].iloc[i-1] > df['open'].iloc[i-1]:  # Previous bullish
                result.iloc[i-1, result.columns.get_loc('OB')] = -1
                result.iloc[i-1, result.columns.get_loc('Top')] = df['high'].iloc[i-1]
                result.iloc[i-1, result.columns.get_loc('Bottom')] = df['low'].iloc[i-1]
                if 'volume' in df.columns:
                    result.iloc[i-1, result.columns.get_loc('OBVolume')] = df['volume'].iloc[i-1]
    
    return result


def calculate_fvg(
    dataframe: pd.DataFrame,
    join_consecutive: bool = False
) -> pd.DataFrame:
    """
    Calculate Fair Value Gaps.
    
    Returns DataFrame with:
    - FVG: 1 for bullish, -1 for bearish
    - Top: top of the gap
    - Bottom: bottom of the gap
    - MitigatedIndex: index where gap was filled
    """
    if not SMC_AVAILABLE:
        return _fallback_fvg(dataframe)
    
    ohlc = prepare_ohlc(dataframe)
    return smc.fvg(ohlc, join_consecutive=join_consecutive)


def _fallback_fvg(df: pd.DataFrame) -> pd.DataFrame:
    """Fallback FVG detection."""
    result = pd.DataFrame(index=df.index)
    result['FVG'] = 0
    result['Top'] = np.nan
    result['Bottom'] = np.nan
    result['MitigatedIndex'] = np.nan
    
    for i in range(2, len(df)):
        # Bullish FVG: gap up
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            result.iloc[i-1, result.columns.get_loc('FVG')] = 1
            result.iloc[i-1, result.columns.get_loc('Top')] = df['low'].iloc[i]
            result.iloc[i-1, result.columns.get_loc('Bottom')] = df['high'].iloc[i-2]
        
        # Bearish FVG: gap down
        elif df['high'].iloc[i] < df['low'].iloc[i-2]:
            result.iloc[i-1, result.columns.get_loc('FVG')] = -1
            result.iloc[i-1, result.columns.get_loc('Top')] = df['low'].iloc[i-2]
            result.iloc[i-1, result.columns.get_loc('Bottom')] = df['high'].iloc[i]
    
    return result


def calculate_liquidity(
    dataframe: pd.DataFrame,
    swing_highs_lows: pd.DataFrame,
    range_percent: float = 0.01
) -> pd.DataFrame:
    """
    Calculate Liquidity zones.
    
    Returns DataFrame with:
    - Liquidity: 1 for bullish (lows), -1 for bearish (highs)
    - Level: the liquidity level
    - End: end index of liquidity zone
    - Swept: index where liquidity was swept
    """
    if not SMC_AVAILABLE:
        return _fallback_liquidity(dataframe, swing_highs_lows, range_percent)
    
    ohlc = prepare_ohlc(dataframe)
    return smc.liquidity(ohlc, swing_highs_lows, range_percent=range_percent)


def _fallback_liquidity(df: pd.DataFrame, swings: pd.DataFrame, range_pct: float) -> pd.DataFrame:
    """Fallback Liquidity detection."""
    result = pd.DataFrame(index=df.index)
    result['Liquidity'] = 0
    result['Level'] = np.nan
    result['End'] = np.nan
    result['Swept'] = np.nan
    
    # Find clusters of equal highs/lows
    swing_highs = swings[swings['HighLow'] == 1]['Level'].dropna()
    swing_lows = swings[swings['HighLow'] == -1]['Level'].dropna()
    
    # Check for equal highs (bearish liquidity)
    for i, (idx1, level1) in enumerate(swing_highs.items()):
        for idx2, level2 in list(swing_highs.items())[i+1:]:
            if abs(level1 - level2) / level1 < range_pct:
                result.loc[idx2, 'Liquidity'] = -1
                result.loc[idx2, 'Level'] = (level1 + level2) / 2
    
    # Check for equal lows (bullish liquidity)
    for i, (idx1, level1) in enumerate(swing_lows.items()):
        for idx2, level2 in list(swing_lows.items())[i+1:]:
            if abs(level1 - level2) / level1 < range_pct:
                result.loc[idx2, 'Liquidity'] = 1
                result.loc[idx2, 'Level'] = (level1 + level2) / 2
    
    return result


def get_market_structure(
    dataframe: pd.DataFrame,
    swing_length: int = 10
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Get complete market structure analysis.
    
    Returns:
        - swings: Swing highs and lows
        - structure: BOS/CHOCH data
        - order_blocks: Order block zones
    """
    swings = calculate_swing_highs_lows(dataframe, swing_length)
    structure = calculate_bos_choch(dataframe, swings)
    order_blocks = calculate_order_blocks(dataframe, swings)
    
    return swings, structure, order_blocks


def get_entry_zones(
    dataframe: pd.DataFrame,
    swing_length: int = 10
) -> pd.DataFrame:
    """
    Get potential entry zones based on SMC.
    
    Combines Order Blocks and FVG for entry zones.
    """
    swings = calculate_swing_highs_lows(dataframe, swing_length)
    order_blocks = calculate_order_blocks(dataframe, swings)
    fvg = calculate_fvg(dataframe)
    
    # Create entry zones DataFrame
    zones = pd.DataFrame(index=dataframe.index)
    
    # Bullish entry zone: bullish OB or bullish FVG
    zones['bullish_zone'] = (
        ((order_blocks['OB'] == 1) | (fvg['FVG'] == 1))
    ).astype(int)
    
    zones['bullish_top'] = np.where(
        order_blocks['OB'] == 1, order_blocks['Top'],
        np.where(fvg['FVG'] == 1, fvg['Top'], np.nan)
    )
    zones['bullish_bottom'] = np.where(
        order_blocks['OB'] == 1, order_blocks['Bottom'],
        np.where(fvg['FVG'] == 1, fvg['Bottom'], np.nan)
    )
    
    # Bearish entry zone: bearish OB or bearish FVG
    zones['bearish_zone'] = (
        ((order_blocks['OB'] == -1) | (fvg['FVG'] == -1))
    ).astype(int)
    
    zones['bearish_top'] = np.where(
        order_blocks['OB'] == -1, order_blocks['Top'],
        np.where(fvg['FVG'] == -1, fvg['Top'], np.nan)
    )
    zones['bearish_bottom'] = np.where(
        order_blocks['OB'] == -1, order_blocks['Bottom'],
        np.where(fvg['FVG'] == -1, fvg['Bottom'], np.nan)
    )
    
    return zones


# ═══════════════════════════════════════════════════════════════════════════
#                    NEW: MARKET REGIME FUNCTIONS (v7)
# ═══════════════════════════════════════════════════════════════════════════

def calculate_choppiness(dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Choppiness Index.
    
    Values > 60: Ranging/Choppy market
    Values < 40: Trending market
    Values 40-60: Normal market
    """
    import talib.abstract as ta
    
    atr_sum = ta.ATR(dataframe, timeperiod=1).rolling(period).sum()
    high_low_range = (
        dataframe['high'].rolling(period).max() - 
        dataframe['low'].rolling(period).min()
    )
    
    # Avoid division by zero
    high_low_range = high_low_range.replace(0, np.nan)
    
    choppiness = 100 * np.log10(atr_sum / high_low_range) / np.log10(period)
    return choppiness.fillna(50)


def calculate_market_regime(
    dataframe: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 30,
    chop_period: int = 14,
    chop_threshold: float = 60
) -> pd.DataFrame:
    """
    Calculate market regime based on ADX and Choppiness Index.
    
    Returns DataFrame with:
    - adx: ADX value
    - choppiness: Choppiness Index value
    - regime: 'TRENDING_UP', 'TRENDING_DOWN', 'RANGING', or 'NORMAL'
    """
    import talib.abstract as ta
    
    result = pd.DataFrame(index=dataframe.index)
    
    # ADX calculation
    result['adx'] = ta.ADX(dataframe, timeperiod=adx_period)
    result['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=adx_period)
    result['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=adx_period)
    
    # Choppiness Index
    result['choppiness'] = calculate_choppiness(dataframe, chop_period)
    
    # Regime classification
    is_trending = result['adx'] > adx_threshold
    is_choppy = result['choppiness'] > chop_threshold
    is_bullish = result['plus_di'] > result['minus_di']
    
    conditions = [
        is_trending & ~is_choppy & is_bullish,
        is_trending & ~is_choppy & ~is_bullish,
        is_choppy & ~is_trending,
    ]
    choices = ['TRENDING_UP', 'TRENDING_DOWN', 'RANGING']
    
    result['regime'] = np.select(conditions, choices, default='NORMAL')
    
    return result


def calculate_sfp_confirmed(
    dataframe: pd.DataFrame,
    lookback: int = 20,
    volume_threshold: float = 1.0
) -> pd.DataFrame:
    """
    Calculate Swing Failure Pattern (SFP) with close confirmation and volume.
    
    SFP occurs when price sweeps a swing high/low but closes back inside,
    indicating a potential reversal.
    
    Returns DataFrame with:
    - sfp_bullish: 1 when bullish SFP detected
    - sfp_bearish: 1 when bearish SFP detected
    - sfp_strength: Volume ratio at SFP (higher = stronger signal)
    """
    result = pd.DataFrame(index=dataframe.index)
    
    # Previous highs and lows
    prev_high = dataframe['high'].rolling(lookback).max().shift(1)
    prev_low = dataframe['low'].rolling(lookback).min().shift(1)
    
    # Volume ratio
    volume_sma = dataframe['volume'].rolling(20).mean()
    volume_ratio = dataframe['volume'] / volume_sma
    
    # Bullish SFP: Price sweeps low but closes back inside with bullish candle
    result['sfp_bullish'] = (
        (dataframe['low'] < prev_low) &
        (dataframe['close'] > prev_low) &
        (dataframe['close'] > dataframe['open']) &
        (volume_ratio > volume_threshold)
    ).astype(int)
    
    # Bearish SFP: Price sweeps high but closes back inside with bearish candle
    result['sfp_bearish'] = (
        (dataframe['high'] > prev_high) &
        (dataframe['close'] < prev_high) &
        (dataframe['close'] < dataframe['open']) &
        (volume_ratio > volume_threshold)
    ).astype(int)
    
    # SFP strength (volume ratio at signal)
    result['sfp_strength'] = np.where(
        (result['sfp_bullish'] == 1) | (result['sfp_bearish'] == 1),
        volume_ratio,
        np.nan
    )
    
    return result


def calculate_chandelier_exit(
    dataframe: pd.DataFrame,
    period: int = 22,
    atr_period: int = 14,
    multiplier: float = 2.5
) -> pd.DataFrame:
    """
    Calculate Chandelier Exit (ATR-based trailing stop).
    
    Returns DataFrame with:
    - chandelier_long: Stop level for long positions
    - chandelier_short: Stop level for short positions
    """
    import talib.abstract as ta
    
    result = pd.DataFrame(index=dataframe.index)
    
    atr = ta.ATR(dataframe, timeperiod=atr_period)
    highest_high = dataframe['high'].rolling(period).max()
    lowest_low = dataframe['low'].rolling(period).min()
    
    result['chandelier_long'] = highest_high - (atr * multiplier)
    result['chandelier_short'] = lowest_low + (atr * multiplier)
    
    return result


def calculate_volatility_regime(
    dataframe: pd.DataFrame,
    atr_period: int = 14,
    lookback: int = 50
) -> pd.DataFrame:
    """
    Calculate Volatility Regime based on ATR z-score.
    
    Used to adapt position sizing and stop distances:
    - HIGH_VOL (z > 1.5): Reduce position size, widen stops
    - LOW_VOL (z < -0.5): Normal position size, tighter stops
    - NORMAL: Default parameters
    
    Returns DataFrame with:
    - atr: Current ATR value
    - atr_zscore: Z-score of ATR relative to lookback period
    - vol_regime: 'HIGH_VOL', 'LOW_VOL', or 'NORMAL'
    - vol_multiplier: Suggested multiplier for stops (1.0-1.5)
    """
    import talib.abstract as ta
    
    result = pd.DataFrame(index=dataframe.index)
    
    # ATR calculation
    result['atr'] = ta.ATR(dataframe, timeperiod=atr_period)
    
    # Rolling statistics
    atr_ma = result['atr'].rolling(lookback).mean()
    atr_std = result['atr'].rolling(lookback).std()
    
    # Z-score (avoid division by zero)
    atr_std = atr_std.replace(0, np.nan)
    result['atr_zscore'] = (result['atr'] - atr_ma) / atr_std
    result['atr_zscore'] = result['atr_zscore'].fillna(0)
    
    # Regime classification
    result['vol_regime'] = np.select(
        [
            result['atr_zscore'] > 1.5,
            result['atr_zscore'] < -0.5
        ],
        ['HIGH_VOL', 'LOW_VOL'],
        default='NORMAL'
    )
    
    # Multiplier for stop distance adaptation
    result['vol_multiplier'] = np.select(
        [
            result['atr_zscore'] > 1.5,
            result['atr_zscore'] < -0.5
        ],
        [1.5, 0.8],
        default=1.0
    )
    
    return result
