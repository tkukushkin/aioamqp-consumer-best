from __future__ import annotations

from typing import Generic, TypeVar

from aioamqp.channel import Channel
from aioamqp.envelope import Envelope
from aioamqp.properties import Properties


T = TypeVar('T')
U = TypeVar('U')


class Message(Generic[T]):  # pylint: disable=unsubscriptable-object
    body: T
    envelope: Envelope
    properties: Properties

    _channel: Channel
    _is_completed: bool

    def __init__(self, channel: Channel, body: T, envelope: Envelope, properties: Properties) -> None:
        self.body = body
        self.envelope = envelope
        self.properties = properties
        self._channel = channel
        self._is_completed = False

    async def ack(self) -> None:
        if self._is_completed:
            raise MessageAlreadyResolved
        await self._channel.basic_client_ack(delivery_tag=self.envelope.delivery_tag)
        self._is_completed = True

    async def reject(self, requeue: bool = True) -> None:
        if self._is_completed:
            raise MessageAlreadyResolved
        await self._channel.basic_reject(delivery_tag=self.envelope.delivery_tag, requeue=requeue)
        self._is_completed = True

    def _replace_body(self, new_body: U) -> Message[U]:
        return Message(
            channel=self._channel,
            body=new_body,
            envelope=self.envelope,
            properties=self.properties,
        )

    def __repr__(self) -> str:
        return f'<Message body={self.body!r}>'


class MessageAlreadyResolved(Exception):
    pass
