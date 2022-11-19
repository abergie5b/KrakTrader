from abc import ABC, abstractmethod
from websockets import client, WebSocketClientProtocol

class WebsocketHandler:
    @abstractmethod
    def on_message(self, message:str) -> None:
        pass


class WebsocketClient:
    def __init__(self, url:str):
        self._url = url
        self._websocket:Union[WebSocketClientProtocol|None] = None

    async def start(self, handler:WebsocketHandler) -> None:
        if not self._websocket or self._websocket.close_code:
            self.connect()

        print(f'starting -> {self._url}')
        try:
            async for message in self._websocket:
                await handler.on_message(message)
        finally:
            await self.close()

    async def send(self, data:str) -> None:
        await self._websocket.send(data)

    async def recv(self, data:str) -> None:
        await self._websocket.send(data)

    async def connect(self) -> None:
        print(f'connecting -> {self._url}')
        self._websocket = await client.connect(self._url)

    async def close(self) -> None:
        await self._websocket.close()

