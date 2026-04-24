import time


class HealthMonitor:
    def __init__(self):
        self._data: dict[str, dict] = {}

    def on_update(self, exchange: str, symbol: str):
        now = time.time()
        if exchange not in self._data:
            self._data[exchange] = {
                "last_update": now,
                "updates": 0,
                "symbols": set(),
                "first_seen": now,
            }

        exchange_data = self._data[exchange]
        exchange_data["last_update"] = now
        exchange_data["updates"] += 1
        exchange_data["symbols"].add(symbol)

    def get_status(self) -> list[dict]:
        return [
            self._build_status(exchange, payload)
            for exchange, payload in sorted(self._data.items())
        ]

    def get_exchange_status(self, exchange: str) -> dict | None:
        payload = self._data.get(exchange)
        if not payload:
            return None
        return self._build_status(exchange, payload)

    def _build_status(self, exchange: str, payload: dict) -> dict:
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
