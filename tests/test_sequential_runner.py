from functools import partial
from typing import Generator

import pytest
from qt_async_threads import SequentialRunner

from tests.testing import assert_is_main_thread


@pytest.fixture
def sequential_runner() -> Generator[SequentialRunner, None, None]:
    with SequentialRunner() as runner:
        assert runner.is_idle() is True
        yield runner


def test_run(sequential_runner: SequentialRunner) -> None:
    """
    Functions submitted to ``run`` actually run in the main thread
    when using a ``SequentialRunner``.
    """
    results: list[int] = []

    def double(x: int) -> int:
        assert_is_main_thread()
        return x * 2

    async def foo() -> None:
        assert_is_main_thread()
        result = await sequential_runner.run(double, 33)
        results.append(result)

    sync_func = sequential_runner.to_sync(foo)
    sync_func()
    assert results == [66]


def test_run_parallel(sequential_runner: SequentialRunner) -> None:
    """
    Functions submitted to ``run_parallel`` actually run in the main thread
    when using a ``SequentialRunner``.
    """
    results: list[int] = []

    def double(x: int) -> int:
        assert_is_main_thread()
        return x * 2

    async def foo() -> None:
        assert_is_main_thread()
        funcs = [partial(double, i) for i in range(5)]
        async for result in sequential_runner.run_parallel(funcs):
            results.append(result)

    sequential_runner.run_coroutine(foo())
    assert results == [0, 2, 4, 6, 8]


def test_run_coroutine(sequential_runner: SequentialRunner) -> None:
    """
    ``run_coroutine`` returns the result of the async function
    immediately.
    """

    def halve(x: int) -> int:
        assert_is_main_thread()
        return x // 2

    async def foo(x: int) -> int:
        assert_is_main_thread()
        result = await sequential_runner.run(halve, 44)
        return result + x

    assert sequential_runner.run_coroutine(foo(10)) == 44 // 2 + 10


def test_run_coroutine_error(sequential_runner: SequentialRunner) -> None:
    """SequentialRunner should propagate exceptions naturally."""

    class MyException(Exception):
        pass

    def halve(x: int) -> int:
        assert_is_main_thread()
        raise MyException()

    async def foo(x: int) -> int:
        assert_is_main_thread()
        result = await sequential_runner.run(halve, 44)
        return result + x  # pragma: no cover

    with pytest.raises(MyException):
        sequential_runner.run_coroutine(foo(10))
