"""
Signal Generator
================
Ensemble signal generation combining all analysis components.
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from ..config import Config, get_config
from ..data.fetcher import DataFetcher
from ..data.news_aggregator import NewsAggregator
from ..analysis.indicators import TechnicalIndicators
from ..analysis.patterns import PatternRecognition
from ..analysis.multi_timeframe import MultiTimeframeAnalyzer
from ..ai.sentiment_analyzer import FinBERTSentimentAnalyzer, SimpleSentimentAnalyzer
from ..ai.price_predictor import LSTMPricePredictor
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Signal strength levels."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class SignalDirection(Enum):
    """Signal direction."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradingSignal:
    """Complete trading signal with all analysis data."""
    ticker: str
    timestamp: str
    
    # Signal
    direction: SignalDirection
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    
    # Individual scores (each -100 to +100)
    technical_score: float
    pattern_score: float
    sentiment_score: float
    ai_score: float
    mtf_score: float
    
    # Combined score
    ensemble_score: float  # -100 to +100
    
    # Risk management
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    position_size_pct: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Supporting data
    key_levels: Dict[str, float] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "signal": {
                "direction": self.direction.value,
                "strength": self.strength.value,
                "confidence": round(self.confidence, 3),
            },
            "scores": {
                "technical": round(self.technical_score, 1),
                "pattern": round(self.pattern_score, 1),
                "sentiment": round(self.sentiment_score, 1),
                "ai_prediction": round(self.ai_score, 1),
                "multi_timeframe": round(self.mtf_score, 1),
                "ensemble": round(self.ensemble_score, 1),
            },
            "trade_setup": {
                "entry_price": self.entry_price,
                "stop_loss": self.stop_loss,
                "take_profit_1": self.take_profit_1,
                "take_profit_2": self.take_profit_2,
                "position_size_pct": self.position_size_pct,
                "risk_reward_ratio": self.risk_reward_ratio,
            },
            "key_levels": self.key_levels,
            "reasons": self.reasons,
            "warnings": self.warnings,
        }


