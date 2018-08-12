import asyncio

import pytest

from aioamqp_consumer_best.base_middlewares import (
    Eoq,
    Filter,
    FilterNones,
    Map,
    Middleware,
    SkipAll,
    ToBulks,
    _Composition,
)
from tests.utils import collect_queue, future, make_queue


pytestmark = pytest.mark.asyncio


class TestMiddleware:

    async def test__or__(self, mocker):
        # arrange
        CompositionMock = mocker.patch(
            'aioamqp_consumer_best.base_middlewares._Composition',
            autospec=True,
        )
        mid1 = Middleware()
        mid2 = Middleware()

        # act
        result = mid1 | mid2

        # assert
        assert result is CompositionMock.return_value
        CompositionMock.assert_called_once_with(first=mid1, second=mid2)


class Test_Composition:

    async def test_run(self, mocker, event_loop):
        # arrange
        mid1 = mocker.Mock(spec=Middleware)
        mid1.run.return_value = future(None)

        mid2 = mocker.Mock(spec=Middleware)
        mid2.run.return_value = future(None)

        QueueMock = mocker.patch.object(asyncio, 'Queue', autospec=True)

        # act
        await _Composition(mid1, mid2).run(
            input_queue=mocker.sentinel.input_queue,
            output_queue=mocker.sentinel.output_queue,
        )

        # assert
        mid1.run.assert_called_once_with(mocker.sentinel.input_queue, QueueMock.return_value, loop=event_loop)
        mid2.run.assert_called_once_with(QueueMock.return_value, mocker.sentinel.output_queue, loop=event_loop)


class TestToBulks:

    async def test_run(self):
        # arrange
        input_queue = asyncio.Queue()
        output_queue = asyncio.Queue()
        middleware = ToBulks(max_bulk_size=3, bulk_timeout=0.3)

        # act
        await asyncio.gather(
            self._fill_queue(input_queue),
            middleware.run(input_queue=input_queue, output_queue=output_queue),
        )

        # assert
        assert collect_queue(output_queue) == [
            [0, 1],
            [2, 3, 4],
            [5, 6],
            Eoq(),
        ]

    @staticmethod
    async def _fill_queue(queue):
        for i, delta in enumerate([0.3, 0.2, 0.2, 0, 0, 0, 0]):
            await asyncio.sleep(delta)
            queue.put_nowait(i)
        queue.put_nowait(Eoq())


class TestFilter:

    async def test_run(self):
        # arrange
        input_queue = make_queue([1, 2, 3, 4, 5, Eoq()])
        output_queue = asyncio.Queue()

        # act
        await Filter(self.predicate).run(input_queue, output_queue)

        # assert
        assert collect_queue(output_queue) == [2, 4, Eoq()]

    @staticmethod
    async def predicate(item):
        return item % 2 == 0


class TestMap:

    async def test_run(self):
        # arrange
        input_queue = make_queue([1, 2, 3, 4, 5, Eoq()])
        output_queue = asyncio.Queue()

        # act
        await Map(self.func).run(input_queue, output_queue)

        # assert
        assert collect_queue(output_queue) == [2, 3, 4, 5, 6, Eoq()]

    @staticmethod
    async def func(item):
        return item + 1


class TestFilterNones:

    async def test_run(self):
        # arrange
        input_queue = make_queue([1, None, 3, Eoq()])
        output_queue = asyncio.Queue()

        # act
        await FilterNones().run(input_queue, output_queue)

        # assert
        assert collect_queue(output_queue) == [1, 3, Eoq()]


class TestSkipAll:

    async def test_run(self):
        # arrange
        input_queue = make_queue([1, 2, 3, Eoq()])
        output_queue = asyncio.Queue()

        # act
        await SkipAll().run(input_queue, output_queue)

        # assert
        assert collect_queue(output_queue) == [Eoq()]
