import asyncio
from typing import Any

from .exceptions import AioamqpException as AioamqpException
from .protocol import AmqpProtocol as AmqpProtocol

async def connect(
    host: str = ...,
    port: int | None = ...,
    login: str = ...,
    password: str = ...,
    virtualhost: str | None = ...,
    login_method: str = ...,
    **kwargs: Any,
) -> tuple[asyncio.Transport, AmqpProtocol]: ...
