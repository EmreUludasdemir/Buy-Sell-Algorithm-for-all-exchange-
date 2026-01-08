"""
Configuration Management
========================
Centralized configuration for the trading algorithm.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


class APIConfig(BaseModel):
    """API Keys Configuration"""
    news_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("NEWS_API_KEY"))
    alpha_vantage_key: Optional[str] = Field(default_factory=lambda: os.getenv("ALPHA_VANTAGE_KEY"))
    finnhub_key: Optional[str] = Field(default_factory=lambda: os.getenv("FINNHUB_API_KEY"))
    openai_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))


class TradingConfig(BaseModel):
    """Trading Settings"""
    default_risk_percent: float = Field(
        default_factory=lambda: float(os.getenv("DEFAULT_RISK_PERCENT", "2.0"))
    )
    default_rr_ratio: float = Field(
        default_factory=lambda: float(os.getenv("DEFAULT_RR_RATIO", "2.0"))
    )
    min_confidence_threshold: int = Field(
        default_factory=lambda: int(os.getenv("MIN_CONFIDENCE_THRESHOLD", "70"))
    )
    default_capital: float = Field(
        default_factory=lambda: float(os.getenv("DEFAULT_CAPITAL", "10000"))
    )
    

class IndicatorConfig(BaseModel):
    """Technical Indicator Settings"""
    # EMA periods
    ema_fast: int = 10
    ema_slow: int = 30
    ema_trend: int = 100
    
    # RSI
    rsi_period: int = 14
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    
    # ATR
    atr_period: int = 14


class SentimentConfig(BaseModel):
    """Sentiment Analysis Settings"""
    model_name: str = "ProsusAI/finbert"
    max_length: int = 512
    batch_size: int = 8
    cache_duration_hours: int = 1


class SignalWeights(BaseModel):
    """Signal Generation Weights"""
    technical_analysis: float = 0.30
    pattern_recognition: float = 0.20
    sentiment_analysis: float = 0.20
    ai_prediction: float = 0.15
    mtf_analysis: float = 0.15


class ServerConfig(BaseModel):
    """API Server Settings"""
    host: str = Field(default_factory=lambda: os.getenv("API_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")


class Config(BaseModel):
    """Main Configuration Container"""
    api: APIConfig = Field(default_factory=APIConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    indicators: IndicatorConfig = Field(default_factory=IndicatorConfig)
    sentiment: SentimentConfig = Field(default_factory=SentimentConfig)
    weights: SignalWeights = Field(default_factory=SignalWeights)
    server: ServerConfig = Field(default_factory=ServerConfig)


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


if __name__ == "__main__":
    # Print configuration for debugging
    import json
    print(json.dumps(config.model_dump(), indent=2))
