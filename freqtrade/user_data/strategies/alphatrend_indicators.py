"""
AlphaTrend Indicators Module

Core indicators for EPAAlphaTrendV1 strategy:
- AlphaTrend: MFI-gated trend direction (non-repainting)
- Squeeze Momentum: Volatility squeeze + momentum
- WaveTrend: Double-smoothed momentum oscillator
- BB Width Percentile: Volatility regime detection

Author: EPA Trading Bot
"""

import pandas as pd
import numpy as np
import talib.abstract as ta
from typing import Tuple


def alphatrend(
    df: pd.DataFrame,
    period: int = 14,
    coeff: float = 1.0,
    src: str = 'mfi'
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate AlphaTrend indicator.
    
    AlphaTrend uses MFI (or RSI) as a momentum gate to determine trend direction,
    combined with ATR-based bands for dynamic support/resistance.
    
    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume
        period: ATR and MFI calculation period
        coeff: ATR multiplier for bands
        src: Momentum source - 'mfi' or 'rsi'
        
    Returns:
        Tuple of (alphatrend_line, alphatrend_signal) where signal = line.shift(2)
    """
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']
    
    # Calculate ATR using SMA (not RMA for consistency)
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # Calculate momentum source
    if src == 'mfi':
        # Money Flow Index
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        pos_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        neg_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        pos_sum = pos_flow.rolling(window=period).sum()
        neg_sum = neg_flow.rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, np.nan)))
        momentum = mfi.fillna(50)
    else:
        # RSI fallback
        momentum = ta.RSI(df, timeperiod=period)
    
    # Calculate upper and lower bands
    upper_band = low - (atr * coeff)
    lower_band = high + (atr * coeff)
    
    # Initialize AlphaTrend line
    at_line = pd.Series(index=df.index, dtype=float)
    at_line.iloc[:period] = close.iloc[:period]
    
    # Loop required due to self-referencing nature
    for i in range(period, len(df)):
        prev_at = at_line.iloc[i-1]
        
        # Bullish condition: MFI >= 50
        if momentum.iloc[i] >= 50:
            # Use lower band but don't go below previous
            new_at = max(lower_band.iloc[i], prev_at)
        else:
            # Bearish: Use upper band but don't go above previous
            new_at = min(upper_band.iloc[i], prev_at)
        
        at_line.iloc[i] = new_at
    
    # Signal line is shifted AlphaTrend
    at_signal = at_line.shift(2)
    
    return at_line, at_signal


def squeeze_momentum(
    df: pd.DataFrame,
    bb_length: int = 20,
    bb_mult: float = 2.0,
    kc_length: int = 20,
    kc_mult: float = 1.5,
    mom_length: int = 12
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Squeeze Momentum indicator (LazyBear style).
    
    Detects when Bollinger Bands are inside Keltner Channels (squeeze),
    and measures momentum using linear regression.
    
    Args:
        df: OHLCV DataFrame
        bb_length: Bollinger Band period
        bb_mult: Bollinger Band std dev multiplier
        kc_length: Keltner Channel period
        kc_mult: Keltner Channel ATR multiplier
        mom_length: Momentum calculation period
        
    Returns:
        Tuple of (momentum_value, squeeze_on boolean)
    """
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Bollinger Bands
    bb_basis = close.rolling(window=bb_length).mean()
    bb_dev = close.rolling(window=bb_length).std() * bb_mult
    bb_upper = bb_basis + bb_dev
    bb_lower = bb_basis - bb_dev
    
    # Keltner Channels (using ATR)
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=kc_length).mean()
    
    kc_basis = close.rolling(window=kc_length).mean()
    kc_upper = kc_basis + atr * kc_mult
    kc_lower = kc_basis - atr * kc_mult
    
    # Squeeze detection: BB inside KC
    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    
    # Momentum using linear regression
    # Simplified: using the difference from midline
    highest = high.rolling(window=kc_length).max()
    lowest = low.rolling(window=kc_length).min()
    avg_hl = (highest + lowest) / 2
    avg_close = close.rolling(window=kc_length).mean()
    
    # Momentum value
    momentum = close - (avg_hl + avg_close) / 2
    
    # Smooth momentum with linear regression (simplified)
    momentum = momentum.rolling(window=mom_length).mean()
    
    return momentum, squeeze_on


