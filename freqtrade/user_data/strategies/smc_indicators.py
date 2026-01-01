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


# ═══════════════════════════════════════════════════════════════════════════
#                    V4 FOUNDATION: ORDER BLOCKS & FVG (Vectorized)
# ═══════════════════════════════════════════════════════════════════════════

def detect_order_blocks_vectorized(
    dataframe: pd.DataFrame,
    impulse_candles: int = 3,
    impulse_pct: float = 0.02,
    lookback: int = 50
) -> pd.DataFrame:
    """
    Vectorized Order Block Detection for Smart Money Concepts.
    
    SMC Methodology:
    - Bullish OB: Last RED candle before impulsive UP move
    - Bearish OB: Last GREEN candle before impulsive DOWN move
    - Impulsive move: 3+ consecutive same-direction candles OR single candle > 2%
    - OB zone remains active until price "mitigates" (closes inside zone)
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data with 'open', 'high', 'low', 'close', 'volume' columns
    impulse_candles : int
        Number of consecutive candles to confirm impulsive move (default: 3)
    impulse_pct : float
        Single candle move percentage for impulse (default: 2%)
    lookback : int
        How far back to track active OBs (default: 50 candles)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - ob_bull_top, ob_bull_bottom: Bullish Order Block zone
        - ob_bear_top, ob_bear_bottom: Bearish Order Block zone  
        - ob_bull_active: 1 if bullish OB not yet mitigated
        - ob_bear_active: 1 if bearish OB not yet mitigated
        - price_at_ob_bull: 1 if current price touching active bullish OB
        - price_at_ob_bear: 1 if current price touching active bearish OB
    """
    result = pd.DataFrame(index=dataframe.index)
    
    # Vectorized candle color detection
    is_green = dataframe['close'] > dataframe['open']
    is_red = dataframe['close'] < dataframe['open']
    
    # Percentage move per candle
    pct_move = (dataframe['close'] - dataframe['open']) / dataframe['open']
    
    # Count consecutive green/red candles using rolling
    # Green streak: count consecutive greens
    green_streak = is_green.astype(int)
    for i in range(1, impulse_candles):
        green_streak = green_streak + is_green.shift(i).fillna(0).astype(int)
    
    # Red streak: count consecutive reds
    red_streak = is_red.astype(int)
    for i in range(1, impulse_candles):
        red_streak = red_streak + is_red.shift(i).fillna(0).astype(int)
    
    # Impulsive up: 3+ green candles OR single candle > 2%
    impulsive_up = (green_streak >= impulse_candles) | (pct_move > impulse_pct)
    
    # Impulsive down: 3+ red candles OR single candle < -2%
    impulsive_down = (red_streak >= impulse_candles) | (pct_move < -impulse_pct)
    
    # ==================== BULLISH ORDER BLOCK ====================
    # Find last RED candle before impulsive UP move
    # The candle before the impulsive move should be red
    
    bullish_ob_candle = impulsive_up & is_red.shift(1).fillna(False)
    
    # OB zone from that red candle
    result['ob_bull_top'] = np.where(
        bullish_ob_candle,
        dataframe['high'].shift(1),  # High of the red candle before impulse
        np.nan
    )
    result['ob_bull_bottom'] = np.where(
        bullish_ob_candle,
        dataframe['low'].shift(1),  # Low of the red candle before impulse
        np.nan
    )
    
    # Forward fill to track active OBs (for lookback period)
    result['ob_bull_top'] = result['ob_bull_top'].ffill(limit=lookback)
    result['ob_bull_bottom'] = result['ob_bull_bottom'].ffill(limit=lookback)
    
    # ==================== BEARISH ORDER BLOCK ====================
    # Find last GREEN candle before impulsive DOWN move
    
    bearish_ob_candle = impulsive_down & is_green.shift(1).fillna(False)
    
    result['ob_bear_top'] = np.where(
        bearish_ob_candle,
        dataframe['high'].shift(1),
        np.nan
    )
    result['ob_bear_bottom'] = np.where(
        bearish_ob_candle,
        dataframe['low'].shift(1),
        np.nan
    )
    
    result['ob_bear_top'] = result['ob_bear_top'].ffill(limit=lookback)
    result['ob_bear_bottom'] = result['ob_bear_bottom'].ffill(limit=lookback)
    
    # ==================== MITIGATION CHECK ====================
    # Bullish OB mitigated when close goes below OB bottom
    bull_mitigated = dataframe['close'] < result['ob_bull_bottom']
    
    # Bearish OB mitigated when close goes above OB top
    bear_mitigated = dataframe['close'] > result['ob_bear_top']
    
    # Active status (not yet mitigated)
    # Use cumsum to track mitigation events
    result['ob_bull_active'] = (~bull_mitigated & result['ob_bull_top'].notna()).astype(int)
    result['ob_bear_active'] = (~bear_mitigated & result['ob_bear_top'].notna()).astype(int)
    
    # ==================== PRICE AT ORDER BLOCK ====================
    # Price touching bullish OB zone (low touches zone)
    result['price_at_ob_bull'] = (
        (result['ob_bull_active'] == 1) &
        (dataframe['low'] <= result['ob_bull_top']) &
        (dataframe['low'] >= result['ob_bull_bottom'])
    ).astype(int)
    
    # Price touching bearish OB zone (high touches zone)
    result['price_at_ob_bear'] = (
        (result['ob_bear_active'] == 1) &
        (dataframe['high'] >= result['ob_bear_bottom']) &
        (dataframe['high'] <= result['ob_bear_top'])
    ).astype(int)
    
    return result


