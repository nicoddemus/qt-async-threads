================
qt-async-threads
================

.. image:: https://img.shields.io/pypi/v/qt-async-threads.svg
    :target: https://pypi.org/project/qt-async-threads/

.. image:: https://img.shields.io/conda/vn/conda-forge/qt-async-threads.svg
    :target: https://anaconda.org/conda-forge/qt-async-threads

.. image:: https://img.shields.io/pypi/pyversions/qt-async-threads.svg
    :target: https://pypi.org/project/qt-async-threads/

.. image:: https://github.com/nicoddemus/qt-async-threads/workflows/test/badge.svg
    :target: https://github.com/nicoddemus/qt-async-threads/actions?query=workflow%3Atest

.. image:: https://results.pre-commit.ci/badge/github/nicoddemus/qt-async-threads/main.svg
    :target: https://results.pre-commit.ci/latest/github/nicoddemus/qt-async-threads/main
    :alt: pre-commit.ci status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: https://readthedocs.org/projects/qt-async-threads/badge/?version=latest
    :target: https://qt-async-threads.readthedocs.io/en/latest/?badge=latest

----

``qt-async-threads`` allows Qt applications to use convenient ``async/await`` syntax to run
computational intensive or IO operations in threads, selectively changing the code slightly
to provide a more responsive UI.

The objective of this library is to provide a simple and convenient way to improve
UI responsiveness in existing Qt applications by using ``async/await``, while
at the same time not requiring large scale refactorings.

Supports `PyQt5`_, `PyQt6`_, `PySide2`_, and `PySide6`_ thanks to `qtpy`_.

Example
=======

The widget below downloads pictures of cats when the user clicks on a button (some parts omitted for brevity):

.. code-block:: python

    class CatsWidget(QWidget):
        def __init__(self, parent: QWidget) -> None:
            ...
            self.download_button.clicked.connect(self._on_download_button_clicked)

        def _on_download_button_clicked(self, checked: bool = False) -> None:
            self.progress_label.setText("Searching...")

            api_url = "https://api.thecatapi.com/v1/images/search"

            for i in range(10):
                try:
                    # Search.
                    search_response = requests.get(api_url)
                    self.progress_label.setText("Found, downloading...")

                    # Download.
                    url = search_response.json()[0]["url"]
                    download_response = requests.get(url)
                except ConnectionError as e:
                    QMessageBox.critical(self, "Error", f"Error: {e}")
                    return

                self._save_image_file(download_response)
                self.progress_label.setText(f"Done downloading image {i}.")

            self.progress_label.setText(f"Done, {downloaded_count} cats downloaded")


This works well, but while the pictures are being downloaded the UI will freeze a bit,
becoming unresponsive.

With ``qt-async-threads``, we can easily change the code to:

.. code-block:: python

    class CatsWidget(QWidget):
        def __init__(self, runner: QtAsyncRunner, parent: QWidget) -> None:
            ...
            # QtAsyncRunner allows us to submit code to threads, and
            # provide a way to connect async functions to Qt slots.
            self.runner = runner

            # `to_sync` returns a slot that Qt's signals can call, but will
            # allow it to asynchronously run code in threads.
            self.download_button.clicked.connect(
                self.runner.to_sync(self._on_download_button_clicked)
            )

        async def _on_download_button_clicked(self, checked: bool = False) -> None:
            self.progress_label.setText("Searching...")

            api_url = "https://api.thecatapi.com/v1/images/search"

            for i in range(10):
                try:
                    # Search.
                    # `self.runner.run` calls requests.get() in a thread,
                    # but without blocking the main event loop.
                    search_response = await self.runner.run(requests.get, api_url)
                    self.progress_label.setText("Found, downloading...")

                    # Download.
                    url = search_response.json()[0]["url"]
                    download_response = await self.runner.run(requests.get, url)
                except ConnectionError as e:
                    QMessageBox.critical(self, "Error", f"Error: {e}")
                    return

                self._save_image_file(download_response)
                self.progress_label.setText(f"Done downloading image {i}.")

            self.progress_label.setText(f"Done, {downloaded_count} cats downloaded")

By using a `QtAsyncRunner`_ instance and changing the slot to an ``async`` function, the ``runner.run`` calls
will run the requests in a thread, without blocking the Qt event loop, making the UI snappy and responsive.

Thanks to the ``async``/``await`` syntax, we can keep the entire flow in the same function as before,
including handling exceptions naturally.

We could rewrite the first example using a `ThreadPoolExecutor`_ or `QThreads`_,
but that would require a significant rewrite of the flow of the code if we don't want to block
the Qt event loop.



Documentation
=============

For full documentation, please see https://qt-async-threads.readthedocs.io/en/latest.

Differences with other libraries
================================

There are excellent libraries that allow to use async frameworks with Qt:

* `qasync`_ integrates with `asyncio`_
* `qtrio`_ integrates with `trio`_

Those libraries fully integrate with their respective frameworks, allowing the application to asynchronously communicate
with sockets, threads, file system, tasks, cancellation systems, use other async libraries
(such as `httpx`_), etc.

They are very powerful in their own right, however they have one downside in that they require your ``main``
entry point to also be ``async``, which might be hard to accommodate in an existing application.

``qt-async-threads``, on the other hand, focuses only on one feature: allow the user to leverage ``async``/``await``
syntax to *handle threads more naturally*, without the need for major refactorings in existing applications.

License
=======

Distributed under the terms of the `MIT`_ license.

.. _MIT: https://github.com/pytest-dev/pytest-mock/blob/master/LICENSE
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _PyQt6: https://pypi.org/project/PyQt6/
.. _PySide2: https://pypi.org/project/PySide2/
.. _PySide6: https://pypi.org/project/PySide6/
.. _QThreads: https://doc.qt.io/qt-5/qthread.html
.. _QtAsyncRunner: https://qt-async-threads.readthedocs.io/en/latest/reference.html#qt_async_threads.QtAsyncRunner
.. _ThreadPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _httpx: https://www.python-httpx.org
.. _qasync: https://pypi.org/project/qasync
.. _qtpy: https://pypi.org/project/qtpy/
.. _qtrio: https://pypi.org/project/qtrio
.. _trio: https://pypi.org/project/trio
