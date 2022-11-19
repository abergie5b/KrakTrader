import asyncio
from os import getenv
from typing import List

from app import KrakTrader

async def main():
    symbols:List[str] = [ 'XBT/USD' ]

    app:KrakTrader = KrakTrader(
        'wss://beta-ws.kraken.com', 
        'wss://beta-ws-auth.kraken.com',
        'https://api.kraken.com',
        getenv('KRAKEN_API_KEY') or '',
        getenv('KRAKEN_API_SECRET' or '')
    )
    await app.connect()

    await app.subscribe_private('openOrders')
    await app.subscribe_private('ownTrades')

    await app.cancel_all()

    await app.subscribe_public(symbols, 'book')
    await app.subscribe_public(symbols, 'trade')

    await app.start()


if __name__ == '__main__':
    asyncio.run(main())
