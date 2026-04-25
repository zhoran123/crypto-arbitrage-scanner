import time


class HealthMonitor:
    def __init__(self):
        self._data: dict[str, dict] = {}
        self._known_exchanges: set[str] = set()

    def register_exchange(self, exchange: str):
        self._known_exchanges.add(exchange)

    def on_update(self, exchange: str, symbol: str):
        now = time.time()
        exchange_data = self._data.get(exchange)
        if exchange_data is None:
            self._known_exchanges.add(exchange)
            exchange_data = {
                "last_update": now,
                "updates": 0,
                "symbols": set(),
                "first_seen": now,
            }
            self._data[exchange] = exchange_data

        exchange_data["last_update"] = now
        exchange_data["updates"] += 1
        # Hot path: only touch the set when we see a new symbol. Avoids hashing
        # ~50k times/sec for already-known (exchange, symbol) pairs.
        symbols = exchange_data["symbols"]
        if symbol not in symbols:
            symbols.add(symbol)

    def get_status(self) -> list[dict]:
        exchanges = sorted(self._known_exchanges | set(self._data))
        return [self._build_status(exchange, self._data.get(exchange)) for exchange in exchanges]

    def get_exchange_status(self, exchange: str) -> dict | None:
        payload = self._data.get(exchange)
        if not payload:
            if exchange in self._known_exchanges:
                return self._offline_status(exchange)
            return None
        return self._build_status(exchange, payload)

    @staticmethod
    def _offline_status(exchange: str) -> dict:
        return {
            "exchange": exchange,
            "status": "offline",
            "last_update_sec": None,
            "total_updates": 0,
            "symbols_active": 0,
            "updates_per_sec": 0,
        }

    def _build_status(self, exchange: str, payload: dict | None) -> dict:
        if not payload:
            return self._offline_status(exchange)

        now = time.time()
        age = now - payload["last_update"]
        uptime = now - payload["first_seen"]

        if age < 10:
            status = "online"
        elif age < 30:
            status = "lagging"
        else:
            status = "offline"

        return {
            "exchange": exchange,
            "status": status,
            "last_update_sec": round(age, 1),
            "total_updates": payload["updates"],
            "symbols_active": len(payload["symbols"]),
            "updates_per_sec": round(payload["updates"] / max(uptime, 1), 1),
        }
