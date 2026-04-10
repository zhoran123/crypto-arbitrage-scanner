"""
Тест Signal Engine — запусти чтобы убедиться что всё ОК.

Команда:   python test_signal_engine.py
Ожидание:  все строки покажут  ✅
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.aggregator import Aggregator
from core.signal_engine import SignalEngine


def main():
    errors = 0
    signals = []

    # Создаём агрегатор + движок, связываем их
    agg = Aggregator()
    engine = SignalEngine(on_signal=lambda s: signals.append(s))

    def on_price(symbol, exchange, bid, ask):
        """Когда агрегатор получает цену — передаём в движок."""
        agg.update(symbol, exchange, bid, ask)
        prices = agg.get_prices(symbol)
        if prices:
            engine.on_price_update(symbol, prices)

    # --- Тест 1: одна биржа — сигналов нет (нужно минимум 2) ---
    signals.clear()
    on_price("BTCUSDT", "binance", 67000.0, 67000.1)
    if len(signals) == 0:
        print("✅ Тест 1: одна биржа — нет сигналов — ОК")
    else:
        print("❌ Тест 1: не должно быть сигналов с одной биржей")
        errors += 1

    # --- Тест 2: две биржи, маленький spread — нет сигнала ---
    signals.clear()
    # Цены почти одинаковые — не должно быть сигнала
    for i in range(20):
        on_price("ETHUSDT", "binance", 3400.0 + i * 0.01, 3400.1 + i * 0.01)
        on_price("ETHUSDT", "bybit",   3400.0 + i * 0.01, 3400.1 + i * 0.01)

    if len(signals) == 0:
        print("✅ Тест 2: маленький spread — нет сигналов — ОК")
    else:
        print(f"❌ Тест 2: получили {len(signals)} сигналов при маленьком spread")
        errors += 1

    # --- Тест 3: набираем историю, потом резкий скачок → сигнал ---
    signals.clear()

    # Сначала 40 «нормальных» обновлений — spread около 0
    for i in range(40):
        on_price("SOLUSDT", "binance", 150.00, 150.01)
        on_price("SOLUSDT", "bybit",   150.00, 150.01)

    # Теперь резкий разрыв: на Bybit bid сильно ниже
    # Binance bid=150.00, Bybit ask=149.80 → spread ~0.13%
    signals.clear()
    on_price("SOLUSDT", "bybit", 149.70, 149.80)

    if len(signals) > 0:
        sig = signals[0]
        print(f"✅ Тест 3: аномальный spread → сигнал получен — ОК")
        print(f"   → {sig['symbol']}: купить на {sig['buy_on']}, "
              f"продать на {sig['sell_on']}, "
              f"z={sig['z_score']}, spread={sig['deviation_pct']}%")
    else:
        print("❌ Тест 3: ожидался сигнал при резком скачке")
        errors += 1

    # --- Тест 4: формат сигнала содержит все нужные поля ---
    if len(signals) > 0:
        required = [
            "symbol", "buy_on", "sell_on", "buy_price", "sell_price",
            "deviation_pct", "z_score", "quality", "net_spread_pct",
            "timestamp"
        ]
        sig = signals[0]
        missing = [f for f in required if f not in sig]
        if not missing:
            print("✅ Тест 4: формат сигнала — все поля на месте — ОК")
        else:
            print(f"❌ Тест 4: не хватает полей: {missing}")
            errors += 1
    else:
        print("⚠️  Тест 4: пропущен (нет сигналов из теста 3)")
        errors += 1

    # --- Тест 5: quality в диапазоне 0–100 ---
    if len(signals) > 0:
        q = signals[0]["quality"]
        if 0 <= q <= 100:
            print(f"✅ Тест 5: quality = {q} (в диапазоне 0–100) — ОК")
        else:
            print(f"❌ Тест 5: quality = {q} — вне диапазона")
            errors += 1
    else:
        print("⚠️  Тест 5: пропущен")
        errors += 1

    # --- Тест 6: signal_count ---
    total = engine.signal_count
    if total > 0:
        print(f"✅ Тест 6: signal_count = {total} — ОК")
    else:
        print("❌ Тест 6: signal_count = 0")
        errors += 1

    # --- Итог ---
    print()
    if errors == 0:
        print("🎉 Все тесты пройдены! Signal Engine работает.")
    else:
        print(f"⚠️  Ошибок: {errors}")


if __name__ == "__main__":
    main()
