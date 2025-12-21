"""
API Routes
==========
FastAPI endpoints for the trading algorithm.
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

from ..config import get_config
from ..data.fetcher import DataFetcher
from ..analysis.indicators import TechnicalIndicators
from ..analysis.patterns import PatternRecognition
from ..analysis.multi_timeframe import MultiTimeframeAnalyzer
from ..signals.generator import SignalGenerator
from ..ai.company_researcher import AICompanyResearcher

logger = logging.getLogger(__name__)

# Initialize components
config = get_config()
data_fetcher = DataFetcher()
indicators = TechnicalIndicators()
patterns = PatternRecognition()
mtf_analyzer = MultiTimeframeAnalyzer()
signal_generator = SignalGenerator(use_finbert=False)
company_researcher = AICompanyResearcher(use_finbert=False)


# Request/Response models
class SignalRequest(BaseModel):
    ticker: str = Field(..., description="Stock/crypto symbol")
    include_sentiment: bool = Field(default=False, description="Include sentiment analysis")
    include_ai: bool = Field(default=True, description="Include AI prediction")


class WatchlistRequest(BaseModel):
    tickers: List[str] = Field(..., description="List of symbols to analyze")
    include_sentiment: bool = Field(default=False)
    include_ai: bool = Field(default=False)


class BacktestRequest(BaseModel):
    ticker: str
    period: str = "1y"
    initial_capital: float = 10000
    risk_percent: float = 2.0


# Create FastAPI app
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="AI Trading Algorithm API",
        description="""
        Advanced AI-powered trading algorithm combining:
        - Technical Analysis (20+ indicators)
        - Pattern Recognition (Smart Money Concepts)
        - Sentiment Analysis (FinBERT)
        - AI Price Prediction (LSTM)
        - Multi-Timeframe Analysis
        
        Developed by Emre Uludaşdemir
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include router
    app.include_router(router, prefix="/api")
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "AI Trading Algorithm",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    return app


# Router for API endpoints
from fastapi import APIRouter
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
#                              SIGNAL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/signal/{ticker}")
async def get_signal(
    ticker: str,
    include_sentiment: bool = Query(default=False),
    include_ai: bool = Query(default=True)
):
    """
    Get trading signal for a ticker.
    
    Returns comprehensive analysis including:
    - Signal direction (buy/sell/hold)
    - Confidence score
    - Component scores (technical, pattern, sentiment, AI, MTF)
    - Trade setup (entry, stop, targets)
    """
    try:
        signal = await signal_generator.generate_signal(
            ticker.upper(),
            include_sentiment=include_sentiment,
            include_ai=include_ai
        )
        return signal.to_dict()
    except Exception as e:
        logger.error(f"Error generating signal for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/watchlist")
