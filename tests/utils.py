import asyncio
from typing import List, TypeVar


T = TypeVar('T')


def future(value: T = None, exception: Exception = None) -> 'asyncio.Future[T]':
    f: asyncio.Future[T] = asyncio.Future()
    if exception:
        f.set_exception(exception)
    else:
        f.set_result(value)
    return f


class Arg(object):

    def __eq__(self, other):
        self.value = other
        return True


def collect_queue(queue: 'asyncio.Queue[T]') -> List[T]:
    result: List[T] = []
    while True:
        try:
            item = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        result.append(item)
    return result


def make_queue(items: List[T]) -> 'asyncio.Queue[T]':
    queue: asyncio.Queue[T] = asyncio.Queue()
    for item in items:
        queue.put_nowait(item)
    return queue
