import asyncio
from typing import AsyncIterator, List, TypeVar

T = TypeVar("T")


def future(value: T = None, *, exception: BaseException = None) -> "asyncio.Future[T]":
    f: asyncio.Future[T] = asyncio.Future()
    if exception:
        f.set_exception(exception)
    else:
        f.set_result(value)
    return f


class Arg(object):
    def __eq__(self, other):
        self.value = other
        return True


async def make_iterator(items: List[T]) -> AsyncIterator[T]:
    for item in items:
        yield item


async def collect_iterator(it: AsyncIterator[T]) -> List[T]:
    result: List[T] = []
    async for item in it:
        result.append(item)
    return result
