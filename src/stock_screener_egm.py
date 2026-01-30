"""
EGM Stock Screener - Earnings Growth Momentum
==============================================
LoneStockTrader'ın EGM metodolojisi ve CANSLIM prensiplerini
kullanarak hisse senedi tarama scripti.

Tarama Kriterleri:
------------------
1. FUNDAMENTAL (Earnings Growth):
   - Quarterly EPS Growth >= 25%
   - Annual EPS Growth >= 20%
   - Revenue Growth >= 15%
   - ROE >= 15%

2. TECHNICAL (Price Action):
   - Price > 200 EMA (uptrend)
   - Price near 52-week high (within 25%)
   - Volume surge (> 1.5x average)
   - RSI between 50-70 (momentum, not overbought)

3. MOMENTUM (Breakout Signals):
   - EMA Ribbon bullish alignment
   - Breaking out of consolidation
   - Relative Strength vs market

Kullanım:
---------
python stock_screener_egm.py

Gereksinimler:
--------------
pip install yfinance pandas numpy ta

Kaynaklar:
----------
- LoneStockTrader (@LoneStockTrader) - EGM Strategy
- William O'Neil - CANSLIM Methodology
- https://traderlion.com/trading-strategies/canslim/
"""

import warnings
from dataclasses import dataclass

import pandas as pd


warnings.filterwarnings("ignore")


@dataclass
class ScreeningCriteria:
    """Tarama kriterleri konfigürasyonu."""

    # Fundamental Criteria
    min_quarterly_eps_growth: float = 0.25  # %25
    min_annual_eps_growth: float = 0.20  # %20
    min_revenue_growth: float = 0.15  # %15
    min_roe: float = 0.15  # %15

    # Technical Criteria
    max_distance_from_high: float = 0.25  # 52-hafta zirvesinden max %25 uzakta
    min_volume_surge: float = 1.5  # Ortalama hacmin 1.5 katı
    min_rsi: float = 50  # Minimum RSI
    max_rsi: float = 70  # Maximum RSI (aşırı alım değil)

    # Price Criteria
    min_price: float = 5.0  # Minimum fiyat (penny stock'ları ele)
    min_avg_volume: int = 100000  # Minimum günlük ortalama hacim


@dataclass
class StockScore:
    """Hisse değerlendirme skoru."""

    symbol: str
    company_name: str
    current_price: float
    eps_growth_q: float | None
    eps_growth_y: float | None
    revenue_growth: float | None
    roe: float | None
    distance_from_high: float
    volume_ratio: float
    rsi: float
    ema_ribbon_bullish: bool
    above_ema200: bool
    total_score: int
    signals: list[str]


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """EMA hesapla."""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI hesapla."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def check_ema_ribbon(df: pd.DataFrame) -> bool:
    """EMA Ribbon bullish mi kontrol et."""
    ema_8 = calculate_ema(df["Close"], 8).iloc[-1]
    ema_13 = calculate_ema(df["Close"], 13).iloc[-1]
    ema_21 = calculate_ema(df["Close"], 21).iloc[-1]
    ema_34 = calculate_ema(df["Close"], 34).iloc[-1]
    ema_55 = calculate_ema(df["Close"], 55).iloc[-1]

    return ema_8 > ema_13 > ema_21 > ema_34 > ema_55


