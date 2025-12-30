"""
Kıvanç Özbilgiç Indicators for Freqtrade
==========================================
Popular TradingView indicators by Kıvanç Özbilgiç implemented in Python.

Author: Emre Uludaşdemir
Version: 1.0.0
"""

import numpy as np
import pandas as pd
import talib.abstract as ta
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def supertrend(
    dataframe: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0
) -> Tuple[pd.Series, pd.Series]:
    """
    Supertrend Indicator - Kıvanç Özbilgiç style
    
    Uses ATR for dynamic band calculation to identify trend direction.
    
    Args:
        dataframe: OHLC dataframe
        period: ATR period (default: 10)
        multiplier: ATR multiplier for bands (default: 3.0)
    
    Returns:
        Tuple of (supertrend_direction, supertrend_line):
        - direction: 1 for bullish, -1 for bearish
        - line: The supertrend line value
    """
    high = dataframe['high']
    low = dataframe['low']
    close = dataframe['close']
    
    # Calculate ATR
    atr = ta.ATR(dataframe, timeperiod=period)
    
    # Calculate basic upper and lower bands
    hl2 = (high + low) / 2
    basic_ub = hl2 + (multiplier * atr)
    basic_lb = hl2 - (multiplier * atr)
    
    # Initialize bands
    final_ub = pd.Series(0.0, index=dataframe.index)
    final_lb = pd.Series(0.0, index=dataframe.index)
    supertrend = pd.Series(0.0, index=dataframe.index)
    direction = pd.Series(1, index=dataframe.index)
    
    # Calculate final bands
    # Note: Loop-based approach for compatibility with Supertrend logic
    # Could be vectorized for better performance on very large datasets
    for i in range(period, len(dataframe)):
        # Upper band
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
        
        # Lower band
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
        
        # Supertrend direction
        if supertrend.iloc[i-1] == final_ub.iloc[i-1] and close.iloc[i] <= final_ub.iloc[i]:
            supertrend.iloc[i] = final_ub.iloc[i]
            direction.iloc[i] = -1
        elif supertrend.iloc[i-1] == final_ub.iloc[i-1] and close.iloc[i] > final_ub.iloc[i]:
            supertrend.iloc[i] = final_lb.iloc[i]
            direction.iloc[i] = 1
        elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and close.iloc[i] >= final_lb.iloc[i]:
            supertrend.iloc[i] = final_lb.iloc[i]
            direction.iloc[i] = 1
        elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and close.iloc[i] < final_lb.iloc[i]:
            supertrend.iloc[i] = final_ub.iloc[i]
            direction.iloc[i] = -1
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]
    
    return direction, supertrend


