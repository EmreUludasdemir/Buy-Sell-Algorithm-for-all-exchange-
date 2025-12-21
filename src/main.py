"""
AI-Powered Trading Algorithm
============================
Main entry point for the trading algorithm.

Usage:
    python -m src.main                    # Start API server
    python -m src.main --test AAPL       # Test signal generation
    python -m src.main --research AAPL   # Company research
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config, Config
from src.signals.generator import SignalGenerator
from src.ai.company_researcher import AICompanyResearcher
from src.analysis.multi_timeframe import MultiTimeframeAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def start_server(config: Config):
    """Start the FastAPI server."""
    import uvicorn
    from src.api.routes import app
    
    logger.info(f"Starting API server on {config.server.host}:{config.server.port}")
    
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level="info" if config.server.debug else "warning"
    )


async def test_signal(ticker: str, use_finbert: bool = False):
    """Test signal generation for a ticker."""
    print(f"\n{'='*60}")
    print(f" AI Trading Signal: {ticker}")
    print(f"{'='*60}")
    
    generator = SignalGenerator(use_finbert=use_finbert)
    
    signal = await generator.generate_signal(
        ticker,
        include_sentiment=False,
        include_ai=True
    )
    
    # Signal summary
    print(f"\n📊 Signal: {signal.direction.value.upper()}")
    print(f"💪 Strength: {signal.strength.value}")
    print(f"🎯 Confidence: {signal.confidence:.1%}")
    
    # Scores
    print(f"\n--- Component Scores ---")
    print(f"  Technical:  {signal.technical_score:+6.1f}")
    print(f"  Pattern:    {signal.pattern_score:+6.1f}")
    print(f"  Sentiment:  {signal.sentiment_score:+6.1f}")
    print(f"  AI:         {signal.ai_score:+6.1f}")
    print(f"  MTF:        {signal.mtf_score:+6.1f}")
    print(f"  {'─'*25}")
    print(f"  ENSEMBLE:   {signal.ensemble_score:+6.1f}")
    
    # Trade setup
    if signal.entry_price:
        print(f"\n--- Trade Setup ---")
        print(f"  Entry:      ${signal.entry_price}")
        print(f"  Stop Loss:  ${signal.stop_loss}")
        print(f"  Target 1:   ${signal.take_profit_1}")
        print(f"  Target 2:   ${signal.take_profit_2}")
        print(f"  R:R Ratio:  {signal.risk_reward_ratio}")
    
    # Reasons
    if signal.reasons:
        print(f"\n--- Reasons ---")
        for reason in signal.reasons:
            print(f"  ✓ {reason}")
    
    # Warnings
    if signal.warnings:
        print(f"\n--- Warnings ---")
        for warning in signal.warnings:
            print(f"  ⚠ {warning}")
    
    print(f"\n{'='*60}\n")


async def research_company(ticker: str):
    """Run company research."""
    print(f"\n{'='*60}")
    print(f" AI Company Research: {ticker}")
    print(f"{'='*60}")
    
    researcher = AICompanyResearcher(use_finbert=False)
    report = await researcher.research_company(ticker, include_news=False)
    
    print(f"\n📈 {report.company_name}")
    print(f"   Sector: {report.sector}")
    print(f"   Industry: {report.industry}")
    
    print(f"\n--- Price ---")
    print(f"  Current: ${report.current_price}")
    if report.price_change_pct:
        print(f"  Change:  {report.price_change_pct:+.2f}%")
    
    print(f"\n--- Valuation ---")
    print(f"  P/E Ratio: {report.pe_ratio}")
    print(f"  Forward P/E: {report.forward_pe}")
    print(f"  PEG Ratio: {report.peg_ratio}")
    
    print(f"\n--- Analyst ---")
    print(f"  Target Price: ${report.target_price}")
    print(f"  Upside: {report.target_upside:+.1f}%")
    print(f"  Recommendation: {report.recommendation}")
    
    print(f"\n--- Assessment ---")
    print(f"  Score: {report.overall_score}/100")
    print(f"  Signal: {report.overall_signal}")
    
    print(f"\n{report.summary}")
    print(f"\n{'='*60}\n")


async def mtf_analysis(ticker: str):
    """Run multi-timeframe analysis."""
    print(f"\n{'='*60}")
    print(f" Multi-Timeframe Analysis: {ticker}")
    print(f"{'='*60}")
    
    mtf = MultiTimeframeAnalyzer()
    dashboard = mtf.generate_dashboard(ticker)
    
    print(f"\n📊 Current Price: ${dashboard['current_price']:.2f}")
    print(f"🎯 Confluence Score: {dashboard['confluence_score']}")
    print(f"📣 Signal: {dashboard['signal']}")
    
    print(f"\n--- Timeframe Breakdown ---")
    for tf, data in dashboard.get('breakdown', {}).items():
        print(f"  {tf}: {data['bias']} (score: {data['score']})")
    
    print(f"\n--- Entry Timing ---")
    entry = dashboard.get('entry_timing', {})
    print(f"  HTF Direction: {entry.get('htf_direction', 'N/A')}")
    print(f"  LTF Aligned: {entry.get('ltf_aligned', 'N/A')}")
    print(f"  Can Enter: {entry.get('can_enter', 'N/A')}")
    
    print(f"\n{dashboard.get('summary', '')}")
    print(f"\n{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Trading Algorithm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    Start API server
  python -m src.main --test AAPL       Generate signal for AAPL
  python -m src.main --research TSLA   Research TSLA company
  python -m src.main --mtf BTC-USD     Multi-timeframe analysis
        """
    )
    
    parser.add_argument(
        "--test", "-t",
        metavar="TICKER",
        help="Test signal generation for a ticker"
    )
    
    parser.add_argument(
        "--research", "-r",
        metavar="TICKER",
        help="Run company research for a ticker"
    )
    
    parser.add_argument(
        "--mtf", "-m",
        metavar="TICKER",
        help="Run multi-timeframe analysis"
    )
    
    parser.add_argument(
        "--finbert",
        action="store_true",
        help="Use FinBERT for sentiment analysis (slower)"
    )
    
    parser.add_argument(
        "--host",
        default=None,
        help="API server host"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="API server port"
    )
    
    args = parser.parse_args()
    config = get_config()
    
    # Override config with CLI args
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    
    # Run appropriate command
    if args.test:
        asyncio.run(test_signal(args.test.upper(), args.finbert))
    
    elif args.research:
        asyncio.run(research_company(args.research.upper()))
    
    elif args.mtf:
        asyncio.run(mtf_analysis(args.mtf.upper()))
    
    else:
        # Start server
        start_server(config)


if __name__ == "__main__":
    main()
