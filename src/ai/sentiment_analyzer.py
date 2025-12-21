"""
FinBERT Sentiment Analyzer
==========================
Financial sentiment analysis using FinBERT model.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from concurrent.futures import ThreadPoolExecutor
import os

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    text: str
    sentiment: str  # 'positive', 'negative', 'neutral'
    confidence: float  # 0.0 to 1.0
    scores: Dict[str, float]  # All class scores
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text[:100] + "..." if len(self.text) > 100 else self.text,
            "sentiment": self.sentiment,
            "confidence": round(self.confidence, 4),
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
        }


class FinBERTSentimentAnalyzer:
    """
    Financial Sentiment Analyzer using FinBERT.
    
    FinBERT is a BERT model fine-tuned on financial text,
    providing superior accuracy for financial sentiment analysis.
    
    Model: ProsusAI/finbert
    Classes: positive, negative, neutral
    """
    
    DEFAULT_MODEL = "ProsusAI/finbert"
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        max_length: int = 512,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the sentiment analyzer.
        
        Args:
            model_name: Hugging Face model name
            max_length: Maximum token length
            device: Device to use ('cuda', 'cpu', or None for auto)
            cache_dir: Directory to cache model files
        """
        self.model_name = model_name
        self.max_length = max_length
        self.cache_dir = cache_dir
        
        # Determine device
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize model and tokenizer (lazy loading)
        self._model = None
        self._tokenizer = None
        self._loaded = False
        
        # Label mapping for FinBERT
        self.labels = ["positive", "negative", "neutral"]
    
    def _load_model(self):
        """Lazy load the model and tokenizer."""
        if self._loaded:
            return
        
        logger.info(f"Loading FinBERT model: {self.model_name}")
        
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            self._model.to(self.device)
            self._model.eval()
            
            self._loaded = True
            logger.info("FinBERT model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise
    
    def analyze_text(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            SentimentResult with sentiment and confidence
        """
        self._load_model()
        
        if not text or not text.strip():
            return SentimentResult(
                text="",
                sentiment="neutral",
                confidence=1.0,
                scores={"positive": 0.0, "negative": 0.0, "neutral": 1.0}
            )
        
        try:
            # Tokenize
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_length,
                padding=True
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
            
            # Convert to probabilities
            probs = torch.nn.functional.softmax(logits, dim=-1)
            probs = probs.cpu().numpy()[0]
            
            # Get predicted class
            predicted_idx = np.argmax(probs)
            sentiment = self.labels[predicted_idx]
            confidence = float(probs[predicted_idx])
            
            # Build scores dict
            scores = {label: float(probs[i]) for i, label in enumerate(self.labels)}
            
            return SentimentResult(
                text=text,
                sentiment=sentiment,
                confidence=confidence,
                scores=scores
            )
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return SentimentResult(
                text=text,
                sentiment="neutral",
                confidence=0.0,
                scores={"positive": 0.33, "negative": 0.33, "neutral": 0.34}
            )
    
    def analyze_batch(
        self, 
        texts: List[str], 
        batch_size: int = 8
    ) -> List[SentimentResult]:
        """
        Analyze sentiment of multiple texts in batches.
        
        Args:
            texts: List of texts to analyze
            batch_size: Number of texts per batch
            
        Returns:
            List of SentimentResult objects
        """
        self._load_model()
        
        if not texts:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                # Tokenize batch
                inputs = self._tokenizer(
                    batch,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.max_length,
                    padding=True
                )
                
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Inference
                with torch.no_grad():
                    outputs = self._model(**inputs)
                    logits = outputs.logits
                
                # Convert to probabilities
                probs = torch.nn.functional.softmax(logits, dim=-1)
                probs = probs.cpu().numpy()
                
                # Process each result
                for j, text in enumerate(batch):
                    predicted_idx = np.argmax(probs[j])
                    sentiment = self.labels[predicted_idx]
                    confidence = float(probs[j][predicted_idx])
                    scores = {label: float(probs[j][k]) for k, label in enumerate(self.labels)}
                    
                    results.append(SentimentResult(
                        text=text,
                        sentiment=sentiment,
                        confidence=confidence,
                        scores=scores
                    ))
                    
            except Exception as e:
                logger.error(f"Error in batch analysis: {e}")
                # Add neutral results for failed batch
                for text in batch:
                    results.append(SentimentResult(
                        text=text,
                        sentiment="neutral",
                        confidence=0.0,
                        scores={"positive": 0.33, "negative": 0.33, "neutral": 0.34}
                    ))
        
        return results
    
    def analyze_news_batch(
        self, 
        news_list: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Analyze sentiment of news articles.
        
        Args:
            news_list: List of news dictionaries with 'title' and 'description'
            
        Returns:
            Tuple of (enriched news list, aggregate summary)
        """
        if not news_list:
            return [], self._empty_summary()
        
        # Extract text for analysis (title + description for better context)
        texts = []
        for news in news_list:
            title = news.get("title", "")
            description = news.get("description", "")
            combined = f"{title}. {description}".strip()
            texts.append(combined if combined else "")
        
        # Analyze all texts
        results = self.analyze_batch(texts)
        
        # Enrich news with sentiment
        enriched_news = []
        for news, result in zip(news_list, results):
            enriched = dict(news)
            enriched["sentiment"] = result.sentiment
            enriched["sentiment_confidence"] = result.confidence
            enriched["sentiment_scores"] = result.scores
            enriched_news.append(enriched)
        
        # Calculate aggregate summary
        summary = self._calculate_summary(results)
        
        return enriched_news, summary
    
    def _calculate_summary(self, results: List[SentimentResult]) -> Dict[str, Any]:
        """Calculate aggregate sentiment summary."""
        if not results:
            return self._empty_summary()
        
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        total_scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
        confidences = []
        
        for result in results:
            sentiments[result.sentiment] += 1
            confidences.append(result.confidence)
            for label, score in result.scores.items():
                total_scores[label] += score
        
        total = len(results)
        
        # Average scores
        avg_scores = {k: v / total for k, v in total_scores.items()}
        
        # Determine overall sentiment
        if avg_scores["positive"] > avg_scores["negative"] + 0.1:
            overall = "positive"
        elif avg_scores["negative"] > avg_scores["positive"] + 0.1:
            overall = "negative"
        else:
            overall = "neutral"
        
        # Calculate sentiment score (-1 to +1)
        sentiment_score = avg_scores["positive"] - avg_scores["negative"]
        
        return {
            "total_analyzed": total,
            "positive_count": sentiments["positive"],
            "negative_count": sentiments["negative"],
            "neutral_count": sentiments["neutral"],
            "positive_ratio": round(sentiments["positive"] / total, 3),
            "negative_ratio": round(sentiments["negative"] / total, 3),
            "neutral_ratio": round(sentiments["neutral"] / total, 3),
            "avg_positive_score": round(avg_scores["positive"], 4),
            "avg_negative_score": round(avg_scores["negative"], 4),
            "avg_neutral_score": round(avg_scores["neutral"], 4),
            "avg_confidence": round(sum(confidences) / total, 4),
            "overall_sentiment": overall,
            "sentiment_score": round(sentiment_score, 4),  # -1 to +1
        }
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "total_analyzed": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "neutral_ratio": 0.0,
            "avg_positive_score": 0.0,
            "avg_negative_score": 0.0,
            "avg_neutral_score": 0.0,
            "avg_confidence": 0.0,
            "overall_sentiment": "neutral",
            "sentiment_score": 0.0,
        }
    
    def get_trading_signal(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert sentiment summary to trading signal.
        
        Args:
            summary: Sentiment summary from analyze_news_batch
            
        Returns:
            Trading signal with direction and strength
        """
        score = summary.get("sentiment_score", 0)
        confidence = summary.get("avg_confidence", 0)
        
        # Determine signal strength (0 to 1)
        strength = abs(score) * confidence
        
        # Determine direction
        if score > 0.2 and strength > 0.3:
            direction = "bullish"
            signal = "BUY" if strength > 0.5 else "WEAK_BUY"
        elif score < -0.2 and strength > 0.3:
            direction = "bearish"
            signal = "SELL" if strength > 0.5 else "WEAK_SELL"
        else:
            direction = "neutral"
            signal = "HOLD"
        
        return {
            "direction": direction,
            "signal": signal,
            "strength": round(strength, 3),
            "sentiment_score": score,
            "confidence": confidence,
        }


# Simple sentiment analyzer without model (rule-based fallback)
class SimpleSentimentAnalyzer:
    """
    Rule-based sentiment analyzer as fallback when FinBERT is unavailable.
    Uses keyword matching for basic sentiment detection.
    """
    
    POSITIVE_WORDS = {
        "up", "rise", "gain", "bull", "bullish", "grow", "growth", "positive",
        "profit", "earnings", "beat", "exceed", "strong", "surge", "rally",
        "buy", "upgrade", "outperform", "record", "high", "best", "success",
        "recovery", "optimistic", "boost", "improve", "expansion"
    }
    
    NEGATIVE_WORDS = {
        "down", "fall", "loss", "bear", "bearish", "decline", "negative",
        "miss", "weak", "drop", "crash", "sell", "downgrade", "underperform",
        "low", "worst", "fail", "warning", "risk", "concern", "cut", "layoff",
        "recession", "pessimistic", "slump", "decrease", "contraction"
    }
    
    def analyze_text(self, text: str) -> SentimentResult:
        """Simple keyword-based sentiment analysis."""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(
                text=text,
                sentiment="neutral",
                confidence=0.5,
                scores={"positive": 0.33, "negative": 0.33, "neutral": 0.34}
            )
        
        positive_ratio = positive_count / total
        negative_ratio = negative_count / total
        
        if positive_ratio > 0.6:
            sentiment = "positive"
        elif negative_ratio > 0.6:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=max(positive_ratio, negative_ratio),
            scores={
                "positive": positive_ratio,
                "negative": negative_ratio,
                "neutral": 1 - max(positive_ratio, negative_ratio)
            }
        )


if __name__ == "__main__":
    # Test sentiment analyzer
    logging.basicConfig(level=logging.INFO)
    
    print("Testing FinBERT Sentiment Analyzer...")
    
    # Test texts
    test_texts = [
        "Apple reports record-breaking quarterly earnings, beating analyst expectations.",
        "Company announces major layoffs amid declining sales and economic uncertainty.",
        "The stock traded sideways today with no significant news.",
        "Tesla shares surge 10% after positive delivery numbers.",
        "Bank warns of potential losses due to rising interest rates.",
    ]
    
    # Try FinBERT first
    try:
        analyzer = FinBERTSentimentAnalyzer()
        
        print("\n=== Individual Analysis ===")
        for text in test_texts:
            result = analyzer.analyze_text(text)
            print(f"\nText: {text[:60]}...")
            print(f"Sentiment: {result.sentiment} (confidence: {result.confidence:.2f})")
            print(f"Scores: +{result.scores['positive']:.2f} / -{result.scores['negative']:.2f} / ={result.scores['neutral']:.2f}")
        
        print("\n=== Batch Analysis ===")
        results = analyzer.analyze_batch(test_texts)
        summary = analyzer._calculate_summary(results)
        
        print(f"Total analyzed: {summary['total_analyzed']}")
        print(f"Positive: {summary['positive_count']} ({summary['positive_ratio']:.1%})")
        print(f"Negative: {summary['negative_count']} ({summary['negative_ratio']:.1%})")
        print(f"Neutral: {summary['neutral_count']} ({summary['neutral_ratio']:.1%})")
        print(f"Overall: {summary['overall_sentiment']}")
        print(f"Sentiment Score: {summary['sentiment_score']:.3f}")
        
        print("\n=== Trading Signal ===")
        signal = analyzer.get_trading_signal(summary)
        print(f"Signal: {signal['signal']}")
        print(f"Direction: {signal['direction']}")
        print(f"Strength: {signal['strength']:.3f}")
        
    except Exception as e:
        print(f"\nFinBERT not available: {e}")
        print("Using simple fallback analyzer...")
        
        analyzer = SimpleSentimentAnalyzer()
        for text in test_texts:
            result = analyzer.analyze_text(text)
            print(f"\n{text[:50]}... → {result.sentiment}")
