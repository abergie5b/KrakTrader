import json
import jsonpickle
import websockets
from common import get_logger


class Publisher:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._subs = []
        self.callbacks = {}
        self._logger = get_logger(__name__)

    async def _handler(self, websocket, path):
        self._logger.info(f"new connection received: {path}")
        self._subs.append(websocket)
        on_new_connection = self.callbacks.get('new_connection')
        if on_new_connection:
            await on_new_connection()
        try:
            while True:
                message = await websocket.recv()
                js = json.loads(message)
                callback = self.callbacks.get(js['topic'])
                if callback:
                    await callback(js)
        finally:
            self._subs.remove(websocket)

    def on_new_connection(self, func):
        self.callbacks['new_connection'] = func

    def on_receive_message(self, func, topic):
        self.callbacks[topic] = func

    async def publish(self, message):
        for ws in self._subs:
            await ws.send(jsonpickle.encode(message))

    async def start(self):
        server = await websockets.serve(
            self._handler,
            self._host,
            self._port
        )
        self._logger.info(f"serving websocket on {self._host}:{self._port}")
        await server.serve_forever()
