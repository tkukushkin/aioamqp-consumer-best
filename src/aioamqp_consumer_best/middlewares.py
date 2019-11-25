from __future__ import annotations

import asyncio
import json
import logging
from functools import wraps
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, TypeVar

from aioamqp_consumer_best.base_middlewares import Map, Middleware
from aioamqp_consumer_best.message import Message, MessageAlreadyResolved


logger = logging.getLogger(__name__)

T = TypeVar('T')


@Middleware.from_callable
async def load_json(
        inp: AsyncIterator[Message[bytes]],
) -> AsyncIterator[Message[Dict[str, Any]]]:
    async for message in inp:
        try:
            new_body = json.loads(message.body)
        except json.JSONDecodeError:
            logger.exception('Failed to decode message body')
            await message.reject(requeue=False)
        else:
            yield message._replace_body(new_body)


class ProcessBulk(Map[List[Message[T]], None]):

    def __init__(self, func: Callable[[List[Message[T]]], Awaitable[None]]) -> None:
        super().__init__(self._ack_all_if_success(func))

    @staticmethod
    def _ack_all_if_success(
            callback: Callable[[List[Message[T]]], Awaitable[None]],
    ) -> Callable[[List[Message[T]]], Awaitable[None]]:
        @wraps(callback)
        async def wrapper(messages: List[Message[T]]) -> None:
            try:
                await callback(messages)
            except asyncio.CancelledError:  # pylint: disable=try-except-raise
                raise
            except Exception as e:  # pylint: disable=broad-except
                logger.exception(str(e))
                for message in messages:
                    try:
                        await message.reject()
                    except MessageAlreadyResolved:
                        pass
            else:
                for message in messages:
                    try:
                        await message.ack()
                    except MessageAlreadyResolved:
                        pass

        return wrapper


class Process(Map[Message[T], None]):

    def __init__(self, func: Callable[[Message[T]], Awaitable[None]]) -> None:
        super().__init__(self._ack_if_success(func))

    @staticmethod
    def _ack_if_success(
            callback: Callable[[Message[T]], Awaitable[None]],
    ) -> Callable[[Message[T]], Awaitable[None]]:
        @wraps(callback)
        async def wrapper(message: Message[T]) -> None:
            try:
                await callback(message)
            except asyncio.CancelledError:  # pylint: disable=try-except-raise
                raise
            except Exception as e:  # pylint: disable=broad-except
                logger.exception(str(e))
                try:
                    await message.reject()
                except MessageAlreadyResolved:
                    pass
            else:
                try:
                    await message.ack()
                except MessageAlreadyResolved:
                    pass

        return wrapper