class SignalGenerator:
    """
    Ensemble signal generator combining multiple analysis components.
    
    Components and weights:
    - Technical Analysis: 30%
    - Pattern Recognition: 20%
    - Sentiment Analysis: 20%
    - AI Prediction: 15%
    - Multi-Timeframe: 15%
    
    Signal generation process:
    1. Fetch market data
    2. Run all analysis components
    3. Calculate weighted ensemble score
    4. Generate trading signal with risk management
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        newsapi_key: Optional[str] = None,
        finnhub_key: Optional[str] = None,
        use_finbert: bool = False  # Default to simple analyzer for speed
    ):
        """
        Initialize signal generator.
        
        Args:
            config: Configuration object
            newsapi_key: NewsAPI key for news fetching
            finnhub_key: Finnhub key for additional data
            use_finbert: Whether to use FinBERT (slower but more accurate)
        """
        self.config = config or get_config()
        
        # Initialize components
        self.data_fetcher = DataFetcher()
        self.news_aggregator = NewsAggregator(
            newsapi_key=newsapi_key or self.config.api.news_api_key,
            finnhub_key=finnhub_key or self.config.api.finnhub_key
        )
        self.indicators = TechnicalIndicators()
        self.patterns = PatternRecognition()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.risk_manager = RiskManager()
        
        # Sentiment analyzer
        if use_finbert:
            try:
                self.sentiment_analyzer = FinBERTSentimentAnalyzer()
            except:
                logger.warning("FinBERT not available, using simple analyzer")
                self.sentiment_analyzer = SimpleSentimentAnalyzer()
        else:
            self.sentiment_analyzer = SimpleSentimentAnalyzer()
        
        # Price predictor
        self.price_predictor = LSTMPricePredictor()
        
        # Weights for ensemble (from config)
        self.weights = {
            "technical": 0.30,
            "pattern": 0.20,
            "sentiment": 0.20,
            "ai": 0.15,
            "mtf": 0.15,
        }
    
    async def generate_signal(
        self,
        ticker: str,
        include_sentiment: bool = True,
        include_ai: bool = True
    ) -> TradingSignal:
        """
        Generate comprehensive trading signal.
        
        Args:
            ticker: Stock/crypto symbol
            include_sentiment: Whether to include sentiment analysis
            include_ai: Whether to include AI prediction
            
        Returns:
            TradingSignal with all analysis data
        """
        logger.info(f"Generating signal for {ticker}")
        
        reasons = []
        warnings = []
        
        # Fetch market data
        df = self.data_fetcher.get_stock_data(ticker, period="6mo", interval="1d")
        
        if df.empty:
            return self._create_no_data_signal(ticker)
        
        current_price = df['close'].iloc[-1]
        
        # 1. Technical Analysis
        technical_score = self.indicators.get_confluence_score(df)
        technical_analysis = self.indicators.analyze_all(df)
        
        if technical_score > 30:
            reasons.append(f"Technical indicators bullish (score: {technical_score:.0f})")
        elif technical_score < -30:
            reasons.append(f"Technical indicators bearish (score: {technical_score:.0f})")
        
        # 2. Pattern Recognition
        pattern_score, pattern_signal = self.patterns.get_pattern_score(df)
        recent_patterns = self.patterns.get_recent_patterns(df, 10)
        
        if recent_patterns:
            top_pattern = recent_patterns[0]
            reasons.append(f"Recent pattern: {top_pattern.type.value} ({top_pattern.direction})")
        
        # 3. Multi-Timeframe Analysis
        try:
            mtf_score, mtf_signal, mtf_breakdown = self.mtf_analyzer.get_confluence_score(ticker)
        except Exception as e:
            logger.warning(f"MTF analysis failed: {e}")
            mtf_score = 0
            mtf_breakdown = {}
        
        if abs(mtf_score) > 40:
            aligned_count = sum(1 for v in mtf_breakdown.values() if abs(v.get('score', 0)) > 30)
            reasons.append(f"Multi-timeframe aligned: {aligned_count} TFs in agreement")
        
        # 4. Sentiment Analysis (optional)
        sentiment_score = 0.0
        if include_sentiment:
            try:
                # Fetch and analyze news
                articles = await self.news_aggregator.fetch_all_news(ticker, days=7)
                
                if articles:
                    news_dicts = [a.to_dict() for a in articles]
                    
                    # Analyze sentiment
                    sentiments = []
                    for news in news_dicts[:20]:  # Limit for performance
                        text = f"{news.get('title', '')} {news.get('description', '')}"
                        result = self.sentiment_analyzer.analyze_text(text)
                        sentiments.append(result)
                    
                    # Calculate aggregate
                    pos = sum(1 for s in sentiments if s.sentiment == "positive")
                    neg = sum(1 for s in sentiments if s.sentiment == "negative")
                    total = len(sentiments)
                    
                    if total > 0:
                        sentiment_score = ((pos - neg) / total) * 100
                        
                        if pos > neg * 1.5:
                            reasons.append(f"Positive news sentiment ({pos}/{total} articles)")
                        elif neg > pos * 1.5:
                            reasons.append(f"Negative news sentiment ({neg}/{total} articles)")
                            
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {e}")
                warnings.append("Sentiment analysis unavailable")
        
        # 5. AI Prediction (optional)
        ai_score = 0.0
        if include_ai:
            try:
                prediction = self.price_predictor.predict(df)
                
                if prediction.direction == "up":
                    ai_score = prediction.probability * 100
                    if prediction.confidence in ["high", "medium"]:
                        reasons.append(f"AI predicts upward move ({prediction.probability:.0%} probability)")
                elif prediction.direction == "down":
                    ai_score = -prediction.probability * 100
                    if prediction.confidence in ["high", "medium"]:
                        reasons.append(f"AI predicts downward move ({prediction.probability:.0%} probability)")
                        
            except Exception as e:
                logger.warning(f"AI prediction failed: {e}")
                warnings.append("AI prediction unavailable")
        
        # Calculate ensemble score
        ensemble_score = (
            technical_score * self.weights["technical"] +
            pattern_score * self.weights["pattern"] +
            sentiment_score * self.weights["sentiment"] +
            ai_score * self.weights["ai"] +
            mtf_score * self.weights["mtf"]
        )
        
        # Determine signal direction and strength
        direction, strength = self._determine_signal(ensemble_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            technical_score, pattern_score, sentiment_score, ai_score, mtf_score
        )
        
        # Add warnings for low confidence
        if confidence < 0.5:
            warnings.append("Low confidence signal - consider waiting for better setup")
        
        # Risk management calculations
        risk_params = self._calculate_risk_parameters(
            df, direction, current_price, technical_analysis
        )
        
        # Key levels
        key_levels = {
            "current_price": round(current_price, 2),
            "ema_10": round(technical_analysis["trend"]["ema_10"], 2),
            "ema_30": round(technical_analysis["trend"]["ema_30"], 2),
            "bb_upper": round(technical_analysis["volatility"]["bb_upper"], 2),
            "bb_lower": round(technical_analysis["volatility"]["bb_lower"], 2),
            "recent_high": round(df['high'].tail(20).max(), 2),
            "recent_low": round(df['low'].tail(20).min(), 2),
        }
        
        return TradingSignal(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            direction=direction,
            strength=strength,
            confidence=confidence,
            technical_score=technical_score,
            pattern_score=pattern_score,
            sentiment_score=sentiment_score,
            ai_score=ai_score,
            mtf_score=mtf_score,
            ensemble_score=ensemble_score,
            entry_price=risk_params.get("entry"),
            stop_loss=risk_params.get("stop_loss"),
            take_profit_1=risk_params.get("tp1"),
            take_profit_2=risk_params.get("tp2"),
            position_size_pct=risk_params.get("position_size"),
            risk_reward_ratio=risk_params.get("rr_ratio"),
            key_levels=key_levels,
            reasons=reasons,
            warnings=warnings,
        )
    
    def generate_signal_sync(
        self,
        ticker: str,
        include_sentiment: bool = True,
        include_ai: bool = True
    ) -> TradingSignal:
        """Synchronous wrapper for generate_signal."""
        return asyncio.run(self.generate_signal(ticker, include_sentiment, include_ai))
    
    def _determine_signal(
        self, 
        ensemble_score: float
    ) -> tuple:
        """Determine signal direction and strength from ensemble score."""
        if ensemble_score >= 50:
            return SignalDirection.BUY, SignalStrength.STRONG
        elif ensemble_score >= 25:
            return SignalDirection.BUY, SignalStrength.MODERATE
        elif ensemble_score >= 10:
            return SignalDirection.BUY, SignalStrength.WEAK
        elif ensemble_score <= -50:
            return SignalDirection.SELL, SignalStrength.STRONG
        elif ensemble_score <= -25:
            return SignalDirection.SELL, SignalStrength.MODERATE
        elif ensemble_score <= -10:
            return SignalDirection.SELL, SignalStrength.WEAK
        else:
            return SignalDirection.HOLD, SignalStrength.WEAK
    
    def _calculate_confidence(
        self,
        technical: float,
        pattern: float,
        sentiment: float,
        ai: float,
        mtf: float
    ) -> float:
        """Calculate overall signal confidence."""
        scores = [technical, pattern, sentiment, ai, mtf]
        
        # Count agreeing signals
        positive = sum(1 for s in scores if s > 20)
        negative = sum(1 for s in scores if s < -20)
        
        # Higher agreement = higher confidence
        agreement = max(positive, negative)
        
        if agreement >= 4:
            base_confidence = 0.85
        elif agreement >= 3:
            base_confidence = 0.70
        elif agreement >= 2:
            base_confidence = 0.55
        else:
            base_confidence = 0.40
        
        # Adjust based on score magnitudes
        avg_magnitude = sum(abs(s) for s in scores) / len(scores)
        magnitude_bonus = min(0.1, avg_magnitude / 500)
        
        confidence = min(0.95, base_confidence + magnitude_bonus)
        
        return round(confidence, 3)
    
    def _calculate_risk_parameters(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
        current_price: float,
        analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate risk management parameters."""
        atr = analysis["volatility"]["atr"]
        atr_pct = analysis["volatility"]["atr_percent"]
        
        if direction == SignalDirection.BUY:
            entry = current_price
            stop_loss = self.risk_manager.calculate_stop_loss(
                entry, atr, direction="long"
            )
            tp1 = self.risk_manager.calculate_take_profit(
                entry, stop_loss, rr_ratio=1.5
            )
            tp2 = self.risk_manager.calculate_take_profit(
                entry, stop_loss, rr_ratio=2.5
            )
            
        elif direction == SignalDirection.SELL:
            entry = current_price
            stop_loss = self.risk_manager.calculate_stop_loss(
                entry, atr, direction="short"
            )
            tp1 = self.risk_manager.calculate_take_profit(
                entry, stop_loss, rr_ratio=1.5, direction="short"
            )
            tp2 = self.risk_manager.calculate_take_profit(
                entry, stop_loss, rr_ratio=2.5, direction="short"
            )
        else:
            return {}
        
        # Calculate position size
        risk_amount = abs(entry - stop_loss)
        rr_ratio = abs(tp1 - entry) / risk_amount if risk_amount > 0 else 0
        
        # Position size based on 2% risk
        position_size = self.risk_manager.calculate_position_size(
            capital=10000,  # Example capital
            risk_percent=self.config.trading.default_risk_percent,
            entry_price=entry,
            stop_loss=stop_loss
        )
        
        return {
            "entry": round(entry, 2),
            "stop_loss": round(stop_loss, 2),
            "tp1": round(tp1, 2),
            "tp2": round(tp2, 2),
            "position_size": round(position_size, 2),
            "rr_ratio": round(rr_ratio, 2),
        }
    
    def _create_no_data_signal(self, ticker: str) -> TradingSignal:
        """Create signal for when no data is available."""
        return TradingSignal(
            ticker=ticker,
            timestamp=datetime.now().isoformat(),
            direction=SignalDirection.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            technical_score=0,
            pattern_score=0,
            sentiment_score=0,
            ai_score=0,
            mtf_score=0,
            ensemble_score=0,
            reasons=["No data available for analysis"],
            warnings=["Unable to fetch market data"],
        )
    
    async def generate_watchlist_signals(
        self,
        tickers: List[str],
        include_sentiment: bool = False,  # Disabled by default for speed
        include_ai: bool = False
    ) -> List[TradingSignal]:
        """
        Generate signals for multiple tickers.
        
        Args:
            tickers: List of stock symbols
            include_sentiment: Whether to include sentiment analysis
            include_ai: Whether to include AI prediction
            
        Returns:
            List of TradingSignal objects
        """
        signals = []
        
        for ticker in tickers:
            try:
                signal = await self.generate_signal(ticker, include_sentiment, include_ai)
                signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal for {ticker}: {e}")
        
        # Sort by ensemble score (best opportunities first)
        signals.sort(key=lambda x: abs(x.ensemble_score), reverse=True)
        
        return signals


