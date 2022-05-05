from __future__ import annotations

import functools
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import AsyncIterator
from typing import Callable
from typing import Coroutine
from typing import Iterable
from typing import ParamSpec
from typing import TypeVar


Params = ParamSpec("Params")
T = TypeVar("T")


class AbstractAsyncRunner(ABC):
    """
    Abstract interface to a runner.

    A runner allow us to start an ``async`` function so that the async function (coroutine) can easily submit
    computational expensive functions to run in a thread, yielding back to the caller so the caller
    can go and do other things.

    This is analogous to what is possible in async libraries like ``asyncio`` and ``trio``,
    but with the difference that this can easily be used from within a normal/blocking function
    in a Qt application.

    This allows us to write slots as async functions that can yield back to the Qt event loop
    when we want to run something in a thread, and resume the slot once the function finishes
    (using the concrete ``QtAsyncRunner`` implementation).

    For tests, there is the ``SequentialRunner`` which evaluates the async function
    to completion in the spot, not executing anything in threads.

    Use it as a context manager to ensure proper cleanup.

    **Usage**

    Usually you want to connect normal Qt signals to slots written as async functions to signals,
    something like this:

    .. code-block:: python

        def _build_ui(self):
            button.clicked.connect(self._on_button_clicked_sync_slot)


        def _on_button_clicked_sync_slot(self):
            self.runner.start_coroutine(self._on_button_clicked_async())


        async def _on_button_clicked_async(self):
            result = await self.runner.run(compute_spectrum, self.spectrum)

    However, the ``to_sync`` method can be used to reduce the boilerplate:

    .. code-block:: python

        def _build_ui(self):
            button.clicked.connect(self.runner.to_sync(self._on_button_clicked))


        async def _on_button_clicked(self):
            result = await self.runner.run(compute_spectrum, self.spectrum)


    **Running many functions in parallel**

    Often we want to submit several functions to run at the same time (respecting the underlying
    number of threads in the pool of course), in which case one can use ``run_parallel``:

    .. code-block:: python

        def compute(*args):
            ...


        async def _compute(self) -> None:
            funcs = [partial(compute, ...) for _ in range(attempts)]
            async for result in self.runner.run_parallel(funcs):
                # do something with ``result``
                ...

    Using ``async for``, we submit the functions to a thread pool, and we asynchronously
    process the results as they are completed.
    """

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @abstractmethod
    def is_idle(self) -> bool:
        """Return True if this runner is not currently executing anything."""

    @abstractmethod
    def close(self) -> None:
        """Close runner and cleanup resources."""

    @abstractmethod
    async def run(
        self, func: Callable[Params, T], *args: Params.args, **kwargs: Params.kwargs
    ) -> T:
        """
        Async function which executes the given callable in a separate
        thread, and yields the control back to async runner while the
        thread is executing.
        """

    @abstractmethod
    async def run_parallel(self, funcs: Iterable[Callable[[], T]]) -> AsyncIterator[T]:
        """
        Runs functions in parallel (without arguments, use ``partial`` as necessary), yielding
        their results as they get ready.
        """

    @abstractmethod
    def start_coroutine(self, async_func: Coroutine) -> None:
        """
        Starts a coroutine, and returns immediately (except in dummy implementations).
        """

    @abstractmethod
    def run_coroutine(self, coroutine: Coroutine[Any, Any, T]) -> T:
        """
        Starts a coroutine, and blocks execution until it finishes, returning its result.

        Note: this blocks the call and should be avoided in production, being used as a last resort
        in cases the main application window or event processing has not started yet (before QApplication.exec()),
        or for testing.
        """

    def to_sync(self, async_func: Callable[..., Coroutine[Any, Any, None]]) -> Callable[..., None]:
        """
        Returns a new sync function that will start its coroutine using ``start_coroutine`` when
        called, returning immediately.

        Use to connect Qt signals to async functions, see ``AbstractAsyncRunner`` docs for example usage.
        """

        @functools.wraps(async_func)
        def func(*args: object, **kwargs: object) -> None:
            gen = async_func(*args, **kwargs)
            self.start_coroutine(gen)

        return func
