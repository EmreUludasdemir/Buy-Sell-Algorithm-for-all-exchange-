"""
Efloud-style Range Structure: Range High/Low + Equilibrium (RH/RL/EQ)

Live-safe, non-repainting implementation for Freqtrade strategies.
Provides demand/supply zone detection and equilibrium tracking.
"""

import pandas as pd
from pandas import DataFrame
import pandas_ta as ta


def add_range_levels(
    dataframe: DataFrame,
    lookback: int = 50,
    atr_period: int = 14,
    zone_atr_mult: float = 1.0
) -> DataFrame:
    """
    Add Efloud-style range structure levels to dataframe.
    
    Calculates:
    - RH (Range High): Rolling max high over lookback period
    - RL (Range Low): Rolling min low over lookback period
    - EQ (Equilibrium): Midpoint between RH and RL
    - Demand Zone: Area around RL (RL ± ATR*zone_atr_mult)
    - Supply Zone: Area around RH (RH ± ATR*zone_atr_mult)
    
    Args:
        dataframe: OHLCV dataframe
        lookback: Period for range high/low calculation
        atr_period: Period for ATR calculation
        zone_atr_mult: Multiplier for zone width (ATR-based)
    
    Returns:
        Dataframe with added columns:
        - range_high (RH): Rolling max high
        - range_low (RL): Rolling min low
        - range_eq (EQ): Equilibrium (RH+RL)/2
        - demand_zone_low: Lower bound of demand zone
        - demand_zone_high: Upper bound of demand zone
        - supply_zone_low: Lower bound of supply zone
        - supply_zone_high: Upper bound of supply zone
        - in_demand_zone: Boolean flag if price in demand zone
        - in_supply_zone: Boolean flag if price in supply zone
        - above_eq: Boolean flag if price above equilibrium
        - reclaim_eq: Boolean flag if price reclaimed EQ this candle (non-repainting)
    
    Example:
        >>> df = add_range_levels(df, lookback=50, atr_period=14, zone_atr_mult=1.0)
        >>> # Use in entry logic: if df['in_demand_zone'] & df['reclaim_eq']
    """
    
    # Calculate Range High/Low (live-safe rolling max/min)
    dataframe['range_high'] = dataframe['high'].rolling(window=lookback, min_periods=1).max()
    dataframe['range_low'] = dataframe['low'].rolling(window=lookback, min_periods=1).min()
    
    # Calculate Equilibrium (midpoint)
    dataframe['range_eq'] = (dataframe['range_high'] + dataframe['range_low']) / 2
    
    # Calculate ATR for zone width
    atr = ta.atr(
        high=dataframe['high'],
        low=dataframe['low'],
        close=dataframe['close'],
        length=atr_period
    )
    
    # Define Demand Zone (around Range Low)
    dataframe['demand_zone_low'] = dataframe['range_low'] - (atr * zone_atr_mult)
    dataframe['demand_zone_high'] = dataframe['range_low'] + (atr * zone_atr_mult)
    
    # Define Supply Zone (around Range High)
    dataframe['supply_zone_low'] = dataframe['range_high'] - (atr * zone_atr_mult)
    dataframe['supply_zone_high'] = dataframe['range_high'] + (atr * zone_atr_mult)
    
    # Boolean flags for zone detection (current candle only - live-safe)
    dataframe['in_demand_zone'] = (
        (dataframe['close'] >= dataframe['demand_zone_low']) &
        (dataframe['close'] <= dataframe['demand_zone_high'])
    )
    
    dataframe['in_supply_zone'] = (
        (dataframe['close'] >= dataframe['supply_zone_low']) &
        (dataframe['close'] <= dataframe['supply_zone_high'])
    )
    
    # Above/Below Equilibrium
    dataframe['above_eq'] = dataframe['close'] > dataframe['range_eq']
    dataframe['below_eq'] = dataframe['close'] < dataframe['range_eq']
    
    # Equilibrium Reclaim Detection (non-repainting)
    # True when: current close above EQ AND previous close was below/at previous EQ
    dataframe['reclaim_eq'] = (
        (dataframe['close'] > dataframe['range_eq']) &
        (dataframe['close'].shift(1) <= dataframe['range_eq'].shift(1))
    )
    
    # Equilibrium Lose Detection (for shorts)
    dataframe['lose_eq'] = (
        (dataframe['close'] < dataframe['range_eq']) &
        (dataframe['close'].shift(1) >= dataframe['range_eq'].shift(1))
    )
    
    # Distance from EQ (normalized by ATR for cross-pair comparisons)
    dataframe['eq_distance_atr'] = (dataframe['close'] - dataframe['range_eq']) / atr.fillna(1)
    
    return dataframe


def get_range_boost(
    dataframe: DataFrame,
    in_demand_zone_boost: float = 0.10,
    reclaim_eq_boost: float = 0.05,
    max_boost: float = 0.15
) -> pd.Series:
    """
    Calculate range-based boost multiplier for position sizing.
    
    Returns a Series of boost values (0.0 to max_boost) based on:
    - Price in demand zone
    - Equilibrium reclaim
    
    Args:
        dataframe: Dataframe with range indicators from add_range_levels()
        in_demand_zone_boost: Boost when in demand zone (default 0.10 = +10%)
        reclaim_eq_boost: Boost on EQ reclaim (default 0.05 = +5%)
        max_boost: Maximum total boost cap (default 0.15 = +15%)
    
    Returns:
        Series of boost multipliers (values between 0.0 and max_boost)
    
    Example:
        >>> boost = get_range_boost(df)
        >>> # boost will be 0.10 if in_demand_zone, 0.15 if in_demand_zone + reclaim_eq
    """
    boost = pd.Series(0.0, index=dataframe.index)
    
    # Add boost for being in demand zone
    boost += dataframe['in_demand_zone'].astype(int) * in_demand_zone_boost
    
    # Add boost for EQ reclaim
    boost += dataframe['reclaim_eq'].astype(int) * reclaim_eq_boost
    
    # Cap at max_boost
    boost = boost.clip(upper=max_boost)
    
    return boost
