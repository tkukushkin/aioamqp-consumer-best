import asyncio

import pytest

from aioamqp_consumer_best.base_middlewares import (
    Filter,
    FilterNones,
    Map,
    Middleware,
    SkipAll,
    ToBulks,
    _Composition,
    _FromCallable,
)
from tests.utils import collect_iterator, make_iterator

pytestmark = pytest.mark.asyncio


class TestMiddleware:
    async def test__or__(self, mocker):
        # arrange
        CompositionMock = mocker.patch(
            "aioamqp_consumer_best.base_middlewares._Composition",
            autospec=True,
        )
        middleware1 = Middleware()
        middleware2 = Middleware()

        # act
        result = middleware1 | middleware2

        # assert
        assert result is CompositionMock.return_value
        CompositionMock.assert_called_once_with(first=middleware1, second=middleware2)

    async def test_from_callable(self, mocker):
        # arrange
        _FromCallableMock = mocker.patch("aioamqp_consumer_best.base_middlewares._FromCallable", autospec=True)

        # act
        middleware = Middleware.from_callable(mocker.sentinel._func)

        # assert
        assert middleware is _FromCallableMock.return_value
        _FromCallableMock.assert_called_once_with(mocker.sentinel._func)


class Test_Composition:
    async def test__call__(self, mocker):
        # arrange
        mid1 = mocker.Mock(spec=Middleware, return_value=mocker.sentinel.it1)
        mid2 = mocker.Mock(spec=Middleware, return_value=make_iterator([mocker.sentinel.item]))
        middleware = _Composition(mid1, mid2)

        # act
        out = middleware(mocker.sentinel.inp)

        # assert
        assert await collect_iterator(out) == [mocker.sentinel.item]
        mid1.assert_called_once_with(mocker.sentinel.inp)
        mid2.assert_called_once_with(mocker.sentinel.it1)


class Test_FromCallable:
    async def test__call__(self):
        # arrange
        middleware = _FromCallable(self._foo)
        inp = make_iterator([1, 2])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [2, 3]

    @staticmethod
    async def _foo(inp):
        async for item in inp:
            yield item + 1


class TestToBulks:
    async def test__call__(self):
        # arrange
        middleware = ToBulks(max_bulk_size=3, bulk_timeout=0.3)
        inp = self._get_it()

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [
            [0, 1],
            [2, 3, 4],
            [5, 6],
        ]

    @staticmethod
    async def _get_it():
        for i, delta in enumerate([0.3, 0.2, 0.2, 0, 0, 0, 0]):
            await asyncio.sleep(delta)
            yield i


class TestFilter:
    async def test__call__(self):
        # arrange
        middleware = Filter(self._predicate)
        inp = make_iterator([1, 2, 3, 4, 5])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [2, 4]

    @staticmethod
    async def _predicate(item):
        return item % 2 == 0


class TestMap:
    async def test__call__(self):
        # arrange
        middleware = Map(self._func)
        inp = make_iterator([1, 2, 3, 4, 5])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [2, 3, 4, 5, 6]

    @staticmethod
    async def _func(item):
        return item + 1


class TestFilterNones:
    async def test__call__(self):
        # arrange
        middleware = FilterNones()
        inp = make_iterator([1, None, 3])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [1, 3]


class TestSkipAll:
    async def test__call__(self):
        # arrange
        middleware = SkipAll()
        inp = make_iterator([1, 2, 3])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == []
