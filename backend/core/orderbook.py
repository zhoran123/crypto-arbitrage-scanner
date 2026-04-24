import asyncio
import time

import aiohttp


MAX_SLIPPAGE_PCT = 0.2
REFRESH_INTERVAL = 20
TOP_N = 80
CACHE_TTL = 90
DEPTH = 20


class OrderbookFetcher:
    def __init__(self):
        self._books: dict[tuple[str, str], dict] = {}
        self._size_cache: dict[tuple[str, str, str], float] = {}
        self._size_ts: dict[tuple[str, str, str], float] = {}
        self._dex_liquidity: dict[str, float] = {}
        self._session: aiohttp.ClientSession | None = None

    def set_dex_liquidity(self, symbol: str, liquidity_usd: float):
        self._dex_liquidity[symbol.upper()] = float(liquidity_usd)

    async def start(self):
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8))

    async def stop(self):
        if self._session:
            await self._session.close()
            self._session = None

    def get_max_size(self, symbol: str, buy_exchange: str, sell_exchange: str) -> float:
        key = (symbol.upper(), buy_exchange, sell_exchange)
        ts = self._size_ts.get(key, 0)
        if time.time() - ts > CACHE_TTL:
            return 0.0
        return self._size_cache.get(key, 0.0)

    async def refresh_for_spreads(self, spreads: list[dict]):
        if not self._session:
            return

        top_spreads = spreads[:TOP_N]
        tasks = []
        seen: set[tuple[str, str]] = set()

        for spread in top_spreads:
            for exchange in (spread["buy_on"], spread["sell_on"]):
                key = (spread["symbol"], exchange)
                if key in seen:
                    continue
                seen.add(key)
                tasks.append(self._fetch_book(spread["symbol"], exchange))

        semaphore = asyncio.Semaphore(10)

        async def _bounded(coro):
            async with semaphore:
                try:
                    await coro
                except Exception:
                    pass

        await asyncio.gather(*[_bounded(task) for task in tasks], return_exceptions=True)

        now = time.time()
        for spread in top_spreads:
            key = (spread["symbol"], spread["buy_on"], spread["sell_on"])
            max_size = self._estimate_pair_size(spread["symbol"], spread["buy_on"], spread["sell_on"])
            if max_size <= 0:
                continue
            self._size_cache[key] = max_size
            self._size_ts[key] = now

    def _estimate_pair_size(self, symbol: str, buy_exchange: str, sell_exchange: str) -> float:
        buy_leg = self._leg_size(symbol, buy_exchange, side="buy")
        sell_leg = self._leg_size(symbol, sell_exchange, side="sell")
        if buy_leg <= 0 or sell_leg <= 0:
            return 0.0
        return min(buy_leg, sell_leg)

    def _leg_size(self, symbol: str, exchange: str, side: str) -> float:
        if exchange == "dex":
            liquidity = self._dex_liquidity.get(symbol.upper(), 0.0)
            return liquidity * 0.01 if liquidity > 0 else 0.0

        book = self._books.get((symbol, exchange))
        if not book:
            return 0.0

        if side == "buy":
            return self._walk_one_side(book["asks"], direction="up")
        return self._walk_one_side(book["bids"], direction="down")

    @staticmethod
    def _walk_one_side(levels: list[list[float]], direction: str) -> float:
        if not levels:
            return 0.0

        best_price = levels[0][0]
        if direction == "up":
            limit = best_price * (1 + MAX_SLIPPAGE_PCT / 100)
            notional = 0.0
            for price, qty in levels:
                if price > limit or price <= 0 or qty <= 0:
                    break
                notional += price * qty
            return notional

        limit = best_price * (1 - MAX_SLIPPAGE_PCT / 100)
        notional = 0.0
        for price, qty in levels:
            if price < limit or price <= 0 or qty <= 0:
                break
            notional += price * qty
        return notional

    async def _fetch_book(self, symbol: str, exchange: str):
        fetcher = _FETCHERS.get(exchange)
        if not fetcher:
            return

        try:
            book = await fetcher(self._session, symbol)
        except Exception:
            return

        if book:
            self._books[(symbol, exchange)] = {
                "bids": book[0],
                "asks": book[1],
                "ts": time.time(),
            }


