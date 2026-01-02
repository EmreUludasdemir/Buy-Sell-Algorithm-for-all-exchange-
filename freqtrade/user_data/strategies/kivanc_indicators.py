"""
Kıvanç Özbilgiç Indicators for Freqtrade
==========================================
Popular TradingView indicators by Kıvanç Özbilgiç implemented in Python.

Author: Emre Uludaşdemir
Version: 1.2.0
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
    # Ensure all price columns are pandas Series (not numpy arrays)
    high = pd.Series(dataframe['high'], index=dataframe.index)
    low = pd.Series(dataframe['low'], index=dataframe.index)
    close = pd.Series(dataframe['close'], index=dataframe.index)
    
    # Calculate ATR and ensure it's a pandas Series
    atr = pd.Series(ta.ATR(dataframe, timeperiod=period), index=dataframe.index)
    
    # Calculate basic upper and lower bands (ensure pandas Series)
    hl2 = (high + low) / 2
    basic_ub = pd.Series(hl2 + (multiplier * atr), index=dataframe.index)
    basic_lb = pd.Series(hl2 - (multiplier * atr), index=dataframe.index)
    
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
    # Ensure all price columns are pandas Series (not numpy arrays)
    high = pd.Series(dataframe['high'], index=dataframe.index)
    low = pd.Series(dataframe['low'], index=dataframe.index)
    close = pd.Series(dataframe['close'], index=dataframe.index)
    
    # Calculate ATR for adaptive bands (ensure pandas Series)
    atr = pd.Series(ta.ATR(dataframe, timeperiod=14), index=dataframe.index)
    
    # Rolling high and low (these are already Series from rolling operations)
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
    
    # Smooth RSI with EMA (convert to Series for shift compatibility)
    rsi_ma = pd.Series(ta.EMA(rsi, timeperiod=sf), index=dataframe.index)
    
    # Calculate ATR equivalent for RSI (Wilders smoothing)
    atr_rsi = abs(rsi_ma - rsi_ma.shift(1))
    ma_atr_rsi = pd.Series(ta.EMA(atr_rsi, timeperiod=2*rsi_period - 1), index=dataframe.index)
    
    # Calculate QQE bands
    dar = pd.Series(ta.EMA(ma_atr_rsi, timeperiod=2*rsi_period - 1), index=dataframe.index) * qq_factor
    
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
    
    # MACD calculation (convert to Series for shift compatibility)
    fast_ma = pd.Series(ta.EMA(close, timeperiod=fast_length), index=dataframe.index)
    slow_ma = pd.Series(ta.EMA(close, timeperiod=slow_length), index=dataframe.index)
    macd = fast_ma - slow_ma
    
    # Bollinger Bands
    bb_result = ta.BBANDS(
        close, timeperiod=bb_length, nbdevup=bb_mult, nbdevdn=bb_mult
    )
    bb_upper = pd.Series(bb_result[0], index=dataframe.index)
    bb_middle = pd.Series(bb_result[1], index=dataframe.index)
    bb_lower = pd.Series(bb_result[2], index=dataframe.index)
    
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


def alphatrend(
    dataframe: pd.DataFrame,
    atr_period: int = 14,
    atr_multiplier: float = 1.0,
    mfi_period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    AlphaTrend Indicator by Kıvanç Özbilgiç

    Combines ATR-based bands with MFI direction for trend detection.
    More responsive than traditional trend indicators.

    Logic:
    1. Calculate ATR for volatility measurement
    2. Use MFI (Money Flow Index) for directional bias
    3. Upper band = low - (ATR * multiplier)
    4. Lower band = high + (ATR * multiplier)
    5. If MFI >= 50: AlphaTrend = max(upT, prev_AlphaTrend) [bullish]
    6. If MFI < 50: AlphaTrend = min(downT, prev_AlphaTrend) [bearish]
    7. Trend direction based on price vs AlphaTrend line

    Args:
        dataframe: OHLC dataframe with volume
        atr_period: ATR calculation period (default: 14)
        atr_multiplier: ATR multiplier for bands (default: 1.0)
        mfi_period: MFI calculation period (default: 14)

    Returns:
        Tuple of (alphatrend_line, trend_direction, buy_signal, sell_signal):
        - alphatrend_line: The AlphaTrend line value
        - trend_direction: 1 for bullish, -1 for bearish
        - buy_signal: Boolean series, True on bullish crossover
        - sell_signal: Boolean series, True on bearish crossover
    """
    # Ensure all price columns are pandas Series (not numpy arrays)
    high = pd.Series(dataframe['high'], index=dataframe.index)
    low = pd.Series(dataframe['low'], index=dataframe.index)
    close = pd.Series(dataframe['close'], index=dataframe.index)

    # Calculate ATR (ensure pandas Series)
    atr = pd.Series(ta.ATR(high, low, close, timeperiod=atr_period), index=dataframe.index)

    # Calculate MFI for direction (ensure pandas Series)
    mfi = pd.Series(ta.MFI(high, low, close, dataframe['volume'], timeperiod=mfi_period), index=dataframe.index)

    # Calculate bands (ensure pandas Series)
    upT = pd.Series(low - (atr * atr_multiplier), index=dataframe.index)
    downT = pd.Series(high + (atr * atr_multiplier), index=dataframe.index)

    # AlphaTrend calculation (iterative - requires previous value)
    alphatrend = pd.Series(0.0, index=dataframe.index, dtype=float)

    # Initialize first value as midpoint
    alphatrend.iloc[0] = (upT.iloc[0] + downT.iloc[0]) / 2

    # Calculate AlphaTrend line based on MFI direction
    for i in range(1, len(dataframe)):
        if pd.notna(mfi.iloc[i]) and pd.notna(upT.iloc[i]) and pd.notna(downT.iloc[i]):
            if mfi.iloc[i] >= 50:
                # Bullish: use upper band, keep rising
                alphatrend.iloc[i] = max(upT.iloc[i], alphatrend.iloc[i-1])
            else:
                # Bearish: use lower band, keep falling
                alphatrend.iloc[i] = min(downT.iloc[i], alphatrend.iloc[i-1])
        else:
            # If data not available, carry forward
            alphatrend.iloc[i] = alphatrend.iloc[i-1]

    # Trend direction: 1 if price above AlphaTrend, -1 if below
    trend = pd.Series(0, index=dataframe.index, dtype=int)
    trend = np.where(close > alphatrend, 1, -1)
    trend = pd.Series(trend, index=dataframe.index)

    # Cross signals
    alphatrend_shifted = alphatrend.shift(1)
    close_shifted = close.shift(1)

    # Buy signal: price crosses above AlphaTrend
    buy_signal = (close > alphatrend) & (close_shifted <= alphatrend_shifted)

    # Sell signal: price crosses below AlphaTrend
    sell_signal = (close < alphatrend) & (close_shifted >= alphatrend_shifted)

    return alphatrend, trend, buy_signal, sell_signal