def detect_fvg_vectorized(
    dataframe: pd.DataFrame,
    lookback: int = 50
) -> pd.DataFrame:
    """
    Vectorized Fair Value Gap (FVG) Detection for Smart Money Concepts.
    
    SMC Methodology:
    - Bullish FVG: Gap between candle[i-2].high and candle[i].low
      (Middle candle doesn't fill the gap)
    - Bearish FVG: Gap between candle[i-2].low and candle[i].high
    - FVG remains active until price fills it
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data
    lookback : int
        How far back to track active FVGs (default: 50 candles)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - fvg_bull_top, fvg_bull_bottom: Bullish FVG zone
        - fvg_bear_top, fvg_bear_bottom: Bearish FVG zone
        - fvg_bull_active: 1 if bullish FVG not yet filled
        - fvg_bear_active: 1 if bearish FVG not yet filled
        - price_in_fvg_bull: 1 if current price inside bullish FVG
        - price_in_fvg_bear: 1 if current price inside bearish FVG
    """
    result = pd.DataFrame(index=dataframe.index)
    
    # Shifted values for 3-candle pattern
    high_2 = dataframe['high'].shift(2)  # Candle 2 bars ago
    low_2 = dataframe['low'].shift(2)
    low_0 = dataframe['low']  # Current candle
    high_0 = dataframe['high']
    
    # ==================== BULLISH FVG ====================
    # Gap exists when current low > high of 2 candles ago
    bullish_fvg = low_0 > high_2
    
    result['fvg_bull_top'] = np.where(bullish_fvg, low_0, np.nan)
    result['fvg_bull_bottom'] = np.where(bullish_fvg, high_2, np.nan)
    
    # Forward fill to track active FVGs
    result['fvg_bull_top'] = result['fvg_bull_top'].ffill(limit=lookback)
    result['fvg_bull_bottom'] = result['fvg_bull_bottom'].ffill(limit=lookback)
    
    # ==================== BEARISH FVG ====================
    # Gap exists when current high < low of 2 candles ago
    bearish_fvg = high_0 < low_2
    
    result['fvg_bear_top'] = np.where(bearish_fvg, low_2, np.nan)
    result['fvg_bear_bottom'] = np.where(bearish_fvg, high_0, np.nan)
    
    result['fvg_bear_top'] = result['fvg_bear_top'].ffill(limit=lookback)
    result['fvg_bear_bottom'] = result['fvg_bear_bottom'].ffill(limit=lookback)
    
    # ==================== FILL CHECK ====================
    # Bullish FVG filled when price goes below FVG bottom
    bull_filled = dataframe['close'] < result['fvg_bull_bottom']
    
    # Bearish FVG filled when price goes above FVG top  
    bear_filled = dataframe['close'] > result['fvg_bear_top']
    
    # Active status
    result['fvg_bull_active'] = (~bull_filled & result['fvg_bull_top'].notna()).astype(int)
    result['fvg_bear_active'] = (~bear_filled & result['fvg_bear_top'].notna()).astype(int)
    
    # ==================== PRICE IN FVG ====================
    # Price inside bullish FVG zone
    result['price_in_fvg_bull'] = (
        (result['fvg_bull_active'] == 1) &
        (dataframe['close'] >= result['fvg_bull_bottom']) &
        (dataframe['close'] <= result['fvg_bull_top'])
    ).astype(int)
    
    # Price inside bearish FVG zone
    result['price_in_fvg_bear'] = (
        (result['fvg_bear_active'] == 1) &
        (dataframe['close'] <= result['fvg_bear_top']) &
        (dataframe['close'] >= result['fvg_bear_bottom'])
    ).astype(int)
    
    return result


