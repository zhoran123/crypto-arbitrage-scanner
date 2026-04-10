"""
Aggregator — центральный модуль сбора цен со всех бирж.

Как это работает:
1. Каждый коннектор (Binance, Bybit, ...) при получении новой цены
   вызывает  aggregator.update(symbol, exchange, bid, ask)
2. Агрегатор сохраняет данные в словарь  prices[symbol][exchange]
3. Любой другой модуль (signal_engine) может прочитать текущие цены
   через  aggregator.get_prices(symbol)
"""

import time
from typing import Optional


class Aggregator:
    """Хранилище актуальных bid/ask со всех бирж."""

    def __init__(self):
        # Главный словарь цен.
        # Формат:
        # {
        #   "BTCUSDT": {
        #       "binance": {"bid": 67000.0, "ask": 67000.1, "ts": 17123...},
        #       "bybit":   {"bid": 66998.0, "ask": 66998.2, "ts": 17123...},
        #   },
        #   ...
        # }
        self.prices: dict[str, dict[str, dict]] = {}

        # Счётчик обновлений — пригодится для отладки
        self._update_count = 0

        # Callback, который вызовется после каждого обновления цены.
        # Signal engine подпишется сюда, чтобы проверять арбитраж.
        self._on_update = None

    # ------------------------------------------------------------------
    # Подписка на обновления
    # ------------------------------------------------------------------

    def set_on_update(self, callback):
        """
        Задать функцию, которая вызовется после каждого обновления цены.
        callback(symbol, exchange, bid, ask)
        """
        self._on_update = callback

    # ------------------------------------------------------------------
    # Запись цен (вызывается коннекторами)
    # ------------------------------------------------------------------

    def update(self, symbol: str, exchange: str, bid: float, ask: float):
        """
        Коннектор вызывает этот метод при каждом обновлении цены.
        Сохраняет bid/ask + текущее время в словарь.
        """
        if symbol not in self.prices:
            self.prices[symbol] = {}

        self.prices[symbol][exchange] = {
            "bid": bid,
            "ask": ask,
            "ts": time.time(),
        }

        self._update_count += 1

        # Уведомляем signal_engine (если подписан)
        if self._on_update:
            self._on_update(symbol, exchange, bid, ask)

    # ------------------------------------------------------------------
    # Чтение цен (используется signal_engine)
    # ------------------------------------------------------------------

    def get_prices(self, symbol: str) -> Optional[dict]:
        """
        Вернуть все цены по символу.
        Возвращает словарь {exchange: {bid, ask, ts}} или None.
        """
        return self.prices.get(symbol)

    def get_pair(self, symbol: str, exch_a: str, exch_b: str):
        """
        Вернуть bid/ask для конкретной пары бирж.
        Удобно для быстрого сравнения двух бирж.

        Возвращает (data_a, data_b) или (None, None) если данных нет.
        """
        symbol_data = self.prices.get(symbol)
        if not symbol_data:
            return None, None

        return symbol_data.get(exch_a), symbol_data.get(exch_b)

    def get_all_symbols(self) -> list[str]:
        """Список всех символов, по которым есть хотя бы одна цена."""
        return list(self.prices.keys())

    # ------------------------------------------------------------------
    # Проверка «свежести» данных
    # ------------------------------------------------------------------

    def is_fresh(self, symbol: str, exchange: str, max_age: float = 5.0) -> bool:
        """
        Проверить, что цена не старше max_age секунд.
        Если данных нет — вернёт False.
        """
        symbol_data = self.prices.get(symbol)
        if not symbol_data:
            return False

        entry = symbol_data.get(exchange)
        if not entry:
            return False

        return (time.time() - entry["ts"]) <= max_age

    # ------------------------------------------------------------------
    # Отладка
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Вернуть полную копию всех цен (для логов / debug)."""
        return {
            symbol: {
                exch: {**data}
                for exch, data in exchanges.items()
            }
            for symbol, exchanges in self.prices.items()
        }

    @property
    def update_count(self) -> int:
        """Сколько раз обновлялись цены с момента запуска."""
        return self._update_count

    def __repr__(self):
        symbols = len(self.prices)
        exchanges = set()
        for exch_dict in self.prices.values():
            exchanges.update(exch_dict.keys())
        return (
            f"<Aggregator: {symbols} symbols, "
            f"{len(exchanges)} exchanges, "
            f"{self._update_count} updates>"
        )
