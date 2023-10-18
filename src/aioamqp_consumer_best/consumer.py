import asyncio
import logging
import socket
from collections.abc import Iterable, Mapping
from typing import Any

import aioamqp
import anyio
import exceptiongroup
from aioamqp.channel import Channel
from aioamqp.envelope import Envelope
from aioamqp.properties import Properties

from aioamqp_consumer_best._connect import connect, open_channel
from aioamqp_consumer_best._helpers import queue_to_iterator
from aioamqp_consumer_best._load_balancing_policy import LoadBalancingPolicyABC, RoundRobinPolicy
from aioamqp_consumer_best.base_middlewares import Middleware, SkipAll
from aioamqp_consumer_best.declare_queue import declare_queue
from aioamqp_consumer_best.message import Message
from aioamqp_consumer_best.records import ConnectionParams, Queue

_logger = logging.getLogger(__name__)


class Consumer:
    queue: Queue
    prefetch_count: int
    default_reconnect_timeout: float
    max_reconnect_timeout: float
    tag: str
    consume_arguments: Mapping[str, str]
    load_balancing_policy: LoadBalancingPolicyABC
    heartbeat_interval: int | None
    client_properties: Mapping[str, Any]

    _middleware: Middleware[Message[bytes], None]

    def __init__(
        self,
        queue: Queue,
        prefetch_count: int,
        middleware: Middleware[Message[bytes], Any],
        connection_params: Iterable[ConnectionParams] | None = None,
        default_reconnect_timeout: float = 3.0,
        max_reconnect_timeout: float = 30.0,
        tag: str = "",
        consume_arguments: Mapping[str, str] | None = None,
        load_balancing_policy: type[LoadBalancingPolicyABC] = RoundRobinPolicy,
        heartbeat_interval: int | None = 60,
        client_properties: Mapping[str, Any] | None = None,
    ) -> None:
        self.queue = queue
        self.prefetch_count = prefetch_count
        self.tag = tag or socket.gethostname()
        self.consume_arguments = consume_arguments or {}
        self.default_reconnect_timeout = default_reconnect_timeout
        self.max_reconnect_timeout = max_reconnect_timeout
        self.heartbeat_interval = heartbeat_interval
        self.client_properties = client_properties or {}

        connection_params = connection_params or [ConnectionParams()]
        self.load_balancing_policy = load_balancing_policy(connection_params, queue.name)

        self._middleware = middleware | SkipAll()

    async def start(self) -> None:
        reconnect_attempts = 0

        while True:
            connected: bool = False
            try:
                connection_params = await self.load_balancing_policy.get_connection_params()

                _logger.info("Trying to connect to %s", connection_params)
                async with connect(
                    connection_params,
                    heartbeat_interval=self.heartbeat_interval,
                    client_properties=self.client_properties,
                ) as (_, protocol, connection_closed_future):
                    _logger.info("Connection ready.")

                    async with open_channel(protocol) as channel:
                        _logger.info("Channel ready.")
                        reconnect_attempts = 0

                        await channel.basic_qos(prefetch_count=self.prefetch_count)
                        await declare_queue(channel=channel, queue=self.queue)
                        _logger.info("Queue is ready.")
                        connected = True

                        async def cancellation_callback(_channel: Channel, _consumer_tag: str) -> None:
                            connection_closed_future.set_exception(_ConsumerCancelled())

                        channel.add_cancellation_callback(cancellation_callback)

                        async with anyio.create_task_group() as tg:
                            tg.start_soon(self._process_queue, channel)
                            await connection_closed_future

            except (aioamqp.AioamqpException, OSError, exceptiongroup.ExceptionGroup) as exc:
                if isinstance(exc, exceptiongroup.ExceptionGroup):
                    if any(isinstance(inner_exc, _ConsumerCancelled) for inner_exc in exc.exceptions):
                        _logger.info("Consumer cancelled, trying to reconnect.")
                        continue

                    if not all(
                        isinstance(inner_exc, aioamqp.AioamqpException | OSError) for inner_exc in exc.exceptions
                    ):
                        raise
                    exc = exc.exceptions[0]
                if connected:
                    msg = f"Connection closed with exception {type(exc)}"
                else:
                    msg = f"Failed to connect with exception {type(exc)}"
                _logger.warning(msg, exc_info=True)
                reconnect_attempts += 1
                reconnect_interval = min(
                    self.default_reconnect_timeout * reconnect_attempts,
                    self.max_reconnect_timeout,
                )
                _logger.info("Trying to reconnect in %d seconds.", reconnect_interval)
                await asyncio.sleep(reconnect_interval)

    async def _process_queue(self, channel: Channel) -> None:
        input_queue: asyncio.Queue[Message[bytes]] = asyncio.Queue()

        async def callback(_: Channel, body: bytes, envelope: Envelope, properties: Properties) -> None:
            input_queue.put_nowait(
                Message(
                    channel=channel,
                    body=body,
                    envelope=envelope,
                    properties=properties,
                )
            )

        await channel.basic_consume(
            callback=callback,
            queue_name=self.queue.name,
            consumer_tag=self.tag,
            arguments=dict(self.consume_arguments),
        )

        async for _ in self._middleware(inp=queue_to_iterator(input_queue)):
            pass


class _ConsumerCancelled(Exception):
    pass
