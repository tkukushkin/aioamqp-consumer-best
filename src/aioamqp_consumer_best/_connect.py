from __future__ import annotations

import asyncio
from asyncio import Future
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Mapping, Optional, Tuple, Dict

import aioamqp
from aioamqp import AioamqpException, AmqpProtocol
from aioamqp.channel import Channel

from aioamqp_consumer_best.records import ConnectionParams


@asynccontextmanager
async def connect(
        connection_params: ConnectionParams,
        *,
        heartbeat_interval: Optional[int] = 60,
        client_properties: Optional[Mapping[str, Any]] = None,
) -> AsyncGenerator[
    Tuple[asyncio.Transport, aioamqp.AmqpProtocol, Future[None]],
    None
]:  # pylint: disable=unsubscriptable-object
    client_properties = client_properties or {}

    kwargs: Dict[str, Any] = {}
    if heartbeat_interval is not None:
        kwargs['heartbeat'] = heartbeat_interval

    connection_error_future: Future[None] = Future()  # pylint: disable=unsubscriptable-object

    def on_error(exception: AioamqpException) -> None:
        if not connection_error_future.done():
            connection_error_future.set_exception(exception)

    transport, protocol = await aioamqp.connect(
        host=connection_params.host,
        port=connection_params.port,
        login=connection_params.username,
        password=connection_params.password,
        virtualhost=connection_params.virtual_host,
        login_method='PLAIN',
        on_error=on_error,
        client_properties=client_properties,
        **kwargs,
    )
    try:
        yield transport, protocol, connection_error_future
    finally:
        transport.close()
        await protocol.wait_closed()


@asynccontextmanager
async def open_channel(protocol: AmqpProtocol) -> AsyncGenerator[Channel, None]:
    channel = await protocol.channel()
    try:
        yield channel
    finally:
        if channel.is_open:
            await channel.close()
