"""Load tradable USDT perpetual symbols from supported exchanges."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time as _time

import requests


TIMEOUT = 10


def _is_valid_usdt_symbol(symbol: str) -> bool:
    return (
        symbol.endswith("USDT")
        and symbol.isascii()
        and all(char.isupper() or char.isdigit() for char in symbol)
    )


def _fetch_binance() -> set[str]:
    try:
        response = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=TIMEOUT)
        return {
            item["symbol"]
            for item in response.json().get("symbols", [])
            if item.get("status") == "TRADING"
            and item.get("contractType") == "PERPETUAL"
            and item.get("quoteAsset") == "USDT"
            and _is_valid_usdt_symbol(item["symbol"])
        }
    except Exception as exc:
        print(f"  [!] Binance: {exc}")
        return set()


def _fetch_bybit() -> set[str]:
    try:
        response = requests.get(
            "https://api.bybit.com/v5/market/instruments-info",
            params={"category": "linear", "limit": "1000"},
            timeout=TIMEOUT,
        )
        return {
            item["symbol"]
            for item in response.json().get("result", {}).get("list", [])
            if item.get("status") == "Trading" and _is_valid_usdt_symbol(item["symbol"])
        }
    except Exception as exc:
        print(f"  [!] Bybit: {exc}")
        return set()


def _fetch_okx() -> set[str]:
    try:
        response = requests.get(
            "https://www.okx.com/api/v5/public/instruments",
            params={"instType": "SWAP"},
            timeout=TIMEOUT,
        )
        symbols = set()
        for item in response.json().get("data", []):
            if item.get("state") == "live" and item["instId"].endswith("-USDT-SWAP"):
                symbol = item["instId"].replace("-USDT-SWAP", "USDT")
                if _is_valid_usdt_symbol(symbol):
                    symbols.add(symbol)
        return symbols
    except Exception as exc:
        print(f"  [!] OKX: {exc}")
        return set()


def _fetch_bitget() -> set[str]:
    try:
        response = requests.get(
            "https://api.bitget.com/api/v2/mix/market/tickers",
            params={"productType": "USDT-FUTURES"},
            timeout=TIMEOUT,
        )
        return {
            item["symbol"]
            for item in response.json().get("data", [])
            if _is_valid_usdt_symbol(item["symbol"])
        }
    except Exception as exc:
        print(f"  [!] Bitget: {exc}")
        return set()


def _fetch_gate() -> set[str]:
    try:
        response = requests.get(
            "https://api.gateio.ws/api/v4/futures/usdt/contracts",
            timeout=TIMEOUT,
        )
        symbols = set()
        for item in response.json():
            if not item.get("in_delisting"):
                symbol = item["name"].replace("_", "")
                if _is_valid_usdt_symbol(symbol):
                    symbols.add(symbol)
        return symbols
    except Exception as exc:
        print(f"  [!] Gate: {exc}")
        return set()


def _fetch_mexc() -> set[str]:
    try:
        response = requests.get(
            "https://contract.mexc.com/api/v1/contract/detail",
            timeout=TIMEOUT,
        )
        symbols = set()
        for item in response.json().get("data", []):
            if item.get("state") == 0 and item.get("quoteCoin") == "USDT":
                symbol = item["symbol"].replace("_", "")
                if _is_valid_usdt_symbol(symbol):
                    symbols.add(symbol)
        return symbols
    except Exception as exc:
        print(f"  [!] MEXC: {exc}")
        return set()


def _fetch_bingx() -> set[str]:
    try:
        response = requests.get(
            "https://open-api.bingx.com/openApi/swap/v2/quote/contracts",
            timeout=TIMEOUT,
        )
        return {
            item["symbol"].replace("-", "")
            for item in response.json().get("data", [])
            if item.get("status") == 1
            and _is_valid_usdt_symbol(item["symbol"].replace("-", ""))
        }
    except Exception as exc:
        print(f"  [!] BingX: {exc}")
        return set()


def _fetch_kucoin() -> set[str]:
    try:
        response = requests.get(
            "https://api-futures.kucoin.com/api/v1/contracts/active",
            timeout=TIMEOUT,
        )
        symbols = set()
        for item in response.json().get("data", []):
            if item.get("status") == "Open" and item.get("quoteCurrency") == "USDT":
                symbol = item["symbol"]
                if symbol.endswith("M"):
                    symbol = symbol[:-1]
                symbol = symbol.replace("XBT", "BTC", 1)
                if _is_valid_usdt_symbol(symbol):
                    symbols.add(symbol)
        return symbols
    except Exception as exc:
        print(f"  [!] KuCoin: {exc}")
        return set()


EXCHANGE_FETCHERS = {
    "binance": _fetch_binance,
    "bybit": _fetch_bybit,
    "okx": _fetch_okx,
    "bitget": _fetch_bitget,
    "gate": _fetch_gate,
    "mexc": _fetch_mexc,
    "bingx": _fetch_bingx,
    "kucoin": _fetch_kucoin,
}


def fetch_symbols_by_exchange(exchanges: list[str]) -> dict[str, set[str]]:
    """Fetch symbols for every exchange while keeping the source mapping."""
    print("[Config] Loading symbols from exchanges in parallel...")
    started = _time.monotonic()
    exchange_symbols: dict[str, set[str]] = {}

    def _fetch_one(exchange: str) -> tuple[str, set[str]]:
        fetcher = EXCHANGE_FETCHERS.get(exchange)
        if not fetcher:
            return exchange, set()
        return exchange, fetcher()

    with ThreadPoolExecutor(max_workers=max(1, len(exchanges))) as pool:
        futures = {pool.submit(_fetch_one, exchange): exchange for exchange in exchanges}
        for future in as_completed(futures):
            exchange, symbols = future.result()
            exchange_symbols[exchange] = symbols
            print(f"  ok {exchange}: {len(symbols)} pairs")

    elapsed = _time.monotonic() - started
    print(f"[Config] Symbol fetch completed in {elapsed:.1f}s")
    return exchange_symbols


def build_symbol_universe(exchanges: list[str], min_exchanges: int = 2) -> tuple[list[str], dict[str, set[str]]]:
    """
    Return the monitored global universe and raw per-exchange symbol sets.

    A symbol enters the global universe when it is listed on at least
    min_exchanges exchanges, but connectors must still subscribe only to the
    symbols supported by their own exchange.
    """
    started = _time.monotonic()
    exchange_symbols = fetch_symbols_by_exchange(exchanges)

    symbol_count: dict[str, int] = {}
    for symbols in exchange_symbols.values():
        for symbol in symbols:
            symbol_count[symbol] = symbol_count.get(symbol, 0) + 1

    universe = sorted([
        symbol
        for symbol, count in symbol_count.items()
        if count >= min_exchanges
    ])

    elapsed = _time.monotonic() - started
    print(f"[Config] Total: {len(universe)} symbols ({min_exchanges}+ exchanges) in {elapsed:.1f}s")
    return universe, exchange_symbols


def fetch_all_symbols(exchanges: list[str], min_exchanges: int = 2) -> list[str]:
    """Backward-compatible wrapper returning only the monitored universe."""
    universe, _exchange_symbols = build_symbol_universe(exchanges, min_exchanges)
    return universe


FALLBACK_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "ATOMUSDT",
    "NEARUSDT",
    "APTUSDT",
    "ARBUSDT",
    "OPUSDT",
    "SUIUSDT",
    "SEIUSDT",
]
