import gc
import signal
import asyncio
import traceback
from os import getenv
from typing import List, Optional

from app import KrakTrader
from app.publisher import Publisher
from common import get_logger


async def on_exit(app):
    logger.info(f'app -> on_exit: CANCEL_ALL')
    await app.cancel_all()
    try:
        tasks = asyncio.all_tasks()
        for t in [t for t in tasks if not (t.done() or t.cancelled())]:
            loop.run_until_complete(t)
    finally:
        asyncio.ensure_future(stop())


async def stop():
    loop.stop()


def setup_sig_handlers(app):
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(on_exit(app)))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(on_exit(app)))
    loop.add_signal_handler(signal.SIGABRT, lambda: asyncio.create_task(on_exit(app)))


async def preload_app(symbol: str, app: KrakTrader):
    try:
        setup_sig_handlers(app)
    except Exception as e:
        logger.warning('signal handlers not implemented on windows')

    await app.connect()

    await app.cancel_all()

    await app.subscribe({'name': 'openOrders'}, is_private=True)
    await app.subscribe({'name': 'ownTrades', 'snapshot': False}, is_private=True)

    await app.subscribe({'name': 'book'}, pair=[symbol])
    await app.subscribe({'name': 'trade'}, pair=[symbol])
    # await app.subscribe({'name': 'ohlc'}, pair=symbols)
    # await app.subscribe({'name': 'ticker'}, pair=symbols)
    # await app.subscribe({'name': 'spread'}, pair=symbols)

async def start_app(app: KrakTrader):
    try:
        await app.start()
    except Exception as e:
        logger.critical(f'\n{traceback.format_exc()}')
        await app.cancel_all()

    await on_exit(app)


async def main() -> None:
    symbols: List[str] = ['XBT/USD', 'ATOM/USD']

    key: Optional[str] = getenv('KRAKEN_API_KEY')
    secret: Optional[str] = getenv('KRAKEN_API_SECRET')

    if key and secret:
        app: KrakTrader = KrakTrader(
            symbols[0],
            url='wss://ws.kraken.com',
            auth_url='wss://ws-auth.kraken.com',
            http_url='https://api.kraken.com',
            key=key,
            secret=secret,
            publisher=Publisher("127.0.0.1", 8889)
        )

        await preload_app(symbols[0], app)
        await start_app(app)

    else:
        logger.error(f'main() not started: missing api key or secret')
        loop.stop()


def run_mypy():
    from mypy import api
    result = api.run([f'{__name__}.py'])

    if result[0]:
        logger.info(f'mypy -> {result[0]}')

    if result[1]:
        logger.error(f'mypy type check failed')
        logger.error(result[1])
    return result[2]


if __name__ == '__main__':
    logger = get_logger(__name__)
    exit_status = run_mypy()
    if not exit_status:
        gc.collect()
        gc.set_threshold(4096, 10, 10)

        loop = asyncio.new_event_loop()
        loop.create_task(main())
        loop.run_forever()

