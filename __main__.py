import time
import signal
import asyncio
import traceback
from os import getenv
from typing import List, Optional

from app import KrakTrader

async def on_exit(app):
    print(f'app -> on_exit: CANCEL_ALL')
    await app.cancel_all()
    asyncio.get_event_loop().stop()

def setup_sig_handlers(app):
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(on_exit(app)))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(on_exit(app)))
    loop.add_signal_handler(signal.SIGQUIT, lambda: asyncio.create_task(on_exit(app)))
    loop.add_signal_handler(signal.SIGABRT, lambda: asyncio.create_task(on_exit(app)))

async def main() -> None:
    symbols:List[str] = [ 'XBT/USD' ]

    key:Optional[str] = getenv('KRAKEN_API_KEY')
    secret:Optional[str] = getenv('KRAKEN_API_SECRET')

    if key and secret:
        app:KrakTrader = KrakTrader(
            'wss://ws.kraken.com', 
            'wss://ws-auth.kraken.com',
            'https://api.kraken.com',
            key,
            secret
        )

        setup_sig_handlers(app)

        await app.connect()

        await app.cancel_all()

        await app.subscribe_private('openOrders')
        await app.subscribe_private('ownTrades')

        await app.subscribe_public(symbols, 'book')
        await app.subscribe_public(symbols, 'trade')

        try:
            await app.start()
        except Exception as e:
            print(f'app -> FATAL ERROR CANCEL_ALL: \n{traceback.format_exc()}')
            await app.cancel_all()
            asyncio.get_event_loop().stop()

    else:
        print(f'main() not started: missing api key or secret')

def run_mypy():
    from mypy import api
    result = api.run([ f'{__name__}.py' ])

    if result[0]:
        print('\nmypy report:\n')
        print(result[0])  # stdout

    if result[1]:
        print('\nerrors:\n')
        print(result[1])  # stderr
    return result[2]

if __name__ == '__main__':
    exit_status = run_mypy()
    if not exit_status:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()

