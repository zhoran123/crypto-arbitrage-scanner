"""
Signal History — сохранение сигналов в файл.
Формат: JSON Lines (одна строка = один сигнал).
Ротация: максимум N записей, старые удаляются.
"""

import json
from pathlib import Path
from collections import deque

HISTORY_FILE = Path(__file__).parent.parent / "signal_history.jsonl"
MAX_HISTORY = 5000  # максимум записей в памяти
MAX_FILE_LINES = 10000  # максимум строк в файле
ROTATE_CHECK_INTERVAL = 500  # проверяем ротацию каждые N записей (не каждую)


class SignalHistory:
    def __init__(self):
        self._history: deque = deque(maxlen=MAX_HISTORY)
        self._writes_since_rotate = 0
        self._load()

    def _load(self):
        """Загрузить историю из файла при старте."""
        if HISTORY_FILE.exists():
            try:
                lines = HISTORY_FILE.read_text().strip().split("\n")
                count = 0
                for line in lines[-MAX_HISTORY:]:
                    if line.strip():
                        self._history.append(json.loads(line))
                        count += 1
                self._writes_since_rotate = len(lines)
                print(f"[History] Загружено {count} сигналов из файла")
            except Exception as e:
                print(f"[History] Ошибка загрузки: {e}")

    def add(self, signal: dict):
        """Добавить сигнал в историю."""
        self._history.append(signal)
        try:
            with open(HISTORY_FILE, "a") as f:
                f.write(json.dumps(signal) + "\n")
            self._writes_since_rotate += 1
            # Ротация только каждые N записей — не читаем файл каждый раз
            if self._writes_since_rotate > MAX_FILE_LINES + ROTATE_CHECK_INTERVAL:
                self._rotate()
        except Exception as e:
            print(f"[History] Ошибка записи: {e}")

    def _rotate(self):
        """Обрезать файл если слишком много строк."""
        try:
            lines = HISTORY_FILE.read_text().strip().split("\n")
            if len(lines) > MAX_FILE_LINES:
                keep = lines[-MAX_FILE_LINES:]
                HISTORY_FILE.write_text("\n".join(keep) + "\n")
                self._writes_since_rotate = len(keep)
        except Exception:
            pass

    def get_recent(self, limit: int = 200) -> list[dict]:
        """Последние N сигналов (новые первые)."""
        items = list(self._history)
        items.reverse()
        return items[:limit]

    def get_stats(self) -> dict:
        """Статистика по истории."""
        if not self._history:
            return {"total": 0}

        symbols: dict[str, int] = {}
        exchanges: dict[str, int] = {}
        for s in self._history:
            sym = s.get("symbol", "?")
            symbols[sym] = symbols.get(sym, 0) + 1
            buy = s.get("buy_on", "?")
            sell = s.get("sell_on", "?")
            exchanges[buy] = exchanges.get(buy, 0) + 1
            exchanges[sell] = exchanges.get(sell, 0) + 1

        top_symbols = sorted(symbols.items(), key=lambda x: -x[1])[:10]
        top_exchanges = sorted(exchanges.items(), key=lambda x: -x[1])[:10]

        return {
            "total": len(self._history),
            "top_symbols": [{"symbol": s, "count": c} for s, c in top_symbols],
            "top_exchanges": [{"exchange": e, "count": c} for e, c in top_exchanges],
        }

    @property
    def total(self) -> int:
        return len(self._history)
