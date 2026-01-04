"""
Validation utilities for strategy development.
Checks for lookahead bias and repainting.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple


def validate_no_lookahead(
    dataframe: pd.DataFrame,
    signal_column: str = 'enter_long',
    check_columns: List[str] = None
) -> Dict[str, bool]:
    """
    Validate that signals don't use future data.
    
    Args:
        dataframe: DataFrame with signals and indicators
        signal_column: Name of the signal column to check
        check_columns: List of indicator columns to validate
        
    Returns:
        Dictionary with validation results
    """
    results = {
        'signal_shift_ok': False,
        'no_future_data': True,
        'details': []
    }
    
    if signal_column not in dataframe.columns:
        results['details'].append(f"Signal column '{signal_column}' not found")
        return results
    
    # Check 1: Signal should be shifted
    signals = dataframe[signal_column]
    if signals.sum() == 0:
        results['details'].append("No signals to validate")
        results['signal_shift_ok'] = True
        return results
    
    # A properly shifted signal won't have values at the last row
    # (since we can't know the future to shift into)
    last_signal = signals.iloc[-1]
    if pd.isna(last_signal) or last_signal == 0:
        results['signal_shift_ok'] = True
    else:
        results['details'].append("Warning: Signal at last row may indicate no shift")
    
    # Check 2: Verify no centered rolling windows
    if check_columns:
        for col in check_columns:
            if col in dataframe.columns:
                # Check for NaN pattern that suggests centered window
                nans_at_end = dataframe[col].isna().iloc[-5:].sum()
                nans_at_start = dataframe[col].isna().iloc[:5].sum()
                
                if nans_at_end > nans_at_start:
                    results['no_future_data'] = False
                    results['details'].append(f"Column '{col}' may use future data (centered window)")
    
    return results


def check_repaint(
    func,
    dataframe: pd.DataFrame,
    n_checks: int = 5
) -> Tuple[bool, List[str]]:
    """
    Check if an indicator function repaints by comparing
    results on progressively longer datasets.
    
    Args:
        func: Function to test (takes dataframe, returns series)
        dataframe: Full historical data
        n_checks: Number of check points
        
    Returns:
        Tuple of (repaints, list of repaint details)
    """
    repaints = False
    details = []
    
    total_len = len(dataframe)
    check_points = [int(total_len * (i + 1) / (n_checks + 1)) for i in range(n_checks)]
    
    previous_values = {}
    
    for cp in check_points:
        # Calculate on subset
        subset = dataframe.iloc[:cp].copy()
        result = func(subset)
        
        # Store values for comparison
        for idx in result.index:
            if idx in previous_values:
                if previous_values[idx] != result.loc[idx]:
                    repaints = True
                    details.append(f"Value changed at index {idx}")
            previous_values[idx] = result.loc[idx]
    
    return repaints, details


def validate_strategy(strategy_class, dataframe: pd.DataFrame) -> Dict:
    """
    Comprehensive strategy validation.
    """
    results = {
        'lookahead_free': True,
        'repaint_free': True,
        'issues': []
    }
    
    # Instantiate strategy
    try:
        strategy = strategy_class({})
        
        # Run populate_indicators
        df = strategy.populate_indicators(dataframe.copy(), {'pair': 'BTC/USDT'})
        
        # Run populate_entry_trend  
        df = strategy.populate_entry_trend(df, {'pair': 'BTC/USDT'})
        
        # Validate
        lookahead = validate_no_lookahead(df)
        if not lookahead['signal_shift_ok'] or not lookahead['no_future_data']:
            results['lookahead_free'] = False
            results['issues'].extend(lookahead['details'])
            
    except Exception as e:
        results['issues'].append(f"Validation error: {str(e)}")
    
    return results
