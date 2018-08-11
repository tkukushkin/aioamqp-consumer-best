from enum import Enum
from typing import Dict, List, Type, TypeVar, Union
from urllib.parse import urlparse

from dataclasses import dataclass, field


ArgumentsType = Dict[str, Union[str, bool, int]]


class ExchangeType(Enum):
    topic = 'topic'
    direct = 'direct'
    fanout = 'fanout'


@dataclass(frozen=True)
class Exchange:
    name: str
    type: ExchangeType = ExchangeType.topic
    durable: bool = True
    auto_delete: bool = False
    internal: bool = False
    arguments: ArgumentsType = field(default_factory=dict)


@dataclass(frozen=True)
class QueueBinding:
    exchange: Exchange
    routing_key: str
    arguments: ArgumentsType = field(default_factory=dict)


@dataclass(frozen=True)
class Queue:
    name: str
    bindings: List[QueueBinding] = field(default_factory=list)
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    arguments: ArgumentsType = field(default_factory=dict)


T = TypeVar('T', bound='ConnectionParams')


@dataclass(frozen=True)
class ConnectionParams:
    host: str = 'localhost'
    port: int = 5672
    username: str = 'guest'
    password: str = 'guest'
    virtual_host: str = '/'

    @classmethod
    def from_string(cls: Type[T], connection_string: str) -> T:
        parse_result = urlparse(connection_string)
        assert parse_result.scheme == 'amqp', 'Scheme must be amqp'
        return cls(  # type: ignore  # https://github.com/python/mypy/issues/2683
            host=parse_result.hostname or cls.host,
            port=int(parse_result.port) if parse_result.port else cls.port,
            username=parse_result.username or cls.username,
            password=parse_result.password or cls.password,
            virtual_host=parse_result.path[1:] if parse_result.path else None
        )
