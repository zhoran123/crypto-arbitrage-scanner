"""
orderbook.py — Auto Size Calculator.

Для топ-N самых прибыльных спредов периодически тянем стаканы с обеих бирж
и считаем максимальный USD-объём, который можно залить в обе ноги
с допустимым слиппаджем (по умолчанию 0.2% на ногу).

Результат:
    get_max_size(symbol, buy_exch, sell_exch) -> float (USD)

Результат кэшируется, пересчёт в фоновом таске каждые N секунд.
"""

import asyncio
import time
import aiohttp

# Допустимый слиппадж на одну ногу (в %)
MAX_SLIPPAGE_PCT = 0.2

# Глубина пересчитывается раз в N секунд для активных пар
REFRESH_INTERVAL = 20

# Сколько топ-символов держим в активном пуле
TOP_N = 40

# Cache TTL — сколько секунд кэш валиден
CACHE_TTL = 60


class OrderbookFetcher:
    """
    Снимает стаканы с публичных REST endpoint-ов бирж и считает
    максимальный безопасный объём для арб-сделки.
    """

    def __init__(self):
        # {(symbol, exchange): {"bids": [[price, qty], ...], "asks": [...], "ts": float}}
        self._books: dict[tuple, dict] = {}
        # {(symbol, buy_exch, sell_exch): max_size_usd}
        self._size_cache: dict[tuple, float] = {}
        self._size_ts: dict[tuple, float] = {}
        self._session: aiohttp.ClientSession | None = None

    async def start(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8)
        )

    async def stop(self):
        if self._session:
            await self._session.close()

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------

    def get_max_size(self, symbol: str, buy_exch: str, sell_exch: str) -> float:
        """Получить max size USD из кэша. Возвращает 0 если неизвестно."""
        key = (symbol.upper(), buy_exch, sell_exch)
        ts = self._size_ts.get(key, 0)
        if time.time() - ts > CACHE_TTL:
            return 0.0
        return self._size_cache.get(key, 0.0)

    async def refresh_for_spreads(self, spreads: list[dict]):
        """
        Обновить стаканы для топ-N спредов и пересчитать max size.
        spreads — отсортированный список dict с ключами symbol, buy_on, sell_on.
        """
        if not self._session:
            return
        top = spreads[:TOP_N]

        # Собираем какие стаканы нужно обновить
        tasks = []
        seen: set[tuple] = set()
        for s in top:
            for ex in (s["buy_on"], s["sell_on"]):
                k = (s["symbol"], ex)
                if k in seen:
                    continue
                seen.add(k)
                tasks.append(self._fetch_book(s["symbol"], ex))

        # Выполняем параллельно с лимитом
        sem = asyncio.Semaphore(10)

        async def _bounded(coro):
            async with sem:
                try:
                    await coro
                except Exception:
                    pass

        await asyncio.gather(*[_bounded(t) for t in tasks], return_exceptions=True)

        # Пересчитываем max size для каждой пары
        now = time.time()
        for s in top:
            key = (s["symbol"], s["buy_on"], s["sell_on"])
            buy_book = self._books.get((s["symbol"], s["buy_on"]))
            sell_book = self._books.get((s["symbol"], s["sell_on"]))
            if not buy_book or not sell_book:
                continue
            size_usd = self._compute_max_size(buy_book["asks"], sell_book["bids"])
            self._size_cache[key] = size_usd
            self._size_ts[key] = now

    # ------------------------------------------------------------------
    # Расчёт max size по стаканам
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_max_size(
        asks: list[list[float]],
        bids: list[list[float]],
    ) -> float:
        """
        asks — из стакана биржи, где ПОКУПАЕМ (walk вверх по ask)
        bids — из стакана биржи, где ПРОДАЁМ   (walk вниз по bid)

        Берём lowest ask, собираем объём пока price impact <= MAX_SLIPPAGE_PCT.
        Аналогично для bids. Возвращаем min из двух ног (в USD).
        """
        if not asks or not bids:
            return 0.0

        # BUY leg: walk asks upward
        best_ask = asks[0][0]
        ask_limit = best_ask * (1 + MAX_SLIPPAGE_PCT / 100)
        buy_notional = 0.0
        for price, qty in asks:
            if price > ask_limit or price <= 0 or qty <= 0:
                break
            buy_notional += price * qty

        # SELL leg: walk bids downward
        best_bid = bids[0][0]
        bid_limit = best_bid * (1 - MAX_SLIPPAGE_PCT / 100)
        sell_notional = 0.0
        for price, qty in bids:
            if price < bid_limit or price <= 0 or qty <= 0:
                break
            sell_notional += price * qty

        return min(buy_notional, sell_notional)

    # ------------------------------------------------------------------
    # Загрузка стаканов
    # ------------------------------------------------------------------

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


# ======================================================================
# Per-exchange REST fetchers
# Все возвращают: ([[bid_price, bid_qty], ...], [[ask_price, ask_qty], ...])
# Отсортированные: bids по убыванию цены, asks по возрастанию.
# ======================================================================

