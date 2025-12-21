"""
AI Signal Service for Freqtrade
================================
Provides sentiment analysis and LSTM predictions via HTTP API.
Freqtrade strategy can call this service for AI-enhanced signals.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os
import sys

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np

# Import AI modules
try:
    from src.ai.sentiment_analyzer import FinBERTSentimentAnalyzer, SimpleSentimentAnalyzer
    from src.ai.price_predictor import LSTMPricePredictor
    from src.data.news_aggregator import NewsAggregator
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI modules not fully available: {e}")
    MODULES_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Request/Response models
class PriceData(BaseModel):
    """OHLCV price data."""
    open: List[float]
    high: List[float]
    low: List[float]
    close: List[float]
    volume: List[float]


class SignalRequest(BaseModel):
    """Request for AI signal."""
    symbol: str
    price_data: Optional[PriceData] = None
    include_sentiment: bool = True
    include_lstm: bool = True


class AISignal(BaseModel):
    """AI-enhanced trading signal."""
    symbol: str
    timestamp: str
    
    # Sentiment
    sentiment_score: float = 0.0  # -1 to +1
    sentiment_direction: str = "neutral"
    news_count: int = 0
    
    # LSTM Prediction
    lstm_direction: str = "neutral"
    lstm_probability: float = 0.5
    lstm_predicted_change: float = 0.0
    
    # Combined Signal
    ai_score: float = 0.0  # -100 to +100
    ai_signal: str = "hold"  # buy, sell, hold
    confidence: float = 0.0


# Initialize AI components
class AISignalService:
    """Service providing AI signals for trading."""
    
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self._sentiment_analyzer = None
        self._price_predictor = None
        self._news_aggregator = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        
    def _init_sentiment_analyzer(self):
        """Lazy load sentiment analyzer."""
        if self._sentiment_analyzer is None:
            try:
                logger.info("Initializing FinBERT sentiment analyzer (GPU)...")
                self._sentiment_analyzer = FinBERTSentimentAnalyzer()
                logger.info("FinBERT initialized successfully")
            except Exception as e:
                logger.warning(f"FinBERT not available: {e}. Using simple analyzer.")
                self._sentiment_analyzer = SimpleSentimentAnalyzer()
        return self._sentiment_analyzer
    
    def _init_price_predictor(self):
        """Lazy load LSTM predictor."""
        if self._price_predictor is None:
            logger.info("Initializing LSTM price predictor...")
            self._price_predictor = LSTMPricePredictor(
                sequence_length=20,
                hidden_size=64,
                num_layers=2
            )
            # Try to load pre-trained model
            if self._price_predictor.load_model():
                logger.info("Loaded pre-trained LSTM model")
            else:
                logger.info("No pre-trained model found, using momentum fallback")
        return self._price_predictor
    
    def _init_news_aggregator(self):
        """Lazy load news aggregator."""
        if self._news_aggregator is None:
            from dotenv import load_dotenv
            load_dotenv()
            
            self._news_aggregator = NewsAggregator(
                newsapi_key=os.getenv("NEWS_API_KEY"),
                finnhub_key=os.getenv("FINNHUB_API_KEY")
            )
        return self._news_aggregator
    
    def _get_cache_key(self, symbol: str) -> str:
        """Generate cache key."""
        return f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    async def get_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get sentiment analysis for a symbol."""
        cache_key = f"sentiment_{self._get_cache_key(symbol)}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Fetch news
            aggregator = self._init_news_aggregator()
            articles = await aggregator.fetch_all_news(symbol, days=3)
            
            if not articles:
                return {
                    "score": 0.0,
                    "direction": "neutral",
                    "news_count": 0,
                    "confidence": 0.0
                }
            
            # Analyze sentiment
            analyzer = self._init_sentiment_analyzer()
            
            sentiments = []
            for article in articles[:20]:  # Limit for performance
                text = f"{article.title}. {article.description or ''}"
                result = analyzer.analyze_text(text)
                sentiments.append(result)
            
            # Aggregate
            positive = sum(1 for s in sentiments if s.sentiment == "positive")
            negative = sum(1 for s in sentiments if s.sentiment == "negative")
            total = len(sentiments)
            
            score = (positive - negative) / total if total > 0 else 0
            avg_confidence = sum(s.confidence for s in sentiments) / total if total > 0 else 0
            
            if score > 0.2:
                direction = "bullish"
            elif score < -0.2:
                direction = "bearish"
            else:
                direction = "neutral"
            
            result = {
                "score": score,
                "direction": direction,
                "news_count": total,
                "confidence": avg_confidence,
                "positive_count": positive,
                "negative_count": negative,
            }
            
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {
                "score": 0.0,
                "direction": "neutral",
                "news_count": 0,
                "confidence": 0.0
            }
    
    def get_lstm_prediction(self, price_data: PriceData) -> Dict[str, Any]:
        """Get LSTM price prediction."""
        try:
            predictor = self._init_price_predictor()
            
            # Convert to DataFrame
            df = pd.DataFrame({
                "open": price_data.open,
                "high": price_data.high,
                "low": price_data.low,
                "close": price_data.close,
                "volume": price_data.volume,
            })
            
            if len(df) < 30:
                return {
                    "direction": "neutral",
                    "probability": 0.5,
                    "predicted_change": 0.0,
                    "confidence": "low"
                }
            
            # Get prediction
            prediction = predictor.predict(df)
            
            return {
                "direction": prediction.direction,
                "probability": prediction.probability,
                "predicted_change": prediction.predicted_change,
                "confidence": prediction.confidence
            }
            
        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            return {
                "direction": "neutral",
                "probability": 0.5,
                "predicted_change": 0.0,
                "confidence": "low"
            }
    
    async def get_combined_signal(self, request: SignalRequest) -> AISignal:
        """Get combined AI signal."""
        symbol = request.symbol
        timestamp = datetime.now().isoformat()
        
        # Default values
        sentiment_score = 0.0
        sentiment_direction = "neutral"
        news_count = 0
        lstm_direction = "neutral"
        lstm_probability = 0.5
        lstm_predicted_change = 0.0
        
        # Get sentiment
        if request.include_sentiment:
            sentiment = await self.get_sentiment(symbol)
            sentiment_score = sentiment["score"]
            sentiment_direction = sentiment["direction"]
            news_count = sentiment["news_count"]
        
        # Get LSTM prediction
        if request.include_lstm and request.price_data:
            lstm = self.get_lstm_prediction(request.price_data)
            lstm_direction = lstm["direction"]
            lstm_probability = lstm["probability"]
            lstm_predicted_change = lstm["predicted_change"]
        
        # Calculate combined AI score (-100 to +100)
        # Sentiment weight: 40%, LSTM weight: 60%
        sentiment_contribution = sentiment_score * 40
        
        lstm_contribution = 0
        if lstm_direction == "up":
            lstm_contribution = lstm_probability * 60
        elif lstm_direction == "down":
            lstm_contribution = -lstm_probability * 60
        
        ai_score = sentiment_contribution + lstm_contribution
        
        # Determine signal
        if ai_score > 30:
            ai_signal = "strong_buy"
        elif ai_score > 15:
            ai_signal = "buy"
        elif ai_score < -30:
            ai_signal = "strong_sell"
        elif ai_score < -15:
            ai_signal = "sell"
        else:
            ai_signal = "hold"
        
        # Calculate confidence
        confidence = min(abs(ai_score) / 50, 1.0)
        
        return AISignal(
            symbol=symbol,
            timestamp=timestamp,
            sentiment_score=round(sentiment_score, 4),
            sentiment_direction=sentiment_direction,
            news_count=news_count,
            lstm_direction=lstm_direction,
            lstm_probability=round(lstm_probability, 4),
            lstm_predicted_change=round(lstm_predicted_change, 4),
            ai_score=round(ai_score, 2),
            ai_signal=ai_signal,
            confidence=round(confidence, 4)
        )


# Create FastAPI app
app = FastAPI(
    title="AI Signal Service for Freqtrade",
    description="Provides FinBERT sentiment and LSTM predictions for trading",
    version="1.0.0"
)

# Initialize service
ai_service = AISignalService(use_gpu=True)


@app.get("/")
async def root():
    return {"status": "running", "service": "AI Signal Service"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/signal", response_model=AISignal)
async def get_signal(request: SignalRequest):
    """Get AI-enhanced trading signal."""
    try:
        signal = await ai_service.get_combined_signal(request)
        return signal
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/{symbol}")
async def get_sentiment(symbol: str):
    """Get sentiment analysis for a symbol."""
    try:
        result = await ai_service.get_sentiment(symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Error getting sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("  AI Signal Service for Freqtrade")
    print("  GPU-accelerated FinBERT + LSTM predictions")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=5555, log_level="info")
