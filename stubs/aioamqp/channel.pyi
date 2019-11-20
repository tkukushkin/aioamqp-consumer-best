from typing import Any, Optional, Dict, Union, Callable, Awaitable

from aioamqp.envelope import Envelope
from aioamqp.properties import Properties


_ArgumentsType = Dict[str, Union[str, bool, int]]


class Channel:

    is_open: bool

    async def close(self) -> None: ...

    async def basic_qos(self, *, prefetch_count: int) -> None: ...

    async def basic_consume(
            self,
            *,
            callback: Callable[[Channel, bytes, Envelope, Properties], Awaitable[None]],
            queue_name: str,
            consumer_tag: str,
            arguments: Optional[Dict[str, str]],
    ) -> None: ...

    async def basic_client_ack(self, delivery_tag: int) -> None: ...

    async def basic_reject(self, delivery_tag: int, requeue: bool = ...) -> None: ...

    async def queue_declare(
            self,
            *,
            queue_name: Optional[str],
            durable: bool,
            exclusive: bool,
            auto_delete: bool,
            arguments: Optional[_ArgumentsType],
    ) -> Any: ...

    async def exchange_declare(
            self,
            *,
            exchange_name: str,
            type_name: str,
            durable: bool,
            auto_delete: bool,
            arguments: Optional[_ArgumentsType],
    ) -> Any: ...

    async def queue_bind(
            self,
            *,
            queue_name: str,
            exchange_name: str,
            routing_key: str,
            arguments: Optional[_ArgumentsType],
    ) -> Any: ...
