import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Generic, TypeVar

_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")


class Middleware(Generic[_T, _U]):
    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[_U]:  # pragma: no cover
        # ensure function to be generator
        empty_list: list[_U] = []
        for x in empty_list:
            yield x
        raise NotImplementedError

    def __or__(self, other: "Middleware[_U, _V]") -> "_Composition[_T, _U, _V]":
        return _Composition(first=self, second=other)

    @staticmethod
    def from_callable(func: Callable[[AsyncIterator[_T]], AsyncIterator[_U]]) -> "_FromCallable[_T, _U]":
        return _FromCallable(func)


class _Composition(Middleware[_T, _V], Generic[_T, _U, _V]):
    first: Middleware[_T, _U]
    second: Middleware[_U, _V]

    def __init__(
        self,
        first: Middleware[_T, _U],
        second: Middleware[_U, _V],
    ) -> None:
        self.first = first
        self.second = second

    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[_V]:
        async for item in self.second(self.first(inp)):
            yield item


class _FromCallable(Middleware[_T, _U]):
    def __init__(self, func: Callable[[AsyncIterator[_T]], AsyncIterator[_U]]) -> None:
        self._func = func

    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[_U]:
        async for item in self._func(inp):
            yield item


class ToBulks(Middleware[_T, list[_T]]):
    max_bulk_size: int | None
    bulk_timeout: float | None

    def __init__(self, max_bulk_size: int | None = None, bulk_timeout: float | None = None) -> None:
        assert (
            max_bulk_size is not None or bulk_timeout is not None
        ), "`max_bulk_size` or `bulk_timeout` must be specified"
        self.max_bulk_size = max_bulk_size
        self.bulk_timeout = bulk_timeout

    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[list[_T]]:
        items: list[_T] = []
        bulk_start: float | None = None
        nxt = asyncio.ensure_future(inp.__anext__())
        try:
            while True:
                timeout: float | None = None
                if bulk_start is not None and self.bulk_timeout is not None:
                    timeout = self.bulk_timeout - (time.monotonic() - bulk_start)
                try:
                    item = await asyncio.wait_for(asyncio.shield(nxt), timeout)
                except asyncio.TimeoutError:
                    yield items
                    items = []
                    bulk_start = None
                    continue
                except StopAsyncIteration:
                    break

                bulk_start = bulk_start or time.monotonic()
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


class Filter(Middleware[_T, _T]):
    def __init__(self, predicate: Callable[[_T], Awaitable[bool]]) -> None:
        self._predicate = predicate

    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[_T]:
        async for item in inp:
            if await self._predicate(item):
                yield item


class Map(Middleware[_T, _U]):
    def __init__(self, func: Callable[[_T], Awaitable[_U]]) -> None:
        self._func = func

    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[_U]:
        async for item in inp:
            yield await self._func(item)


class FilterNones(Middleware[_T | None, _T]):
    async def __call__(self, inp: AsyncIterator[_T | None]) -> AsyncIterator[_T]:
        async for item in inp:
            if item:
                yield item


class SkipAll(Middleware[_T, None]):
    async def __call__(self, inp: AsyncIterator[_T]) -> AsyncIterator[None]:
        async for _ in inp:
            pass
        # ensure function to be generator
        empty_list: list[None] = []
        for x in empty_list:
            yield x  # pragma: no cover
