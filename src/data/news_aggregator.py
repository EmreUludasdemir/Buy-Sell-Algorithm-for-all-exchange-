"""
News Aggregator Module
======================
Multi-source news aggregation for sentiment analysis.
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)

# Rate limiting constants
_MAX_REQUESTS_PER_SECOND = 5
_last_request_times: List[float] = []


@dataclass
class NewsArticle:
    """Standardized news article structure."""
    title: str
    description: str
    source: str
    url: str
    published_at: str
    ticker: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def _rate_limit_check():
    """Enforce rate limiting for API requests."""
    global _last_request_times
    now = time.time()
    
    # Remove old timestamps (older than 1 second)
    _last_request_times = [t for t in _last_request_times if now - t < 1.0]
    
    # If at limit, wait
    if len(_last_request_times) >= _MAX_REQUESTS_PER_SECOND:
        wait_time = 1.0 - (now - _last_request_times[0])
        if wait_time > 0:
            await asyncio.sleep(wait_time)
    
    _last_request_times.append(time.time())


class NewsAggregator:
    """
    Multi-source news aggregator.
    
    Supports:
    - NewsAPI
    - Finnhub
    - Yahoo Finance (via DataFetcher)
    """
    
    def __init__(
        self, 
        newsapi_key: Optional[str] = None,
        finnhub_key: Optional[str] = None
    ):
        """
        Initialize the news aggregator.
        
        Args:
            newsapi_key: NewsAPI API key
            finnhub_key: Finnhub API key
        """
        self.newsapi_key = newsapi_key
        self.finnhub_key = finnhub_key
        self._cache: Dict[str, List[NewsArticle]] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=15)
        self._max_retries = 3
    
    async def fetch_all_news(
        self, 
        ticker: str,
        company_name: Optional[str] = None,
        days: int = 7
    ) -> List[NewsArticle]:
        """
        Fetch news from all available sources.
        
        Args:
            ticker: Stock symbol
            company_name: Optional company name for broader search
            days: Number of days to look back
            
        Returns:
            List of NewsArticle objects
        """
        # Check cache
        cache_key = f"{ticker}_{days}"
        if cache_key in self._cache:
            cache_age = datetime.now() - self._cache_time.get(cache_key, datetime.min)
            if cache_age < self._cache_duration:
                logger.info(f"Returning cached news for {ticker}")
                return self._cache[cache_key]
        
        all_articles: List[NewsArticle] = []
        
        async with aiohttp.ClientSession() as session:
            # Gather all sources concurrently
            tasks = []
            
            if self.newsapi_key:
                tasks.append(self._fetch_newsapi(session, ticker, company_name, days))
            
            if self.finnhub_key:
                tasks.append(self._fetch_finnhub(session, ticker, days))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, list):
                        all_articles.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"News fetch error: {result}")
        
        # Remove duplicates based on title similarity
        unique_articles = self._deduplicate(all_articles)
        
        # Sort by date (newest first)
        unique_articles.sort(
            key=lambda x: x.published_at if x.published_at else "",
            reverse=True
        )
        
        # Cache the results
        self._cache[cache_key] = unique_articles
        self._cache_time[cache_key] = datetime.now()
        
        logger.info(f"Fetched {len(unique_articles)} unique articles for {ticker}")
        return unique_articles
    
    async def _fetch_newsapi(
        self, 
        session: aiohttp.ClientSession,
        ticker: str,
        company_name: Optional[str],
        days: int
    ) -> List[NewsArticle]:
        """Fetch from NewsAPI with rate limiting and retry."""
        articles = []
        
        # Build query
        query = ticker
        if company_name:
            query = f"{ticker} OR {company_name}"
        
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "apiKey": self.newsapi_key,
            "pageSize": 50,
        }
        
        for attempt in range(self._max_retries):
            try:
                # Rate limit check
                await _rate_limit_check()
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get("articles", []):
                            articles.append(NewsArticle(
                                title=item.get("title", ""),
                                description=item.get("description", ""),
                                source=item.get("source", {}).get("name", "NewsAPI"),
                                url=item.get("url", ""),
                                published_at=item.get("publishedAt", ""),
                                ticker=ticker,
                            ))
                        return articles
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = (2 ** attempt) * 1.0
                        logger.warning(f"NewsAPI rate limited. Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"NewsAPI returned status {response.status}")
                        return articles
                        
            except asyncio.TimeoutError:
                logger.warning(f"NewsAPI timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"NewsAPI error: {e}")
        
        return articles
    
    async def _fetch_finnhub(
        self,
        session: aiohttp.ClientSession,
        ticker: str,
        days: int
    ) -> List[NewsArticle]:
        """Fetch from Finnhub with rate limiting and retry."""
        articles = []
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        url = f"https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": ticker,
            "from": start_date,
            "to": end_date,
            "token": self.finnhub_key,
        }
        
        for attempt in range(self._max_retries):
            try:
                # Rate limit check
                await _rate_limit_check()
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data:
                            # Convert timestamp to ISO format
                            pub_date = datetime.fromtimestamp(
                                item.get("datetime", 0)
                            ).isoformat() if item.get("datetime") else ""
                            
                            articles.append(NewsArticle(
                                title=item.get("headline", ""),
                                description=item.get("summary", ""),
                                source=item.get("source", "Finnhub"),
                                url=item.get("url", ""),
                                published_at=pub_date,
                                ticker=ticker,
                            ))
                        return articles
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = (2 ** attempt) * 1.0
                        logger.warning(f"Finnhub rate limited. Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"Finnhub returned status {response.status}")
                        return articles
                        
            except asyncio.TimeoutError:
                logger.warning(f"Finnhub timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Finnhub news error: {e}")
        
        return articles
    
    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on title similarity."""
        seen_titles = set()
        unique = []
        
        for article in articles:
            # Normalize title for comparison
            normalized = article.title.lower().strip()
            
            # Check for exact or very similar titles
            if normalized not in seen_titles and len(normalized) > 10:
                seen_titles.add(normalized)
                unique.append(article)
        
        return unique
    
    def search_news(
        self,
        articles: List[NewsArticle],
        keywords: List[str]
    ) -> List[NewsArticle]:
        """
        Filter articles by keywords.
        
        Args:
            articles: List of articles to filter
            keywords: Keywords to search for
            
        Returns:
            Filtered list of articles
        """
        if not keywords:
            return articles
        
        filtered = []
        keywords_lower = [k.lower() for k in keywords]
        
        for article in articles:
            text = (article.title + " " + article.description).lower()
            if any(keyword in text for keyword in keywords_lower):
                filtered.append(article)
        
        return filtered
    
    def get_sentiment_summary(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """
        Get sentiment summary from articles (requires sentiment to be populated).
        
        Args:
            articles: List of articles with sentiment data
            
        Returns:
            Summary statistics
        """
        if not articles:
            return {
                "total": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "avg_score": 0.0,
            }
        
        sentiments = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
        }
        
        scores = []
        for article in articles:
            if article.sentiment:
                sentiments[article.sentiment] = sentiments.get(article.sentiment, 0) + 1
            if article.sentiment_score is not None:
                scores.append(article.sentiment_score)
        
        return {
            "total": len(articles),
            "positive": sentiments["positive"],
            "negative": sentiments["negative"],
            "neutral": sentiments["neutral"],
            "positive_ratio": sentiments["positive"] / len(articles) if articles else 0,
            "negative_ratio": sentiments["negative"] / len(articles) if articles else 0,
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
        }


