import asyncio
from collections import Coroutine

import pytest

from aioamqp_consumer._helpers import gather
from tests.utils import future


@pytest.mark.asyncio
async def test_gather__exception_raised__close_all_coroutines(mocker):
    # arrange
    mocker.patch.object(asyncio, 'gather', return_value=future(exception=Exception()))
    coro = mocker.Mock(spec=Coroutine)
    fut = future()

    # act & assert
    with pytest.raises(Exception):
        await gather(coro, fut)

    asyncio.gather.assert_called_once_with(coro, fut, loop=asyncio.get_event_loop())

    coro.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_gather__no_exceptions__no_close_calls(mocker):
    # arrange
    mocker.patch.object(asyncio, 'gather', return_value=future())
    coro = mocker.Mock(spec=Coroutine)
    fut = future()

    # act
    await gather(coro, fut)

    # assert
    assert not coro.close.called
