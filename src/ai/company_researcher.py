"""
AI Company Researcher
=====================
AI-powered comprehensive company analysis and research.
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from ..data.fetcher import DataFetcher
from ..data.news_aggregator import NewsAggregator, NewsArticle
from .sentiment_analyzer import FinBERTSentimentAnalyzer, SimpleSentimentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class CompanyResearchReport:
    """Comprehensive company research report."""
    ticker: str
    company_name: str
    generated_at: str
    
    # Basic Info
    sector: str = ""
    industry: str = ""
    market_cap: Optional[float] = None
    
    # Price Data
    current_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    
    # Valuation
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    
    # Financials
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    eps: Optional[float] = None
    
    # Analyst
    target_price: Optional[float] = None
    recommendation: str = ""
    target_upside: Optional[float] = None
    
    # Sentiment
    news_sentiment: Dict[str, Any] = field(default_factory=dict)
    recent_news: List[Dict[str, Any]] = field(default_factory=list)
    
    # Technical
    technical_levels: Dict[str, float] = field(default_factory=dict)
    
    # Overall Assessment
    overall_score: float = 0.0
    overall_signal: str = "HOLD"
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "generated_at": self.generated_at,
            "basic_info": {
                "sector": self.sector,
                "industry": self.industry,
                "market_cap": self.market_cap,
            },
            "price": {
                "current": self.current_price,
                "change_pct": self.price_change_pct,
            },
            "valuation": {
                "pe_ratio": self.pe_ratio,
                "forward_pe": self.forward_pe,
                "peg_ratio": self.peg_ratio,
                "price_to_book": self.price_to_book,
            },
            "financials": {
                "revenue": self.revenue,
                "revenue_growth": self.revenue_growth,
                "profit_margin": self.profit_margin,
                "eps": self.eps,
            },
            "analyst": {
                "target_price": self.target_price,
                "recommendation": self.recommendation,
                "target_upside": self.target_upside,
            },
            "sentiment": self.news_sentiment,
            "recent_news": self.recent_news[:5],  # Limit to 5
            "technical_levels": self.technical_levels,
            "overall": {
                "score": self.overall_score,
                "signal": self.overall_signal,
                "summary": self.summary,
            }
        }


class AICompanyResearcher:
    """
    AI-powered company research and analysis.
    
    Combines:
    - Fundamental data (financials, valuation)
    - News sentiment analysis
    - Technical levels
    - Analyst recommendations
    
    To generate comprehensive research reports with actionable signals.
    """
    
    def __init__(
        self,
        newsapi_key: Optional[str] = None,
        finnhub_key: Optional[str] = None,
        use_finbert: bool = True
    ):
        """
        Initialize the researcher.
        
        Args:
            newsapi_key: NewsAPI API key
            finnhub_key: Finnhub API key
            use_finbert: Whether to use FinBERT (requires GPU/more memory)
        """
        self.data_fetcher = DataFetcher()
        self.news_aggregator = NewsAggregator(
            newsapi_key=newsapi_key,
            finnhub_key=finnhub_key
        )
        
        # Initialize sentiment analyzer
        if use_finbert:
            try:
                self._sentiment_analyzer = FinBERTSentimentAnalyzer()
            except Exception as e:
                logger.warning(f"FinBERT not available: {e}. Using simple analyzer.")
                self._sentiment_analyzer = SimpleSentimentAnalyzer()
        else:
            self._sentiment_analyzer = SimpleSentimentAnalyzer()
    
    async def research_company(
        self, 
        ticker: str,
        include_news: bool = True,
        news_days: int = 7
    ) -> CompanyResearchReport:
        """
        Generate comprehensive company research report.
        
        Args:
            ticker: Stock symbol
            include_news: Whether to fetch and analyze news
            news_days: Number of days of news to analyze
            
        Returns:
            CompanyResearchReport with all analysis
        """
        logger.info(f"Researching company: {ticker}")
        
        # Fetch basic company info
        info = self.data_fetcher.get_company_info(ticker)
        
        # Initialize report
        report = CompanyResearchReport(
            ticker=ticker,
            company_name=info.get("name", ticker),
            generated_at=datetime.now().isoformat(),
            sector=info.get("sector", ""),
            industry=info.get("industry", ""),
            market_cap=info.get("market_cap"),
            current_price=info.get("current_price"),
            pe_ratio=info.get("pe_ratio"),
            forward_pe=info.get("forward_pe"),
            peg_ratio=info.get("peg_ratio"),
            price_to_book=info.get("price_to_book"),
            revenue=info.get("revenue"),
            revenue_growth=info.get("revenue_growth"),
            profit_margin=info.get("profit_margin"),
            eps=info.get("eps"),
            target_price=info.get("target_price"),
            recommendation=info.get("recommendation", ""),
        )
        
        # Calculate price change and target upside
        if report.current_price and info.get("previous_close"):
            change = report.current_price - info["previous_close"]
            report.price_change_pct = round((change / info["previous_close"]) * 100, 2)
        
        if report.current_price and report.target_price:
            upside = ((report.target_price - report.current_price) / report.current_price) * 100
            report.target_upside = round(upside, 2)
        
        # Fetch technical levels
        report.technical_levels = {
            "52_week_high": info.get("52_week_high"),
            "52_week_low": info.get("52_week_low"),
            "50_day_avg": info.get("50_day_avg"),
            "200_day_avg": info.get("200_day_avg"),
        }
        
        # Fetch and analyze news
        if include_news:
            try:
                articles = await self.news_aggregator.fetch_all_news(
                    ticker, 
                    report.company_name, 
                    days=news_days
                )
                
                if articles:
                    # Convert to dicts for sentiment analysis
                    news_dicts = [a.to_dict() for a in articles]
                    
                    # Analyze sentiment
                    enriched_news, sentiment_summary = self._sentiment_analyzer.analyze_news_batch(
                        news_dicts
                    ) if hasattr(self._sentiment_analyzer, 'analyze_news_batch') else (news_dicts, {})
                    
                    # If using simple analyzer, do manual analysis
                    if not hasattr(self._sentiment_analyzer, 'analyze_news_batch'):
                        sentiments = []
                        for news in news_dicts:
                            text = f"{news.get('title', '')} {news.get('description', '')}"
                            result = self._sentiment_analyzer.analyze_text(text)
                            news['sentiment'] = result.sentiment
                            news['sentiment_confidence'] = result.confidence
                            sentiments.append(result)
                        
                        enriched_news = news_dicts
                        sentiment_summary = self._calculate_simple_summary(sentiments)
                    
                    report.news_sentiment = sentiment_summary
                    report.recent_news = enriched_news[:10]  # Keep top 10
                    
            except Exception as e:
                logger.error(f"Error fetching news for {ticker}: {e}")
        
        # Calculate overall score
        report.overall_score, report.overall_signal = self._calculate_overall_score(report)
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
        return report
    
    def research_company_sync(
        self,
        ticker: str,
        include_news: bool = True,
        news_days: int = 7
    ) -> CompanyResearchReport:
        """Synchronous wrapper for research_company."""
        return asyncio.run(self.research_company(ticker, include_news, news_days))
    
    def _calculate_simple_summary(self, sentiments) -> Dict[str, Any]:
        """Calculate summary from simple sentiment results."""
        if not sentiments:
            return {}
        
        positive = sum(1 for s in sentiments if s.sentiment == "positive")
        negative = sum(1 for s in sentiments if s.sentiment == "negative")
        neutral = sum(1 for s in sentiments if s.sentiment == "neutral")
        total = len(sentiments)
        
        avg_conf = sum(s.confidence for s in sentiments) / total
        
        pos_score = positive / total
        neg_score = negative / total
        
        if pos_score > neg_score + 0.1:
            overall = "positive"
        elif neg_score > pos_score + 0.1:
            overall = "negative"
        else:
            overall = "neutral"
        
        return {
            "total_analyzed": total,
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "positive_ratio": round(pos_score, 3),
            "negative_ratio": round(neg_score, 3),
            "overall_sentiment": overall,
            "sentiment_score": round(pos_score - neg_score, 4),
            "avg_confidence": round(avg_conf, 4),
        }
    
    def _calculate_overall_score(self, report: CompanyResearchReport) -> tuple:
        """
        Calculate overall score based on all factors.
        
        Scoring weights:
        - Valuation: 25%
        - Growth: 20%
        - Analyst: 20%
        - Sentiment: 20%
        - Technical: 15%
        
        Returns:
            Tuple of (score 0-100, signal)
        """
        score = 50.0  # Start neutral
        
        # Valuation score (25%)
        valuation_score = 0
        if report.pe_ratio:
            if report.pe_ratio < 15:
                valuation_score += 10  # Undervalued
            elif report.pe_ratio > 30:
                valuation_score -= 5  # Expensive
        
        if report.peg_ratio:
            if report.peg_ratio < 1:
                valuation_score += 10  # Good value
            elif report.peg_ratio > 2:
                valuation_score -= 5  # Overvalued for growth
        
        score += valuation_score * 0.25
        
        # Growth score (20%)
        growth_score = 0
        if report.revenue_growth:
            if report.revenue_growth > 0.2:
                growth_score += 15  # Strong growth
            elif report.revenue_growth > 0.1:
                growth_score += 10
            elif report.revenue_growth < 0:
                growth_score -= 10  # Declining
        
        if report.profit_margin:
            if report.profit_margin > 0.2:
                growth_score += 5  # High margin
            elif report.profit_margin < 0:
                growth_score -= 10  # Unprofitable
        
        score += growth_score * 0.20
        
        # Analyst score (20%)
        analyst_score = 0
        if report.target_upside:
            if report.target_upside > 20:
                analyst_score += 15
            elif report.target_upside > 10:
                analyst_score += 10
            elif report.target_upside < -10:
                analyst_score -= 10
        
        recommendation_scores = {
            "strong_buy": 15,
            "buy": 10,
            "hold": 0,
            "sell": -10,
            "strong_sell": -15,
        }
        analyst_score += recommendation_scores.get(report.recommendation, 0)
        
        score += analyst_score * 0.20
        
        # Sentiment score (20%)
        sentiment_score = 0
        if report.news_sentiment:
            sent_value = report.news_sentiment.get("sentiment_score", 0)
            sentiment_score = sent_value * 20  # -20 to +20
        
        score += sentiment_score * 0.20
        
        # Technical score (15%)
        technical_score = 0
        if report.current_price and report.technical_levels:
            # Above 50 DMA is bullish
            if report.technical_levels.get("50_day_avg"):
                if report.current_price > report.technical_levels["50_day_avg"]:
                    technical_score += 5
                else:
                    technical_score -= 5
            
            # Above 200 DMA is bullish
            if report.technical_levels.get("200_day_avg"):
                if report.current_price > report.technical_levels["200_day_avg"]:
                    technical_score += 5
                else:
                    technical_score -= 5
        
        score += technical_score * 0.15
        
        # Normalize to 0-100
        score = max(0, min(100, score))
        
        # Determine signal
        if score >= 70:
            signal = "STRONG_BUY"
        elif score >= 60:
            signal = "BUY"
        elif score <= 30:
            signal = "STRONG_SELL"
        elif score <= 40:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return round(score, 1), signal
    
    def _generate_summary(self, report: CompanyResearchReport) -> str:
        """Generate human-readable summary."""
        parts = []
        
        # Company intro
        parts.append(f"{report.company_name} ({report.ticker})")
        if report.sector:
            parts.append(f"operates in the {report.sector} sector")
        parts.append(".")
        
        # Price and valuation
        if report.current_price:
            parts.append(f" Current price: ${report.current_price:.2f}")
            if report.price_change_pct:
                direction = "up" if report.price_change_pct > 0 else "down"
                parts.append(f" ({direction} {abs(report.price_change_pct):.1f}% today).")
        
        if report.pe_ratio:
            if report.pe_ratio < 15:
                parts.append(f" P/E of {report.pe_ratio:.1f} suggests undervaluation.")
            elif report.pe_ratio > 30:
                parts.append(f" P/E of {report.pe_ratio:.1f} indicates premium valuation.")
        
        # Analyst view
        if report.target_price and report.target_upside:
            if report.target_upside > 10:
                parts.append(f" Analysts see {report.target_upside:.0f}% upside to ${report.target_price:.2f}.")
            elif report.target_upside < -10:
                parts.append(f" Analysts see {abs(report.target_upside):.0f}% downside risk.")
        
        # Sentiment
        if report.news_sentiment:
            overall_sent = report.news_sentiment.get("overall_sentiment", "neutral")
            parts.append(f" News sentiment is {overall_sent}.")
        
        # Signal
        parts.append(f" Overall signal: {report.overall_signal} (score: {report.overall_score}/100).")
        
        return "".join(parts)
    
    async def compare_companies(
        self, 
        tickers: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple companies.
        
        Args:
            tickers: List of stock symbols to compare
            
        Returns:
            Comparison report
        """
        reports = {}
        
        for ticker in tickers:
            try:
                report = await self.research_company(ticker, include_news=False)
                reports[ticker] = report
            except Exception as e:
                logger.error(f"Error researching {ticker}: {e}")
        
        # Build comparison
        comparison = {
            "tickers": tickers,
            "reports": {t: r.to_dict() for t, r in reports.items()},
            "rankings": self._rank_companies(reports),
        }
        
        return comparison
    
    def _rank_companies(self, reports: Dict[str, CompanyResearchReport]) -> Dict[str, List[str]]:
        """Rank companies by various metrics."""
        if not reports:
            return {}
        
        rankings = {}
        
        # By overall score
        by_score = sorted(
            reports.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
        rankings["by_score"] = [t for t, _ in by_score]
        
        # By P/E (lower is better for value)
        with_pe = [(t, r) for t, r in reports.items() if r.pe_ratio]
        if with_pe:
            by_pe = sorted(with_pe, key=lambda x: x[1].pe_ratio)
            rankings["by_value"] = [t for t, _ in by_pe]
        
        # By target upside
        with_upside = [(t, r) for t, r in reports.items() if r.target_upside]
        if with_upside:
            by_upside = sorted(with_upside, key=lambda x: x[1].target_upside, reverse=True)
            rankings["by_upside"] = [t for t, _ in by_upside]
        
        return rankings


if __name__ == "__main__":
    # Test company researcher
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        researcher = AICompanyResearcher(
            newsapi_key=os.getenv("NEWS_API_KEY"),
            finnhub_key=os.getenv("FINNHUB_API_KEY"),
            use_finbert=False  # Use simple analyzer for testing
        )
        
        print("\n=== Company Research: AAPL ===")
        report = await researcher.research_company("AAPL")
        
        print(f"\nCompany: {report.company_name}")
        print(f"Sector: {report.sector}")
        print(f"Price: ${report.current_price}")
        print(f"P/E: {report.pe_ratio}")
        print(f"Target: ${report.target_price} ({report.target_upside:+.1f}%)")
        print(f"Recommendation: {report.recommendation}")
        
        if report.news_sentiment:
            print(f"\nNews Sentiment: {report.news_sentiment.get('overall_sentiment')}")
            print(f"Sentiment Score: {report.news_sentiment.get('sentiment_score', 0):.3f}")
        
        print(f"\nOverall Score: {report.overall_score}/100")
        print(f"Signal: {report.overall_signal}")
        print(f"\nSummary: {report.summary}")
    
    asyncio.run(main())