def analyze_stock(symbol: str, criteria: ScreeningCriteria) -> StockScore | None:
    """
    Tek bir hisseyi analiz et.

    Args:
        symbol: Hisse sembolü
        criteria: Tarama kriterleri

    Returns:
        StockScore veya None (kriterleri karşılamıyorsa)
    """
    try:
        import yfinance as yf

        # Hisse verilerini çek
        stock = yf.Ticker(symbol)
        info = stock.info

        # Temel kontroller
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        if current_price < criteria.min_price:
            return None

        avg_volume = info.get("averageVolume", 0)
        if avg_volume < criteria.min_avg_volume:
            return None

        # Historical data
        df = stock.history(period="1y")
        if len(df) < 200:
            return None

        # ===== FUNDAMENTAL METRICS =====
        eps_growth_q = info.get("earningsQuarterlyGrowth")
        eps_growth_y = info.get("earningsGrowth")
        revenue_growth = info.get("revenueGrowth")
        roe = info.get("returnOnEquity")

        # ===== TECHNICAL METRICS =====
        # 52-week high distance
        high_52w = info.get("fiftyTwoWeekHigh", df["High"].max())
        distance_from_high = (high_52w - current_price) / high_52w

        # Volume surge
        current_volume = info.get("volume", df["Volume"].iloc[-1])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        # RSI
        rsi = calculate_rsi(df["Close"]).iloc[-1]

        # EMA 200
        ema_200 = calculate_ema(df["Close"], 200).iloc[-1]
        above_ema200 = current_price > ema_200

        # EMA Ribbon
        ema_ribbon_bullish = check_ema_ribbon(df)

        # ===== SCORING =====
        score = 0
        signals = []

        # Fundamental scoring
        if eps_growth_q is not None and eps_growth_q >= criteria.min_quarterly_eps_growth:
            score += 2
            signals.append(f"✓ EPS Q Growth: {eps_growth_q:.1%}")

        if eps_growth_y is not None and eps_growth_y >= criteria.min_annual_eps_growth:
            score += 2
            signals.append(f"✓ EPS Y Growth: {eps_growth_y:.1%}")

        if revenue_growth is not None and revenue_growth >= criteria.min_revenue_growth:
            score += 1
            signals.append(f"✓ Revenue Growth: {revenue_growth:.1%}")

        if roe is not None and roe >= criteria.min_roe:
            score += 1
            signals.append(f"✓ ROE: {roe:.1%}")

        # Technical scoring
        if above_ema200:
            score += 2
            signals.append("✓ Above 200 EMA (Uptrend)")

        if distance_from_high <= criteria.max_distance_from_high:
            score += 2
            signals.append(f"✓ Near 52W High: {distance_from_high:.1%} away")

        if volume_ratio >= criteria.min_volume_surge:
            score += 2
            signals.append(f"✓ Volume Surge: {volume_ratio:.1f}x average")

        if criteria.min_rsi <= rsi <= criteria.max_rsi:
            score += 1
            signals.append(f"✓ RSI Momentum: {rsi:.0f}")

        if ema_ribbon_bullish:
            score += 2
            signals.append("✓ EMA Ribbon Bullish")

        # Minimum score threshold
        if score < 5:
            return None

        company_name = info.get("shortName", info.get("longName", symbol))

        return StockScore(
            symbol=symbol,
            company_name=company_name,
            current_price=current_price,
            eps_growth_q=eps_growth_q,
            eps_growth_y=eps_growth_y,
            revenue_growth=revenue_growth,
            roe=roe,
            distance_from_high=distance_from_high,
            volume_ratio=volume_ratio,
            rsi=rsi,
            ema_ribbon_bullish=ema_ribbon_bullish,
            above_ema200=above_ema200,
            total_score=score,
            signals=signals,
        )

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None


