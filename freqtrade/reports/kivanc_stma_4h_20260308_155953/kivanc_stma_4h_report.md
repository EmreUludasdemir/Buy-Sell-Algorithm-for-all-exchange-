# Kivanc SuperTrended Moving Averages 4H Backtest Report

Bu rapor 1 g?nl?k hyperopt ile bulunan mevcut parametrelerin 4 saatlik mumlarda do?rudan uygulanmas?yla ?retildi. Bu nedenle sonu?lar 4h i?in optimize edilmi? sonu?lar de?ildir.

## Scenario Summary

| Senaryo | Tarih | Getiri | 1000 USDT Sonu? | ??lem | Win Rate | PF | MaxDD | Market | Markete G?re | Ortalama Elde Tutma | En ?yi Pair |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| bear_2022 | 2022-05-01 00:00:00 -> 2022-12-31 00:00:00 | -24.57% | 754.31 | 46 | 23.91% | 0.51 | 27.87% | -56.16% | 31.59% | 12 days, 8:00:00 | ETH/USDT (3.15%) |
| recovery_2023 | 2023-01-01 00:00:00 -> 2023-12-31 00:00:00 | 74.33% | 1743.33 | 80 | 27.50% | 2.00 | 19.85% | 253.94% | -179.61% | 9 days, 17:57:00 | SOL/USDT (68.13%) |
| bull_2024 | 2024-01-01 00:00:00 -> 2024-12-31 00:00:00 | 65.85% | 1658.50 | 65 | 38.46% | 1.98 | 17.65% | 121.61% | -55.76% | 11 days, 11:56:00 | SOL/USDT (23.71%) |
| choppy_2025 | 2025-01-01 00:00:00 -> 2025-12-31 00:00:00 | -34.17% | 658.31 | 77 | 25.97% | 0.55 | 36.49% | -8.10% | -26.07% | 10 days, 1:02:00 | BNB/USDT (2.92%) |
| ytd_2026 | 2026-01-01 00:00:00 -> 2026-03-01 00:00:00 | -3.41% | 965.94 | 10 | 60.00% | 0.53 | 7.17% | -27.07% | 23.66% | 9 days, 9:36:00 | BNB/USDT (0.00%) |
| full_2022_2026 | 2022-01-01 00:00:00 -> 2026-03-01 00:00:00 | 30.17% | 1301.70 | 295 | 31.19% | 1.08 | 38.56% | 7.88% | 22.29% | 10 days, 22:48:00 | SOL/USDT (50.09%) |

## Full Period Pair Breakdown

| Pair | Getiri | ??lem | PF |
|---|---:|---:|---:|
| SOL/USDT | 50.09% | 57 | 1.57 |
| XRP/USDT | 16.16% | 56 | 1.19 |
| BTC/USDT | 1.41% | 68 | 1.03 |
| BNB/USDT | -8.19% | 48 | 0.81 |
| ETH/USDT | -29.29% | 66 | 0.69 |

## Key Takeaways

- Full d?nem 4h sonu?: 1000 USDT -> 1301.70 USDT, toplam getiri 30.17%, toplam 295 i?lem.
- Full d?nemde en iyi pair SOL/USDT (50.09%), en zay?f pair ETH/USDT (-29.29%).
- 2023 ve 2024 y?kseli? d?nemlerinde pozitif ama marketin gerisinde kald?.
- 2022 ay? piyasas?nda marketten daha az d??t?, ancak yine de zarar yazd?.
- 2025 yatay/dalgal? d?nemde belirgin ?ekilde k?t? performans verdi ve drawdown y?kseldi.
- 4h sonu?lar, ayn? stratejinin 1d optimize edilmi? versiyonuna g?re daha zay?f ve daha oynak g?r?n?yor.
