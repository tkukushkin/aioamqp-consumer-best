from __future__ import annotations

import asyncio
from typing import AsyncIterator, TypeVar


T = TypeVar('T')


async def queue_to_iterator(queue: asyncio.Queue[T]) -> AsyncIterator[T]:  # pylint: disable=unsubscriptable-object
    while True:
        yield await queue.get()
