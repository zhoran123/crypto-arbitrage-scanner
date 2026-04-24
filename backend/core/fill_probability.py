import math
import time
from collections import defaultdict, deque


EXCHANGE_RELIABILITY = {
    "binance": 0.97,
    "bybit": 0.93,
    "okx": 0.92,
    "bitget": 0.88,
    "gate": 0.84,
    "kucoin": 0.83,
    "bingx": 0.80,
    "mexc": 0.74,
    "dex": 0.58,
}

VOLATILITY_WINDOW_SEC = 60
VOLATILITY_SAMPLE_SEC = 1.0
SPREAD_GAP_RESET_SEC = 8
SPREAD_TRACK_SAMPLE_SEC = 1.0
SPREAD_PROXY_TARGET_SEC = 10
SPREAD_STATE_TTL_SEC = 45
STABILITY_TARGET_SEC = 30
CLEANUP_INTERVAL_SEC = 5.0


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class FillProbabilityModel:
    def __init__(self):
        self._mid_history: dict[tuple[str, str], deque[tuple[float, float]]] = defaultdict(deque)
        self._mid_stats: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"sum": 0.0, "sum_sq": 0.0})
        self._last_mid_sample: dict[tuple[str, str], float] = {}
        self._spread_state: dict[tuple[str, str, str], dict] = {}
        self._last_spread_sample: dict[tuple[str, str, str], float] = {}
        self._proxy_history: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "total": 0})
        self._last_cleanup_ts = 0.0

    def on_price(self, symbol: str, exchange: str, bid: float, ask: float):
        if bid <= 0 or ask <= 0:
            return

        now = time.time()
        key = (symbol.upper(), exchange)
        mid = (bid + ask) / 2

        last_sample = self._last_mid_sample.get(key, 0.0)
        if (now - last_sample) < VOLATILITY_SAMPLE_SEC:
            return
        self._last_mid_sample[key] = now

        window = self._mid_history[key]
        stats = self._mid_stats[key]
        window.append((now, mid))
        stats["sum"] += mid
        stats["sum_sq"] += mid * mid

        cutoff = now - VOLATILITY_WINDOW_SEC
        while window and window[0][0] < cutoff:
            _, old_mid = window.popleft()
            stats["sum"] -= old_mid
            stats["sum_sq"] -= old_mid * old_mid

    def track_spread(self, symbol: str, buy_exchange: str, sell_exchange: str, gross_spread_pct: float):
        now = time.time()
        if (now - self._last_cleanup_ts) >= CLEANUP_INTERVAL_SEC:
            self._cleanup_spread_state(now)
            self._last_cleanup_ts = now

        if gross_spread_pct <= 0:
            return

        key = (symbol.upper(), buy_exchange, sell_exchange)
        last_sample = self._last_spread_sample.get(key, 0.0)
        if key in self._spread_state and (now - last_sample) < SPREAD_TRACK_SAMPLE_SEC:
            return
        self._last_spread_sample[key] = now

        state = self._spread_state.get(key)

        if state is None or (now - state["last_seen"]) > SPREAD_GAP_RESET_SEC:
            self._spread_state[key] = {
                "first_seen": now,
                "last_seen": now,
                "peak": gross_spread_pct,
                "last": gross_spread_pct,
                "resolved": False,
            }
            self._proxy_history[symbol.upper()]["total"] += 1
            return

        state["last_seen"] = now
        state["last"] = gross_spread_pct
        if gross_spread_pct > state["peak"]:
            state["peak"] = gross_spread_pct

        duration = now - state["first_seen"]
        if (
            not state["resolved"]
            and duration >= SPREAD_PROXY_TARGET_SEC
            and gross_spread_pct >= state["peak"] * 0.7
        ):
            self._proxy_history[symbol.upper()]["success"] += 1
            state["resolved"] = True

    def estimate(
        self,
        symbol: str,
        buy_exchange: str,
        sell_exchange: str,
        gross_spread_pct: float,
        max_size_usd: float,
        buy_age_sec: float,
        sell_age_sec: float,
        buy_health: dict | None,
        sell_health: dict | None,
    ) -> float:
        symbol = symbol.upper()

        buy_freshness = self._freshness_score(buy_age_sec)
        sell_freshness = self._freshness_score(sell_age_sec)
        buy_health_score = self._health_score(buy_health)
        sell_health_score = self._health_score(sell_health)

        buy_leg = self._leg_score(buy_exchange, buy_freshness, buy_health_score)
        sell_leg = self._leg_score(sell_exchange, sell_freshness, sell_health_score)

        context_score = (
            0.25 * self._depth_score(max_size_usd)
            + 0.15 * ((buy_freshness + sell_freshness) / 2)
            + 0.20 * self._stability_score(symbol, buy_exchange, sell_exchange)
            + 0.15 * ((buy_health_score + sell_health_score) / 2)
            + 0.10 * self._volatility_score(symbol, buy_exchange, sell_exchange)
            + 0.15 * self._history_score(symbol)
        )

        probability = buy_leg * sell_leg * context_score * self._spread_penalty(gross_spread_pct)
        return round(_clamp(probability) * 100, 1)

    def _cleanup_spread_state(self, now: float):
        expired = [
            key
            for key, state in self._spread_state.items()
            if (now - state["last_seen"]) > SPREAD_STATE_TTL_SEC
        ]
        for key in expired:
            del self._spread_state[key]
            self._last_spread_sample.pop(key, None)

    def _freshness_score(self, age_sec: float) -> float:
        if age_sec <= 0.5:
            return 1.0
        if age_sec <= 2:
            return 1.0 - ((age_sec - 0.5) / 1.5) * 0.2
        if age_sec <= 5:
            return 0.8 - ((age_sec - 2) / 3.0) * 0.55
        if age_sec <= 8:
            return 0.25 - ((age_sec - 5) / 3.0) * 0.20
        return 0.05

    def _health_score(self, health: dict | None) -> float:
        if not health:
            return 0.35

        status_factor = {
            "online": 1.0,
            "lagging": 0.55,
            "offline": 0.1,
        }.get(health.get("status"), 0.35)

        updates_per_sec = float(health.get("updates_per_sec", 0) or 0)
        last_update = float(health.get("last_update_sec", 999) or 999)

        activity = 0.25 + 0.75 * _clamp(updates_per_sec / 8.0)
        recency = self._freshness_score(last_update)
        return _clamp(status_factor * (0.5 * activity + 0.5 * recency))

    def _leg_score(self, exchange: str, freshness: float, health_score: float) -> float:
        reliability = EXCHANGE_RELIABILITY.get(exchange, 0.65)
        return _clamp(0.60 * reliability + 0.25 * freshness + 0.15 * health_score)

    def _depth_score(self, max_size_usd: float) -> float:
        if max_size_usd <= 0:
            return 0.22

        floor = 100.0
        ceiling = 15_000.0
        capped = max(floor, min(ceiling, max_size_usd))
        ratio = (math.log10(capped) - math.log10(floor)) / (math.log10(ceiling) - math.log10(floor))
        return _clamp(0.35 + ratio * 0.65)

    def _stability_score(self, symbol: str, buy_exchange: str, sell_exchange: str) -> float:
        state = self._spread_state.get((symbol, buy_exchange, sell_exchange))
        if not state:
            return 0.35

        duration = min((time.time() - state["first_seen"]) / STABILITY_TARGET_SEC, 1.0)
        peak = state.get("peak", 0) or 0
        current = state.get("last", 0) or 0
        near_peak = _clamp(current / peak) if peak > 0 else 0.5
        return _clamp(0.20 + 0.55 * duration + 0.25 * near_peak)

    def _volatility_score(self, symbol: str, buy_exchange: str, sell_exchange: str) -> float:
        scores = []
        for exchange in (buy_exchange, sell_exchange):
            key = (symbol, exchange)
            window = self._mid_history.get(key)
            if not window:
                continue
            count = len(window)
            if count < 5:
                continue

            stats = self._mid_stats.get(key)
            if not stats:
                continue

            mean = stats["sum"] / count
            if mean <= 0:
                continue

            variance = (stats["sum_sq"] / count) - (mean * mean)
            rel_std = math.sqrt(max(variance, 0.0)) / mean

            if rel_std <= 0.001:
                scores.append(1.0)
            elif rel_std >= 0.02:
                scores.append(0.10)
            else:
                normalized = (rel_std - 0.001) / 0.019
                scores.append(_clamp(1.0 - normalized * 0.90))

        if not scores:
            return 0.60
        return min(scores)

    def _history_score(self, symbol: str) -> float:
        history = self._proxy_history.get(symbol)
        if not history:
            return 0.55

        total = history["total"]
        success = history["success"]
        if total < 5:
            return 0.55
        return _clamp((success + 2) / (total + 4), 0.15, 0.95)

    def _spread_penalty(self, gross_spread_pct: float) -> float:
        if gross_spread_pct >= 50:
            return 0.0
        if gross_spread_pct >= 25:
            return 0.10
        if gross_spread_pct >= 10:
            return 0.35
        if gross_spread_pct >= 5:
            return 0.70
        return 1.0
