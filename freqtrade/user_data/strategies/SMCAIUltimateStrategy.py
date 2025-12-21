"""
SMC + AI Ultimate Strategy
==========================
Advanced Freqtrade strategy combining:
- Smart Money Concepts (Order Blocks, FVG, BOS/CHOCH)
- FinBERT Sentiment Analysis (GPU accelerated)
- LSTM Price Prediction
- Multi-timeframe confirmation
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import requests

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

# Import SMC indicators
from smc_indicators import (
    calculate_swing_highs_lows,
    calculate_bos_choch,
    calculate_order_blocks,
    calculate_fvg,
    calculate_liquidity,
)

logger = logging.getLogger(__name__)


class SMCAIUltimateStrategy(IStrategy):
    """
    Ultimate Trading Strategy combining SMC + AI
    
    This is the most advanced strategy combining:
    1. Smart Money Concepts (institutional trading patterns)
    2. FinBERT sentiment analysis (news-based signals)
    3. LSTM price prediction (ML-based forecasting)
    4. Technical confirmation (EMA, RSI, Volume)
    
    Signal weights:
    - SMC Patterns: 35%
    - AI Sentiment: 25%
    - AI LSTM: 25%
    - Technical: 15%
    """
    
    INTERFACE_VERSION = 3
    
    # Strategy settings
    timeframe = '15m'
    can_short = False
    
    # ROI targets
    minimal_roi = {
        "0": 0.06,      # 6% initial
        "30": 0.04,     # 4% after 30 mins
        "60": 0.025,    # 2.5% after 1 hour
        "120": 0.015,   # 1.5% after 2 hours
    }
    
    # Stop loss
    stoploss = -0.025  # 2.5%
    
    # Trailing
    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    # Settings
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 100
    
    # AI Service URL
    AI_SERVICE_URL = "http://host.docker.internal:5555"
    
    # Hyperopt parameters
    swing_length = IntParameter(5, 20, default=10, space='buy', optimize=True)
    ai_weight = DecimalParameter(0.3, 0.6, default=0.5, space='buy', optimize=True)
    min_confidence = DecimalParameter(0.3, 0.7, default=0.4, space='buy', optimize=True)
    
    # Cache for AI signals
    _ai_cache: Dict[str, Any] = {}
    _cache_timeout = 300  # 5 minutes
    
    def informative_pairs(self):
        """Add higher timeframes for trend confirmation."""
        pairs = self.dp.current_whitelist()
        return [(pair, '1h') for pair in pairs] + [(pair, '4h') for pair in pairs]
    
    def _get_ai_signal(self, pair: str, dataframe: DataFrame) -> Dict[str, Any]:
        """Get AI signal from the service."""
        cache_key = f"{pair}_{dataframe.index[-1]}"
        
        # Check cache
        if cache_key in self._ai_cache:
            cached = self._ai_cache[cache_key]
            if (datetime.now() - cached['time']).seconds < self._cache_timeout:
                return cached['signal']
        
        try:
            # Prepare price data
            price_data = {
                "open": dataframe['open'].tail(50).tolist(),
                "high": dataframe['high'].tail(50).tolist(),
                "low": dataframe['low'].tail(50).tolist(),
                "close": dataframe['close'].tail(50).tolist(),
                "volume": dataframe['volume'].tail(50).tolist(),
            }
            
            # Call AI service
            response = requests.post(
                f"{self.AI_SERVICE_URL}/signal",
                json={
                    "symbol": pair.split('/')[0],  # BTC/USDT -> BTC
                    "price_data": price_data,
                    "include_sentiment": True,
                    "include_lstm": True
                },
                timeout=5
            )
            
            if response.status_code == 200:
                signal = response.json()
                
                # Cache the result
                self._ai_cache[cache_key] = {
                    'time': datetime.now(),
                    'signal': signal
                }
                
                logger.info(f"AI Signal for {pair}: {signal['ai_signal']} (score: {signal['ai_score']})")
                return signal
            else:
                logger.warning(f"AI service returned {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"AI service not available: {e}")
        except Exception as e:
            logger.error(f"Error getting AI signal: {e}")
        
        # Return neutral signal if service unavailable
        return {
            "ai_score": 0,
            "ai_signal": "hold",
            "confidence": 0,
            "sentiment_direction": "neutral",
            "lstm_direction": "neutral"
        }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate all indicators."""
        pair = metadata['pair']
        
        # ═══════════════════════════════════════════════════════════
        #                    TECHNICAL INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        # Trend EMAs
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ATR for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close'] * 100
        
        # Volume
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        
        # ═══════════════════════════════════════════════════════════
        #                    SMC INDICATORS
        # ═══════════════════════════════════════════════════════════
        
        swing_len = self.swing_length.value
        
        # Swing points
        swings = calculate_swing_highs_lows(dataframe, swing_len)
        dataframe['swing_hl'] = swings['HighLow']
        dataframe['swing_level'] = swings['Level']
        
        # Market structure
        structure = calculate_bos_choch(dataframe, swings)
        dataframe['bos'] = structure['BOS']
        dataframe['choch'] = structure['CHOCH']
        
        # Order Blocks
        obs = calculate_order_blocks(dataframe, swings)
        dataframe['ob'] = obs['OB']
        dataframe['ob_top'] = obs['Top']
        dataframe['ob_bottom'] = obs['Bottom']
        
        # Fair Value Gaps
        fvg = calculate_fvg(dataframe)
        dataframe['fvg'] = fvg['FVG']
        dataframe['fvg_top'] = fvg['Top']
        dataframe['fvg_bottom'] = fvg['Bottom']
        
        # Liquidity
        liq = calculate_liquidity(dataframe, swings)
        dataframe['liquidity'] = liq['Liquidity']
        dataframe['liquidity_swept'] = liq['Swept']
        
        # ═══════════════════════════════════════════════════════════
        #                    DERIVED SIGNALS
        # ═══════════════════════════════════════════════════════════
        
        # Trend determination
        dataframe['trend'] = np.where(
            (dataframe['ema_9'] > dataframe['ema_21']) & 
            (dataframe['ema_21'] > dataframe['ema_50']),
            1,  # Bullish
            np.where(
                (dataframe['ema_9'] < dataframe['ema_21']) & 
                (dataframe['ema_21'] < dataframe['ema_50']),
                -1,  # Bearish
                0    # Neutral
            )
        )
        
        # Recent structure breaks - fixed for pandas compatibility
        lookback = 15
        
        # Create boolean masks first, then combine
        bos_bullish = (dataframe['bos'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        choch_bullish = (dataframe['choch'] == 1).rolling(lookback, min_periods=1).max().fillna(0)
        dataframe['recent_bullish_structure'] = ((bos_bullish > 0) | (choch_bullish > 0)).astype(int)
        
        bos_bearish = (dataframe['bos'] == -1).rolling(lookback, min_periods=1).max().fillna(0)
        choch_bearish = (dataframe['choch'] == -1).rolling(lookback, min_periods=1).max().fillna(0)
        dataframe['recent_bearish_structure'] = ((bos_bearish > 0) | (choch_bearish > 0)).astype(int)
        
        # Price in Order Block
        dataframe['in_bullish_ob'] = (
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['ob'].ffill() == 1)
        ).astype(int)
        
        dataframe['in_bearish_ob'] = (
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['ob'].ffill() == -1)
        ).astype(int)
        
        # SMC Score (-100 to +100)
        dataframe['smc_score'] = (
            dataframe['recent_bullish_structure'] * 30 -
            dataframe['recent_bearish_structure'] * 30 +
            dataframe['in_bullish_ob'] * 25 -
            dataframe['in_bearish_ob'] * 25 +
            (dataframe['fvg'] == 1).astype(int) * 15 -
            (dataframe['fvg'] == -1).astype(int) * 15 +
            dataframe['trend'] * 10
        )
        
        # Technical Score (-100 to +100)
        dataframe['tech_score'] = (
            np.where(dataframe['rsi'] < 30, 20, np.where(dataframe['rsi'] > 70, -20, 0)) +
            np.where(dataframe['macdhist'] > 0, 15, -15) +
            np.where(dataframe['close'] > dataframe['ema_50'], 15, -15) +
            np.where(dataframe['volume_ratio'] > 1.2, 10, 0) +
            dataframe['trend'] * 20
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Entry conditions combining SMC + AI + Technical."""
        pair = metadata['pair']
        
        # Get AI signal for the last candle
        ai_signal = self._get_ai_signal(pair, dataframe)
        ai_score = ai_signal.get('ai_score', 0)
        ai_confidence = ai_signal.get('confidence', 0)
        
        # Store AI scores in dataframe for backtesting
        dataframe['ai_score'] = ai_score
        dataframe['ai_confidence'] = ai_confidence
        
        # Calculate combined score
        # SMC: 35%, AI: 50% (25% sentiment + 25% LSTM), Technical: 15%
        ai_weight = self.ai_weight.value
        smc_weight = 0.35
        tech_weight = 1 - ai_weight - smc_weight
        
        dataframe['combined_score'] = (
            dataframe['smc_score'] * smc_weight +
            ai_score * ai_weight +
            dataframe['tech_score'] * tech_weight
        )
        
        # Entry conditions
        min_conf = self.min_confidence.value
        
        dataframe.loc[
            (
                # Combined score threshold
                (dataframe['combined_score'] > 25) &
                
                # SMC confirmation
                (
                    (dataframe['recent_bullish_structure'] == 1) |
                    (dataframe['in_bullish_ob'] == 1) |
                    (dataframe['fvg'] == 1)
                ) &
                
                # Trend filter
                (dataframe['trend'] >= 0) &
                
                # Technical filters
                (dataframe['rsi'] < 70) &
                (dataframe['volume_ratio'] > 0.7) &
                
                # AI confidence (when available)
                ((ai_confidence >= min_conf) | (ai_confidence == 0)) &
                
                # Valid data
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit conditions."""
        
        # Get AI signal
        ai_signal = self._get_ai_signal(metadata['pair'], dataframe)
        ai_score = ai_signal.get('ai_score', 0)
        
        dataframe.loc[
            (
                # Bearish structure break
                (dataframe['choch'] == -1) |
                
                # Strong bearish AI signal
                (ai_score < -30) |
                
                # Technical exit
                (
                    (dataframe['rsi'] > 75) &
                    (dataframe['close'] > dataframe['bb_upper'])
                ) |
                
                # Trend reversal
                (
                    (dataframe['trend'] == -1) &
                    (dataframe['macdhist'] < 0)
                )
            ),
            'exit_long'
        ] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """Dynamic stop loss based on ATR and Order Blocks."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
        
        last_candle = dataframe.iloc[-1]
        atr = last_candle['atr']
        
        # Use Order Block bottom as stop if available
        ob_bottom = last_candle.get('ob_bottom')
        if pd.notna(ob_bottom) and ob_bottom > 0:
            ob_stop = (ob_bottom / current_rate) - 1
            if ob_stop > -0.05:  # Don't set stop more than 5% away
                return ob_stop
        
        # Default: ATR-based stop
        stop_price = trade.open_rate - (atr * 2)
        return (stop_price / current_rate) - 1
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float,
                    after_fill: bool, **kwargs) -> Optional[str]:
        """Custom exit logic."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
        
        last_candle = dataframe.iloc[-1]
        
        # Exit on CHOCH
        if last_candle['choch'] == -1:
            logger.info(f"Exiting {pair}: Bearish CHOCH detected")
            return 'smc_choch_exit'
        
        # Exit on strong bearish AI signal
        if self._ai_cache.get(f"{pair}_{dataframe.index[-1]}", {}).get('signal', {}).get('ai_score', 0) < -40:
            logger.info(f"Exiting {pair}: Strong bearish AI signal")
            return 'ai_bearish_exit'
        
        return None
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                            rate: float, time_in_force: str, current_time: datetime,
                            entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """Final trade confirmation using AI."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return True
        
        # Get fresh AI signal
        ai_signal = self._get_ai_signal(pair, dataframe)
        
        # Block entry if AI is strongly bearish
        if ai_signal.get('ai_signal') in ['strong_sell', 'sell']:
            logger.info(f"Blocking entry for {pair}: AI signal is {ai_signal['ai_signal']}")
            return False
        
        return True
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """No leverage for spot trading."""
        return 1.0
