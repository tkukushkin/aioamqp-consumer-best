from __future__ import annotations

from typing import AsyncIterator, TypeVar


T = TypeVar('T')


async def queue_to_iterator(queue: asyncio.Queue[T]) -> AsyncIterator[T]:
    while True:
        yield await queue.get()