def get_sp500_symbols() -> list[str]:
    """S&P 500 sembollerini al."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        return tables[0]["Symbol"].tolist()
    except Exception:
        # Fallback: Popüler hisseler
        return [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "META",
            "TSLA",
            "BRK-B",
            "UNH",
            "JNJ",
            "XOM",
            "JPM",
            "V",
            "PG",
            "MA",
            "HD",
            "CVX",
            "MRK",
            "ABBV",
            "LLY",
            "PEP",
            "KO",
            "COST",
            "AVGO",
            "TMO",
            "MCD",
            "WMT",
            "CSCO",
            "ACN",
            "ABT",
            "DHR",
            "VZ",
            "ADBE",
            "NKE",
            "TXN",
            "NEE",
            "PM",
            "CRM",
            "LIN",
            "UPS",
            "RTX",
            "BMY",
            "QCOM",
            "ORCL",
            "AMD",
        ]


def get_nasdaq100_symbols() -> list[str]:
    """NASDAQ-100 sembollerini al."""
    return [
        "AAPL",
        "MSFT",
        "AMZN",
        "NVDA",
        "GOOGL",
        "META",
        "TSLA",
        "GOOG",
        "AVGO",
        "COST",
        "PEP",
        "CSCO",
        "ADBE",
        "NFLX",
        "AMD",
        "CMCSA",
        "INTC",
        "TXN",
        "QCOM",
        "TMUS",
        "AMGN",
        "INTU",
        "AMAT",
        "ISRG",
        "BKNG",
        "HON",
        "SBUX",
        "MDLZ",
        "VRTX",
        "ADP",
        "GILD",
        "ADI",
        "REGN",
        "LRCX",
        "PANW",
        "MU",
        "SNPS",
        "KLAC",
        "CDNS",
        "MELI",
        "ASML",
        "PYPL",
        "MAR",
        "ORLY",
        "CTAS",
        "CSX",
        "MNST",
        "NXPI",
    ]


def get_growth_stocks() -> list[str]:
    """Bilinen growth stock'ları."""
    return [
        # AI & Semiconductors
        "NVDA",
        "AMD",
        "AVGO",
        "MRVL",
        "ARM",
        "SMCI",
        "TSM",
        # Cloud & Software
        "CRM",
        "NOW",
        "SNOW",
        "PLTR",
        "DDOG",
        "CRWD",
        "ZS",
        "NET",
        # E-commerce & Fintech
        "SHOP",
        "SQ",
        "PYPL",
        "COIN",
        "AFRM",
        "SOFI",
        # EV & Clean Energy
        "TSLA",
        "RIVN",
        "LCID",
        "NIO",
        "ENPH",
        "SEDG",
        "FSLR",
        # Biotech
        "MRNA",
        "REGN",
        "VRTX",
        "BIIB",
        "ILMN",
        # Other Growth
        "ABNB",
        "UBER",
        "DASH",
        "RBLX",
        "U",
        "TTD",
        "ROKU",
        # Quantum Computing (RGTI gibi)
        "RGTI",
        "IONQ",
        "QBTS",
    ]


def screen_stocks(
    symbols: list[str],
    criteria: ScreeningCriteria | None = None,
    max_results: int = 20,
) -> list[StockScore]:
    """
    Verilen sembolleri tara ve kriterlere uyanları döndür.

    Args:
        symbols: Taranacak semboller
        criteria: Tarama kriterleri (None ise default)
        max_results: Maximum sonuç sayısı

    Returns:
        StockScore listesi (skora göre sıralı)
    """
    if criteria is None:
        criteria = ScreeningCriteria()

    results = []
    total = len(symbols)

    print(f"\n{'=' * 60}")
    print("EGM Stock Screener - Earnings Growth Momentum")
    print(f"{'=' * 60}")
    print(f"Taranan hisse sayısı: {total}")
    print("Tarama kriterleri:")
    print(f"  - Min EPS Q Growth: {criteria.min_quarterly_eps_growth:.0%}")
    print(f"  - Min EPS Y Growth: {criteria.min_annual_eps_growth:.0%}")
    print(f"  - Min Revenue Growth: {criteria.min_revenue_growth:.0%}")
    print(f"  - Max Distance from 52W High: {criteria.max_distance_from_high:.0%}")
    print(f"  - Min Volume Surge: {criteria.min_volume_surge}x")
    print(f"{'=' * 60}\n")

    for i, symbol in enumerate(symbols, 1):
        print(f"Taraniyor [{i}/{total}]: {symbol}...", end="\r")
        result = analyze_stock(symbol, criteria)
        if result:
            results.append(result)

    # Skora göre sırala
    results.sort(key=lambda x: x.total_score, reverse=True)

    return results[:max_results]


