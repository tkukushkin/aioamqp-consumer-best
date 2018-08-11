import json
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from aioamqp_consumer_best.base_middlewares import FilterNones, Map
from aioamqp_consumer_best.message import Message, MessageAlreadyResolved


logger = logging.getLogger(__name__)

T = TypeVar('T')


async def _convert_body_to_json(message: Message[bytes]) -> Optional[Message[Dict[str, Any]]]:
    try:
        new_body = json.loads(message.body)
    except json.JSONDecodeError:
        logger.exception('Failed to decode message body')
        await message.reject(requeue=False)
        return None
    return message._replace_body(new_body)


to_json = Map(_convert_body_to_json) | FilterNones()


class ProcessBulk(Map[List[Message[T]], None]):

    def __init__(self, func: Callable[[List[Message[T]]], Awaitable[None]]) -> None:
        super().__init__(self._ack_all_if_success(func))

    @staticmethod
    def _ack_all_if_success(
            callback: Callable[[List[Message[T]]], Awaitable[None]],
    ) -> Callable[[List[Message[T]]], Awaitable[None]]:
        @wraps(callback)
        async def wrapper(messages):
            try:
                await callback(messages)
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
