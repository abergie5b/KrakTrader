import asyncio
from typing import List
from app import KrakTrader

async def main():
    symbols:List[str] = [ "XBT/USD" ]
    system:KrakTrader = KrakTrader("wss://beta-ws.kraken.com")
    await system.connect()
    await system.subscribe(symbols, 'book')
    await system.subscribe(symbols, 'trade')

    await system.run()


if __name__ == '__main__':
    asyncio.run(main())
