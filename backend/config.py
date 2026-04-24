import os


CEX_EXCHANGES = [
    "binance",
    "bybit",
    "mexc",
    "bingx",
    "gate",
    "bitget",
    "okx",
    "kucoin",
]

EXCHANGES = [*CEX_EXCHANGES, "dex"]

# Symbols are loaded lazily at startup, not at import time.
SYMBOLS: list[str] = []


def load_symbols():
    global SYMBOLS
    from core.symbols import FALLBACK_SYMBOLS, fetch_all_symbols

    # DEX quotes are discovered on top of the CEX universe and should not
    # participate in the initial intersection logic.
    SYMBOLS = fetch_all_symbols(CEX_EXCHANGES, min_exchanges=2)
    if not SYMBOLS:
        print("[Config] WARNING: using fallback symbols list")
        SYMBOLS = FALLBACK_SYMBOLS
    return SYMBOLS


Z_THRESHOLD = 1.5
MIN_DEVIATION = 0.3
WINDOW = 50

MIN_TG_SPREAD = float(os.getenv("MIN_TG_SPREAD", "0.5"))

FEES = {
    "binance": 0.04,
    "bybit": 0.06,
    "mexc": 0.01,
    "bingx": 0.045,
    "gate": 0.05,
    "bitget": 0.051,
    "okx": 0.05,
    "kucoin": 0.06,
    "dex": 0.3,
}
