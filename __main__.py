import asyncio
from typing import List
from krak_trader import KrakTrader

async def main():
    symbols:List[str] = [ "XBT/USD" ]
    system:KrakTrader = KrakTrader("wss://beta-ws.kraken.com")
    await system.connect()
    await system.subscribe_to_book(symbols)
    await system.subscribe_to_trades(symbols)
    await system.run()


if __name__ == '__main__':
    asyncio.run(main())