def add_smc_zones(
    dataframe: pd.DataFrame,
    impulse_candles: int = 3,
    impulse_pct: float = 0.02,
    lookback: int = 50
) -> pd.DataFrame:
    """
    Convenience function to add all SMC zones (OB + FVG) to dataframe.
    
    Usage in strategy:
    ```python
    from smc_indicators import add_smc_zones
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add SMC zones
        smc_zones = add_smc_zones(dataframe)
        dataframe = pd.concat([dataframe, smc_zones], axis=1)
        return dataframe
    ```
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data
    impulse_candles : int
        Consecutive candles for impulse detection
    impulse_pct : float
        Single candle percentage for impulse
    lookback : int
        Active zone tracking period
        
    Returns:
    --------
    pd.DataFrame with all OB and FVG columns
    """
    # Get Order Blocks
    ob_data = detect_order_blocks_vectorized(
        dataframe, 
        impulse_candles=impulse_candles,
        impulse_pct=impulse_pct,
        lookback=lookback
    )
    
    # Get Fair Value Gaps
    fvg_data = detect_fvg_vectorized(dataframe, lookback=lookback)
    
    # Combine
    result = pd.concat([ob_data, fvg_data], axis=1)
    
    # Add convenience columns for entry boost
    result['smc_bull_confluence'] = (
        (result['price_at_ob_bull'] == 1) | 
        (result['price_in_fvg_bull'] == 1)
    ).astype(int)
    
    result['smc_bear_confluence'] = (
        (result['price_at_ob_bear'] == 1) | 
        (result['price_in_fvg_bear'] == 1)
    ).astype(int)
    
    return result


def calculate_smc_boost(
    dataframe: pd.DataFrame,
    ob_boost: float = 0.15,
    fvg_boost: float = 0.10
) -> pd.Series:
    """
    Calculate position sizing boost based on SMC zones.
    
    Usage in custom_stake_amount:
    ```python
    smc_boost = calculate_smc_boost(dataframe)
    position_size *= smc_boost.iloc[-1]
    ```
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        DataFrame with SMC zone columns (from add_smc_zones)
    ob_boost : float
        Additional size multiplier when at Order Block (default: 15%)
    fvg_boost : float
        Additional size multiplier when in FVG (default: 10%)
    
    Returns:
    --------
    pd.Series with boost multiplier (1.0 to 1.0 + ob_boost + fvg_boost)
    """
    boost = pd.Series(1.0, index=dataframe.index)
    
    # Add OB boost
    if 'price_at_ob_bull' in dataframe.columns:
        boost = boost + (dataframe['price_at_ob_bull'] * ob_boost)
    if 'price_at_ob_bear' in dataframe.columns:
        boost = boost + (dataframe['price_at_ob_bear'] * ob_boost)
    
    # Add FVG boost
    if 'price_in_fvg_bull' in dataframe.columns:
        boost = boost + (dataframe['price_in_fvg_bull'] * fvg_boost)
    if 'price_in_fvg_bear' in dataframe.columns:
        boost = boost + (dataframe['price_in_fvg_bear'] * fvg_boost)
    
    return boost


