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
EXCHANGE_SYMBOLS: dict[str, list[str]] = {}


def load_symbols():
    global SYMBOLS, EXCHANGE_SYMBOLS
    from core.symbols import FALLBACK_SYMBOLS, build_symbol_universe

    # DEX quotes are discovered on top of the CEX universe and should not
    # participate in the initial intersection logic.
    SYMBOLS, raw_exchange_symbols = build_symbol_universe(CEX_EXCHANGES, min_exchanges=2)
    if not SYMBOLS:
        print("[Config] WARNING: using fallback symbols list")
        SYMBOLS = FALLBACK_SYMBOLS
        EXCHANGE_SYMBOLS = {
            exchange: list(FALLBACK_SYMBOLS)
            for exchange in CEX_EXCHANGES
        }
        return SYMBOLS

    monitored = set(SYMBOLS)
    EXCHANGE_SYMBOLS = {
        exchange: sorted(symbols & monitored)
        for exchange, symbols in raw_exchange_symbols.items()
    }
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
