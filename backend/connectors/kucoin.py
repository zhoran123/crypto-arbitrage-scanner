import asyncio, json, time, websockets, requests
from .base import BaseConnector


class KucoinConnector(BaseConnector):
    """
    KuCoin Futures WebSocket.
    Особенность: перед подключением нужен REST-запрос для токена.
    Формат символа: BTCUSDTM (наш BTCUSDT + M).
    """
    name = "kucoin"

    def get_fee(self):
        return 0.06

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """BTCUSDT → BTCUSDTM"""
        return symbol + "M"

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        """BTCUSDTM → BTCUSDT"""
        if symbol.endswith("M"):
            return symbol[:-1]
        return symbol

    def _get_ws_token(self):
        """Получить токен и endpoint для WebSocket через REST API."""
        resp = requests.post(
            "https://api-futures.kucoin.com/api/v1/bullet-public",
            timeout=10,
        )
        data = resp.json().get("data", {})
        token = data.get("token", "")
        servers = data.get("instanceServers", [])
        if not servers or not token:
            raise Exception("Не удалось получить WS-токен от KuCoin")
        endpoint = servers[0]["endpoint"]
        ping_interval = servers[0].get("pingInterval", 18000)
        return endpoint, token, ping_interval

    async def connect(self, symbols: list[str]):
        while True:
            try:
                # Шаг 1: получаем токен через REST
                endpoint, token, ping_ms = self._get_ws_token()
                connect_id = int(time.time() * 1000)
                url = f"{endpoint}?token={token}&connectId={connect_id}"

                async with websockets.connect(url) as ws:
                    # Шаг 2: ждём welcome
                    welcome = await asyncio.wait_for(ws.recv(), timeout=10)

                    # Шаг 3: подписываемся на тикеры
                    topics = ",".join(
                        f"/contractMarket/tickerV2:{self._convert_symbol(s)}"
                        for s in symbols
                    )
                    await ws.send(json.dumps({
                        "id": connect_id,
                        "type": "subscribe",
                        "topic": topics,
                        "privateChannel": False,
                        "response": True,
                    }))

                    print(f"[KuCoin] подключён — {len(symbols)} пар")

                    # Шаг 4: ping по таймеру + чтение данных
                    ping_sec = ping_ms / 1000 / 2  # пинг в 2 раза чаще

                    async def pinger():
                        while True:
                            await asyncio.sleep(ping_sec)
                            try:
                                await ws.send(json.dumps({
                                    "id": int(time.time() * 1000),
                                    "type": "ping",
                                }))
                            except Exception:
                                break

                    ping_task = asyncio.create_task(pinger())

                    try:
                        async for raw in ws:
                            data = json.loads(raw)

                            if data.get("type") != "message":
                                continue

                            topic = data.get("topic", "")
                            d = data.get("data", {})

                            if "/contractMarket/tickerV2:" in topic:
                                symbol_raw = d.get("symbol", "")
                                bid = d.get("bestBidPrice")
                                ask = d.get("bestAskPrice")

                                if bid and ask and symbol_raw:
                                    self.on_price_update(
                                        self._restore_symbol(symbol_raw),
                                        self.name,
                                        float(bid), float(ask),
                                    )
                    finally:
                        ping_task.cancel()

            except Exception as e:
                print(f"[KuCoin] ошибка: {e} — реконнект через 3с")
                await asyncio.sleep(3)
