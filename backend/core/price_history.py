"""
price_history.py — In-memory ring buffer for 1-minute price candles.

Stores mid-price (avg of bid+ask) per symbol × exchange.
Aggregates raw ticks into 1m candles. Keeps last 2 hours (120 candles).
Supports on-the-fly aggregation to 5m, 15m, 1h timeframes.
"""

import time
from collections import defaultdict


# Max 1m candles to keep per symbol×exchange (4 hours)
MAX_CANDLES = 240


class PriceHistory:

    def __init__(self, max_candles: int = MAX_CANDLES):
        self._max = max_candles
        # {symbol: {exchange: [candle, ...]}}
        # candle = {"t": minute_ts, "o": open, "h": high, "l": low, "c": close}
        self._data: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        # Current tick accumulator: {symbol: {exchange: {"t": minute_ts, "o","h","l","c"}}}
        self._current: dict[str, dict[str, dict]] = defaultdict(dict)

    def on_price(self, symbol: str, exchange: str, bid: float, ask: float):
        """Called on every price update. Aggregates into 1m candles."""
        mid = (bid + ask) / 2
        now = time.time()
        minute_ts = int(now // 60) * 60  # floor to current minute

        cur = self._current[symbol].get(exchange)

        if cur and cur["t"] == minute_ts:
            # Same minute — update candle
            cur["h"] = max(cur["h"], mid)
            cur["l"] = min(cur["l"], mid)
            cur["c"] = mid
        else:
            # New minute — flush previous candle if exists
            if cur:
                candles = self._data[symbol][exchange]
                candles.append(cur)
                if len(candles) > self._max:
                    del candles[: len(candles) - self._max]

            # Start new candle
            self._current[symbol][exchange] = {
                "t": minute_ts,
                "o": mid,
                "h": mid,
                "l": mid,
                "c": mid,
            }

    def get_history(self, symbol: str, tf: str = "1m") -> dict[str, list[dict]]:
        """
        Return price history for a symbol across all exchanges.

        Args:
            symbol: e.g. "BTCUSDT"
            tf: "1m", "5m", "15m", "1h"

        Returns:
            {exchange: [{"t": unix_ts, "o": ..., "h": ..., "l": ..., "c": ...}, ...]}
        """
        if symbol not in self._data and symbol not in self._current:
            return {}

        result = {}
        exchanges = set(self._data.get(symbol, {}).keys()) | set(self._current.get(symbol, {}).keys())

        for exch in exchanges:
            # Combine flushed candles + current candle
            candles = list(self._data.get(symbol, {}).get(exch, []))
            cur = self._current.get(symbol, {}).get(exch)
            if cur:
                candles.append(cur)

            if not candles:
                continue

            if tf == "1m":
                result[exch] = candles
            else:
                result[exch] = self._aggregate(candles, tf)

        return result

    @staticmethod
    def _aggregate(candles: list[dict], tf: str) -> list[dict]:
        """Aggregate 1m candles into larger timeframes."""
        seconds = {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}.get(tf, 60)
        if seconds == 60:
            return candles

        grouped: dict[int, list[dict]] = {}
        for c in candles:
            bucket = int(c["t"] // seconds) * seconds
            grouped.setdefault(bucket, []).append(c)

        result = []
        for bucket_ts in sorted(grouped):
            group = grouped[bucket_ts]
            result.append({
                "t": bucket_ts,
                "o": group[0]["o"],
                "h": max(c["h"] for c in group),
                "l": min(c["l"] for c in group),
                "c": group[-1]["c"],
            })
        return result
