"""
Blacklist — чёрный список монет.
Хранится в JSON-файле, переживает перезапуски.
"""

import json
from pathlib import Path

BLACKLIST_FILE = Path(__file__).parent.parent / "blacklist.json"


class Blacklist:
    def __init__(self):
        self._symbols: set[str] = set()
        self._load()

    def _load(self):
        if BLACKLIST_FILE.exists():
            try:
                data = json.loads(BLACKLIST_FILE.read_text())
                self._symbols = set(data)
                print(f"[Blacklist] Загружено {len(self._symbols)} монет")
            except Exception:
                self._symbols = set()

    def _save(self):
        BLACKLIST_FILE.write_text(json.dumps(sorted(self._symbols), indent=2))

    def add(self, symbol: str):
        """Добавить монету в чёрный список."""
        symbol = symbol.upper()
        self._symbols.add(symbol)
        self._save()

    def remove(self, symbol: str):
        """Убрать монету из чёрного списка."""
        symbol = symbol.upper()
        self._symbols.discard(symbol)
        self._save()

    def is_blocked(self, symbol: str) -> bool:
        return symbol.upper() in self._symbols

    def get_all(self) -> list[str]:
        return sorted(self._symbols)

    def __repr__(self):
        return f"<Blacklist: {len(self._symbols)} symbols>"
