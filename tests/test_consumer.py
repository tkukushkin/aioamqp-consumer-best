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
        tg.start_soon(consumer.start)
        await asyncio.sleep(1)
        await rabbitmq.restart()
        await publish(b"1")
        with anyio.fail_after(30):
            result = await result_future
        tg.cancel_scope.cancel()

    assert result == b"1"


@pytest.mark.functional
@pytest.mark.asyncio
async def test_start__consumer_cancelled__reconnect_and_process_message(
    rabbitmq,
    make_consumer,
    get_channel,
    queue_name,
    publish,
):
    result_future = asyncio.Future()

    async def callback(message):
        result_future.set_result(message.body)

    consumer = make_consumer(Process(callback))

    async with anyio.create_task_group() as tg:
        tg.start_soon(consumer.start)
        await asyncio.sleep(1)
        async with get_channel() as channel:
            await channel.queue_delete(queue_name)
        await asyncio.sleep(1)
        await publish(b"1")
        with anyio.fail_after(3):
            result = await result_future
        tg.cancel_scope.cancel()

    assert result == b"1"
