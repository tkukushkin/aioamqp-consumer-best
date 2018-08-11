import pytest
from aioamqp.channel import Channel

from aioamqp_consumer_best import QueueBinding
from aioamqp_consumer_best.declare_queue import declare_queue
from aioamqp_consumer_best.records import Exchange, Queue
from tests.utils import future


@pytest.mark.asyncio
async def test_declare_queue(mocker):
    # arrange
    channel = mocker.Mock(spec=Channel)
    channel.queue_declare.return_value = future()
    channel.exchange_declare.return_value = future()
    channel.queue_bind.return_value = future()

    exchange = Exchange('exchange')
    queue_binding = QueueBinding(exchange=exchange, routing_key='routing-key', )
    queue = Queue(name='queue-name', bindings=[queue_binding])

    # act
    await declare_queue(channel=channel, queue=queue)

    # assert
    channel.queue_declare.assert_called_once_with(
        queue_name=queue.name,
        durable=queue.durable,
        exclusive=queue.exclusive,
        auto_delete=queue.auto_delete,
        arguments=queue.arguments,
    )

    channel.exchange_declare.assert_called_once_with(
        exchange_name=exchange.name,
        type_name=exchange.type.value,
        auto_delete=exchange.auto_delete,
        durable=exchange.durable,
        arguments=exchange.arguments,
    )

    channel.queue_bind.assert_called_once_with(
        queue_name=queue.name,
        exchange_name=exchange.name,
        routing_key=queue_binding.routing_key,
        arguments=exchange.arguments,
    )
