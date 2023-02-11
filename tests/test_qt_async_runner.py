import random
import time
from functools import partial
from threading import Barrier

import pytest
from pytestqt.qtbot import QtBot
from qt_async_threads import QtAsyncRunner
from qtpy.QtWidgets import QApplication

from tests.testing import assert_is_another_thread
from tests.testing import assert_is_main_thread


def test_with_thread(runner: QtAsyncRunner, qtbot: QtBot) -> None:
    """An async function which calls ``run``."""
    results: list[int] = []

    async def foo() -> None:
        assert_is_main_thread()
        result = await runner.run(double, 33)
        results.append(result)

    runner.start_coroutine(foo())
    qtbot.waitUntil(runner.is_idle)
    assert results == [66]


def test_no_thread(runner: QtAsyncRunner) -> None:
    """
    Check a straightforward async function which does not call ``run``.

    We want to make sure our runner can evaluate trivial async functions, more of
    a sanity check thank anything else.
    """
    results: list[int] = []

    async def foo() -> None:
        assert_is_main_thread()
        results.append(42)

    start_func = runner.to_sync(foo)
    start_func()
    assert results == [42]


def test_exception(runner: QtAsyncRunner, qtbot: QtBot) -> None:
    """
    Check that exceptions raised in a thread are propagated naturally
    while we ``await`` it.
    """
    error: Exception | None = None

    def raise_error() -> None:
        assert_is_another_thread()
        raise RuntimeError("oh no")

    async def foo() -> None:
        assert_is_main_thread()
        try:
            await runner.run(raise_error)
        except Exception as e:
            nonlocal error
            error = e

    runner.start_coroutine(foo())
    qtbot.waitUntil(runner.is_idle)
    assert isinstance(error, RuntimeError)


def test_start_several_at_same_time(qtbot: QtBot, runner: QtAsyncRunner) -> None:
    """
    Sanity check that we can have many functions executing in
    threads at the same time.
    """
    assert runner.is_idle()

    results: list[int] = []

    async def foo(i: int) -> None:
        assert_is_main_thread()
        for _ in range(5):
            result = await runner.run(double, i)
            results.append(result)

    loop_count = 100
    for i in range(loop_count):
        runner.start_coroutine(foo(i))

    qtbot.waitUntil(runner.is_idle)
    assert len(results) == loop_count * 5
    # Use a set() as the order is not guaranteed.
    assert set(results) == set([i * 2 for i in range(loop_count)] * 5)


def test_run_parallel(qtbot: QtBot, runner: QtAsyncRunner) -> None:
    """
    run_parallel() will run a sequence of functions in parallel.
    """
    results: list[int] = []

    async def foo(count: int) -> None:
        assert_is_main_thread()
        funcs = [partial(double, x, sleep_s=random.randrange(0, 10) / 1000.0) for x in range(count)]
        async for result in runner.run_parallel(funcs):
            results.append(result)

    count = 100
    runner.start_coroutine(foo(count))
    runner.start_coroutine(foo(count * 2))
    qtbot.waitUntil(runner.is_idle)

    assert len(results) == count * 3
    assert set(results) == {x * 2 for x in range(count * 2)}


def test_run_parallel_in_batches(qtbot: QtBot, runner: QtAsyncRunner) -> None:
    """
    Check that ``run_parallel`` submits functions in batches to the pool (BA-426).
    """
    results: list[int | str] = []

    async def foo(count: int) -> None:
        funcs = [partial(double, x, sleep_s=1 / 1000.0) for x in range(count)]
        async for x in runner.run_parallel(funcs):
            results.append(x)

    async def bar() -> None:
        x = await runner.run(lambda: "bar result")
        results.append(x)

    # Spawn foo(), which submits lots of functions to the pool, and bar() next.
    # If we are not batching the functions in run_parallel(), foo would send all its functions
    # in one go, which would cause bar()'s result to appear at the end of the
    # results list.
    count = 100
    runner.start_coroutine(foo(count))
    runner.start_coroutine(bar())
    qtbot.waitUntil(runner.is_idle)

    # We check that bar() results is in the first quarter of the list; if
    # we are not batching the functions, it almost always appears as the last
    # item, or rarely as one of the few last items.
    assert "bar result" in results[: count // 4]


def test_run_parallel_stop_midway(qtbot: QtBot, runner: QtAsyncRunner) -> None:
    """
    Ensure we can stop in the middle of ``async for``.
    """
    results: list[int] = []

    async def foo(count: int) -> None:
        assert_is_main_thread()
        funcs = [partial(double, x) for x in range(count)]
        async for result in runner.run_parallel(funcs):
            if len(results) >= count // 2:
                break
            results.append(result)

    count = 100
    runner.start_coroutine(foo(count))
    qtbot.waitUntil(runner.is_idle)

    assert len(results) == 50


def test_ensure_parallel(qtbot: QtBot, qapp: QApplication, runner: QtAsyncRunner) -> None:
    """
    Ensure the ``run_parallel`` executes functions in parallel.
    """

    executed_calls: set[str] = set()
    barrier = Barrier(parties=2, timeout=5.0)

    def slow_function(call_id: str) -> str:
        barrier.wait()
        executed_calls.add(call_id)
        return call_id

    async def execute() -> None:
        funcs = [
            partial(slow_function, "call1"),
            partial(slow_function, "call2"),
        ]
        async for result in runner.run_parallel(funcs):
            assert result in ("call1", "call2")

    runner.start_coroutine(execute())
    qtbot.wait_until(runner.is_idle)
    assert executed_calls == {"call1", "call2"}


def double(x: int, *, sleep_s: float = 0.0) -> int:
    assert_is_another_thread()
    if sleep_s > 0.0:
        time.sleep(sleep_s)
    return x * 2


class TestRunAsyncBlocking:
    def test_result(self, runner: QtAsyncRunner) -> None:
        async def foo() -> int:
            return await runner.run(double, 10)

        assert runner.run_coroutine(foo()) == 20

    def test_exception(self, runner: QtAsyncRunner) -> None:
        class MyError(Exception):
            pass

        def raise_error() -> None:
            raise MyError()

        async def foo() -> None:
            await runner.run(raise_error)

        with pytest.raises(MyError):
            runner.run_coroutine(foo())
