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
