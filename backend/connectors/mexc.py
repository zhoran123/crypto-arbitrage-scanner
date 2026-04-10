import asyncio, json, websockets
from .base import BaseConnector


class MexcConnector(BaseConnector):
    """
    MEXC Futures WebSocket.
    Формат символа на MEXC: BTC_USDT (с подчёркиванием).
    У нас внутри: BTCUSDT → конвертируем.
    """
    name = "mexc"

    def get_fee(self):
        return 0.01

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """BTCUSDT → BTC_USDT"""
        return symbol.replace("USDT", "_USDT")

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        """BTC_USDT → BTCUSDT"""
        return symbol.replace("_USDT", "USDT")

    async def connect(self, symbols: list[str]):
        url = "wss://contract.mexc.com/edge"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    # Подписываемся на тикеры
                    for s in symbols:
                        await ws.send(json.dumps({
                            "method": "sub.ticker",
                            "param": {"symbol": self._convert_symbol(s)}
                        }))

                    print(f"[MEXC] подключён — {len(symbols)} пар")

                    async for raw in ws:
                        data = json.loads(raw)
                        channel = data.get("channel", "")

                        if channel == "push.ticker":
                            d = data.get("data", {})
                            symbol_raw = data.get("symbol", "")
                            bid = d.get("bid1")
                            ask = d.get("ask1")

                            if bid and ask and symbol_raw:
                                self.on_price_update(
                                    self._restore_symbol(symbol_raw),
                                    self.name,
                                    float(bid), float(ask),
                                )
            except Exception as e:
                print(f"[MEXC] ошибка: {e} — реконнект через 3с")
                await asyncio.sleep(3)
