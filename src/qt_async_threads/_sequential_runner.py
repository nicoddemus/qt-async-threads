from typing import Any
from typing import AsyncIterator
from typing import Callable
from typing import cast
from typing import Coroutine
from typing import Iterable

from ._async_runner_abc import AbstractAsyncRunner
from ._async_runner_abc import Params
from ._async_runner_abc import T


class SequentialRunner(AbstractAsyncRunner):
    """
    Implementation of an AbstractRunner which doesn't actually run anything
    in other threads, acting just as a placeholder in situations we don't
    care to run functions in other threads, such as in tests.
    """

    def is_idle(self) -> bool:
        return True

    def close(self) -> None:
        pass

    async def run(
        self, func: Callable[Params, T], *args: Params.args, **kwargs: Params.kwargs
    ) -> T:
        """
        Sequential implementation, does not really run in a thread, just calls the
        function and returns its result.
        """
        return func(*args, **kwargs)

    async def run_parallel(  # type:ignore[override]
        self, funcs: Iterable[Callable[[], T]]
    ) -> AsyncIterator[T]:
        """
        Sequential implementation, runs functions sequentially in the main thread.
        """
        for func in funcs:
            yield func()

    def start_coroutine(self, coroutine: Coroutine) -> None:
        """
        Sequential implementation, just runs the coroutine to completion.
        """
        self.run_coroutine(coroutine)

    def run_coroutine(self, coroutine: Coroutine[None, Any, T]) -> T:
        """
        Runs the given coroutine until it completes, returning its result.
        """
        try:
            coroutine.send(None)
        except StopIteration as stop_e:
            return cast(T, stop_e.value)
        else:
            assert False, "should not get here"
