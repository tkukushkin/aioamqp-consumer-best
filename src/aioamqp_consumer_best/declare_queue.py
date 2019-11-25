from __future__ import annotations

from aioamqp.channel import Channel

from aioamqp_consumer_best.records import Queue


async def declare_queue(channel: Channel, queue: Queue) -> None:
    await channel.queue_declare(
        queue_name=queue.name,
        durable=queue.durable,
        auto_delete=queue.auto_delete,
        exclusive=queue.exclusive,
        arguments=queue.arguments,
    )

    for binding in queue.bindings:
        await channel.exchange_declare(
            exchange_name=binding.exchange.name,
            type_name=binding.exchange.type.value,
            durable=binding.exchange.durable,
            auto_delete=binding.exchange.auto_delete,
            arguments=binding.exchange.arguments,
        )

        await channel.queue_bind(
            queue_name=queue.name,
            exchange_name=binding.exchange.name,
            routing_key=binding.routing_key,
            arguments=binding.arguments,
        )
