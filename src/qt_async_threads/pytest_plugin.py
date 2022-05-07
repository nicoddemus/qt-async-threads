from __future__ import annotations

import os
import sys
from typing import Coroutine
from typing import Iterator

import attr
import pytest
from pytestqt.qtbot import QtBot
from qt_async_threads import QtAsyncRunner


@pytest.fixture
def runner(qtbot: QtBot) -> Iterator[QtAsyncRunner]:
    """Returns a QtAsyncRunner, shutting it down at the end of the test."""
    with QtAsyncRunner(max_threads=4) as runner:
        yield runner


@pytest.fixture
def async_tester(qtbot: QtBot, runner: QtAsyncRunner) -> AsyncTester:
    """
    Return an :class:`~qt_async_threads.pytest_plugin.AsyncTester`,
    with utilities to handling async calls in tests.
    """
    return AsyncTester(runner, qtbot)


@attr.s(auto_attribs=True)
class AsyncTester:
    """
    Testing helper for async functions.
    """

    runner: QtAsyncRunner
    qtbot: QtBot

    def _get_wait_idle_timeout(self) -> int:
        """
        Return the maximum amount of time we should wait for the runner to
        become idle, in ms.
        """
        timeout_s = 5  # This is the default timeout from pytest-qt.
        in_ci = os.environ.get("CI") == "true"
        in_debugger = sys.gettrace() is not None
        if in_debugger and not in_ci:
            # Use a very large timeout if we are running in a debugger,
            # accounting that in CI the tracer is set due to coverage.
            timeout_s = 24 * 60 * 60
        return timeout_s * 1000

    def start_and_wait(self, coroutine: Coroutine) -> None:
        """
        Starts the given coroutine and wait for the runner to be idle.

        Note this is not exactly the same as calling ``run_coroutine``, because
        the former waits only for the given coroutine, while this method waits
        for the runner itself to become idle (meaning this will wait even if
        the given coroutine starts other coroutines).
        """
        self.runner.start_coroutine(coroutine)
        self.qtbot.waitUntil(self.runner.is_idle, timeout=self._get_wait_idle_timeout())
