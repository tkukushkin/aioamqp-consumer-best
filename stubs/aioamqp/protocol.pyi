import asyncio

from aioamqp.channel import Channel


class AmqpProtocol(asyncio.StreamReaderProtocol):
    state: int

    async def channel(self) -> Channel: ...

    async def wait_closed(self) -> None: ...




OPEN: int