# Need pandas import in this file
import pandas as pd


if __name__ == "__main__":
    # Test signal generator
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        print("Testing Signal Generator...")
        
        generator = SignalGenerator(use_finbert=False)
        
        print("\n=== Generating Signal for AAPL ===")
        signal = await generator.generate_signal(
            "AAPL",
            include_sentiment=False,
            include_ai=True
        )
        
        print(f"\nTicker: {signal.ticker}")
        print(f"Direction: {signal.direction.value}")
        print(f"Strength: {signal.strength.value}")
        print(f"Confidence: {signal.confidence:.1%}")
        
        print(f"\n--- Component Scores ---")
        print(f"Technical: {signal.technical_score:.1f}")
        print(f"Pattern: {signal.pattern_score:.1f}")
        print(f"Sentiment: {signal.sentiment_score:.1f}")
        print(f"AI: {signal.ai_score:.1f}")
        print(f"MTF: {signal.mtf_score:.1f}")
        print(f"ENSEMBLE: {signal.ensemble_score:.1f}")
        
        print(f"\n--- Trade Setup ---")
        print(f"Entry: ${signal.entry_price}")
        print(f"Stop Loss: ${signal.stop_loss}")
        print(f"TP1: ${signal.take_profit_1}")
        print(f"TP2: ${signal.take_profit_2}")
        print(f"R:R Ratio: {signal.risk_reward_ratio}")
        
        print(f"\n--- Reasons ---")
        for reason in signal.reasons:
            print(f"  ✓ {reason}")
        
        if signal.warnings:
            print(f"\n--- Warnings ---")
            for warning in signal.warnings:
                print(f"  ⚠ {warning}")
    
    asyncio.run(main())
