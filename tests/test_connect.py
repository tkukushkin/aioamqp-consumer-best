import asyncio

import aioamqp
from aioamqp.channel import Channel
import pytest

from aioamqp_consumer_best.connect import connect_and_open_channel
from aioamqp_consumer_best.records import ConnectionParams
from tests.utils import future


@pytest.mark.asyncio
async def test_connect_and_open_channel(mocker):
    # arrange
    transport = mocker.Mock(spec=asyncio.Transport)
    channel = mocker.Mock(spec=Channel)
    protocol = mocker.Mock(spec=aioamqp.AmqpProtocol)
    protocol.channel.return_value = future(channel)
    mocker.patch.object(aioamqp, 'connect', return_value=future((transport, protocol)), auto_spec=True)

    connection_params = ConnectionParams()

    # act
    result = await connect_and_open_channel(
        connection_params=connection_params,
        on_error=mocker.sentinel.on_error,
    )

    # assert
    assert result == (transport, protocol, channel)
    aioamqp.connect.assert_called_once_with(
        host=connection_params.host,
        port=connection_params.port,
        login=connection_params.username,
        password=connection_params.password,
        login_method='PLAIN',
        virtualhost=connection_params.virtual_host,
        on_error=mocker.sentinel.on_error,
        loop=asyncio.get_event_loop(),
    )
    protocol.channel.assert_called_once_with()