def halftrend(
    dataframe: pd.DataFrame,
    amplitude: int = 2,
    channel_deviation: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Half Trend Indicator
    
    Smooth trend detection indicator with less whipsaw than traditional moving averages.
    Provides clear trend direction with ATR-based channels.
    
    Args:
        dataframe: OHLC dataframe
        amplitude: Lookback period for high/low (default: 2)
        channel_deviation: ATR multiplier for channel width (default: 2.0)
    
    Returns:
        Tuple of (direction, halftrend_up, halftrend_down):
        - direction: 1 for bullish, -1 for bearish
        - halftrend_up: Upper trend line value
        - halftrend_down: Lower trend line value
    """
    high = dataframe['high']
    low = dataframe['low']
    close = dataframe['close']
    
    # Calculate ATR for adaptive bands
    atr = ta.ATR(dataframe, timeperiod=14)
    
    # Rolling high and low
    highma = high.rolling(window=amplitude).max()
    lowma = low.rolling(window=amplitude).min()
    
    # Initialize arrays
    trend = pd.Series(0, index=dataframe.index, dtype=int)
    nexttrend = pd.Series(0, index=dataframe.index, dtype=int)
    maxlowprice = pd.Series(low.iloc[0], index=dataframe.index)
    minhighprice = pd.Series(high.iloc[0], index=dataframe.index)
    halftrend_up = pd.Series(0.0, index=dataframe.index)
    halftrend_down = pd.Series(0.0, index=dataframe.index)
    atrHigh = pd.Series(0.0, index=dataframe.index)
    atrLow = pd.Series(0.0, index=dataframe.index)
    
    # Calculate trend
    # Note: Loop-based for clarity and correctness with state transitions
    # Performance is acceptable for typical Freqtrade usage (< 5000 candles)
    for i in range(amplitude, len(dataframe)):
        # Calculate deviation bands
        atrHigh.iloc[i] = high.iloc[i] - atr.iloc[i] * channel_deviation
        atrLow.iloc[i] = low.iloc[i] + atr.iloc[i] * channel_deviation
        
        # Determine trend
        if nexttrend.iloc[i-1] == 1:
            maxlowprice.iloc[i] = max(lowma.iloc[i], maxlowprice.iloc[i-1])
            
            if atrHigh.iloc[i] < maxlowprice.iloc[i]:
                trend.iloc[i] = 1
                nexttrend.iloc[i] = 0
                minhighprice.iloc[i] = highma.iloc[i]
            else:
                trend.iloc[i] = 0
                nexttrend.iloc[i] = 1
                maxlowprice.iloc[i] = maxlowprice.iloc[i-1]
        else:
            minhighprice.iloc[i] = min(highma.iloc[i], minhighprice.iloc[i-1])
            
            if atrLow.iloc[i] > minhighprice.iloc[i]:
                trend.iloc[i] = 0
                nexttrend.iloc[i] = 1
                maxlowprice.iloc[i] = lowma.iloc[i]
            else:
                trend.iloc[i] = 1
                nexttrend.iloc[i] = 0
                minhighprice.iloc[i] = minhighprice.iloc[i-1]
        
        # Set trend lines
        if trend.iloc[i] == 0:
            halftrend_up.iloc[i] = maxlowprice.iloc[i]
            halftrend_down.iloc[i] = 0
        else:
            halftrend_up.iloc[i] = 0
            halftrend_down.iloc[i] = minhighprice.iloc[i]
    
    # Direction: 1 for uptrend, -1 for downtrend
    direction = pd.Series(0, index=dataframe.index)
    direction = np.where(trend == 0, 1, -1)
    
    return pd.Series(direction, index=dataframe.index), halftrend_up, halftrend_down


def qqe(
    dataframe: pd.DataFrame,
    rsi_period: int = 14,
    sf: int = 5,
    qq_factor: float = 4.238
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    QQE (Quantitative Qualitative Estimation)
    
    RSI-based trend filter with smoothed RSI and dynamic bands.
    Excellent for trend confirmation.
    
    Args:
        dataframe: OHLC dataframe
        rsi_period: RSI period (default: 14)
        sf: Smoothing factor (default: 5)
        qq_factor: QQE factor for bands (default: 4.238)
    
    Returns:
        Tuple of (qqe_trend, rsi_ma, qqe_line):
        - qqe_trend: 1 for bullish, -1 for bearish
        - rsi_ma: Smoothed RSI
        - qqe_line: QQE fast line
    """
    close = dataframe['close']
    
    # Calculate RSI
    rsi = ta.RSI(dataframe, timeperiod=rsi_period)
    
    # Smooth RSI with EMA
    rsi_ma = ta.EMA(rsi, timeperiod=sf)
    
    # Calculate ATR equivalent for RSI (Wilders smoothing)
    atr_rsi = abs(rsi_ma - rsi_ma.shift(1))
    ma_atr_rsi = ta.EMA(atr_rsi, timeperiod=2*rsi_period - 1)
    
    # Calculate QQE bands
    dar = ta.EMA(ma_atr_rsi, timeperiod=2*rsi_period - 1) * qq_factor
    
    # Initialize QQE line and trend
    long_band = pd.Series(0.0, index=dataframe.index)
    short_band = pd.Series(0.0, index=dataframe.index)
    trend = pd.Series(1, index=dataframe.index)
    qqe_line = pd.Series(50.0, index=dataframe.index)
    
    # Calculate QQE bands and trend
    # Note: Stateful calculation requires loop for correctness
    for i in range(sf, len(dataframe)):
        # Calculate bands
        dv = dar.iloc[i]
        
        # Upper and lower bands
        long_level = rsi_ma.iloc[i] - dv
        short_level = rsi_ma.iloc[i] + dv
        
        # Update bands based on trend
        if rsi_ma.iloc[i-1] > long_band.iloc[i-1]:
            long_band.iloc[i] = max(long_level, long_band.iloc[i-1])
        else:
            long_band.iloc[i] = long_level
        
        if rsi_ma.iloc[i-1] < short_band.iloc[i-1]:
            short_band.iloc[i] = min(short_level, short_band.iloc[i-1])
        else:
            short_band.iloc[i] = short_level
        
        # Determine trend
        if rsi_ma.iloc[i] > short_band.iloc[i]:
            trend.iloc[i] = 1
            qqe_line.iloc[i] = long_band.iloc[i]
        elif rsi_ma.iloc[i] < long_band.iloc[i]:
            trend.iloc[i] = -1
            qqe_line.iloc[i] = short_band.iloc[i]
        else:
            trend.iloc[i] = trend.iloc[i-1]
            qqe_line.iloc[i] = long_band.iloc[i] if trend.iloc[i] == 1 else short_band.iloc[i]
    
    return trend, rsi_ma, qqe_line


def waddah_attar_explosion(
    dataframe: pd.DataFrame,
    sensitivity: int = 150,
    fast_length: int = 20,
    slow_length: int = 40,
    bb_length: int = 20,
    bb_mult: float = 2.0
) -> pd.DataFrame:
    """
    Waddah Attar Explosion
    
    Volatility and momentum indicator that shows explosion (high volatility) vs dead zone.
    Useful for timing entries during high momentum periods.
    
    Args:
        dataframe: OHLC dataframe
        sensitivity: Sensitivity multiplier (default: 150)
        fast_length: Fast MACD length (default: 20)
        slow_length: Slow MACD length (default: 40)
        bb_length: Bollinger Band length (default: 20)
        bb_mult: Bollinger Band multiplier (default: 2.0)
    
    Returns:
        DataFrame with columns:
        - wae_trend_up: Uptrend explosion value
        - wae_trend_down: Downtrend explosion value
        - wae_explosion_line: Dead zone threshold
        - wae_signal: 1 for bullish explosion, -1 for bearish explosion, 0 for dead zone
    """
    close = dataframe['close']
    
    # MACD calculation
    fast_ma = ta.EMA(close, timeperiod=fast_length)
    slow_ma = ta.EMA(close, timeperiod=slow_length)
    macd = fast_ma - slow_ma
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = ta.BBANDS(
        close, timeperiod=bb_length, nbdevup=bb_mult, nbdevdn=bb_mult
    )
    
    # Dead zone (BB width normalized)
    bb_range = bb_upper - bb_lower
    
    # Calculate trend and explosion
    t1 = (macd - macd.shift(1)) * sensitivity
    explosion_line = bb_range
    
    # Result dataframe
    result = pd.DataFrame(index=dataframe.index)
    
    # Separate trend up and trend down
    result['wae_trend_up'] = np.where(t1 >= 0, t1, 0)
    result['wae_trend_down'] = np.where(t1 < 0, abs(t1), 0)
    result['wae_explosion_line'] = explosion_line
    
    # Signal: 1 for bullish explosion, -1 for bearish, 0 for dead zone
    result['wae_signal'] = np.where(
        t1 > explosion_line, 1,
        np.where(t1 < -explosion_line, -1, 0)
    )
    
    # Additional helper columns
    result['wae_in_explosion'] = (
        (result['wae_trend_up'] > result['wae_explosion_line']) |
        (result['wae_trend_down'] > result['wae_explosion_line'])
    ).astype(int)
    
    return result


def add_kivanc_indicators(
    dataframe: pd.DataFrame,
    supertrend_period: int = 10,
    supertrend_multiplier: float = 3.0,
    halftrend_amplitude: int = 2,
    halftrend_deviation: float = 2.0,
    qqe_rsi_period: int = 14,
    qqe_sf: int = 5,
    qqe_factor: float = 4.238,
    wae_sensitivity: int = 150,
    wae_fast: int = 20,
    wae_slow: int = 40
) -> pd.DataFrame:
    """
    Convenience function to add all Kıvanç indicators to a dataframe.
    
    Args:
        dataframe: OHLC dataframe
        supertrend_period: Supertrend ATR period
        supertrend_multiplier: Supertrend ATR multiplier
        halftrend_amplitude: Half Trend amplitude
        halftrend_deviation: Half Trend channel deviation
        qqe_rsi_period: QQE RSI period
        qqe_sf: QQE smoothing factor
        qqe_factor: QQE factor
        wae_sensitivity: WAE sensitivity
        wae_fast: WAE fast MA length
        wae_slow: WAE slow MA length
    
    Returns:
        DataFrame with all Kıvanç indicators added
    """
    df = dataframe.copy()
    
    # Supertrend
    st_direction, st_line = supertrend(
        df, period=supertrend_period, multiplier=supertrend_multiplier
    )
    df['supertrend_direction'] = st_direction
    df['supertrend_line'] = st_line
    
    # Half Trend
    ht_direction, ht_up, ht_down = halftrend(
        df, amplitude=halftrend_amplitude, channel_deviation=halftrend_deviation
    )
    df['halftrend_direction'] = ht_direction
    df['halftrend_up'] = ht_up
    df['halftrend_down'] = ht_down
    
    # QQE
    qqe_trend, rsi_ma, qqe_line = qqe(
        df, rsi_period=qqe_rsi_period, sf=qqe_sf, qq_factor=qqe_factor
    )
    df['qqe_trend'] = qqe_trend
    df['qqe_rsi_ma'] = rsi_ma
    df['qqe_line'] = qqe_line
    
    # Waddah Attar Explosion
    wae_data = waddah_attar_explosion(
        df, sensitivity=wae_sensitivity, fast_length=wae_fast, slow_length=wae_slow
    )
    df['wae_trend_up'] = wae_data['wae_trend_up']
    df['wae_trend_down'] = wae_data['wae_trend_down']
    df['wae_explosion_line'] = wae_data['wae_explosion_line']
    df['wae_signal'] = wae_data['wae_signal']
    df['wae_in_explosion'] = wae_data['wae_in_explosion']
    
    return df
