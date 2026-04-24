import asyncio
import time

import aiohttp

from .base import BaseConnector


SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
PAIRS_URL = "https://api.dexscreener.com/latest/dex/pairs"
STABLE_QUOTES = {"USDT", "USDC", "DAI", "BUSD", "FDUSD"}

MAX_SYMBOLS = 80
POLL_INTERVAL = 15
POOL_REFRESH_SEC = 1800
BATCH_SIZE = 30
MIN_LIQUIDITY_USD = 50_000


class DexConnector(BaseConnector):
    name = "dex"

    def __init__(self, on_price_update, on_liquidity=None):
        super().__init__(on_price_update)
        self._pool_cache: dict[str, dict] = {}
        self._session: aiohttp.ClientSession | None = None
        self._on_liquidity = on_liquidity

    def get_fee(self):
        return 0.3

    async def connect(self, symbols: list[str]):
        tracked = symbols[:MAX_SYMBOLS]
        print(f"[DEX] tracking {len(tracked)} symbols (limit {MAX_SYMBOLS})")

        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        try:
            while True:
                try:
                    await self._discover_pools(tracked)
                    await self._poll_prices(tracked)
                except Exception as exc:
                    print(f"[DEX] cycle error: {exc}")
                await asyncio.sleep(POLL_INTERVAL)
        finally:
            if self._session:
                await self._session.close()

    async def _discover_pools(self, symbols: list[str]):
        now = time.time()
        to_refresh = [
            symbol
            for symbol in symbols
            if symbol not in self._pool_cache
            or (now - self._pool_cache[symbol]["ts"]) > POOL_REFRESH_SEC
        ]

        for symbol in to_refresh[:20]:
            base_symbol = symbol.replace("USDT", "").replace("USDC", "")
            try:
                async with self._session.get(SEARCH_URL, params={"q": base_symbol}) as response:
                    if response.status != 200:
                        continue
                    data = await response.json()
            except Exception:
                continue

            best_pair = None
            best_liquidity = 0.0
            for pair in data.get("pairs") or []:
                base_token = (pair.get("baseToken") or {}).get("symbol", "").upper()
                quote_token = (pair.get("quoteToken") or {}).get("symbol", "").upper()
                if base_token != base_symbol or quote_token not in STABLE_QUOTES:
                    continue

                liquidity = float((pair.get("liquidity") or {}).get("usd") or 0)
                if liquidity > best_liquidity:
                    best_liquidity = liquidity
                    best_pair = pair

            if best_pair and best_liquidity >= MIN_LIQUIDITY_USD:
                self._pool_cache[symbol] = {
                    "chain": best_pair.get("chainId", ""),
                    "pair_address": best_pair.get("pairAddress", ""),
                    "liquidity": best_liquidity,
                    "ts": now,
                }
                if self._on_liquidity:
                    try:
                        self._on_liquidity(symbol, best_liquidity)
                    except Exception:
                        pass

            await asyncio.sleep(0.25)

    async def _poll_prices(self, symbols: list[str]):
        by_chain: dict[str, list[tuple[str, str]]] = {}
        for symbol in symbols:
            info = self._pool_cache.get(symbol)
            if not info:
                continue
            by_chain.setdefault(info["chain"], []).append((symbol, info["pair_address"]))

        for chain, items in by_chain.items():
            for index in range(0, len(items), BATCH_SIZE):
                batch = items[index:index + BATCH_SIZE]
                addresses = ",".join(address for _, address in batch)
                url = f"{PAIRS_URL}/{chain}/{addresses}"

                try:
                    async with self._session.get(url) as response:
                        if response.status != 200:
                            continue
                        data = await response.json()
                except Exception:
                    continue

                address_to_symbol = {address.lower(): symbol for symbol, address in batch}
                for pair in data.get("pairs") or []:
                    address = (pair.get("pairAddress") or "").lower()
                    symbol = address_to_symbol.get(address)
                    if not symbol:
                        continue

                    try:
                        price = float(pair.get("priceUsd") or 0)
                    except (TypeError, ValueError):
                        continue

                    if price <= 0:
                        continue

                    half_spread = price * 0.0005
                    self.on_price_update(symbol, self.name, price - half_spread, price + half_spread)

                await asyncio.sleep(0.2)
