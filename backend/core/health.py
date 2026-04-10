"""
Exchange Health Monitor — отслеживает статус каждой биржи.
"""

import time


class HealthMonitor:
    def __init__(self):
        # {exchange: {last_update: float, updates: int, symbols: set}}
        self._data: dict[str, dict] = {}

    def on_update(self, exchange: str, symbol: str):
        """Вызывается при каждом обновлении цены."""
        now = time.time()
        if exchange not in self._data:
            self._data[exchange] = {
                "last_update": now,
                "updates": 0,
                "symbols": set(),
                "first_seen": now,
            }
        d = self._data[exchange]
        d["last_update"] = now
        d["updates"] += 1
        d["symbols"].add(symbol)

    def get_status(self) -> list[dict]:
        """Статус всех бирж."""
        now = time.time()
        result = []
        for exch, d in sorted(self._data.items()):
            age = now - d["last_update"]
            uptime = now - d["first_seen"]

            if age < 10:
                status = "online"
            elif age < 30:
                status = "lagging"
            else:
                status = "offline"

            # Updates per second (за всё время)
            ups = d["updates"] / max(uptime, 1)

            result.append({
                "exchange": exch,
                "status": status,
                "last_update_sec": round(age, 1),
                "total_updates": d["updates"],
                "symbols_active": len(d["symbols"]),
                "updates_per_sec": round(ups, 1),
            })

        return result
