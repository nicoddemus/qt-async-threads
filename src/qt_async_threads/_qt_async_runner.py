from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Coroutine
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
from typing import Any
from typing import Callable
from typing import cast
from typing import Generator
from typing import Iterable
from typing import Iterator

import attr
from boltons.iterutils import chunked_iter
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QApplication

from ._async_runner_abc import AbstractAsyncRunner
from ._async_runner_abc import Params
from ._async_runner_abc import T

log = logging.getLogger(__name__)


class QtAsyncRunner(AbstractAsyncRunner):
    """
    An implementation of AbstractRunner which runs computational intensive
    functions using a thread pool.
    """

    def __init__(self, max_threads: int | None = None) -> None:
        """
        :param max_threads:
            Maximum number of threads in the thread pool. If None, uses
            the number of CPUs in the system.
        """
        super().__init__()
        self._max_threads = max_threads or os.cpu_count() or 1
        self._pool = ThreadPoolExecutor(max_workers=max_threads)

        # Keep track of running tasks,
        # mostly to know if we are idle or not.
        self._running_tasks: list[_AsyncTask] = []

        # This signaller object is used to signal to us when a future running
        # in another thread finishes. Thanks to Qt's queued connections,
        # signals can be safely emitted from separate threads and are queued
        # to run in the same thread as the object receiving it lives (the main
        # thread in our case).
        self._signaller = _FutureDoneSignaller()
        self._signaller.future_done_signal.connect(self._resume_coroutine)

    @property
    def max_threads(self) -> int:
        """
        Return the maximum number of threads used by the internal
        threading pool.
        """
        return self._max_threads

    def is_idle(self) -> bool:
        return len(self._running_tasks) == 0

    def close(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)

    async def run(
        self, func: Callable[Params, T], *args: Params.args, **kwargs: Params.kwargs
    ) -> T:
        """
        Runs the given function in a thread, and while it is running, yields
        the control back to the Qt event loop.

        When the thread finishes, this async function resumes, returning
        the return value from the function.
        """
        funcs = [partial(func, *args, **kwargs)]
        async for result in self.run_parallel(funcs):
            return result
        assert False, "should never be reached"

    async def run_parallel(  # type:ignore[override]
        self, funcs: Iterable[Callable[[], T]]
    ) -> AsyncIterator[T]:
        """
        Runs functions in parallel (without arguments, use ``partial`` as necessary), yielding
        their results as they get ready.
        """
        # We submit the functions in batches to avoid overloading the pool, which can cause other
        # coroutines to stall. For example, Autofit works by executing 1000s of small functions,
        # which might take a few ms each. If we submitted all those 1000s of functions
        # at once (at the time ``run_parallel`` is called), then other coroutines that try to submit
        # functions to execute in threads would only be resumed much later, causing a noticeable
        # slow down in the application.
        batch_size = max(self._max_threads // 2, 1)
        for function_batch in chunked_iter(funcs, batch_size):
            # Submit all functions from the current batch to the thread pool,
            # using the _AsyncTask to track the futures and await when they finish.
            task = _AsyncTask({self._pool.submit(f) for f in function_batch})
            self._running_tasks.append(task)
            for future in task.futures:
                future.add_done_callback(partial(self._on_task_future_done, task=task))
            try:
                # We wait until all functions in this batch have finished
                # until we submit the next batch. This is not 100% optimal
                # but ensures we get a fairer share of the pool.
                while task.futures:
                    await task
                    for result in task.pop_done_futures():
                        yield result
            finally:
                task.shutdown()
                self._running_tasks.remove(task)

    def _on_future_done(
        self,
        future: Future,
        *,
        coroutine: Coroutine[Any, Any, Any],
    ) -> None:
        """
        Called when a ``Future`` that was submitted to the thread pool finishes.

        This function is called from a separate thread, so we emit the signal
        of the internal ``_signaller``, which thanks to Qt's queued connections feature,
        will post the event to the main loop, and it will be processed there.
        """
        self._signaller.future_done_signal.emit(future, coroutine)

    def _on_task_future_done(self, future: Future, *, task: _AsyncTask) -> None:
        """
        Called when a ``Future`` belonging to a ``_AsyncTask`` has finished.

        Similar to ``_on_future_done``, this will emit a signal so the coroutine is resumed
        in the main thread.
        """
        # At this point, we want to get the coroutine associated with the task, and resume
        # its execution in the main loop, but we must take care here because this callback is called
        # from another thread, and it may be called multiple times in succession, but we
        # want only **one** event to be sent, that's
        # why we use ``pop_coroutine``, which is lock-protected and will return
        # the coroutine and set it to None, so next calls of this method will get ``None``
        # and won't trigger the event again.
        if coroutine := task.pop_coroutine():
            self._signaller.future_done_signal.emit(future, coroutine)

    def _resume_coroutine(
        self,
        future: Future,
        coroutine: Coroutine[Any, Any, Any],
    ) -> None:
        """
        Slots connected to our internal ``_signaller`` object,
        called in the main thread after a future finishes, resuming the paused coroutine.
        """
        assert threading.current_thread() is threading.main_thread()
        self.start_coroutine(coroutine)

    def start_coroutine(self, coroutine: Coroutine) -> None:
        """
        Starts the coroutine, and returns immediately.
        """
        # Note: this function will also be called to resume a paused coroutine that was
        # waiting for a thread to finish (by ``_resume_coroutine``).
        with suppress(StopIteration):
            value = coroutine.send(None)
            if isinstance(value, _AsyncTask):
                # At this point, return control to the event loop; when one
                # of the futures running in the task finishes, it will resume the
                # coroutine back in the main thread.
                value.coroutine = coroutine
                return
            else:
                assert False, f"Unexpected awaitable type: {value!r} {value}"

    def run_coroutine(self, coroutine: Coroutine[Any, Any, T]) -> T:
        """
        Starts the coroutine, doing a busy loop while waiting for it to complete,
        returning then the result.

        Note: see warning in AbstractAsyncRunner about when to use this function.
        """

        result: T | None = None
        exception: Exception | None = None
        completed = False

        async def wrapper() -> None:
            nonlocal result, exception, completed
            try:
                result = await coroutine
            except Exception as e:
                exception = e
            completed = True

        self.start_coroutine(wrapper())
        while not completed:
            QApplication.processEvents()
            time.sleep(0.01)

        if exception is not None:
            raise exception
        return cast(T, result)


@attr.s(auto_attribs=True, eq=False)
class _AsyncTask(Awaitable[None]):
    """
    Awaitable that is propagated up the async stack, containing
    running futures.

    It "awaits" while all futures are processing, and will
    stop and return once any of them complete.
    """

    futures: set[Future]
    coroutine: Coroutine | None = None
    _lock: threading.Lock = attr.Factory(threading.Lock)

    def __await__(self) -> Generator[Any, None, None]:
        if any(x for x in self.futures if x.done()):
            return None
        else:
            yield self

    def pop_done_futures(self) -> Iterator[Any]:
        """
        Yields futures that are done, removing them from the ``futures`` set
        at the same time.
        """
        for future in list(self.futures):
            if future.done():
                self.futures.discard(future)
                yield future.result()

    def pop_coroutine(self) -> Coroutine | None:
        """
        Returns the current coroutine associated with this object, while
        also setting the ``coroutine`` attribute to ``None``. This
        is meant to be called from multiple threads, in a way that only
        one of them will be able to obtain the coroutine object, while the
        others will get ``None``.
        """
        with self._lock:
            coroutine = self.coroutine
            self.coroutine = None
            return coroutine

    def shutdown(self) -> None:
        """Cancels any running futures and clears up its attributes."""
        msg = "Should always be called from ``run_parallel``, at which point this should not have a coroutine associated"
        assert self.coroutine is None, msg
        while self.futures:
            future = self.futures.pop()
            future.cancel()


class _FutureDoneSignaller(QObject):
    """
    QObject subclass which we use as an intermediary to safely emit a signal
    to the main thread when a future finishes in another thread.
    """

    # This emits(Future, Coroutine). We need to use ``object`` as the
    # second parameter because Qt doesn't allow us to use an ABC class there it seems.
    future_done_signal = Signal(Future, object)
