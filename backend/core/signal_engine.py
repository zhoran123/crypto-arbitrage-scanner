"""
Signal Engine — мозг арбитражного сканера.

Как это работает:
1. Aggregator вызывает  on_price_update(symbol, exchange, bid, ask)
   каждый раз, когда приходит новая цена с любой биржи.
2. Signal Engine сравнивает цены между ВСЕМИ парами бирж:
   - Binance bid vs Bybit ask  (купить на Bybit, продать на Binance)
   - Bybit bid vs Binance ask  (купить на Binance, продать на Bybit)
3. Считает:
   - spread (разница в %)
   - net_spread (spread минус комиссии обеих бирж)
   - z_score (насколько текущий spread аномален по сравнению с историей)
   - quality (оценка 0–100 для фронтенда)
4. Если z_score > Z_THRESHOLD и deviation > MIN_DEVIATION → генерируется сигнал.
"""

import time
import math
from datetime import datetime, timezone
from collections import deque
from typing import Optional

from config import Z_THRESHOLD, MIN_DEVIATION, WINDOW, FEES, EXCHANGES


class _RunningStats:
    """Инкрементальная статистика (mean/std) для скользящего окна.
    Не создаёт numpy массив на каждый тик — O(1) на обновление."""

    __slots__ = ("_window", "_values", "_sum", "_sum_sq", "_n")

    def __init__(self, window: int):
        self._window = window
        self._values: deque[float] = deque(maxlen=window)
        self._sum = 0.0
        self._sum_sq = 0.0
        self._n = 0

    def push(self, value: float) -> tuple[float, float]:
        """Добавить значение, вернуть (mean, std)."""
        # Если окно полное — вычитаем старое значение
        if self._n == self._window:
            old = self._values[0]
            self._sum -= old
            self._sum_sq -= old * old
        else:
            self._n += 1

        self._values.append(value)
        self._sum += value
        self._sum_sq += value * value

        mean = self._sum / self._n
        variance = (self._sum_sq / self._n) - (mean * mean)
        std = math.sqrt(max(variance, 0.0))
        return mean, std

    @property
    def count(self) -> int:
        return self._n