# ═══════════════════════════════════════════════════════════════════════════
#                    V4 COMPLETE: LIQUIDITY GRAB, BOS, CHoCH
# ═══════════════════════════════════════════════════════════════════════════

def detect_swing_points(
    dataframe: pd.DataFrame,
    window: int = 5
) -> pd.DataFrame:
    """
    Detect swing highs and swing lows using rolling window.
    
    A swing high is a local maximum where the high is higher than
    the highs of the surrounding candles.
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data
    window : int
        Number of candles on each side to confirm swing (default: 5)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - swing_high: Price level of swing high (NaN if not a swing)
        - swing_low: Price level of swing low (NaN if not a swing)
        - last_swing_high: Most recent swing high (forward filled)
        - last_swing_low: Most recent swing low (forward filled)
    """
    result = pd.DataFrame(index=dataframe.index)
    
    # Rolling max/min for window on each side
    high = dataframe['high']
    low = dataframe['low']
    
    # A swing high is where current high is the max in the window
    rolling_max = high.rolling(window * 2 + 1, center=True).max()
    is_swing_high = (high == rolling_max)
    
    # A swing low is where current low is the min in the window
    rolling_min = low.rolling(window * 2 + 1, center=True).min()
    is_swing_low = (low == rolling_min)
    
    # Record swing levels
    result['swing_high'] = np.where(is_swing_high, high, np.nan)
    result['swing_low'] = np.where(is_swing_low, low, np.nan)
    
    # Forward fill to get last swing levels
    result['last_swing_high'] = result['swing_high'].ffill()
    result['last_swing_low'] = result['swing_low'].ffill()
    
    return result


def detect_liquidity_grab(
    dataframe: pd.DataFrame,
    swing_window: int = 10
) -> pd.DataFrame:
    """
    Vectorized Liquidity Grab Detection for Smart Money Concepts.
    
    SMC Methodology:
    - Liquidity exists at swing highs/lows (stop losses)
    - Smart money hunts this liquidity before reversing
    - Bullish LG: Sweep below swing low, close above (accumulated)
    - Bearish LG: Sweep above swing high, close below (distributed)
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data
    swing_window : int
        Lookback for swing high/low detection (default: 10)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - liq_grab_bull: 1 when bullish liquidity grab detected
        - liq_grab_bear: 1 when bearish liquidity grab detected
        - swing_high: Reference swing high level
        - swing_low: Reference swing low level
    """
    result = pd.DataFrame(index=dataframe.index)
    
    # Get recent swing levels
    swing_low = dataframe['low'].rolling(swing_window).min().shift(1)
    swing_high = dataframe['high'].rolling(swing_window).max().shift(1)
    
    result['swing_low'] = swing_low
    result['swing_high'] = swing_high
    
    # ==================== BULLISH LIQUIDITY GRAB ====================
    # Price sweeps below recent swing low (takes liquidity)
    swept_below = dataframe['low'] < swing_low
    
    # Then closes back above that swing low (rejection/accumulation)
    close_above = dataframe['close'] > swing_low
    
    # Bullish candle confirmation
    bullish_candle = dataframe['close'] > dataframe['open']
    
    result['liq_grab_bull'] = (
        swept_below & close_above & bullish_candle
    ).astype(int)
    
    # ==================== BEARISH LIQUIDITY GRAB ====================
    # Price sweeps above recent swing high
    swept_above = dataframe['high'] > swing_high
    
    # Then closes back below that swing high
    close_below = dataframe['close'] < swing_high
    
    # Bearish candle confirmation
    bearish_candle = dataframe['close'] < dataframe['open']
    
    result['liq_grab_bear'] = (
        swept_above & close_below & bearish_candle
    ).astype(int)
    
    return result


