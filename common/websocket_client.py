from typing import Optional, Union
from abc import ABC, abstractmethod
from websockets.client import connect, WebSocketClientProtocol

from .logger import get_logger


class WebsocketHandler:
    @abstractmethod
    async def on_message(self, message: str) -> None:
        ...


class WebsocketClient:
    def __init__(self, url: str):
        self._url = url
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._logger = get_logger(__name__)

    async def read_til_close(self, handler: WebsocketHandler) -> None:
        if not self._websocket or self._websocket.close_code:
            await self.connect()

        if self._websocket:
            self._logger.info(f'starting read loop -> {self._url}')
            try:
                async for message in self._websocket:
                    await handler.on_message(str(message))
            finally:
                await self.close()

    async def send(self, data: str) -> None:
        if self._websocket:
            await self._websocket.send(data)

    async def recv(self, data: str) -> None:
        if self._websocket:        
            await self._websocket.send(data)

    async def connect(self) -> None:
        self._logger.info(f'connecting to websocket -> {self._url}')
        self._websocket = await connect(self._url)

    async def close(self) -> None:
        if self._websocket:
            await self._websocket.close()

