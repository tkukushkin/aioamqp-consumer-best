import asyncio
from typing import Awaitable, Callable, Tuple

import aioamqp
from aioamqp.channel import Channel

from aioamqp_consumer_best.records import ConnectionParams


async def connect_and_open_channel(
        connection_params: ConnectionParams,
        on_error: Callable[[Exception], Awaitable[None]] = None,
        loop: asyncio.AbstractEventLoop = None,
) -> Tuple[asyncio.Transport, aioamqp.AmqpProtocol, Channel]:
    loop = loop or asyncio.get_event_loop()
    transport, protocol = await aioamqp.connect(
        host=connection_params.host,
        port=connection_params.port,
        login=connection_params.username,
        password=connection_params.password,
        virtualhost=connection_params.virtual_host,
        on_error=on_error,
        loop=loop,
    )
    channel = await protocol.channel()
    return transport, protocol, channel