def detect_bos_choch(
    dataframe: pd.DataFrame,
    swing_window: int = 5
) -> pd.DataFrame:
    """
    Vectorized Break of Structure (BOS) and Change of Character (CHoCH) Detection.
    
    SMC Methodology:
    - BOS: Price breaks beyond previous swing point (trend continuation)
    - CHoCH: First BOS against the prevailing trend (potential reversal)
    
    Bullish BOS: Close > previous swing high (uptrend continues)
    Bearish BOS: Close < previous swing low (downtrend continues)
    
    CHoCH is detected when BOS occurs against the established trend:
    - In uptrend (higher highs): First bearish BOS = CHoCH
    - In downtrend (lower lows): First bullish BOS = CHoCH
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data
    swing_window : int
        Window for swing point detection (default: 5)
    
    Returns:
    --------
    pd.DataFrame with columns:
        - bos_bull: 1 when bullish BOS detected
        - bos_bear: 1 when bearish BOS detected
        - choch_bull: 1 when bullish CHoCH detected (reversal up)
        - choch_bear: 1 when bearish CHoCH detected (reversal down)
        - last_swing_high: Most recent swing high level
        - last_swing_low: Most recent swing low level
        - trend: 1 for uptrend, -1 for downtrend, 0 for neutral
    """
    result = pd.DataFrame(index=dataframe.index)
    
    # Get swing points
    swings = detect_swing_points(dataframe, window=swing_window)
    result['last_swing_high'] = swings['last_swing_high']
    result['last_swing_low'] = swings['last_swing_low']
    
    # ==================== BREAK OF STRUCTURE ====================
    # Bullish BOS: Close breaks above previous swing high
    prev_swing_high = result['last_swing_high'].shift(1)
    result['bos_bull'] = (
        (dataframe['close'] > prev_swing_high) &
        (dataframe['close'].shift(1) <= prev_swing_high.shift(1))  # Wasn't above before
    ).astype(int)
    
    # Bearish BOS: Close breaks below previous swing low
    prev_swing_low = result['last_swing_low'].shift(1)
    result['bos_bear'] = (
        (dataframe['close'] < prev_swing_low) &
        (dataframe['close'].shift(1) >= prev_swing_low.shift(1))  # Wasn't below before
    ).astype(int)
    
    # ==================== TREND DETECTION ====================
    # Simple trend based on swing structure
    # Higher swing high = uptrend, Lower swing low = downtrend
    hh = swings['swing_high'] > swings['swing_high'].shift(1).ffill()  # Higher high
    ll = swings['swing_low'] < swings['swing_low'].shift(1).ffill()    # Lower low
    
    # Trend accumulator
    trend_signal = hh.astype(int) - ll.astype(int)
    result['trend'] = trend_signal.rolling(5).sum().fillna(0)
    result['trend'] = np.sign(result['trend'])  # Normalize to -1, 0, 1
    
    # ==================== CHANGE OF CHARACTER ====================
    # CHoCH is BOS against the prevailing trend
    
    # Bullish CHoCH: In downtrend, first bullish BOS (reversal signal)
    in_downtrend = result['trend'].shift(1) < 0
    result['choch_bull'] = (result['bos_bull'] == 1) & in_downtrend
    result['choch_bull'] = result['choch_bull'].astype(int)
    
    # Bearish CHoCH: In uptrend, first bearish BOS (reversal signal)
    in_uptrend = result['trend'].shift(1) > 0
    result['choch_bear'] = (result['bos_bear'] == 1) & in_uptrend
    result['choch_bear'] = result['choch_bear'].astype(int)
    
    return result


