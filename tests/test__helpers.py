import asyncio

import pytest

from aioamqp_consumer_best._helpers import queue_to_iterator
from tests.utils import future


pytestmark = pytest.mark.asyncio


class Cancelled(BaseException):
    pass


async def test_queue_to_iterator(mocker):
    # arrange
    queue = mocker.Mock(spec=asyncio.Queue)
    queue.get.side_effect = [future(1), future(2), future(exception=Cancelled())]

    # act
    result = []
    with pytest.raises(Cancelled):
        async for item in queue_to_iterator(queue):
            result.append(item)

    # assert
    assert result == [1, 2]
