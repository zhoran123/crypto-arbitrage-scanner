EXCHANGES = [
    "binance", "bybit",
    "mexc", "bingx", "gate", "bitget", "okx", "kucoin",
]

# Символы загружаются лениво — НЕ при импорте модуля.
# Вызывай load_symbols() в startup, чтобы не блокировать запуск FastAPI.
SYMBOLS: list[str] = []


def load_symbols():
    """Загрузить символы со всех бирж (параллельно). Вызывать один раз при старте."""
    global SYMBOLS
    from core.symbols import fetch_all_symbols
    SYMBOLS = fetch_all_symbols(EXCHANGES, min_exchanges=2)
    if not SYMBOLS:
        from core.symbols import FALLBACK_SYMBOLS
        print("[Config] ВНИМАНИЕ: используем резервный список символов")
        SYMBOLS = FALLBACK_SYMBOLS
    return SYMBOLS


Z_THRESHOLD   = 1.5
MIN_DEVIATION = 0.3
WINDOW        = 50

# Telegram: уведомлять только если net spread >= этого значения (%)
# Было 5.0 — слишком высокий порог, сигналы редко достигают 5% net.
# Значение берётся из .env, дефолт — 0.5%
import os as _os
MIN_TG_SPREAD = float(_os.getenv("MIN_TG_SPREAD", "0.5"))

FEES = {
    "binance": 0.04,
    "bybit":   0.06,
    "mexc":    0.01,
    "bingx":   0.045,
    "gate":    0.05,
    "bitget":  0.051,
    "okx":     0.05,
    "kucoin":  0.06,
}
