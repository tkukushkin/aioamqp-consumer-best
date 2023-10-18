import asyncio
from collections.abc import AsyncIterator
from typing import TypeVar

_T = TypeVar("_T")


def future(value: _T = None, *, exception: BaseException | None = None) -> asyncio.Future[_T]:
    f: asyncio.Future[_T] = asyncio.Future()
    if exception:
        f.set_exception(exception)
    else:
        f.set_result(value)
    return f


class Arg:
    def __eq__(self, other):
        self.value = other
        return True


async def make_iterator(items: list[_T]) -> AsyncIterator[_T]:
    for item in items:
        yield item


async def collect_iterator(it: AsyncIterator[_T]) -> list[_T]:
    result: list[_T] = []
    async for item in it:
        result.append(item)
    return result
