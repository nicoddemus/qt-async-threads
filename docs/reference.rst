=========
Reference
=========

Overview
--------

To use this library, it is recommended that you instantiate a :class:`QtAsyncRunner <qt_async_threads.QtAsyncRunner>`
at the start of the application, using it in context-manager, and then pass that instance along to your main
window/widgets:

.. code-block:: python

    def main(argv: list[str]) -> None:
        app = QApplication(argv)
        with QtAsyncRunner() as runner:
            main_window = MainWindow(runner)
            main_window.show()
            app.exec()

Using it as a context manager ensures a clean exit.

After that, your ``MainWindow`` can pass the ``runner`` along to the other parts of the application that need it.

Alternatively, you might decide to create a local :class:`QtAsyncRunner <qt_async_threads.QtAsyncRunner>` instance
into a widget (and this is a great way to try the library actually), and it will work fine, but for large scale
usage creating a single instance is recommended, to limit the number of running threads in the application.

Classes
-------


.. autoclass:: qt_async_threads.AbstractAsyncRunner
    :members:

.. autoclass:: qt_async_threads.QtAsyncRunner
    :members:

.. autoclass:: qt_async_threads.SequentialRunner
    :members:
