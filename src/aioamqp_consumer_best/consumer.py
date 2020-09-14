from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Dict, Iterable, Mapping, Optional, Type, TypeVar

import aioamqp
import anyio
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


logger = logging.getLogger(__name__)

T = TypeVar('T')


class Consumer:
    queue: Queue
    prefetch_count: int
    default_reconnect_timeout: float
    max_reconnect_timeout: float
    tag: str
    load_balancing_policy: LoadBalancingPolicyABC
    heartbeat_interval: Optional[int]
    client_properties: Mapping[str, Any]

    _middleware: Middleware[Message[bytes], None]

    def __init__(
            self,
            queue: Queue,
            prefetch_count: int,
            middleware: Middleware[Message[bytes], T],
            connection_params: Optional[Iterable[ConnectionParams]] = None,
            default_reconnect_timeout: float = 3.0,
            max_reconnect_timeout: float = 30.0,
            tag: str = '',
            consume_arguments: Optional[Dict[str, str]] = None,
            load_balancing_policy: Type[LoadBalancingPolicyABC] = RoundRobinPolicy,
            heartbeat_interval: Optional[int] = 60,
            client_properties: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.queue = queue
        self.prefetch_count = prefetch_count
        self.tag = tag or socket.gethostname()
        self.consume_arguments = consume_arguments
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

                logger.info('Trying to connect to %s', connection_params)
                async with connect(
                        connection_params,
                        heartbeat_interval=self.heartbeat_interval,
                        client_properties=self.client_properties,
                ) as (_, protocol, connection_closed_future):
                    logger.info('Connection ready.')

                    async with open_channel(protocol) as channel:
                        logger.info('Channel ready.')
                        reconnect_attempts = 0

                        await channel.basic_qos(prefetch_count=self.prefetch_count)
                        await declare_queue(channel=channel, queue=self.queue)
                        logger.info('Queue is ready.')
                        connected = True

                        async def cancellation_callback(_channel: Channel, _consumer_tag: str) -> None:
                            connection_closed_future.set_exception(_ConsumerCancelled())

                        channel.add_cancellation_callback(cancellation_callback)

                        async with anyio.create_task_group() as tg:
                            await tg.spawn(self._process_queue, channel)
                            await connection_closed_future

            except _ConsumerCancelled:
                logger.info('Consumer cancelled, trying to reconnect.')

            except (aioamqp.AioamqpException, OSError, anyio.ExceptionGroup) as exc:
                if isinstance(exc, anyio.ExceptionGroup):
                    for inner_exc in exc.exceptions:  # pylint: disable=no-member
                        if not isinstance(inner_exc, (aioamqp.AioamqpException, OSError)):
                            raise inner_exc from exc
                if connected:
                    msg = f'Connection closed with exception {type(exc)}'
                else:
                    msg = f'Failed to connect with exception {type(exc)}'
                logger.warning(msg, exc_info=True)
                reconnect_attempts += 1
                reconnect_interval = min(
                    self.default_reconnect_timeout * reconnect_attempts,
                    self.max_reconnect_timeout,
                )
                logger.info('Trying to reconnect in %d seconds.', reconnect_interval)
                await asyncio.sleep(reconnect_interval)

    async def _process_queue(self, channel: Channel) -> None:
        input_queue: asyncio.Queue[Message[bytes]] = (  # pylint: disable=unsubscriptable-object
            asyncio.Queue()
        )

        async def callback(_: Channel, body: bytes, envelope: Envelope, properties: Properties) -> None:
            input_queue.put_nowait(Message(
                channel=channel,
                body=body,
                envelope=envelope,
                properties=properties,
            ))

        await channel.basic_consume(
            callback=callback,
            queue_name=self.queue.name,
            consumer_tag=self.tag,
            arguments=self.consume_arguments
        )

        async for _ in self._middleware(inp=queue_to_iterator(input_queue)):
            pass


class _ConsumerCancelled(Exception):
    pass