class SignalEngine:
    """Обнаружение арбитражных возможностей между биржами."""

    def __init__(self, on_signal=None):
        """
        on_signal — callback, вызывается при обнаружении сигнала.
        Сюда подключится WebSocket для отправки на фронтенд
        и Telegram-алерт.
        """
        self._on_signal = on_signal

        # Running stats для расчёта z-score (вместо numpy).
        # Ключ: "BTCUSDT|binance|bybit" → _RunningStats
        self._spread_stats: dict[str, _RunningStats] = {}

        # Счётчик сигналов
        self._signal_count = 0

        # Hook для трекера конвергенции (и других наблюдателей)
        # Вызывается на каждой рассчитанной паре (symbol, buy_exch, sell_exch, gross, buy_price, sell_price)
        self._on_pair = None

    def set_on_pair(self, callback):
        self._on_pair = callback

    # ------------------------------------------------------------------
    # Подписка на сигналы
    # ------------------------------------------------------------------

    def set_on_signal(self, callback):
        """Задать callback для новых сигналов: callback(signal_dict)."""
        self._on_signal = callback

    # ------------------------------------------------------------------
    # Главный метод — вызывается агрегатором при каждом обновлении цены
    # ------------------------------------------------------------------

    def on_price_update(self, symbol: str, prices_for_symbol: dict):
        """
        Проверить все пары бирж для данного символа.

        prices_for_symbol — словарь из агрегатора:
        {
            "binance": {"bid": 67000.0, "ask": 67000.1, "ts": ...},
            "bybit":   {"bid": 66998.0, "ask": 66998.2, "ts": ...},
        }
        """
        if not prices_for_symbol:
            return

        exchanges = list(prices_for_symbol.keys())
        if len(exchanges) < 2:
            return  # нужно минимум 2 биржи для сравнения

        # Перебираем все пары бирж
        for i in range(len(exchanges)):
            for j in range(len(exchanges)):
                if i == j:
                    continue

                sell_exch = exchanges[i]   # продаём тут (берём bid)
                buy_exch = exchanges[j]    # покупаем тут (берём ask)

                sell_data = prices_for_symbol[sell_exch]
                buy_data = prices_for_symbol[buy_exch]

                sell_price = sell_data["bid"]    # цена продажи
                buy_price = buy_data["ask"]      # цена покупки

                # Считаем spread
                signal = self._evaluate(
                    symbol, buy_exch, sell_exch, buy_price, sell_price
                )

                if signal:
                    self._signal_count += 1
                    if self._on_signal:
                        self._on_signal(signal)

    # ------------------------------------------------------------------
    # Расчёт spread, z-score, quality
    # ------------------------------------------------------------------

    def _evaluate(
        self,
        symbol: str,
        buy_exch: str,
        sell_exch: str,
        buy_price: float,
        sell_price: float,
    ) -> Optional[dict]:
        """
        Оценить пару бирж. Вернуть сигнал (dict) или None.
        """
        if buy_price <= 0 or sell_price <= 0:
            return None

        # --- Gross spread (до комиссий) ---
        gross_spread_pct = ((sell_price - buy_price) / buy_price) * 100

        # --- Net spread (после комиссий) ---
        fee_buy = FEES.get(buy_exch, 0.04)
        fee_sell = FEES.get(sell_exch, 0.04)
        total_fee = fee_buy + fee_sell
        net_spread_pct = gross_spread_pct - total_fee

        # --- Hook для трекера конвергенции (и т.п.) ---
        if self._on_pair:
            try:
                self._on_pair(symbol, buy_exch, sell_exch, gross_spread_pct, buy_price, sell_price)
            except Exception:
                pass

        # --- Z-score ---
        pair_key = f"{symbol}|{buy_exch}|{sell_exch}"
        z_score = self._update_zscore(pair_key, gross_spread_pct)

        # --- Фильтр: оба условия должны выполняться ---
        if z_score < Z_THRESHOLD or gross_spread_pct < MIN_DEVIATION:
            return None

        # --- Quality score (0–100) ---
        quality = self._calc_quality(z_score, net_spread_pct)

        # --- Формируем сигнал ---
        return {
            "symbol": symbol,
            "buy_on": buy_exch,
            "sell_on": sell_exch,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "deviation_pct": round(gross_spread_pct, 4),
            "net_spread_pct": round(net_spread_pct, 4),
            "z_score": round(z_score, 2),
            "quality": quality,
            "timestamp": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ),
        }

    # ------------------------------------------------------------------
    # Z-score: насколько текущий spread аномален
    # ------------------------------------------------------------------

    def _update_zscore(self, pair_key: str, spread: float) -> float:
        """
        Добавить spread в историю и вернуть z-score.
        Использует O(1) running stats вместо numpy array.
        """
        stats = self._spread_stats.get(pair_key)
        if stats is None:
            stats = _RunningStats(WINDOW)
            self._spread_stats[pair_key] = stats

        mean, std = stats.push(spread)

        # Нужно минимум 10 значений для осмысленной статистики
        if stats.count < 10:
            return 0.0

        if std < 1e-9:
            return 0.0

        return (spread - mean) / std

    # ------------------------------------------------------------------
    # Quality score для фронтенда
    # ------------------------------------------------------------------

    def _calc_quality(self, z_score: float, net_spread_pct: float) -> int:
        """
        Оценка «качества» сигнала от 0 до 100.

        Логика:
        - 50% веса от z_score (чем аномальнее, тем лучше)
        - 50% веса от net_spread (чем больше чистая прибыль, тем лучше)

        Максимум z_score для расчёта: 10
        Максимум net_spread для расчёта: 3%
        """
        # Z-score: от 3 до 10 → от 0 до 50 баллов
        z_part = min((z_score - Z_THRESHOLD) / (10 - Z_THRESHOLD), 1.0) * 50

        # Net spread: от 0 до 3% → от 0 до 50 баллов
        spread_part = min(max(net_spread_pct, 0) / 3.0, 1.0) * 50

        return max(0, min(100, int(z_part + spread_part)))

    # ------------------------------------------------------------------
    # Отладка
    # ------------------------------------------------------------------

    @property
    def signal_count(self) -> int:
        """Сколько сигналов сгенерировано с момента запуска."""
        return self._signal_count

    def get_history_size(self, pair_key: str) -> int:
        """Размер истории спредов для пары."""
        s = self._spread_stats.get(pair_key)
        return s.count if s else 0

    def __repr__(self):
        pairs = len(self._spread_stats)
        return (
            f"<SignalEngine: {pairs} pairs tracked, "
            f"{self._signal_count} signals>"
        )