async def get_watchlist_signals(request: WatchlistRequest):
    """
    Get signals for multiple tickers.
    
    Returns sorted list of signals by opportunity strength.
    """
    try:
        signals = await signal_generator.generate_watchlist_signals(
            [t.upper() for t in request.tickers],
            include_sentiment=request.include_sentiment,
            include_ai=request.include_ai
        )
        return {
            "count": len(signals),
            "signals": [s.to_dict() for s in signals]
        }
    except Exception as e:
        logger.error(f"Error generating watchlist signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
#                           ANALYSIS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/analysis/technical/{ticker}")
async def get_technical_analysis(
    ticker: str,
    period: str = Query(default="6mo")
):
    """
    Get technical analysis for a ticker.
    
    Includes:
    - Trend indicators (EMA, MACD)
    - Momentum indicators (RSI, Stochastic)
    - Volatility indicators (Bollinger, ATR)
    - Volume indicators (OBV, MFI)
    - Confluence score
    """
    try:
        df = data_fetcher.get_stock_data(ticker.upper(), period=period)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        analysis = indicators.analyze_all(df)
        confluence = indicators.get_confluence_score(df)
        
        return {
            "ticker": ticker.upper(),
            "period": period,
            "analysis": analysis,
            "confluence_score": confluence,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in technical analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/patterns/{ticker}")
async def get_pattern_analysis(
    ticker: str,
    period: str = Query(default="3mo"),
    lookback: int = Query(default=20)
):
    """
    Get pattern recognition analysis.
    
    Detects Smart Money Concepts patterns:
    - Swing Failure Pattern (SFP)
    - Order Blocks
    - Fair Value Gaps
    - Equal Highs/Lows
    - Supply/Demand Zones
    """
    try:
        df = data_fetcher.get_stock_data(ticker.upper(), period=period)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        all_patterns = patterns.analyze_all(df)
        recent = patterns.get_recent_patterns(df, lookback)
        score, signal = patterns.get_pattern_score(df)
        
        return {
            "ticker": ticker.upper(),
            "pattern_score": score,
            "signal": signal,
            "recent_patterns": [p.to_dict() for p in recent[:20]],
            "pattern_counts": {k: len(v) for k, v in all_patterns.items()},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pattern analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/mtf/{ticker}")
async def get_mtf_analysis(ticker: str):
    """
    Get multi-timeframe analysis.
    
    Analyzes:
    - Weekly, Daily, 4H, 1H, 15m timeframes
    - Confluence score across timeframes
    - Entry timing recommendation
    """
    try:
        dashboard = mtf_analyzer.generate_dashboard(ticker.upper())
        return dashboard
    except Exception as e:
        logger.error(f"Error in MTF analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
#                           RESEARCH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/research/{ticker}")
async def get_company_research(
    ticker: str,
    include_news: bool = Query(default=True),
    news_days: int = Query(default=7)
):
    """
    Get AI-powered company research report.
    
    Includes:
    - Company fundamentals
    - Valuation metrics
    - Analyst recommendations
    - News sentiment analysis
    - Overall assessment
    """
    try:
        report = await company_researcher.research_company(
            ticker.upper(),
            include_news=include_news,
            news_days=news_days
        )
        return report.to_dict()
    except Exception as e:
        logger.error(f"Error in company research for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{ticker}")
async def get_company_info(ticker: str):
    """
    Get basic company information.
    """
    try:
        info = data_fetcher.get_company_info(ticker.upper())
        return info
    except Exception as e:
        logger.error(f"Error fetching company info for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
#                           MARKET ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/market/summary")
async def get_market_summary():
    """
    Get overall market summary with major indices.
    """
    try:
        summary = data_fetcher.get_market_summary()
        return {
            "timestamp": datetime.now().isoformat(),
            "indices": summary,
        }
    except Exception as e:
        logger.error(f"Error fetching market summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price/{ticker}")
async def get_price_data(
    ticker: str,
    period: str = Query(default="1mo"),
    interval: str = Query(default="1d")
):
    """
    Get historical price data.
    """
    try:
        df = data_fetcher.get_stock_data(
            ticker.upper(),
            period=period,
            interval=interval
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        # Convert to JSON-friendly format
        records = df.to_dict(orient="records")
        
        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "count": len(records),
            "data": records,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/{ticker}")
async def get_news(
    ticker: str,
    days: int = Query(default=7)
):
    """
    Get recent news for a ticker.
    """
    try:
        news = data_fetcher.get_news(ticker.upper())
        return {
            "ticker": ticker.upper(),
            "count": len(news),
            "articles": news[:20],  # Limit to 20
        }
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
#                           SCANNER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/scanner/top-movers")
async def get_top_movers():
    """
    Get top movers in the market.
    (Placeholder - would need real-time data feed)
    """
    # Example popular tickers
    popular = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD"]
    
    results = []
    for ticker in popular[:5]:  # Limit for speed
        try:
            df = data_fetcher.get_stock_data(ticker, period="5d")
            if not df.empty and len(df) >= 2:
                current = df['close'].iloc[-1]
                prev = df['close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100
                
                results.append({
                    "ticker": ticker,
                    "price": round(current, 2),
                    "change_pct": round(change_pct, 2),
                })
        except:
            pass
    
    # Sort by absolute change
    results.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "movers": results,
    }


# Create the app instance
app = create_app()
