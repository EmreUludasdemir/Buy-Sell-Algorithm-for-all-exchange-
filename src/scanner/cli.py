"""
Winner Scanner - CLI Interface

Kullanım:
    python -m src.scanner.cli --market us --top 20
    python -m src.scanner.cli --market bist --top 10 --no-walkforward
    python -m src.scanner.cli --market us --tickers tickers.txt --output results.csv
"""

from __future__ import annotations
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scanner.providers import YahooProvider
from src.scanner.scanner import ScanConfig, run_scan, run_scan_detailed
from src.scanner.strategy import BacktestConfig
from src.scanner.walkforward import WalkForwardConfig
from src.scanner.baskets.baskets import load_baskets, get_strong_baskets, get_leaders_from_basket


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DEFAULT TICKER LISTS
# ============================================================================

# US - Popular growth/momentum stocks
DEFAULT_US_TICKERS = [
    # AI/Tech
    "NVDA", "AMD", "SMCI", "AVGO", "MRVL", "INTC", "MU", "QCOM",
    # Quantum
    "RGTI", "IONQ", "QBTS",
    # Crypto
    "COIN", "MARA", "RIOT", "CLSK",
    # Cloud/Software
    "PLTR", "SNOW", "DDOG", "NET", "MDB", "CRWD", "ZS",
    # EV/Auto
    "TSLA", "RIVN", "LCID",
    # Fintech
    "SQ", "PYPL", "AFRM", "SOFI",
    # Biotech
    "MRNA", "BNTX", "REGN",
    # Big Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    # Extras
    "SHOP", "TTD", "ROKU", "ZM", "DOCU", "OKTA",
]

# BIST - Major stocks (.IS suffix for Yahoo)
DEFAULT_BIST_TICKERS = [
    "ASELS.IS", "THYAO.IS", "KCHOL.IS", "SAHOL.IS", "SISE.IS",
    "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "GARAN.IS", "VAKBN.IS",
    "BIMAS.IS", "MGROS.IS", "TUPRS.IS", "PETKM.IS", "FROTO.IS",
    "TOASO.IS", "ENKAI.IS", "TCELL.IS", "TTKOM.IS", "PGSUS.IS",
    "EREGL.IS", "KOZAL.IS", "KOZAA.IS", "EKGYO.IS", "HALKB.IS",
    "TAVHL.IS", "DOHOL.IS", "ARCLK.IS", "VESTL.IS", "AYGAZ.IS",
]


def load_tickers_from_file(filepath: str) -> List[str]:
    """Dosyadan ticker listesi yükle"""
    if not os.path.exists(filepath):
        logger.error(f"Dosya bulunamadı: {filepath}")
        return []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    tickers = [line.strip().upper() for line in lines if line.strip() and not line.startswith('#')]
    return tickers


def get_tickers(args) -> List[str]:
    """Ticker listesini al (dosyadan veya default)"""
    if args.tickers:
        return load_tickers_from_file(args.tickers)
    
    if args.market.lower() == "us":
        return DEFAULT_US_TICKERS
    elif args.market.lower() == "bist":
        return DEFAULT_BIST_TICKERS
    else:
        logger.error(f"Bilinmeyen market: {args.market}")
        return []


def get_benchmark(market: str) -> str:
    """Market için benchmark"""
    benchmarks = {
        "us": "SPY",
        "bist": "XU100.IS",
    }
    return benchmarks.get(market.lower(), "SPY")


