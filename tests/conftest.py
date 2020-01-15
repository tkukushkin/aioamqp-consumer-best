from __future__ import annotations

import asyncio
import contextlib
import socket
import uuid

import pytest
from _pytest.fixtures import FixtureRequest
from aiodocker import Docker
from aiodocker.containers import DockerContainer

from aioamqp import AioamqpException
from aioamqp_consumer_best import ConnectionParams, Consumer, Exchange, Queue, QueueBinding, connect, open_channel


_ROUTING_KEY = 'test-routing-key'


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(name='rabbitmq_port', scope='session')
def rabbitmq_port_fixture() -> int:
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture(name='rabbitmq', scope='session')
async def rabbitmq_fixture(rabbitmq_port) -> _RabbitMQFixture:
    result = _RabbitMQFixture(rabbitmq_port)
    await result.setup()
    yield result
    await result.teardown()


@pytest.fixture(autouse=True)
async def ensure_rabbitmq_is_alive(rabbitmq) -> None:
    await rabbitmq.ensure_is_alive()


@pytest.fixture(name='exchange_name')
def exchange_name_fixture(request: FixtureRequest) -> str:
    return f'{request.node.name}.{uuid.uuid1()}'


@pytest.fixture(name='queue_name')
def queue_name_fixture(request: FixtureRequest) -> str:
    return f'{request.node.name}.{uuid.uuid1()}'


@pytest.fixture(name='connection_params')
def connection_params_fixture(rabbitmq_port):
    return ConnectionParams(port=rabbitmq_port)


@pytest.fixture(name='make_consumer')
def make_consumer_fixture(connection_params, exchange_name, queue_name):
    def make_consumer(middleware, prefetch_count=1):
        return Consumer(
            middleware=middleware,
            prefetch_count=prefetch_count,
            queue=Queue(
                name=queue_name,
                bindings=[QueueBinding(exchange=Exchange(exchange_name), routing_key=_ROUTING_KEY)],
            ),
            connection_params=[connection_params],
        )

    return make_consumer


@pytest.fixture(name='channel')
async def channel_fixture(connection_params):
    async with connect(connection_params) as (_, protocol, _):
        async with open_channel(protocol) as channel:
            yield channel


@pytest.fixture(name='publish')
def publish_fixture(channel, exchange_name, queue_name):
    async def publish(payload: bytes) -> None:
        await channel.confirm_select()
        await channel.publish(payload=payload, exchange_name=exchange_name, routing_key=_ROUTING_KEY)

    return publish


class _RabbitMQFixture:
    _rabbitmq_port: int
    _running: bool
    _container: DockerContainer

    def __init__(
            self,
            rabbitmq_port: int,
    ) -> None:
        self._rabbitmq_port = rabbitmq_port
        self._running = False
        self._docker = Docker()

    async def setup(self) -> None:
        await self._docker.images.pull('rabbitmq:latest')
        self._container = await self._docker.containers.create({
            'Image': 'rabbitmq:latest',
            'AttachStdout': False,
            'AttachStderr': False,
            'HostConfig': {
                'PortBindings': {
                    '5672/tcp': [{'HostPort': str(self._rabbitmq_port)}],
                },
            }
        })
        await self.start()

    async def teardown(self) -> None:
        if self._running:
            await self.stop()
        await self._container.delete()

    async def ensure_is_alive(self) -> None:
        if not self._running:
            await self.start()

    async def start(self) -> None:
        if self._running:
            raise RuntimeError('RabbitMQ is already running')
        await self._container.start()
        await self._wait()
        self._running = True

    async def stop(self) -> None:
        if not self._running:
            raise RuntimeError('RabbitMQ already stopped')
        await self._container.stop()
        self._running = False

    async def restart(self) -> None:
        if not self._running:
            raise RuntimeError('RabbitMQ not running')
        await self._container.restart()
        await self._wait()

    async def _wait(self):
        for _ in range(70):
            try:
                async with connect(ConnectionParams(port=self._rabbitmq_port)) as (_, protocol, _):
                    async with open_channel(protocol):
                        pass
            except (AioamqpException, OSError):
                pass
            else:
                return
            await asyncio.sleep(0.5)
        raise RuntimeError('RabbitMQ does not respond')
