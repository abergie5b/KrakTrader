import websockets


class Consumer:
    def __init__(self, url):
        self._url = url
        self._callbacks = {}

    def on(self, topic, callback):
        self._callbacks[topic] = callback

    async def start(self):
        async for message in websockets.connect(self._url):
            topic = message["py/object"]
            callback = self._callbacks.get(topic)
            if callback:
                callback(message)
