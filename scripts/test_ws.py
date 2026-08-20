import asyncio
import websockets

async def test():
    url = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            print('connected')
            msg = await ws.recv()
            print('received:', msg[:200])
    except Exception as e:
        print('error:', type(e).__name__, e)

if __name__ == '__main__':
    asyncio.run(test())