DEPTH = 20


async def _fetch_binance(session, symbol):
    url = "https://fapi.binance.com/fapi/v1/depth"
    async with session.get(url, params={"symbol": symbol, "limit": DEPTH}) as r:
        if r.status != 200:
            return None
        d = await r.json()
    bids = [[float(p), float(q)] for p, q in d.get("bids", [])]
    asks = [[float(p), float(q)] for p, q in d.get("asks", [])]
    return bids, asks


async def _fetch_bybit(session, symbol):
    url = "https://api.bybit.com/v5/market/orderbook"
    params = {"category": "linear", "symbol": symbol, "limit": DEPTH}
    async with session.get(url, params=params) as r:
        if r.status != 200:
            return None
        data = await r.json()
    d = data.get("result") or {}
    bids = [[float(p), float(q)] for p, q in d.get("b", [])]
    asks = [[float(p), float(q)] for p, q in d.get("a", [])]
    return bids, asks


async def _fetch_okx(session, symbol):
    # BTCUSDT → BTC-USDT-SWAP
    inst = symbol.replace("USDT", "-USDT-SWAP")
    url = "https://www.okx.com/api/v5/market/books"
    async with session.get(url, params={"instId": inst, "sz": DEPTH}) as r:
        if r.status != 200:
            return None
        data = await r.json()
    arr = data.get("data") or []
    if not arr:
        return None
    d = arr[0]
    bids = [[float(p), float(q)] for p, q, *_ in d.get("bids", [])]
    asks = [[float(p), float(q)] for p, q, *_ in d.get("asks", [])]
    return bids, asks


async def _fetch_bitget(session, symbol):
    url = "https://api.bitget.com/api/v2/mix/market/merge-depth"
    params = {"symbol": symbol, "productType": "USDT-FUTURES", "limit": str(DEPTH)}
    async with session.get(url, params=params) as r:
        if r.status != 200:
            return None
        data = await r.json()
    d = data.get("data") or {}
    bids = [[float(p), float(q)] for p, q in d.get("bids", [])]
    asks = [[float(p), float(q)] for p, q in d.get("asks", [])]
    return bids, asks


async def _fetch_gate(session, symbol):
    # BTCUSDT → BTC_USDT
    contract = symbol.replace("USDT", "_USDT")
    url = "https://api.gateio.ws/api/v4/futures/usdt/order_book"
    async with session.get(url, params={"contract": contract, "limit": DEPTH}) as r:
        if r.status != 200:
            return None
        d = await r.json()
    bids = [[float(row["p"]), float(row["s"])] for row in d.get("bids", [])]
    asks = [[float(row["p"]), float(row["s"])] for row in d.get("asks", [])]
    return bids, asks


async def _fetch_mexc(session, symbol):
    # BTCUSDT → BTC_USDT
    contract = symbol.replace("USDT", "_USDT")
    url = f"https://contract.mexc.com/api/v1/contract/depth/{contract}"
    async with session.get(url) as r:
        if r.status != 200:
            return None
        data = await r.json()
    d = data.get("data") or {}
    bids = [[float(row[0]), float(row[1])] for row in (d.get("bids") or [])[:DEPTH]]
    asks = [[float(row[0]), float(row[1])] for row in (d.get("asks") or [])[:DEPTH]]
    return bids, asks


async def _fetch_bingx(session, symbol):
    # BTCUSDT → BTC-USDT
    sym = symbol.replace("USDT", "-USDT")
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/depth"
    async with session.get(url, params={"symbol": sym, "limit": DEPTH}) as r:
        if r.status != 200:
            return None
        data = await r.json()
    d = data.get("data") or {}
    bids = [[float(p), float(q)] for p, q in d.get("bids", [])]
    asks = [[float(p), float(q)] for p, q in d.get("asks", [])]
    return bids, asks


async def _fetch_kucoin(session, symbol):
    # BTCUSDT → BTCUSDTM
    inst = symbol + "M"
    url = "https://api-futures.kucoin.com/api/v1/level2/depth20"
    async with session.get(url, params={"symbol": inst}) as r:
        if r.status != 200:
            return None
        data = await r.json()
    d = data.get("data") or {}
    bids = [[float(p), float(q)] for p, q in (d.get("bids") or [])]
    asks = [[float(p), float(q)] for p, q in (d.get("asks") or [])]
    return bids, asks


_FETCHERS = {
    "binance": _fetch_binance,
    "bybit":   _fetch_bybit,
    "okx":     _fetch_okx,
    "bitget":  _fetch_bitget,
    "gate":    _fetch_gate,
    "mexc":    _fetch_mexc,
    "bingx":   _fetch_bingx,
    "kucoin":  _fetch_kucoin,
    # DEX: для DEX честная "глубина" — это liquidity пула из DexScreener.
    # Оцениваем консервативно как 1% от liquidity (типичный безопасный свап).
}