async def _fetch_binance(session, symbol):
    async with session.get(
        "https://fapi.binance.com/fapi/v1/depth",
        params={"symbol": symbol, "limit": DEPTH},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    bids = [[float(price), float(qty)] for price, qty in data.get("bids", [])]
    asks = [[float(price), float(qty)] for price, qty in data.get("asks", [])]
    return bids, asks


async def _fetch_bybit(session, symbol):
    async with session.get(
        "https://api.bybit.com/v5/market/orderbook",
        params={"category": "linear", "symbol": symbol, "limit": DEPTH},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    book = data.get("result") or {}
    bids = [[float(price), float(qty)] for price, qty in book.get("b", [])]
    asks = [[float(price), float(qty)] for price, qty in book.get("a", [])]
    return bids, asks


async def _fetch_okx(session, symbol):
    inst_id = symbol.replace("USDT", "-USDT-SWAP")
    async with session.get(
        "https://www.okx.com/api/v5/market/books",
        params={"instId": inst_id, "sz": DEPTH},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    rows = data.get("data") or []
    if not rows:
        return None
    book = rows[0]
    bids = [[float(price), float(qty)] for price, qty, *_ in book.get("bids", [])]
    asks = [[float(price), float(qty)] for price, qty, *_ in book.get("asks", [])]
    return bids, asks


async def _fetch_bitget(session, symbol):
    async with session.get(
        "https://api.bitget.com/api/v2/mix/market/merge-depth",
        params={"symbol": symbol, "productType": "USDT-FUTURES", "limit": str(DEPTH)},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    book = data.get("data") or {}
    bids = [[float(price), float(qty)] for price, qty in book.get("bids", [])]
    asks = [[float(price), float(qty)] for price, qty in book.get("asks", [])]
    return bids, asks


async def _fetch_gate(session, symbol):
    contract = symbol.replace("USDT", "_USDT")
    async with session.get(
        "https://api.gateio.ws/api/v4/futures/usdt/order_book",
        params={"contract": contract, "limit": DEPTH},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    bids = [[float(row["p"]), float(row["s"])] for row in data.get("bids", [])]
    asks = [[float(row["p"]), float(row["s"])] for row in data.get("asks", [])]
    return bids, asks


async def _fetch_mexc(session, symbol):
    contract = symbol.replace("USDT", "_USDT")
    async with session.get(
        f"https://contract.mexc.com/api/v1/contract/depth/{contract}"
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    book = data.get("data") or {}
    bids = [[float(price), float(qty)] for price, qty in (book.get("bids") or [])[:DEPTH]]
    asks = [[float(price), float(qty)] for price, qty in (book.get("asks") or [])[:DEPTH]]
    return bids, asks


async def _fetch_bingx(session, symbol):
    market_symbol = symbol.replace("USDT", "-USDT")
    async with session.get(
        "https://open-api.bingx.com/openApi/swap/v2/quote/depth",
        params={"symbol": market_symbol, "limit": DEPTH},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    book = data.get("data") or {}
    bids = [[float(price), float(qty)] for price, qty in book.get("bids", [])]
    asks = [[float(price), float(qty)] for price, qty in book.get("asks", [])]
    return bids, asks


async def _fetch_kucoin(session, symbol):
    inst_id = symbol + "M"
    async with session.get(
        "https://api-futures.kucoin.com/api/v1/level2/depth20",
        params={"symbol": inst_id},
    ) as response:
        if response.status != 200:
            return None
        data = await response.json()

    book = data.get("data") or {}
    bids = [[float(price), float(qty)] for price, qty in (book.get("bids") or [])]
    asks = [[float(price), float(qty)] for price, qty in (book.get("asks") or [])]
    return bids, asks


_FETCHERS = {
    "binance": _fetch_binance,
    "bybit": _fetch_bybit,
    "okx": _fetch_okx,
    "bitget": _fetch_bitget,
    "gate": _fetch_gate,
    "mexc": _fetch_mexc,
    "bingx": _fetch_bingx,
    "kucoin": _fetch_kucoin,
}
