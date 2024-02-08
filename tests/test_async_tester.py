import time
from functools import partial

import pytest
from pytestqt import exceptions
from qt_async_threads.pytest_plugin import AsyncTester


def test_start_and_wait(async_tester: AsyncTester) -> None:
    steps: list[str] = []

    async def main() -> None:
        await async_tester.runner.run(lambda: None)
        steps.append("main")
        async_tester.runner.start_coroutine(inner())

    async def inner() -> None:
        await async_tester.runner.run(lambda: None)
        steps.append("inner")

    async_tester.start_and_wait(main())
    assert steps == ["main", "inner"]


def test_start_and_wait_timeout(async_tester: AsyncTester) -> None:

    async def main() -> None:
        await async_tester.runner.run(partial(time.sleep, 2.0))

    async_tester.start_and_wait(main())

    # Test parameter.
    with pytest.raises(exceptions.TimeoutError):
        async_tester.start_and_wait(main(), timeout_s=1)

    # Test default.
    async_tester.timeout_s = 1
    with pytest.raises(exceptions.TimeoutError):
        async_tester.start_and_wait(main())
