"""
price_store.py — SQLite-backed 1-minute candle storage with 7-day retention.

Accumulates ticks in RAM, flushes completed candles to SQLite every minute.
Serves historical data from SQLite + current live candle from RAM.
"""

import sqlite3
import time
import threading
from collections import defaultdict
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "candles.db"
RETENTION_DAYS = 7
RETENTION_SEC = RETENTION_DAYS * 86400
FLUSH_INTERVAL = 60  # seconds


class PriceStore:

    def __init__(self, db_path: str = None):
        self._db_path = str(db_path or DB_PATH)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # RAM: current minute candles (not yet flushed)
        # {(symbol, exchange): {"t": minute_ts, "o", "h", "l", "c"}}
        self._current: dict[tuple, dict] = {}

        # Pending completed candles to flush
        self._pending: list[tuple] = []
        self._lock = threading.Lock()

        self._init_db()
        self._start_cleanup_timer()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candles_1m (
                symbol   TEXT NOT NULL,
                exchange TEXT NOT NULL,
                ts       INTEGER NOT NULL,
                open     REAL NOT NULL,
                high     REAL NOT NULL,
                low      REAL NOT NULL,
                close    REAL NOT NULL,
                PRIMARY KEY (symbol, exchange, ts)
            ) WITHOUT ROWID
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_candles_sym_ts
            ON candles_1m (symbol, ts)
        """)
        conn.commit()
        conn.close()

    def on_price(self, symbol: str, exchange: str, bid: float, ask: float):
        """Called on every price tick. Accumulates into 1m candles in RAM."""
        mid = (bid + ask) / 2
        now = time.time()
        minute_ts = int(now // 60) * 60
        key = (symbol, exchange)

        with self._lock:
            cur = self._current.get(key)

            if cur and cur["t"] == minute_ts:
                # Same minute — update
                cur["h"] = max(cur["h"], mid)
                cur["l"] = min(cur["l"], mid)
                cur["c"] = mid
            else:
                # New minute — move previous candle to pending
                if cur:
                    self._pending.append((
                        key[0], key[1],
                        cur["t"], cur["o"], cur["h"], cur["l"], cur["c"]
                    ))
                # Start new candle
                self._current[key] = {
                    "t": minute_ts,
                    "o": mid, "h": mid, "l": mid, "c": mid,
                }

            # Batch flush when enough pending
            if len(self._pending) >= 500:
                self._flush()

    def flush(self):
        """Force flush pending candles to SQLite."""
        with self._lock:
            self._flush()

    def _flush(self):
        """Internal flush (must hold lock)."""
        if not self._pending:
            return
        batch = self._pending[:]
        self._pending.clear()

        try:
            conn = self._get_conn()
            conn.executemany(
                "INSERT OR REPLACE INTO candles_1m (symbol, exchange, ts, open, high, low, close) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                batch
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[PriceStore] flush error: {e}")

    def get_history(self, symbol: str, tf: str = "1m") -> dict:
        """
        Return {exchange: [{t, o, h, l, c}, ...]} for a symbol.
        Combines SQLite history + current RAM candle.
        """
        tf_seconds = {
            "1m": 60, "5m": 300, "15m": 900,
            "30m": 1800, "1h": 3600, "4h": 14400,
        }
        interval = tf_seconds.get(tf, 60)

        # Determine how far back to look based on timeframe
        # Show reasonable amount of data for each tf
        lookback = {
            "1m": 240,      # 4 hours of 1m
            "5m": 288,      # 24 hours of 5m
            "15m": 672,     # 7 days of 15m
            "30m": 336,     # 7 days of 30m
            "1h": 168,      # 7 days of 1h
            "4h": 42,       # 7 days of 4h
        }
        max_points = lookback.get(tf, 240)
        since = int(time.time()) - max_points * interval

        # Query SQLite
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT exchange, ts, open, high, low, close "
                "FROM candles_1m WHERE symbol = ? AND ts >= ? "
                "ORDER BY ts",
                (symbol.upper(), since)
            ).fetchall()
            conn.close()
        except Exception:
            rows = []

        # Group by exchange
        by_exch: dict[str, list[dict]] = defaultdict(list)
        for exch, ts, o, h, l, c in rows:
            by_exch[exch].append({"t": ts, "o": o, "h": h, "l": l, "c": c})

        # Add current RAM candles
        with self._lock:
            for (sym, exch), candle in self._current.items():
                if sym == symbol.upper():
                    by_exch[exch].append(dict(candle))

        # Aggregate if needed
        result = {}
        for exch, candles in by_exch.items():
            candles.sort(key=lambda c: c["t"])
            if tf == "1m":
                result[exch] = candles
            else:
                result[exch] = self._aggregate(candles, interval)

        return result

    def get_live_candles(self, symbol: str) -> dict:
        """Return current (incomplete) candle for each exchange. For live updates."""
        result = {}
        with self._lock:
            for (sym, exch), candle in self._current.items():
                if sym == symbol.upper():
                    result[exch] = dict(candle)
        return result

    @staticmethod
    def _aggregate(candles: list[dict], interval: int) -> list[dict]:
        grouped: dict[int, list[dict]] = {}
        for c in candles:
            bucket = int(c["t"] // interval) * interval
            grouped.setdefault(bucket, []).append(c)

        result = []
        for ts in sorted(grouped):
            group = grouped[ts]
            result.append({
                "t": ts,
                "o": group[0]["o"],
                "h": max(c["h"] for c in group),
                "l": min(c["l"] for c in group),
                "c": group[-1]["c"],
            })
        return result

    def _cleanup(self):
        """Remove candles older than retention period."""
        cutoff = int(time.time()) - RETENTION_SEC
        try:
            conn = self._get_conn()
            conn.execute("DELETE FROM candles_1m WHERE ts < ?", (cutoff,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[PriceStore] cleanup error: {e}")

    def _start_cleanup_timer(self):
        def run():
            while True:
                time.sleep(3600)  # every hour
                self._cleanup()
                self.flush()  # also flush any pending

        t = threading.Thread(target=run, daemon=True)
        t.start()
