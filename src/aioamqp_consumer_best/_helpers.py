import asyncio
from collections.abc import AsyncIterator
from typing import TypeVar

_T = TypeVar("_T")


async def queue_to_iterator(queue: asyncio.Queue[_T]) -> AsyncIterator[_T]:
    while True:
        yield await queue.get()
