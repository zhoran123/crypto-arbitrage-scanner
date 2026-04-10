"""
Быстрый тест агрегатора — запусти, чтобы убедиться что всё ОК.

Команда:   python test_aggregator.py
Ожидание:  все строки покажут  ✅
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.aggregator import Aggregator


def main():
    agg = Aggregator()
    errors = 0

    # --- Тест 1: запись и чтение цены ---
    agg.update("BTCUSDT", "binance", 67000.0, 67000.1)
    data = agg.get_prices("BTCUSDT")
    if data and "binance" in data and data["binance"]["bid"] == 67000.0:
        print("✅ Тест 1: запись/чтение цены — ОК")
    else:
        print("❌ Тест 1: запись/чтение цены — ОШИБКА")
        errors += 1

    # --- Тест 2: две биржи ---
    agg.update("BTCUSDT", "bybit", 66998.0, 66998.2)
    data = agg.get_prices("BTCUSDT")
    if data and len(data) == 2:
        print("✅ Тест 2: две биржи по одному символу — ОК")
    else:
        print("❌ Тест 2: две биржи — ОШИБКА")
        errors += 1

    # --- Тест 3: get_pair ---
    a, b = agg.get_pair("BTCUSDT", "binance", "bybit")
    if a and b and a["bid"] == 67000.0 and b["bid"] == 66998.0:
        print("✅ Тест 3: get_pair — ОК")
    else:
        print("❌ Тест 3: get_pair — ОШИБКА")
        errors += 1

    # --- Тест 4: is_fresh ---
    if agg.is_fresh("BTCUSDT", "binance", max_age=5.0):
        print("✅ Тест 4: is_fresh — ОК")
    else:
        print("❌ Тест 4: is_fresh — ОШИБКА")
        errors += 1

    # --- Тест 5: несуществующий символ ---
    if agg.get_prices("FAKEUSDT") is None:
        print("✅ Тест 5: несуществующий символ — ОК")
    else:
        print("❌ Тест 5: несуществующий символ — ОШИБКА")
        errors += 1

    # --- Тест 6: callback ---
    called = []
    agg.set_on_update(lambda sym, exch, bid, ask: called.append(sym))
    agg.update("ETHUSDT", "binance", 3400.0, 3400.1)
    if called == ["ETHUSDT"]:
        print("✅ Тест 6: callback on_update — ОК")
    else:
        print("❌ Тест 6: callback — ОШИБКА")
        errors += 1

    # --- Тест 7: счётчик обновлений ---
    # 2 (BTC binance + bybit) + 1 (ETH) = 3
    if agg.update_count == 3:
        print("✅ Тест 7: update_count — ОК")
    else:
        print(f"❌ Тест 7: update_count = {agg.update_count}, ожидалось 3")
        errors += 1

    # --- Итог ---
    print()
    if errors == 0:
        print("🎉 Все тесты пройдены! Aggregator работает.")
    else:
        print(f"⚠️  Ошибок: {errors}")


if __name__ == "__main__":
    main()
