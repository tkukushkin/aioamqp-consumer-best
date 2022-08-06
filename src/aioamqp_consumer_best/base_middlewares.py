import asyncio
from datetime import datetime
from typing import AsyncIterator, Awaitable, Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


class Middleware(Generic[T, U]):
    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[U]:  # pragma: no cover
        # ensure function to be generator
        empty_list: List[U] = []
        for x in empty_list:
            yield x
        raise NotImplementedError

    def __or__(self, other: "Middleware[U, V]") -> "_Composition[T, U, V]":
        return _Composition(first=self, second=other)

    @staticmethod
    def from_callable(func: Callable[[AsyncIterator[T]], AsyncIterator[U]]) -> "_FromCallable[T, U]":
        return _FromCallable(func)


class _Composition(Middleware[T, V], Generic[T, U, V]):
    first: Middleware[T, U]
    second: Middleware[U, V]

    def __init__(
        self,
        first: Middleware[T, U],
        second: Middleware[U, V],
    ) -> None:
        self.first = first
        self.second = second

    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[V]:
        async for item in self.second(self.first(inp)):
            yield item


class _FromCallable(Middleware[T, U]):
    def __init__(self, func: Callable[[AsyncIterator[T]], AsyncIterator[U]]) -> None:
        self._func = func

    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[U]:
        async for item in self._func(inp):
            yield item


class ToBulks(Middleware[T, List[T]]):
    max_bulk_size: Optional[int]
    bulk_timeout: Optional[float]

    def __init__(self, max_bulk_size: Optional[int] = None, bulk_timeout: Optional[float] = None) -> None:
        assert (
            max_bulk_size is not None or bulk_timeout is not None
        ), "`max_bulk_size` or `bulk_timeout` must be specified"
        self.max_bulk_size = max_bulk_size
        self.bulk_timeout = bulk_timeout

    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[List[T]]:
        items: List[T] = []
        bulk_start: Optional[datetime] = None
        nxt = asyncio.ensure_future(inp.__anext__())
        try:
            while True:
                timeout: Optional[float] = None
                if bulk_start is not None and self.bulk_timeout is not None:
                    timeout = self.bulk_timeout - (datetime.now() - bulk_start).total_seconds()
                try:
                    item = await asyncio.wait_for(asyncio.shield(nxt), timeout)
                except asyncio.TimeoutError:
                    yield items
                    items = []
                    bulk_start = None
                    continue
                except StopAsyncIteration:
                    break

                bulk_start = bulk_start or datetime.now()
                items.append(item)
                if self.max_bulk_size is not None and len(items) == self.max_bulk_size:
                    yield items
                    items = []
                    bulk_start = None
                nxt = asyncio.ensure_future(inp.__anext__())
        finally:
            nxt.cancel()
        if items:
            yield items


class Filter(Middleware[T, T]):
    def __init__(self, predicate: Callable[[T], Awaitable[bool]]) -> None:
        self._predicate = predicate

    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[T]:
        async for item in inp:
            if await self._predicate(item):
                yield item


class Map(Middleware[T, U]):
    def __init__(self, func: Callable[[T], Awaitable[U]]) -> None:
        self._func = func

    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[U]:
        async for item in inp:
            yield await self._func(item)


class FilterNones(Middleware[Optional[T], T]):
    async def __call__(self, inp: AsyncIterator[Optional[T]]) -> AsyncIterator[T]:
        async for item in inp:
            if item:
                yield item


class SkipAll(Middleware[T, None]):
    async def __call__(self, inp: AsyncIterator[T]) -> AsyncIterator[None]:
        async for _ in inp:
            pass
        # ensure function to be generator
        empty_list: List[None] = []
        for x in empty_list:
            yield x  # pragma: no cover
