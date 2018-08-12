import asyncio
import logging
from datetime import datetime
from typing import Awaitable, Callable, Generic, List, Optional, TypeVar, Union, cast

from aionursery import Nursery


logger = logging.getLogger(__name__)


class Eoq:
    """
    End Of Queue
    """

    def __eq__(self, other):
        return isinstance(other, Eoq)


T = TypeVar('T')
U = TypeVar('U')
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
PipeT = TypeVar('PipeT')
OtherOutputT = TypeVar('OtherOutputT')


class Middleware(Generic[InputT, OutputT]):

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[InputT, Eoq]]',
            output_queue: 'asyncio.Queue[Union[OutputT, Eoq]]',
            loop: asyncio.AbstractEventLoop = None,
    ) -> None:
        raise NotImplementedError

    def __or__(
            self,
            other: 'Middleware[OutputT, OtherOutputT]'
    ) -> '_Composition[InputT, OutputT, OtherOutputT]':
        return _Composition(first=self, second=other)


class _Composition(Middleware[InputT, OutputT], Generic[InputT, PipeT, OutputT]):
    first: Middleware[InputT, PipeT]
    second: Middleware[PipeT, OutputT]

    def __init__(
            self,
            first: Middleware[InputT, PipeT],
            second: Middleware[PipeT, OutputT],
    ) -> None:
        self.first = first
        self.second = second

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[InputT, Eoq]]',
            output_queue: 'asyncio.Queue[Union[OutputT, Eoq]]',
            loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        loop = loop or asyncio.get_event_loop()
        pipe: asyncio.Queue[Union[PipeT, Eoq]] = asyncio.Queue(loop=loop)  # pylint: disable=unsubscriptable-object
        async with Nursery() as nursery:
            nursery.start_soon(self.first.run(input_queue, pipe, loop=loop))
            nursery.start_soon(self.second.run(pipe, output_queue, loop=loop))


class ToBulks(Middleware[T, List[T]]):
    max_bulk_size: Optional[int]
    bulk_timeout: Optional[float]

    def __init__(self, max_bulk_size: int = None, bulk_timeout: float = None) -> None:
        assert (
            max_bulk_size is not None
            or bulk_timeout is not None
        ), '`max_bulk_size` or `bulk_timeout` must be specified'
        self.max_bulk_size = max_bulk_size
        self.bulk_timeout = bulk_timeout

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[T, Eoq]]',
            output_queue: 'asyncio.Queue[Union[List[T], Eoq]]',
            loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        loop = loop or asyncio.get_event_loop()
        items: List[T] = []
        bulk_start: Optional[datetime] = None

        while True:
            timeout: Optional[float] = None
            if bulk_start is not None and self.bulk_timeout is not None:
                timeout = self.bulk_timeout - (datetime.now() - bulk_start).total_seconds()

            try:
                item = await asyncio.wait_for(input_queue.get(), timeout=timeout, loop=loop)
            except asyncio.TimeoutError:
                output_queue.put_nowait(items)
                items = []
                bulk_start = None
                continue

            if isinstance(item, Eoq):
                break

            bulk_start = bulk_start or datetime.now()
            items.append(item)

            if self.max_bulk_size is not None and len(items) == self.max_bulk_size:
                output_queue.put_nowait(items)
                items = []
                bulk_start = None

        if items:
            output_queue.put_nowait(items)
        output_queue.put_nowait(Eoq())


class Filter(Middleware[T, T]):

    def __init__(self, predicate: Callable[[T], Awaitable[bool]]) -> None:
        self.predicate = predicate  # type: ignore # https://github.com/python/mypy/issues/708

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[T, Eoq]]',
            output_queue: 'asyncio.Queue[Union[T, Eoq]]',
            loop: asyncio.AbstractEventLoop = None,  # pylint: disable=unused-argument
    ) -> None:
        while True:
            item = await input_queue.get()
            if isinstance(item, Eoq):
                output_queue.put_nowait(item)
                return

            if await self.predicate(cast(T, item)):
                output_queue.put_nowait(item)


class Map(Middleware[T, U]):

    def __init__(self, func: Callable[[T], Awaitable[U]]) -> None:
        self.func = func  # type: ignore # https://github.com/python/mypy/issues/708

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[T, Eoq]]',
            output_queue: 'asyncio.Queue[Union[U, Eoq]]',
            loop: asyncio.AbstractEventLoop = None,  # pylint: disable=unused-argument
    ) -> None:
        while True:
            item = await input_queue.get()
            if isinstance(item, Eoq):
                output_queue.put_nowait(item)
                break

            output_queue.put_nowait(await self.func(item))


class FilterNones(Middleware[Optional[T], T]):

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[Optional[T], Eoq]]',
            output_queue: 'asyncio.Queue[Union[T, Eoq]]',
            loop: asyncio.AbstractEventLoop = None,  # pylint: disable=unused-argument
    ) -> None:
        while True:
            item = await input_queue.get()
            if item is None:
                continue

            output_queue.put_nowait(item)

            if isinstance(item, Eoq):
                break


class SkipAll(Middleware[T, None]):

    async def run(
            self,
            input_queue: 'asyncio.Queue[Union[T, Eoq]]',
            output_queue: 'asyncio.Queue[Union[None, Eoq]]',
            loop: asyncio.AbstractEventLoop = None,  # pylint: disable=unused-argument
    ) -> None:
        while not isinstance(await input_queue.get(), Eoq):
            pass
        output_queue.put_nowait(Eoq())