def add_smc_zones_complete(
    dataframe: pd.DataFrame,
    impulse_candles: int = 3,
    impulse_pct: float = 0.02,
    lookback: int = 50,
    swing_window: int = 5,
    liq_swing_window: int = 10
) -> pd.DataFrame:
    """
    Complete SMC toolkit: OB + FVG + Liquidity Grab + BOS + CHoCH.
    
    This is the master convenience function that adds all SMC indicators
    to a dataframe for comprehensive market structure analysis.
    
    Usage in strategy:
    ```python
    from smc_indicators import add_smc_zones_complete
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        smc = add_smc_zones_complete(dataframe)
        dataframe = pd.concat([dataframe, smc], axis=1)
        return dataframe
    ```
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        OHLCV data
    impulse_candles : int
        Consecutive candles for OB impulse detection
    impulse_pct : float
        Single candle percentage for OB impulse
    lookback : int
        Active zone tracking period for OB/FVG
    swing_window : int
        Window for BOS/CHoCH swing detection
    liq_swing_window : int
        Window for liquidity grab swing detection
        
    Returns:
    --------
    pd.DataFrame with all SMC columns:
        - Order Block: ob_bull_*, ob_bear_*, price_at_ob_*
        - FVG: fvg_bull_*, fvg_bear_*, price_in_fvg_*
        - Liquidity Grab: liq_grab_bull, liq_grab_bear, swing_*
        - BOS/CHoCH: bos_bull, bos_bear, choch_bull, choch_bear, trend
        - Confluence: smc_bull_score, smc_bear_score
    """
    # Get Order Blocks
    ob_data = detect_order_blocks_vectorized(
        dataframe, 
        impulse_candles=impulse_candles,
        impulse_pct=impulse_pct,
        lookback=lookback
    )
    
    # Get Fair Value Gaps
    fvg_data = detect_fvg_vectorized(dataframe, lookback=lookback)
    
    # Get Liquidity Grabs
    liq_data = detect_liquidity_grab(dataframe, swing_window=liq_swing_window)
    
    # Get BOS and CHoCH
    bos_data = detect_bos_choch(dataframe, swing_window=swing_window)
    
    # Combine all
    result = pd.concat([ob_data, fvg_data, liq_data, bos_data], axis=1)
    
    # Handle duplicate columns from swing detection
    result = result.loc[:, ~result.columns.duplicated()]
    
    # ==================== SMC CONFLUENCE SCORING ====================
    # Bullish score (higher = stronger signal)
    result['smc_bull_score'] = (
        result['price_at_ob_bull'].fillna(0) * 2 +      # OB = 2 points
        result['price_in_fvg_bull'].fillna(0) * 1 +     # FVG = 1 point
        result['liq_grab_bull'].fillna(0) * 3 +         # Liquidity grab = 3 points
        result['bos_bull'].fillna(0) * 2 +              # BOS = 2 points
        result['choch_bull'].fillna(0) * 3              # CHoCH = 3 points (reversal)
    )
    
    # Bearish score
    result['smc_bear_score'] = (
        result['price_at_ob_bear'].fillna(0) * 2 +
        result['price_in_fvg_bear'].fillna(0) * 1 +
        result['liq_grab_bear'].fillna(0) * 3 +
        result['bos_bear'].fillna(0) * 2 +
        result['choch_bear'].fillna(0) * 3
    )
    
    # Simple confluence flags
    result['smc_bull_confluence'] = (result['smc_bull_score'] >= 2).astype(int)
    result['smc_bear_confluence'] = (result['smc_bear_score'] >= 2).astype(int)
    
    return result


def calculate_smc_score_boost(
    dataframe: pd.DataFrame,
    base_boost: float = 0.05
) -> pd.Series:
    """
    Calculate position sizing boost based on SMC confluence score.
    
    Higher SMC score = larger position (more confluence = higher confidence).
    
    Score breakdown:
    - 0-1: No boost (1.0x)
    - 2-3: Small boost (1.0 + 0.05-0.10)
    - 4-5: Medium boost (1.0 + 0.10-0.15)
    - 6+: Large boost (1.0 + 0.15-0.25)
    
    Parameters:
    -----------
    dataframe : pd.DataFrame
        DataFrame with smc_bull_score and smc_bear_score columns
    base_boost : float
        Boost per score point (default: 5% per point)
    
    Returns:
    --------
    pd.Series with boost multiplier (1.0 to ~1.3)
    """
    boost = pd.Series(1.0, index=dataframe.index)
    
    if 'smc_bull_score' in dataframe.columns:
        bull_score = dataframe['smc_bull_score'].fillna(0).clip(0, 6)
        boost = boost + (bull_score * base_boost)
    
    if 'smc_bear_score' in dataframe.columns:
        bear_score = dataframe['smc_bear_score'].fillna(0).clip(0, 6)
        boost = boost + (bear_score * base_boost)
    
    # Cap at 1.3x maximum boost
    return boost.clip(1.0, 1.3)


