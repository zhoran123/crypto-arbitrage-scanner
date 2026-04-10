class BaseConnector:
    name: str = "base"

    def __init__(self, on_price_update):
        self.on_price_update = on_price_update

    async def connect(self, symbols: list[str]):
        raise NotImplementedError

    def get_fee(self) -> float:
        raise NotImplementedError
