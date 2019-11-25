import asyncio

import anyio
import pytest

from aioamqp_consumer_best import Process


@pytest.mark.functional
@pytest.mark.asyncio
async def test_start__rabbitmq_restarted__reconnect_and_process_message(rabbitmq, make_consumer, publish):
    result_future = asyncio.Future()

    async def callback(message):
        result_future.set_result(message.body)

    consumer = make_consumer(Process(callback))

    async with anyio.create_task_group() as tg:
        await tg.spawn(consumer.start)
        await asyncio.sleep(1)
        await rabbitmq.restart()
        await publish(b'1')
        async with anyio.fail_after(30):
            result = await result_future
        await tg.cancel_scope.cancel()

    assert result == b'1'