def main():
    parser = argparse.ArgumentParser(
        description="Winner Scanner - Lone Stock Trader Methodology",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python -m src.scanner.cli --market us --top 10
  python -m src.scanner.cli --market bist --top 20 --output results.csv
  python -m src.scanner.cli --market us --tickers my_tickers.txt --no-walkforward
  python -m src.scanner.cli --market us --detailed

Kurallar (Thread'den):
  - ADR% >= 4, ATR% >= 5 (volatilite)
  - RS slope > 0 (liderlik)
  - MA squeeze <= 3% (sıkışma)
  - Base score >= 0.4 (yapı)
  - Walk-forward OOS test (gerçekçilik)
        """
    )
    
    parser.add_argument(
        "--market", "-m",
        choices=["us", "bist"],
        default="us",
        help="Market seçimi (default: us)"
    )
    
    parser.add_argument(
        "--tickers", "-t",
        type=str,
        default=None,
        help="Ticker listesi dosyası (her satırda bir ticker)"
    )
    
    parser.add_argument(
        "--benchmark", "-b",
        type=str,
        default=None,
        help="Benchmark ticker (default: SPY/XU100.IS)"
    )
    
    parser.add_argument(
        "--top", "-n",
        type=int,
        default=20,
        help="Kaç hisse göster (default: 20)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="CSV output dosyası (opsiyonel)"
    )
    
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Detaylı çıktı (metriklerle birlikte)"
    )
    
    parser.add_argument(
        "--no-walkforward",
        action="store_true",
        help="Walk-forward testi atla (hızlı tarama için)"
    )
    
    parser.add_argument(
        "--adr-min",
        type=float,
        default=1.5,
        help="Minimum ADR%% (default: 1.5)"
    )
    
    parser.add_argument(
        "--atr-min",
        type=float,
        default=1.5,
        help="Minimum ATR%% (default: 1.5)"
    )
    
    parser.add_argument(
        "--vol-min",
        type=float,
        default=None,
        help="Minimum ortalama hacim (default: market'e göre)"
    )
    
    parser.add_argument(
        "--squeeze-max",
        type=float,
        default=0.15,
        help="Maximum MA squeeze (default: 0.15 = %%15)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Detaylı log"
    )
    
    args = parser.parse_args()
    
    # Logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ticker listesi
    tickers = get_tickers(args)
    if not tickers:
        logger.error("Ticker listesi boş!")
        sys.exit(1)
    
    logger.info(f"Market: {args.market.upper()}")
    logger.info(f"Ticker sayısı: {len(tickers)}")
    
    # Benchmark
    benchmark = args.benchmark or get_benchmark(args.market)
    logger.info(f"Benchmark: {benchmark}")
    
    # Config
    vol_min = args.vol_min
    if vol_min is None:
        vol_min = 1_000_000 if args.market.lower() == "us" else 200_000
    
    scan_cfg = ScanConfig(
        adr_min=args.adr_min,
        atr_min=args.atr_min,
        avg_vol_min=vol_min,
        squeeze_max=args.squeeze_max,
    )
    
    bt_cfg = BacktestConfig()
    wf_cfg = WalkForwardConfig()
    
    # Provider
    provider = YahooProvider()
    
    # Tarama
    run_wf = not args.no_walkforward
    
    if args.detailed:
        logger.info("Detaylı tarama başlıyor...")
        df = run_scan_detailed(
            tickers=tickers,
            benchmark=benchmark,
            provider=provider,
            scan_cfg=scan_cfg,
            bt_cfg=bt_cfg,
            wf_cfg=wf_cfg,
            run_walkforward=run_wf,
            top_n=args.top,
        )
        
        if df.empty:
            logger.warning("Hiçbir hisse filtreleri geçemedi!")
            sys.exit(0)
        
        # Output
        if args.output:
            df.to_csv(args.output, index=False)
            logger.info(f"Sonuçlar kaydedildi: {args.output}")
        
        # Print
        print("\n" + "="*60)
        print(f"TOP {len(df)} ADAYLAR ({args.market.upper()})")
        print("="*60)
        print(df.to_string(index=False))
        
    else:
        logger.info("Tarama başlıyor...")
        picks = run_scan(
            tickers=tickers,
            benchmark=benchmark,
            provider=provider,
            scan_cfg=scan_cfg,
            bt_cfg=bt_cfg,
            wf_cfg=wf_cfg,
            run_walkforward=run_wf,
            top_n=args.top,
            verbose=args.verbose,
        )
        
        if not picks:
            logger.warning("Hiçbir hisse filtreleri geçemedi!")
            sys.exit(0)
        
        # Output
        print("\n" + "="*40)
        print(f"TOP {len(picks)} ({args.market.upper()})")
        print("="*40)
        for i, ticker in enumerate(picks, 1):
            print(f"{i:2d}. {ticker}")
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write('\n'.join(picks))
            logger.info(f"Ticker listesi kaydedildi: {args.output}")
    
    print()


if __name__ == "__main__":
    main()
