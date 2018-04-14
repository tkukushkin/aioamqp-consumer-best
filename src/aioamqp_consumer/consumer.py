import asyncio
import logging
import socket
from itertools import cycle
from typing import Iterable, Iterator, Optional, TypeVar, Union, cast

import aioamqp
from aioamqp.channel import Channel
from aioamqp.envelope import Envelope
from aioamqp.properties import Properties

from aioamqp_consumer._helpers import gather
from aioamqp_consumer.base_middlewares import Eoq, Middleware, SkipAll
from aioamqp_consumer.connect import connect_and_open_channel
from aioamqp_consumer.declare_queue import declare_queue
from aioamqp_consumer.message import Message
from aioamqp_consumer.records import ConnectionParams, Queue


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
    _transport: asyncio.Transport
    _protocol: Optional[aioamqp.AmqpProtocol] = None
    _channel: Optional[Channel] = None
    _connection_closed: 'asyncio.Future[None]'
    _closed: 'Optional[asyncio.Future[None]]' = None
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
        assert not self._closed, 'Consumer already started.'

        loop = loop or asyncio.get_event_loop()

        self._closed = asyncio.Future(loop=loop)
        # Event after close
        self._closed_ok = asyncio.Event(loop=loop)

        reconnect_attempts = 0

        while not self._closed.done():
            try:
                await self._connect(loop=loop)

                reconnect_attempts = 0

                await gather(
                    self._closed,
                    self._connection_closed,
                    self._process_queue(loop=loop),
                    loop=loop,
                )
            except (aioamqp.AioamqpException, OSError) as e:
                logger.exception(str(e))

                reconnect_attempts += 1
                timeout = min(self.default_reconnect_timeout * reconnect_attempts, self.max_reconnect_timeout)
                logger.info('Trying to reconnect in %d seconds.', timeout)
                await asyncio.sleep(timeout, loop=loop)

            except _ConsumerCloseException:
                pass

        await self._disconnect()
        self._closed = None
        self._closed_ok.set()

    async def close(self) -> None:
        closed = cast('asyncio.Future[None]', self._closed)
        closed.set_exception(_ConsumerCloseException)
        await self._closed_ok.wait()

    async def _connect(self, loop):
        await self._disconnect()

        connection_params = next(self._connection_params_iterator)

        logger.info('Connection params: %s', connection_params)

        self._connection_closed = asyncio.Future(loop=loop)

        async def on_error(exception):
            if not self._connection_closed.done():
                self._connection_closed.set_exception(exception)

        self._transport, self._protocol, self._channel = await connect_and_open_channel(
            connection_params=connection_params,
            on_error=on_error,
            loop=loop,
        )

        logger.info('Connection and channel are ready.')

        await self._channel.basic_qos(prefetch_count=self.prefetch_count)

        await declare_queue(self._channel, self.queue)

        logger.info('AsyncQueue is ready.')

    async def _disconnect(self):
        if self._channel:
            if self._channel.is_open:
                await self._channel.close()
            self._channel = None

        if self._protocol:
            if self._protocol.state == aioamqp.protocol.OPEN:
                await self._protocol.close()
            self._protocol = None

            self._transport.close()
            self._transport = None

    async def _process_queue(self, loop: asyncio.AbstractEventLoop) -> None:
        input_queue: asyncio.Queue[Union[Message[bytes], Eoq]] = (  # pylint: disable=unsubscriptable-object
            asyncio.Queue(loop=loop)
        )
        output_queue: asyncio.Queue[Union[None, Eoq]] = (  # pylint: disable=unsubscriptable-object
            asyncio.Queue(loop=loop, maxsize=1)
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

        await self._middleware.run(
            input_queue=input_queue,
            output_queue=output_queue,
            loop=loop,
        )


class _ConsumerCloseException(Exception):
    pass
