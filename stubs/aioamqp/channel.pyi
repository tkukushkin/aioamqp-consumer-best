from collections.abc import Awaitable, Callable
from typing import Any, TypeAlias

from aioamqp.envelope import Envelope
from aioamqp.properties import Properties

_ArgumentsType: TypeAlias = dict[str, str | (bool | int)]

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
        arguments: dict[str, str] | None,
    ) -> None: ...
    async def basic_client_ack(self, delivery_tag: int) -> None: ...
    async def basic_reject(self, delivery_tag: int, requeue: bool = ...) -> None: ...
    async def queue_declare(
        self,
        *,
        queue_name: str | None,
        durable: bool,
        exclusive: bool,
        auto_delete: bool,
        arguments: _ArgumentsType | None,
    ) -> Any: ...
    async def exchange_declare(
        self,
        *,
        exchange_name: str,
        type_name: str,
        durable: bool,
        auto_delete: bool,
        arguments: _ArgumentsType | None,
    ) -> Any: ...
    async def queue_bind(
        self,
        *,
        queue_name: str,
        exchange_name: str,
        routing_key: str,
        arguments: _ArgumentsType | None,
    ) -> Any: ...
    async def confirm_select(self) -> None: ...
    async def publish(
        self,
        payload: bytes,
        exchange_name: str,
        routing_key: str,
    ) -> None: ...
    def add_cancellation_callback(self, callback: Callable[[Channel, str], Awaitable[None]]) -> None: ...
