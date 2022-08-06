import asyncio
from typing import Any, Optional, Tuple

from .exceptions import AioamqpException as AioamqpException
from .protocol import AmqpProtocol as AmqpProtocol

async def connect(
    host: str = ...,
    port: Optional[int] = ...,
    login: str = ...,
    password: str = ...,
    virtualhost: Optional[str] = ...,
    login_method: str = ...,
    **kwargs: Any,
) -> Tuple[asyncio.Transport, AmqpProtocol]: ...
