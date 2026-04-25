import math
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from config import FEES, MAX_SIGNAL_SPREAD, MIN_DEVIATION, WINDOW, Z_THRESHOLD


class _RunningStats:
    __slots__ = ("_window", "_values", "_sum", "_sum_sq", "_n")

    def __init__(self, window: int):
        self._window = window
        self._values: deque[float] = deque(maxlen=window)
        self._sum = 0.0
        self._sum_sq = 0.0
        self._n = 0

    def push(self, value: float) -> tuple[float, float]:
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
    def __init__(self, on_signal=None):
        self._on_signal = on_signal
        self._on_pair = None
        self._spread_stats: dict[str, _RunningStats] = {}
        self._signal_count = 0

    def set_on_signal(self, callback):
        self._on_signal = callback

    def set_on_pair(self, callback):
        self._on_pair = callback

    def on_price_update(self, symbol: str, prices_for_symbol: dict, updated_exchange: str | None = None):
        """
        Инкрементальная оценка: если задан updated_exchange — оцениваем
        только пары, в которых эта биржа участвует (2*(N-1) пар вместо N*(N-1)).
        Без updated_exchange — fallback на полный N² перебор.
        """
        if not prices_for_symbol:
            return
        if len(prices_for_symbol) < 2:
            return

        on_signal = self._on_signal

        if updated_exchange is not None and updated_exchange in prices_for_symbol:
            updated_data = prices_for_symbol[updated_exchange]
            updated_bid = updated_data["bid"]
            updated_ask = updated_data["ask"]

            for other_exchange, other_data in prices_for_symbol.items():
                if other_exchange == updated_exchange:
                    continue
                other_bid = other_data["bid"]
                other_ask = other_data["ask"]

                # Pair A: sell on updated, buy on other
                signal = self._evaluate(symbol, other_exchange, updated_exchange, other_ask, updated_bid)
                if signal:
                    self._signal_count += 1
                    if on_signal:
                        on_signal(signal)

                # Pair B: sell on other, buy on updated
                signal = self._evaluate(symbol, updated_exchange, other_exchange, updated_ask, other_bid)
                if signal:
                    self._signal_count += 1
                    if on_signal:
                        on_signal(signal)
            return

        # Fallback: full N² evaluation (used when triggering exchange unknown)
        items = list(prices_for_symbol.items())
        for sell_index, (sell_exchange, sell_data) in enumerate(items):
            sell_price = sell_data["bid"]
            for buy_index, (buy_exchange, buy_data) in enumerate(items):
                if sell_index == buy_index:
                    continue
                signal = self._evaluate(symbol, buy_exchange, sell_exchange, buy_data["ask"], sell_price)
                if signal:
                    self._signal_count += 1
                    if on_signal:
                        on_signal(signal)

    def _evaluate(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        buy_price: float,
        sell_price: float,
    ) -> Optional[dict]:
        if buy_price <= 0 or sell_price <= 0:
            return None

        gross_spread_pct = ((sell_price - buy_price) / buy_price) * 100
        net_spread_pct = gross_spread_pct - FEES.get(buy_exchange, 0.04) - FEES.get(sell_exchange, 0.04)

        if gross_spread_pct > MAX_SIGNAL_SPREAD or net_spread_pct > MAX_SIGNAL_SPREAD:
            return None

        if "dex" in (buy_exchange, sell_exchange) and gross_spread_pct > 50:
            return None

        if self._on_pair:
            self._on_pair(
                symbol,
                buy_exchange,
                sell_exchange,
                gross_spread_pct,
                buy_price,
                sell_price,
            )

        pair_key = (symbol, buy_exchange, sell_exchange)
        z_score = self._update_zscore(pair_key, gross_spread_pct)

        if z_score < Z_THRESHOLD or gross_spread_pct < MIN_DEVIATION:
            return None

        return {
            "symbol": symbol,
            "buy_on": buy_exchange,
            "sell_on": sell_exchange,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "deviation_pct": round(gross_spread_pct, 4),
            "net_spread_pct": round(net_spread_pct, 4),
            "z_score": round(z_score, 2),
            "quality": self._calc_quality(z_score, net_spread_pct),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }

    def _update_zscore(self, pair_key: tuple, spread: float) -> float:
        stats = self._spread_stats.get(pair_key)
        if stats is None:
            stats = _RunningStats(WINDOW)
            self._spread_stats[pair_key] = stats

        mean, std = stats.push(spread)
        if stats.count < 10 or std < 1e-9:
            return 0.0
        return (spread - mean) / std

    def _calc_quality(self, z_score: float, net_spread_pct: float) -> int:
        z_part = min((z_score - Z_THRESHOLD) / (10 - Z_THRESHOLD), 1.0) * 50
        spread_part = min(max(net_spread_pct, 0.0) / 3.0, 1.0) * 50
        return max(0, min(100, int(z_part + spread_part)))

    @property
    def signal_count(self) -> int:
        return self._signal_count

    def get_history_size(self, pair_key: tuple) -> int:
        stats = self._spread_stats.get(pair_key)
        return stats.count if stats else 0

    def __repr__(self):
        return f"<SignalEngine: {len(self._spread_stats)} pairs tracked, {self._signal_count} signals>"
