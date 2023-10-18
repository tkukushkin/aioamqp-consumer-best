import abc
from collections.abc import Iterable
from itertools import cycle

from aioamqp_consumer_best.records import ConnectionParams


class LoadBalancingPolicyABC(abc.ABC):
    params: Iterable[ConnectionParams]
    queue_name: str

    def __init__(self, params: Iterable[ConnectionParams], queue_name: str) -> None:
        self.params = params
        self.queue_name = queue_name

    @abc.abstractmethod
    async def get_connection_params(self) -> ConnectionParams:
        """Return connection params"""


class RoundRobinPolicy(LoadBalancingPolicyABC):
    def __init__(self, params: Iterable[ConnectionParams], queue_name: str):
        super().__init__(params, queue_name)
        self._connection_params_iterator = cycle(params)

    async def get_connection_params(self) -> ConnectionParams:
        return next(self._connection_params_iterator)
