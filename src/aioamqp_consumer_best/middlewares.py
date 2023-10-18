import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

import anyio

from aioamqp_consumer_best.base_middlewares import Middleware
from aioamqp_consumer_best.message import Message, MessageAlreadyResolved

_logger = logging.getLogger(__name__)

T = TypeVar("T")


@Middleware.from_callable
async def load_json(
    inp: AsyncIterator[Message[bytes]],
) -> AsyncIterator[Message[dict[str, Any]]]:
    async for message in inp:
        try:
            new_body = json.loads(message.body)
        except json.JSONDecodeError:
            _logger.exception("Failed to decode message body")
            await message.reject(requeue=False)
        else:
            yield message.replace_body(new_body)


class ProcessBulk(Middleware[list[Message[T]], None]):
    def __init__(self, func: Callable[[list[Message[T]]], Awaitable[None]]) -> None:
        super().__init__()
        self._func = func

    async def __call__(self, inp: AsyncIterator[list[Message[T]]]) -> AsyncIterator[None]:
        # ensure iterator
        lst: list[None] = []
        for x in lst:
            yield x

        async with anyio.create_task_group() as tg:
            async for messages in inp:
                tg.start_soon(self._process_messages, messages)

    async def _process_messages(self, messages: list[Message[T]]) -> None:
        try:
            await self._func(messages)
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception("Failed to process messages")
            for message in messages:
                await _resolve(message.reject)
        else:
            for message in messages:
                await _resolve(message.ack)


class Process(Middleware[Message[T], None]):
    def __init__(self, func: Callable[[Message[T]], Awaitable[None]]) -> None:
        super().__init__()
        self._func = func

    async def __call__(self, inp: AsyncIterator[Message[T]]) -> AsyncIterator[None]:
        # ensure iterator
        lst: list[None] = []
        for x in lst:
            yield x

        async with anyio.create_task_group() as tg:
            async for message in inp:
                tg.start_soon(self._process_message, message)

    async def _process_message(self, message: Message[T]) -> None:
        try:
            await self._func(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception("Failed to process message")
            await _resolve(message.reject)
        else:
            await _resolve(message.ack)


async def _resolve(method: Callable[[], Awaitable[None]]) -> None:
    with contextlib.suppress(MessageAlreadyResolved):
        await method()
