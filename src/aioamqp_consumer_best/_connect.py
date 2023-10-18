import asyncio
from asyncio import Future
from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import aioamqp
from aioamqp import AioamqpException, AmqpProtocol
from aioamqp.channel import Channel

from aioamqp_consumer_best.records import ConnectionParams


@asynccontextmanager
async def connect(
    connection_params: ConnectionParams,
    *,
    heartbeat_interval: int | None = 60,
    client_properties: Mapping[str, Any] | None = None,
) -> AsyncGenerator[tuple[asyncio.Transport, aioamqp.AmqpProtocol, Future[None]], None]:
    client_properties = client_properties or {}

    kwargs: dict[str, Any] = {}
    if heartbeat_interval is not None:
        kwargs["heartbeat"] = heartbeat_interval

    connection_error_future: Future[None] = Future()

    def on_error(exception: AioamqpException) -> None:
        if not connection_error_future.done():
            connection_error_future.set_exception(exception)

    transport, protocol = await aioamqp.connect(
        host=connection_params.host,
        port=connection_params.port,
        login=connection_params.username,
        password=connection_params.password,
        virtualhost=connection_params.virtual_host,
        login_method="PLAIN",
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