# Synchronous wrapper
class SyncNewsAggregator:
    """Synchronous wrapper for NewsAggregator."""
    
    def __init__(
        self,
        newsapi_key: Optional[str] = None,
        finnhub_key: Optional[str] = None
    ):
        self._async_aggregator = NewsAggregator(newsapi_key, finnhub_key)
    
    def fetch_all_news(
        self,
        ticker: str,
        company_name: Optional[str] = None,
        days: int = 7
    ) -> List[NewsArticle]:
        """Synchronous version of fetch_all_news."""
        return asyncio.run(
            self._async_aggregator.fetch_all_news(ticker, company_name, days)
        )


if __name__ == "__main__":
    # Test the news aggregator
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        aggregator = NewsAggregator(
            newsapi_key=os.getenv("NEWS_API_KEY"),
            finnhub_key=os.getenv("FINNHUB_API_KEY"),
        )
        
        print("\n=== News Aggregator Test (AAPL) ===")
        articles = await aggregator.fetch_all_news("AAPL", "Apple", days=7)
        
        print(f"\nTotal articles: {len(articles)}")
        print("\nLatest 5 articles:")
        for article in articles[:5]:
            print(f"\n- {article.title}")
            print(f"  Source: {article.source}")
            print(f"  Date: {article.published_at}")
    
    asyncio.run(main())
