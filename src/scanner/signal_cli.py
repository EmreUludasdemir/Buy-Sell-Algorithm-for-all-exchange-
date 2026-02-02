"""
Signal Scanner CLI - AL/SAT Sinyalleri

Kullanım:
    python -m src.scanner.signal_cli --market us
    python -m src.scanner.signal_cli --market bist
    python -m src.scanner.signal_cli --ticker NVDA
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scanner.providers import YahooProvider
from src.scanner.signals import (
    SignalType, TradingSignal,
    scan_for_signals, format_signal,
    generate_buy_signal
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Default ticker listeleri
US_WATCHLIST = [
    # AI/Tech
    "NVDA", "AMD", "SMCI", "AVGO", "MRVL", "MU", "QCOM",
    # Quantum
    "RGTI", "IONQ", "QBTS",
    # Crypto
    "COIN", "MARA", "RIOT", "CLSK",
    # Cloud
    "PLTR", "SNOW", "DDOG", "NET", "MDB", "CRWD",
    # EV
    "TSLA", "RIVN",
    # Fintech
    "PYPL", "AFRM", "SOFI",
    # Big Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
]

BIST_WATCHLIST = [
    "ASELS.IS", "THYAO.IS", "KCHOL.IS", "SAHOL.IS", "SISE.IS",
    "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "GARAN.IS",
    "BIMAS.IS", "TUPRS.IS", "FROTO.IS", "TOASO.IS",
    "PGSUS.IS", "VESTL.IS", "ARCLK.IS", "ENKAI.IS",
]


def scan_market(
    tickers: List[str],
    benchmark: str,
    provider: YahooProvider,
    show_all: bool = False
) -> List[TradingSignal]:
    """Tüm ticker'ları tara, sinyalleri döndür"""
    
    logger.info(f"Benchmark yükleniyor: {benchmark}")
    bench_df = provider.fetch(benchmark)
    
    signals = []
    buy_signals = []
    watch_signals = []
    
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        logger.info(f"[{i+1}/{total}] {ticker} taranıyor...")
        
        df = provider.fetch(ticker)
        if df.empty:
            continue
        
        signal = scan_for_signals(df, ticker, bench_df, position_held=False)
        
        if signal.signal == SignalType.BUY:
            buy_signals.append(signal)
        elif signal.signal == SignalType.WATCH:
            watch_signals.append(signal)
        elif show_all:
            signals.append(signal)
    
    # Önce BUY, sonra WATCH, sonra diğerleri
    return buy_signals + watch_signals + signals


def print_summary(signals: List[TradingSignal]):
    """Özet tablo yazdır"""
    
    buy_signals = [s for s in signals if s.signal == SignalType.BUY]
    watch_signals = [s for s in signals if s.signal == SignalType.WATCH]
    
    print("\n" + "="*70)
    print("🚀 TRADİNG SİNYALLERİ - ÖZET")
    print("="*70)
    
    if buy_signals:
        print(f"\n🟢 AL SİNYALLERİ ({len(buy_signals)} adet)")
        print("-"*70)
        print(f"{'Ticker':<10} {'Fiyat':>10} {'Stop':>10} {'Risk%':>8} {'TP1':>10} {'TP2':>10} {'R/R':>6}")
        print("-"*70)
        
        for s in buy_signals:
            print(f"{s.ticker:<10} ${s.price:>8.2f} ${s.stop_loss:>8.2f} {s.risk_pct:>7.1f}% ${s.take_profit_1:>8.2f} ${s.take_profit_2:>8.2f} {s.reward_risk_ratio:>5.1f}")
    else:
        print("\n🟢 AL SİNYALİ YOK")
    
    if watch_signals:
        print(f"\n👀 İZLE - SETUP OLUŞUYOR ({len(watch_signals)} adet)")
        print("-"*70)
        
        for s in watch_signals:
            reasons_short = ", ".join([r.replace("✓ ", "").replace("⏳ ", "") for r in s.reasons[:2]])
            print(f"{s.ticker:<10} ${s.price:>8.2f}  |  {reasons_short}")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Trading Signal Scanner - AL/SAT Sinyalleri",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python -m src.scanner.signal_cli --market us
  python -m src.scanner.signal_cli --market bist
  python -m src.scanner.signal_cli --ticker NVDA TSLA AAPL
  python -m src.scanner.signal_cli --market us --detailed
        """
    )
    
    parser.add_argument(
        "--market", "-m",
        choices=["us", "bist"],
        help="Market seçimi"
    )
    
    parser.add_argument(
        "--ticker", "-t",
        nargs="+",
        help="Tek tek ticker'lar"
    )
    
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Detaylı sinyal çıktısı"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Sinyal olmayan hisseleri de göster"
    )
    
    args = parser.parse_args()
    
    # Ticker listesi belirle
    if args.ticker:
        tickers = [t.upper() for t in args.ticker]
        benchmark = "SPY" if not any(".IS" in t for t in tickers) else "XU100.IS"
    elif args.market == "us":
        tickers = US_WATCHLIST
        benchmark = "SPY"
    elif args.market == "bist":
        tickers = BIST_WATCHLIST
        benchmark = "XU100.IS"
    else:
        parser.print_help()
        print("\n⚠️ --market veya --ticker belirtmelisin!")
        sys.exit(1)
    
    logger.info(f"Taranacak: {len(tickers)} hisse")
    logger.info(f"Benchmark: {benchmark}")
    
    provider = YahooProvider()
    
    # Tara
    signals = scan_market(tickers, benchmark, provider, show_all=args.all)
    
    if not signals:
        print("\n⚠️ Hiç sinyal bulunamadı!")
        sys.exit(0)
    
    # Özet
    print_summary(signals)
    
    # Detaylı çıktı
    if args.detailed:
        buy_signals = [s for s in signals if s.signal == SignalType.BUY]
        for signal in buy_signals:
            print(format_signal(signal))


if __name__ == "__main__":
    main()