def t3_ma(
    dataframe: pd.DataFrame,
    period: int = 5,
    volume_factor: float = 0.7
) -> Tuple[pd.Series, pd.Series]:
    """
    T3 (Tillson T3) Moving Average
    
    A superior smoothing indicator that combines responsiveness with smoothness.
    Created by Tim Tillson in 1998, T3 uses 6 nested EMAs with a volume factor
    to achieve what traditional MAs cannot: smooth like a long MA, responsive like a short MA.
    
    WHY USE T3:
    - Reduces whipsaws compared to regular EMA (fewer false signals)
    - Reacts faster than long-period MAs (catches trends earlier)
    - Acts as reliable dynamic support/resistance (fewer false breaks)
    - Smooths noise without excessive lag (optimal for trend following)
    
    HOW IT WORKS:
    1. Calculates 6 nested EMAs (e1 through e6)
    2. Applies Tillson's formula with coefficients based on volume_factor
    3. The volume_factor controls smoothness vs responsiveness trade-off
    
    MATHEMATICS:
    e1 = EMA(close, period)
    e2 = EMA(e1, period)
    e3 = EMA(e2, period)
    e4 = EMA(e3, period)
    e5 = EMA(e4, period)
    e6 = EMA(e5, period)
    
    b = volume_factor
    c1 = -b³
    c2 = 3b² + 3b³
    c3 = -6b² - 3b - 3b³
    c4 = 1 + 3b + b³ + 3b²
    
    T3 = c1*e6 + c2*e5 + c3*e4 + c4*e3
    
    TRADING APPLICATIONS:
    - Trend filter: Only long when price > T3
    - Dynamic support: Buy pullbacks to T3 in uptrend
    - Exit signal: Close when price crosses below T3
    - Crossover system: T3(fast) crosses T3(slow)
    
    Args:
        dataframe: OHLCV dataframe
        period: EMA period for each of the 6 layers (default: 5)
                Typical values: 5 (responsive), 8 (balanced), 14 (smooth)
        volume_factor: Responsiveness control, 0.0 to 1.0 (default: 0.7)
                      0.0 = Very smooth but laggy (like DEMA)
                      0.7 = Optimal balance (Tillson's recommendation)
                      1.0 = More responsive but less smooth
    
    Returns:
        Tuple of (t3_line, direction):
        - t3_line: The T3 moving average values
        - direction: 1 for uptrend (price > T3), -1 for downtrend (price < T3)
    
    Version: 1.2.0
    Reference: Tim Tillson (1998), "Better Moving Averages"
    """
    close = dataframe['close']
    
    # Input validation
    if not 0 <= volume_factor <= 1:
        logger.warning(f"volume_factor {volume_factor} out of range [0,1], clamping to valid range")
        volume_factor = max(0.0, min(1.0, volume_factor))
    
    if len(dataframe) < period * 6:
        logger.warning(f"Insufficient data for T3: {len(dataframe)} rows, need ~{period * 6}")
    
    # Calculate Tillson's coefficients based on volume_factor
    b = volume_factor
    b2 = b * b  # b²
    b3 = b2 * b  # b³
    
    c1 = -b3
    c2 = 3 * b2 + 3 * b3
    c3 = -6 * b2 - 3 * b - 3 * b3
    c4 = 1 + 3 * b + b3 + 3 * b2
    
    # Calculate 6 nested EMAs
    # Each EMA smooths the previous one, creating progressively smoother signals
    e1 = pd.Series(ta.EMA(close, timeperiod=period), index=dataframe.index)
    e2 = pd.Series(ta.EMA(e1, timeperiod=period), index=dataframe.index)
    e3 = pd.Series(ta.EMA(e2, timeperiod=period), index=dataframe.index)
    e4 = pd.Series(ta.EMA(e3, timeperiod=period), index=dataframe.index)
    e5 = pd.Series(ta.EMA(e4, timeperiod=period), index=dataframe.index)
    e6 = pd.Series(ta.EMA(e5, timeperiod=period), index=dataframe.index)
    
    # Apply Tillson's formula
    # This weighted combination creates the optimal frequency response
    t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    t3 = pd.Series(t3, index=dataframe.index)
    
    # Calculate trend direction
    # 1 = bullish (price above T3), -1 = bearish (price below T3)
    direction = pd.Series(0, index=dataframe.index, dtype=int)
    direction = np.where(close > t3, 1, -1)
    direction = pd.Series(direction, index=dataframe.index)
    
    return t3, direction


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