def print_results(results: list[StockScore]) -> None:
    """Sonuçları formatla ve yazdır."""
    if not results:
        print("\nKriterlere uyan hisse bulunamadı.")
        return

    print(f"\n{'=' * 80}")
    print(f"SONUÇLAR - {len(results)} hisse bulundu")
    print(f"{'=' * 80}\n")

    for i, stock in enumerate(results, 1):
        print(f"\n{'-' * 60}")
        print(f"#{i} {stock.symbol} - {stock.company_name}")
        print(f"    Fiyat: ${stock.current_price:.2f} | Skor: {stock.total_score}/15")
        print(f"    52W High'dan Uzaklık: {stock.distance_from_high:.1%}")
        print(f"    Hacim Oranı: {stock.volume_ratio:.1f}x | RSI: {stock.rsi:.0f}")
        print(f"    EMA Ribbon: {'✓ Bullish' if stock.ema_ribbon_bullish else '✗ Bearish'}")
        print(f"    EMA 200: {'✓ Üstünde' if stock.above_ema200 else '✗ Altında'}")
        print("\n    Sinyaller:")
        for signal in stock.signals:
            print(f"      {signal}")

    # Summary table
    print(f"\n\n{'=' * 80}")
    print("ÖZET TABLO")
    print(f"{'=' * 80}")
    print(f"{'Sembol':<8} {'Şirket':<25} {'Fiyat':>10} {'Skor':>6} {'EMA':>8} {'RSI':>6}")
    print(f"{'-' * 80}")
    for stock in results:
        ema_status = "✓" if stock.ema_ribbon_bullish else "✗"
        print(
            f"{stock.symbol:<8} {stock.company_name[:24]:<25} "
            f"${stock.current_price:>8.2f} {stock.total_score:>6} "
            f"{ema_status:>8} {stock.rsi:>6.0f}"
        )


def main():
    """Ana fonksiyon."""
    print("\n" + "=" * 60)
    print("LoneStockTrader EGM Stock Screener")
    print("Earnings Growth Momentum Methodology")
    print("=" * 60)

    # Tarama kriterleri
    criteria = ScreeningCriteria(
        min_quarterly_eps_growth=0.20,  # %20 (biraz esnek)
        min_annual_eps_growth=0.15,
        min_revenue_growth=0.10,
        min_roe=0.10,
        max_distance_from_high=0.30,  # %30
        min_volume_surge=1.3,  # 1.3x
        min_rsi=45,
        max_rsi=75,
    )

    # Taranacak hisseler
    print("\n1. Growth Stocks taranıyor...")
    growth_symbols = get_growth_stocks()
    results_growth = screen_stocks(growth_symbols, criteria, max_results=15)

    print("\n2. NASDAQ-100 taranıyor...")
    nasdaq_symbols = get_nasdaq100_symbols()
    results_nasdaq = screen_stocks(nasdaq_symbols, criteria, max_results=10)

    # Sonuçları birleştir ve tekrarları kaldır
    all_results = {r.symbol: r for r in results_growth + results_nasdaq}
    final_results = sorted(all_results.values(), key=lambda x: x.total_score, reverse=True)

    print_results(final_results[:20])

    # Trading notes
    print(f"\n\n{'=' * 60}")
    print("TRADİNG NOTLARI (CANSLIM/EGM)")
    print(f"{'=' * 60}")
    print("""
    1. ENTRY: Breakout + Volume surge bekleyin
    2. STOP LOSS: %7-8 altında (sert disiplin)
    3. POSITION SIZE: Portföyün %5-10'u max
    4. MARKET: Genel piyasa yönünü kontrol edin (SPY/QQQ)
    5. EXIT: EMA ribbon bearish olduğunda veya %20-25 kar

    DIKKAT: Bu bir tavsiye değil, tarama aracıdır.
    Kendi araştırmanızı yapın ve risk yönetimi uygulayın.
    """)


if __name__ == "__main__":
    main()
