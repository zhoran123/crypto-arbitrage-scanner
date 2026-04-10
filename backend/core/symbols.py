"""
Автоматическая загрузка списка символов со ВСЕХ бирж.
Объединяет в один список — если монета есть хотя бы на 2 биржах,
она попадает в мониторинг.
"""

import requests

TIMEOUT = 10


def _fetch_binance() -> set[str]:
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=TIMEOUT)
        return {
            s["symbol"] for s in r.json().get("symbols", [])
            if s.get("status") == "TRADING"
            and s.get("contractType") == "PERPETUAL"
            and s.get("quoteAsset") == "USDT"
        }
    except Exception as e:
        print(f"  [!] Binance: {e}")
        return set()


def _fetch_bybit() -> set[str]:
    try:
        r = requests.get(
            "https://api.bybit.com/v5/market/instruments-info",
            params={"category": "linear", "limit": "1000"},
            timeout=TIMEOUT,
        )
        return {
            s["symbol"] for s in r.json().get("result", {}).get("list", [])
            if s.get("status") == "Trading"
            and s["symbol"].endswith("USDT")
        }
    except Exception as e:
        print(f"  [!] Bybit: {e}")
        return set()


def _fetch_okx() -> set[str]:
    try:
        r = requests.get(
            "https://www.okx.com/api/v5/public/instruments",
            params={"instType": "SWAP"},
            timeout=TIMEOUT,
        )
        symbols = set()
        for s in r.json().get("data", []):
            if s.get("state") == "live" and s["instId"].endswith("-USDT-SWAP"):
                # BTC-USDT-SWAP → BTCUSDT
                sym = s["instId"].replace("-USDT-SWAP", "USDT")
                symbols.add(sym)
        return symbols
    except Exception as e:
        print(f"  [!] OKX: {e}")
        return set()


def _fetch_bitget() -> set[str]:
    try:
        r = requests.get(
            "https://api.bitget.com/api/v2/mix/market/tickers",
            params={"productType": "USDT-FUTURES"},
            timeout=TIMEOUT,
        )
        return {
            s["symbol"] for s in r.json().get("data", [])
            if s["symbol"].endswith("USDT")
        }
    except Exception as e:
        print(f"  [!] Bitget: {e}")
        return set()


def _fetch_gate() -> set[str]:
    try:
        r = requests.get(
            "https://api.gateio.ws/api/v4/futures/usdt/contracts",
            timeout=TIMEOUT,
        )
        symbols = set()
        for s in r.json():
            if not s.get("in_delisting"):
                # BTC_USDT → BTCUSDT
                sym = s["name"].replace("_", "")
                if sym.endswith("USDT"):
                    symbols.add(sym)
        return symbols
    except Exception as e:
        print(f"  [!] Gate: {e}")
        return set()


def _fetch_mexc() -> set[str]:
    try:
        r = requests.get(
            "https://contract.mexc.com/api/v1/contract/detail",
            timeout=TIMEOUT,
        )
        symbols = set()
        for s in r.json().get("data", []):
            if s.get("state") == 0 and s.get("quoteCoin") == "USDT":
                # BTC_USDT → BTCUSDT
                sym = s["symbol"].replace("_", "")
                symbols.add(sym)
        return symbols
    except Exception as e:
        print(f"  [!] MEXC: {e}")
        return set()


def _fetch_bingx() -> set[str]:
    try:
        r = requests.get(
            "https://open-api.bingx.com/openApi/swap/v2/quote/contracts",
            timeout=TIMEOUT,
        )
        return {
            s["symbol"].replace("-", "")
            for s in r.json().get("data", [])
            if s.get("status") == 1
            and s["symbol"].endswith("-USDT")
        }
    except Exception as e:
        print(f"  [!] BingX: {e}")
        return set()


def _fetch_kucoin() -> set[str]:
    try:
        r = requests.get(
            "https://api-futures.kucoin.com/api/v1/contracts/active",
            timeout=TIMEOUT,
        )
        symbols = set()
        for s in r.json().get("data", []):
            if s.get("status") == "Open" and s.get("quoteCurrency") == "USDT":
                # XBTUSDTM → XBTUSDT → нормализуем
                sym = s["symbol"]
                if sym.endswith("M"):
                    sym = sym[:-1]
                # KuCoin использует XBT вместо BTC
                sym = sym.replace("XBT", "BTC")
                symbols.add(sym)
        return symbols
    except Exception as e:
        print(f"  [!] KuCoin: {e}")
        return set()


# Маппинг бирж → функции загрузки
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


def fetch_all_symbols(exchanges: list[str], min_exchanges: int = 2) -> list[str]:
    """
    Загрузить символы со всех бирж ПАРАЛЛЕЛЬНО.

    min_exchanges: монета попадает в список только если торгуется
                   хотя бы на N биржах (по умолчанию 2).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time as _time

    print("[Config] Загрузка символов со всех бирж (параллельно)...")
    t0 = _time.monotonic()

    # Собираем символы с каждой биржи ПАРАЛЛЕЛЬНО
    exchange_symbols: dict[str, set[str]] = {}

    def _fetch_one(exch):
        fetcher = EXCHANGE_FETCHERS.get(exch)
        if fetcher:
            return exch, fetcher()
        return exch, set()

    with ThreadPoolExecutor(max_workers=len(exchanges)) as pool:
        futures = {pool.submit(_fetch_one, exch): exch for exch in exchanges}
        for future in as_completed(futures):
            exch, symbols = future.result()
            exchange_symbols[exch] = symbols
            print(f"  ✓ {exch}: {len(symbols)} пар")

    # Считаем на скольких биржах каждый символ
    symbol_count: dict[str, int] = {}
    for symbols in exchange_symbols.values():
        for sym in symbols:
            symbol_count[sym] = symbol_count.get(sym, 0) + 1

    # Фильтруем: минимум на N биржах
    result = sorted([
        sym for sym, count in symbol_count.items()
        if count >= min_exchanges
    ])

    elapsed = _time.monotonic() - t0
    print(f"[Config] Итого: {len(result)} символов (на {min_exchanges}+ биржах) за {elapsed:.1f}с")
    return result


# Резервный список
FALLBACK_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT", "NEARUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "SEIUSDT",
]
