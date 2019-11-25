# aioamqp-consumer-best

[![PyPI version](https://badge.fury.io/py/aioamqp-consumer-best.svg)](https://pypi.org/project/aioamqp-consumer-best/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aioamqp-consumer-best.svg?color=green)
[![Build Status](https://github.com/tkukushkin/aioamqp-consumer-best/workflows/build/badge.svg?branch=master)](https://github.com/tkukushkin/aioamqp-consumer-best/actions?query=workflow%3Abuild+branch%3Amaster)
[![codecov](https://codecov.io/gh/tkukushkin/aioamqp-consumer-best/branch/master/graph/badge.svg)](https://codecov.io/gh/tkukushkin/aioamqp-consumer-best)

## Usage

```python
import asyncio
from typing import List

from aioamqp_consumer_best import (
    ConnectionParams,
    Consumer,
    Exchange,
    Message,
    ProcessBulk,
    Queue,
    QueueBinding,
    ToBulks,
    load_json,
)


async def callback(messages: List[Message]) -> None:
    print(messages)


consumer = Consumer(
    middleware=(
        load_json
        | ToBulks(max_bulk_size=10, bulk_timeout=3.0)
        | ProcessBulk(callback)
    ),
    prefetch_count=10,
    queue=Queue(
        name='test-queue',
        bindings=[
            QueueBinding(
                exchange=Exchange('test-exchange'),
                routing_key='test-routing-key',
            ),
        ],
    ),
    connection_params=[  # Round robin
        ConnectionParams(),
        ConnectionParams.from_string('amqp://user@rmq-host:5672/'),
    ],
)

asyncio.run(consumer.start())
```