def wavetrend(
    df: pd.DataFrame,
    channel_length: int = 10,
    average_length: int = 21
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate WaveTrend oscillator.
    
    Double-smoothed momentum oscillator useful for divergence and
    overbought/oversold conditions.
    
    Args:
        df: OHLCV DataFrame
        channel_length: First EMA period
        average_length: Signal line EMA period
        
    Returns:
        Tuple of (wt1, wt2) where wt2 is signal line
    """
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    
    # First EMA
    esa = hlc3.ewm(span=channel_length, adjust=False).mean()
    
    # Difference from EMA
    d = abs(hlc3 - esa).ewm(span=channel_length, adjust=False).mean()
    
    # CI calculation (Channel Index)
    ci = (hlc3 - esa) / (0.015 * d)
    ci = ci.replace([np.inf, -np.inf], 0).fillna(0)
    
    # WaveTrend lines
    wt1 = ci.ewm(span=average_length, adjust=False).mean()
    wt2 = wt1.rolling(window=4).mean()
    
    return wt1, wt2


def bb_width_percentile(
    df: pd.DataFrame,
    length: int = 20,
    lookback: int = 100
) -> pd.Series:
    """
    Calculate Bollinger Band width as percentile of recent history.
    
    Useful for volatility regime detection:
    - Low percentile (< 25): Squeeze/low volatility
    - High percentile (> 75): High volatility/trend
    
    Args:
        df: OHLCV DataFrame
        length: BB calculation period
        lookback: Percentile lookback period
        
    Returns:
        Series of percentile values (0-100)
    """
    close = df['close']
    
    # Calculate BB width
    bb_basis = close.rolling(window=length).mean()
    bb_dev = close.rolling(window=length).std() * 2
    bb_upper = bb_basis + bb_dev
    bb_lower = bb_basis - bb_dev
    
    bb_width = (bb_upper - bb_lower) / bb_basis * 100
    
    # Calculate percentile rank over lookback
    def percentile_rank(x):
        if len(x) < 2:
            return 50
        return (x.rank().iloc[-1] - 1) / (len(x) - 1) * 100
    
    percentile = bb_width.rolling(window=lookback).apply(percentile_rank, raw=False)
    
    return percentile.fillna(50)


def choppiness_index(
    df: pd.DataFrame,
    period: int = 14
) -> pd.Series:
    """
    Calculate Choppiness Index.
    
    Measures whether market is trending or ranging:
    - < 38.2: Trending
    - > 61.8: Ranging/Choppy
    - 38.2-61.8: Transitional
    
    Args:
        df: OHLCV DataFrame
        period: Calculation period
        
    Returns:
        Series of choppiness values (0-100)
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    
    # ATR sum
    atr_sum = tr.rolling(window=period).sum()
    
    # High-Low range
    high_low_range = (
        high.rolling(period).max() - 
        low.rolling(period).min()
    )
    high_low_range = high_low_range.replace(0, np.nan)
    
    # Choppiness calculation
    chop = 100 * np.log10(atr_sum / high_low_range) / np.log10(period)
    
    return chop.fillna(50)


def ut_bot_trailing(
    df: pd.DataFrame,
    sensitivity: float = 1.5,
    atr_period: int = 10
) -> Tuple[pd.Series, pd.Series]:
    """
    UT Bot trailing stop indicator.
    
    ATR-based trailing stop with EMA confirmation.
    
    Args:
        df: OHLCV DataFrame
        sensitivity: ATR multiplier for stop distance
        atr_period: ATR calculation period
        
    Returns:
        Tuple of (buy_signal, sell_signal) boolean series
    """
    close = df['close']
    high = df['high']
    low = df['low']
    
    # ATR calculation
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period).mean()
    
    # EMA
    ema = close.ewm(span=1, adjust=False).mean()  # Very fast EMA
    
    # Trail calculation
    trail = pd.Series(index=df.index, dtype=float)
    trail.iloc[0] = close.iloc[0]
    
    for i in range(1, len(df)):
        prev_trail = trail.iloc[i-1]
        current_close = close.iloc[i]
        current_atr = atr.iloc[i] if pd.notna(atr.iloc[i]) else 0
        
        n_loss = current_atr * sensitivity
        
        # Update trail
        if current_close > prev_trail:
            trail.iloc[i] = max(prev_trail, current_close - n_loss)
        else:
            trail.iloc[i] = min(prev_trail, current_close + n_loss)
    
    # Buy/Sell signals
    buy_signal = (close > trail) & (close.shift(1) <= trail.shift(1))
    sell_signal = (close < trail) & (close.shift(1) >= trail.shift(1))
    
    return buy_signal, sell_signal


# Convenience function to add all indicators to dataframe
def add_alphatrend_indicators(
    df: pd.DataFrame,
    at_period: int = 14,
    at_coeff: float = 1.0,
    squeeze_length: int = 20,
    wt_channel: int = 10,
    wt_average: int = 21
) -> pd.DataFrame:
    """
    Add all AlphaTrend-related indicators to dataframe.
    
    Args:
        df: OHLCV DataFrame
        at_period: AlphaTrend period
        at_coeff: AlphaTrend ATR coefficient
        squeeze_length: Squeeze Momentum BB/KC length
        wt_channel: WaveTrend channel length
        wt_average: WaveTrend average length
        
    Returns:
        DataFrame with added indicator columns
    """
    df = df.copy()
    
    # AlphaTrend
    df['alphatrend'], df['alphatrend_signal'] = alphatrend(df, at_period, at_coeff)
    
    # Squeeze Momentum
    df['squeeze_momentum'], df['squeeze_on'] = squeeze_momentum(df, squeeze_length)
    
    # WaveTrend
    df['wavetrend_1'], df['wavetrend_2'] = wavetrend(df, wt_channel, wt_average)
    
    # BB Width Percentile
    df['bb_width_pct'] = bb_width_percentile(df)
    
    # Choppiness Index
    df['choppiness'] = choppiness_index(df)
    
    return df
