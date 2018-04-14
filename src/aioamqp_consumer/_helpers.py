import asyncio
from collections import Coroutine
from typing import Awaitable


async def gather(*coros_or_futures: Awaitable[None], loop: asyncio.AbstractEventLoop = None) -> None:
    loop = loop or asyncio.get_event_loop()
    try:
        await asyncio.gather(*coros_or_futures, loop=loop)
    except BaseException:
        for obj in coros_or_futures:
            if isinstance(obj, Coroutine):
                obj.close()
        raise
