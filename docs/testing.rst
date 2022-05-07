=======
Testing
=======

``qt-async-threads`` provides some fixtures and guidelines on how to test applications. The fixtures require `pytest-qt`_.


Patterns
========

When changing an existing slot into an ``async`` function, the test is affected because operations
now not necessarily finish as soon as the slot is called.

For example, we might have the following test for the example in the :ref:`tutorial`:

.. code-block:: python

    def test_download(qtbot: QtBot, tmp_path: Path) -> None:
        window = Window(tmp_path)
        qtbot.addWidget(window)

        window.count_spin.setValue(2)
        window.download_button.click()

        assert len(list(tmp_path.iterdir())) == 2

When we change the function to ``async``, the test will likely fail, because as soon as the function hits the
``runner.run`` call, the ``download_button.click()`` will return, and the assertion will fail because the
files will not have been downloaded yet.

We have some approaches:

Wait on the side-effect
-----------------------

We can leverage :meth:`QtBot.waitUntil <pytestqt.qtbot.QtBot.waitUntil>` to wait until a condition is met, here the condition being that
we have 2 files downloaded in the directory:

.. code-block:: python

    def test_download(qtbot: QtBot, tmp_path: Path, runner: QtAsyncRunner) -> None:
        window = Window(tmp_path, runner)
        qtbot.addWidget(window)

        window.count_spin.setValue(2)
        window.download_button.click()

        def files_downloaded() -> None:
            assert len(list(tmp_path.iterdir())) == 2

        qtbot.waitUntil(files_downloaded)

:meth:`QtBot.waitUntil <pytestqt.qtbot.QtBot.waitUntil>` will call ``files_downloaded()`` in a loop,
until the condition does not raise an :class:`AssertionError` or a time-out occurs.

Wait for the runner to become idle
----------------------------------

We can also use :meth:`QtBot.waitUntil <pytestqt.qtbot.QtBot.waitUntil>` to wait for the runner to
become idle after clicking on the button:

.. code-block:: python

    def test_download(qtbot: QtBot, tmp_path: Path, runner: QtAsyncRunner) -> None:
        window = Window(tmp_path, runner)
        qtbot.addWidget(window)

        window.count_spin.setValue(2)
        window.download_button.click()
        qtbot.waitUntil(runner.is_idle)

        assert len(list(tmp_path.iterdir())) == 2



.. note::
    This approach only works if the signal is connected to the slot using a
    `Qt.DirectConnection <https://doc.qt.io/qt-5/qt.html#ConnectionType-enum>`_ (which is the default).

    If for some reason the connection is of the type ``Qt.QueuedConnection``, this will not work because the signal
    will not be emitted directly by ``.click()``, instead it will be scheduled for later delivery in the
    next pass of the event loop, and ``runner.is_idle()`` will be True.


Calling async functions
-----------------------

If you need to call an ``async`` function directly in the test, you can use :meth:`AsyncTester.start_and_wait <qt_async_threads.pytest_plugin.AsyncTester.start_and_wait>`
to call it.

So it is possible to change from calling ``.click()`` directly to call the slot instead:

.. code-block:: python

    def test_download(
        qtbot: QtBot, tmp_path: Path, runner: QtAsyncRunner, async_tester: AsyncTester
    ) -> None:
        window = Window(tmp_path, runner)
        qtbot.addWidget(window)

        window.count_spin.setValue(2)
        async_tester.start_and_wait(window._on_download_button_clicked())

        assert len(list(tmp_path.iterdir())) == 2

Here we change from calling ``.click()`` to call the slot directly just to exemplify, it is recommended to call functions
which emit the signal when possible as they ensure the signal and slot are connected.

However the technique is useful to test ``async`` functions in isolation when using this library.


Fixtures/classes reference
==========================

.. autofunction:: qt_async_threads.pytest_plugin.runner

.. autofunction:: qt_async_threads.pytest_plugin.async_tester

.. autoclass:: qt_async_threads.pytest_plugin.AsyncTester
    :members:



.. _pytest-qt: https://github.com/pytest-dev/pytest-qt
