import asyncio, json, gzip, websockets
from .base import BaseConnector


class BingxConnector(BaseConnector):
    """
    BingX Perpetual Swap WebSocket.
    Формат символа на BingX: BTC-USDT (через дефис).
    Сообщения приходят в gzip — распаковываем.

    Особенность: BingX шлёт свой "Ping" (текст/json) и ожидает "Pong".
    Библиотечный ping_interval отключаем — иначе конфликт.
    """
    name = "bingx"

    def get_fee(self):
        return 0.045

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """BTCUSDT → BTC-USDT"""
        return symbol.replace("USDT", "-USDT")

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        """BTC-USDT → BTCUSDT"""
        return symbol.replace("-USDT", "USDT")

    async def connect(self, symbols: list[str]):
        url = "wss://open-api-swap.bingx.com/swap-market"

        while True:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=None,    # отключаем библиотечный ping
                    ping_timeout=None,
                    close_timeout=5,
                ) as ws:
                    # Подписка на bookTicker для каждого символа
                    for s in symbols:
                        await ws.send(json.dumps({
                            "id": s,
                            "reqType": "sub",
                            "dataType": f"{self._convert_symbol(s)}@bookTicker",
                        }))

                    print(f"[BingX] подключён — {len(symbols)} пар")

                    # Фоновый keepalive — шлём Pong каждые 10 секунд
                    async def keepalive():
                        while True:
                            await asyncio.sleep(10)
                            try:
                                await ws.send("Pong")
                            except Exception:
                                break

                    ka_task = asyncio.create_task(keepalive())

                    try:
                        async for raw in ws:
                            try:
                                if isinstance(raw, bytes):
                                    text = gzip.decompress(raw).decode("utf-8")
                                else:
                                    text = raw

                                # BingX ping (текстовый)
                                if text == "Ping" or text == "ping":
                                    await ws.send("Pong")
                                    continue

                                data = json.loads(text)

                                # BingX ping (json)
                                if "ping" in data:
                                    await ws.send(json.dumps({"pong": data["ping"]}))
                                    continue

                                d = data.get("data", {})
                                if not d:
                                    continue

                                symbol_raw = d.get("symbol", "")
                                bid = d.get("bidPrice")
                                ask = d.get("askPrice")

                                if bid and ask and symbol_raw:
                                    self.on_price_update(
                                        self._restore_symbol(symbol_raw),
                                        self.name,
                                        float(bid), float(ask),
                                    )
                            except (gzip.BadGzipFile, json.JSONDecodeError):
                                continue
                    finally:
                        ka_task.cancel()

            except Exception as e:
                print(f"[BingX] реконнект через 3с...")
                await asyncio.sleep(3)
