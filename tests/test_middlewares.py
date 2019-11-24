import asyncio

import pytest

from aioamqp_consumer_best.message import Message, MessageAlreadyResolved
from aioamqp_consumer_best.middlewares import Process, ProcessBulk, load_json
from tests.utils import Arg, collect_iterator, future, make_iterator


pytestmark = pytest.mark.asyncio


async def test_load_json(mocker):
    # arrange
    message1 = Message(
        body='{"hello": "world"}',
        channel=mocker.sentinel.channel,
        envelope=mocker.sentinel.envelope,
        properties=mocker.sentinel.properties,
    )
    message2 = Message(
        body='invalid json',
        channel=mocker.sentinel.channel,
        envelope=mocker.sentinel.envelope,
        properties=mocker.sentinel.properties,
    )
    mocker.patch.object(message2, 'reject', return_value=future())
    inp = make_iterator([message1, message2])

    # act
    out = load_json.func(inp)

    # assert
    result = await collect_iterator(out)
    message_arg = Arg()
    assert result == [message_arg]
    assert message_arg.value.body == {'hello': 'world'}

    message2.reject.assert_called_once_with(requeue=False)


class TestProcessBulk:

    async def test_run__success__ack_all_messages(self, mocker):
        # arrange
        message1 = Message(
            body='message1',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message1, 'ack', return_value=future())
        message2 = Message(
            body='message2',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message2, 'ack', return_value=future(exception=MessageAlreadyResolved()))
        middleware = ProcessBulk(lambda messages: future(None))
        inp = make_iterator([[message1, message2]])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [None]
        message1.ack.assert_called_once_with()
        message2.ack.assert_called_once_with()

    async def test_run__func_raised_exception__reject_all_messages(self, mocker):
        # arrange
        message1 = Message(
            body='message1',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message1, 'reject', return_value=future())
        message2 = Message(
            body='message2',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message2, 'reject', return_value=future(exception=MessageAlreadyResolved()))

        middleware = ProcessBulk(lambda messages: future(exception=Exception()))
        inp = make_iterator([[message1, message2]])

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [None]
        message1.reject.assert_called_once_with()
        message2.reject.assert_called_once_with()

    async def test_run__callback_cancelled__should_cancel(self, mocker):
        # arrange
        message = Message(
            body='message',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        inp = make_iterator([message])
        middleware = ProcessBulk(lambda _: future(exception=asyncio.CancelledError()))

        # act
        with pytest.raises(asyncio.CancelledError):
            await collect_iterator(middleware(inp))


class TestProcess:

    @pytest.mark.parametrize('ack_result', [
        future(None),
        future(exception=MessageAlreadyResolved()),
    ])
    async def test_run__success__ack_message(self, mocker, ack_result):
        # arrange
        message = Message(
            body='message',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message, 'ack', return_value=ack_result)
        inp = make_iterator([message])
        middleware = Process(lambda _: future(None))

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [None]
        message.ack.assert_called_once_with()

    @pytest.mark.parametrize('reject_result', [
        future(None),
        future(exception=MessageAlreadyResolved()),
    ])
    async def test_run__callback_raised_exception__reject_message(self, mocker, reject_result):
        # arrange
        message = Message(
            body='message',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        mocker.patch.object(message, 'reject', return_value=reject_result)
        inp = make_iterator([message])
        middleware = Process(lambda _: future(exception=Exception()))

        # act
        out = middleware(inp)

        # assert
        assert await collect_iterator(out) == [None]
        message.reject.assert_called_once_with()

    async def test_run__callback_cancelled__should_cancel(self, mocker):
        # arrange
        message = Message(
            body='message',
            channel=mocker.sentinel.channel,
            envelope=mocker.sentinel.envelope,
            properties=mocker.sentinel.properties,
        )
        inp = make_iterator([message])
        middleware = Process(lambda _: future(exception=asyncio.CancelledError()))

        # act
        with pytest.raises(asyncio.CancelledError):
            await collect_iterator(middleware(inp))
