"""
DEX Connector — котировки с самого ликвидного пула через DexScreener API.

Особенности:
- REST polling (DEX не имеет WS).
- Для каждого символа один раз находим самый ликвидный USDT/USDC пул
  и кэшируем адрес пула. Обновляем кэш раз в 30 минут.
- Котировки обновляем батчами через /latest/dex/pairs (до 30 пар за запрос).
- Rate limit DexScreener: 300 req/min. Защищаем троттлом.
"""

import asyncio
import time
import aiohttp
from .base import BaseConnector


SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
PAIRS_URL = "https://api.dexscreener.com/latest/dex/pairs"
STABLE_QUOTES = {"USDT", "USDC", "DAI", "BUSD", "FDUSD"}

# Сколько символов максимум обслуживаем (rate limit!)
MAX_SYMBOLS = 80

# Частота опроса (сек)
POLL_INTERVAL = 15

# Частота обновления списка пулов (сек)
POOL_REFRESH = 1800

BATCH_SIZE = 30


class DexConnector(BaseConnector):
    """
    Котировки с самых ликвидных DEX-пулов.
    symbol-формат такой же как на CEX: BTCUSDT, ETHUSDT, ...
    """

    name = "dex"

    def get_fee(self):
        # Средняя swap-комиссия DEX (Uniswap v3 0.05-0.3%, PancakeSwap 0.25%)
        # Плюс slippage/gas — закладываем консервативно.
        return 0.3

    def __init__(self, on_price_update):
        super().__init__(on_price_update)
        # {symbol: {"chain": str, "pair_addr": str, "ts": float}}
        self._pool_cache: dict[str, dict] = {}
        self._session: aiohttp.ClientSession | None = None

    async def connect(self, symbols: list[str]):
        # Ограничиваем список, чтобы не улететь в rate limit
        subset = symbols[:MAX_SYMBOLS]
        print(f"[DEX] старт — {len(subset)} символов (лимит {MAX_SYMBOLS})")

        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        try:
            while True:
                try:
                    await self._discover_pools(subset)
                    await self._poll_prices(subset)
                except Exception as e:
                    print(f"[DEX] ошибка цикла: {e}")
                await asyncio.sleep(POLL_INTERVAL)
        finally:
            if self._session:
                await self._session.close()

    async def _discover_pools(self, symbols: list[str]):
        """Найти самый ликвидный USDT/USDC пул для каждого символа."""
        now = time.time()
        to_refresh = [
            s for s in symbols
            if s not in self._pool_cache
            or (now - self._pool_cache[s]["ts"]) > POOL_REFRESH
        ]
        if not to_refresh:
            return

        # Лимитируем — не больше 20 новых символов за цикл
        for sym in to_refresh[:20]:
            base = sym.replace("USDT", "").replace("USDC", "")
            try:
                async with self._session.get(
                    SEARCH_URL, params={"q": base}
                ) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
            except Exception:
                continue

            pairs = data.get("pairs") or []
            best = None
            best_liq = 0.0
            for p in pairs:
                base_tok = (p.get("baseToken") or {}).get("symbol", "").upper()
                quote_tok = (p.get("quoteToken") or {}).get("symbol", "").upper()
                if base_tok != base:
                    continue
                if quote_tok not in STABLE_QUOTES:
                    continue
                liq = (p.get("liquidity") or {}).get("usd") or 0
                if liq > best_liq:
                    best_liq = liq
                    best = p

            if best and best_liq >= 50_000:  # минимум $50k ликвидности
                self._pool_cache[sym] = {
                    "chain": best.get("chainId", ""),
                    "pair_addr": best.get("pairAddress", ""),
                    "liq": best_liq,
                    "ts": now,
                }

            # Пауза между запросами — бережём rate limit
            await asyncio.sleep(0.25)

    async def _poll_prices(self, symbols: list[str]):
        """Опросить все зарегистрированные пулы батчами по 30 пар."""
        # Группируем по chain (endpoint требует chain в path)
        by_chain: dict[str, list[tuple[str, str]]] = {}
        for sym in symbols:
            info = self._pool_cache.get(sym)
            if not info:
                continue
            by_chain.setdefault(info["chain"], []).append((sym, info["pair_addr"]))

        for chain, items in by_chain.items():
            for i in range(0, len(items), BATCH_SIZE):
                batch = items[i:i + BATCH_SIZE]
                addr_list = ",".join(addr for _, addr in batch)
                url = f"{PAIRS_URL}/{chain}/{addr_list}"
                try:
                    async with self._session.get(url) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                except Exception:
                    continue

                pairs = data.get("pairs") or []
                # Сопоставляем по pairAddress
                addr_to_symbol = {addr.lower(): sym for sym, addr in batch}
                for p in pairs:
                    addr = (p.get("pairAddress") or "").lower()
                    sym = addr_to_symbol.get(addr)
                    if not sym:
                        continue
                    price_str = p.get("priceUsd")
                    if not price_str:
                        continue
                    try:
                        price = float(price_str)
                    except (TypeError, ValueError):
                        continue
                    if price <= 0:
                        continue
                    # DEX-ам невозможно получить честный bid/ask через этот API,
                    # поэтому используем mid-цену с зашитым спредом 0.1%
                    # (реальный swap-слиппадж считается в Auto Size Calculator).
                    half_spread = price * 0.0005
                    bid = price - half_spread
                    ask = price + half_spread
                    self.on_price_update(sym, self.name, bid, ask)

                await asyncio.sleep(0.2)
