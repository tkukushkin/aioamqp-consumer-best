import asyncio

import aioamqp
import pytest

from aioamqp_consumer_best import ConnectionParams, connect


@pytest.mark.asyncio
async def test_connect__heartbeat_interval_is_none__not_passed_to_aioamqp(mocker):
    # arrange
    transport = mocker.Mock(spec=asyncio.BaseTransport)
    protocol = mocker.Mock(spec=aioamqp.AmqpProtocol)
    mocker.patch.object(aioamqp, "connect", return_value=(transport, protocol))

    # act
    async with connect(ConnectionParams(), heartbeat_interval=None):
        pass

    # assert
    assert "heartbeat" not in aioamqp.connect.call_args[1]


@pytest.mark.asyncio
async def test_connect__integer_heartbeat_interval__passed_to_aioamqp(mocker):
    # arrange
    transport = mocker.Mock(spec=asyncio.BaseTransport)
    protocol = mocker.Mock(spec=aioamqp.AmqpProtocol)
    mocker.patch.object(aioamqp, "connect", return_value=(transport, protocol))

    # act
    async with connect(ConnectionParams(), heartbeat_interval=30):
        pass

    # assert
    assert aioamqp.connect.call_args[1]["heartbeat"] == 30
