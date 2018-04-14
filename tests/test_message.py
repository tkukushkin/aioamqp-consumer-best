import pytest
from aioamqp.channel import Channel
from aioamqp.envelope import Envelope

from aioamqp_consumer import Message
from aioamqp_consumer.message import MessageAlreadyResolved
from tests.utils import future


pytestmark = pytest.mark.asyncio


class TestMessage:

    async def test_ack(self, mocker):
        # arrange
        channel = mocker.Mock(spec=Channel)
        channel.basic_client_ack.return_value = future()

        message = self._make_message(mocker, channel)

        # act
        await message.ack()

        # assert
        with pytest.raises(MessageAlreadyResolved):
            await message.ack()

        with pytest.raises(MessageAlreadyResolved):
            await message.reject()

        channel.basic_client_ack.assert_called_once_with(delivery_tag=mocker.sentinel.delivery_tag)

        assert not channel.basic_reject.called

    async def test_reject(self, mocker):
        # arrange
        channel = mocker.Mock(spec=Channel)
        channel.basic_reject.return_value = future()

        message = self._make_message(mocker, channel)

        # act
        await message.reject()

        # assert
        with pytest.raises(MessageAlreadyResolved):
            await message.ack()

        with pytest.raises(MessageAlreadyResolved):
            await message.reject()

        channel.basic_reject.assert_called_once_with(delivery_tag=mocker.sentinel.delivery_tag, requeue=True)

        assert not channel.basic_client_ack.called

    @staticmethod
    def _make_message(mocker, channel):
        return Message(
            body=None,
            channel=channel,
            envelope=mocker.Mock(spec=Envelope, delivery_tag=mocker.sentinel.delivery_tag),
            properties=mocker.sentinel.properties,
        )
