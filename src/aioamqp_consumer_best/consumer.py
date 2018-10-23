import asyncio
import logging
import socket
from itertools import cycle
from typing import Iterable, Iterator, Optional, TypeVar, cast

import aioamqp
from aioamqp.channel import Channel
from aioamqp.envelope import Envelope
from aioamqp.properties import Properties
from aionursery import Nursery

from aioamqp_consumer_best._helpers import queue_to_iterator
from aioamqp_consumer_best.base_middlewares import Middleware, SkipAll
from aioamqp_consumer_best.connect import connect_and_open_channel
from aioamqp_consumer_best.declare_queue import declare_queue
from aioamqp_consumer_best.message import Message
from aioamqp_consumer_best.records import ConnectionParams, Queue


logger = logging.getLogger(__name__)

T = TypeVar('T')


class Consumer:
    queue: Queue
    prefetch_count: int
    connection_params: Iterable[ConnectionParams]
    default_reconnect_timeout: float
    max_reconnect_timeout: float
    tag: str

    _middleware: Middleware[Message[bytes], None]
    _connection_params_iterator: Iterator[ConnectionParams]
    _transport: Optional[asyncio.Transport] = None
    _protocol: Optional[aioamqp.AmqpProtocol] = None
    _channel: Optional[Channel] = None
    _closed_future: 'Optional[asyncio.Future[None]]' = None
    _closed_ok: asyncio.Event

    def __init__(
            self,
            queue: Queue,
            prefetch_count: int,
            middleware: Middleware[Message[bytes], T],
            connection_params: Optional[Iterable[ConnectionParams]] = None,
            default_reconnect_timeout: float = 3.0,
            max_reconnect_timeout: float = 30.0,
            tag: str = '',
    ) -> None:
        self.queue = queue
        self.prefetch_count = prefetch_count
        self.connection_params = connection_params or [ConnectionParams()]
        self.tag = tag or socket.gethostname()
        self.default_reconnect_timeout = default_reconnect_timeout
        self.max_reconnect_timeout = max_reconnect_timeout

        self._middleware = middleware | SkipAll()
        self._connection_params_iterator = cycle(self.connection_params)

    async def start(self, loop: asyncio.AbstractEventLoop = None) -> None:
        assert not self._closed_future, 'Consumer already started.'

        loop = loop or asyncio.get_event_loop()

        self._closed_future = asyncio.Future(loop=loop)
        self._closed_ok = asyncio.Event(loop=loop)

        reconnect_attempts = 0

        while True:
            connection_closed_future: asyncio.Future[None] = asyncio.Future(loop=loop)

            try:
                await self._connect(
                    connection_closed_future=connection_closed_future,
                    loop=loop,
                )

                reconnect_attempts = 0

                async with Nursery() as nursery:
                    nursery.start_soon(connection_closed_future)
                    nursery.start_soon(self._closed_future)
                    nursery.start_soon(self._process_queue(loop=loop))

            except (aioamqp.AioamqpException, OSError) as exc:
                logger.exception(str(exc))
                reconnect_attempts += 1
                timeout = min(self.default_reconnect_timeout * reconnect_attempts, self.max_reconnect_timeout)
                logger.info('Trying to reconnect in %d seconds.', timeout)
                await asyncio.sleep(timeout, loop=loop)
            except _ConsumerCloseException:
                break

        await self._disconnect()
        self._closed_future = None
        self._closed_ok.set()

    async def close(self) -> None:
        assert self._closed_future, 'Consumer not started.'
        self._closed_future.set_exception(_ConsumerCloseException())
        await self._closed_ok.wait()

    async def _connect(
            self,
            connection_closed_future: 'asyncio.Future[None]',
            loop: asyncio.AbstractEventLoop,
    ) -> None:
        await self._disconnect()

        connection_params = next(self._connection_params_iterator)

        logger.info('Connection params: %s', connection_params)

        async def on_error(exception):
            if not connection_closed_future.done():
                connection_closed_future.set_exception(exception)

        self._transport, self._protocol, channel = await connect_and_open_channel(
            connection_params=connection_params,
            on_error=on_error,
            loop=loop,
        )
        self._channel = channel

        logger.info('Connection and channel are ready.')

        await channel.basic_qos(prefetch_count=self.prefetch_count)

        await declare_queue(channel=channel, queue=self.queue)

        logger.info('Queue is ready.')

    async def _disconnect(self) -> None:
        if self._channel:
            if self._channel.is_open:
                await self._channel.close()
            self._channel = None

        if self._protocol:
            if self._protocol.state == aioamqp.protocol.OPEN:
                await self._protocol.close()
            self._protocol = None

        if self._transport:
            self._transport.close()
            self._transport = None

    async def _process_queue(self, loop: asyncio.AbstractEventLoop) -> None:
        input_queue: asyncio.Queue[Message[bytes]] = (  # pylint: disable=unsubscriptable-object
            asyncio.Queue(loop=loop)
        )

        async def callback(channel: Channel, body: bytes, envelope: Envelope, properties: Properties) -> None:
            input_queue.put_nowait(Message(
                channel=channel,
                body=body,
                envelope=envelope,
                properties=properties,
            ))

        channel = cast(Channel, self._channel)
        await channel.basic_consume(
            callback=callback,
            queue_name=self.queue.name,
            consumer_tag=self.tag,
        )

        async for _ in self._middleware(inp=queue_to_iterator(input_queue), loop=loop):
            pass


class _ConsumerCloseException(Exception):
    pass
