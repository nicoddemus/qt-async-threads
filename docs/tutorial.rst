.. _`tutorial`:

========
Tutorial
========

This tutorial will show how to change the function in an existing application, that
performs a blocking operation, so it no longer freezes the UI, providing a better
user experience.

Statement of the problem
------------------------

It is common for applications to spawn computational intensive operations based on user interaction,
like downloading some files or performing CPU intensive computations.

Calling those functions directly will usually lead to poor user experience, as the UI will become
unresponsive while the operation is taking place.

The usual solution to avoid making the UI unresponsive is to run the expensive operation in a separate thread,
leaving the main thread free to process other user events (the event loop).

However, this requires to break the normal flow of the code into separate functions, doing extra bookkeeping to
communicate results/errors, and making the original interaction harder to test than before.

Example 1: First implementation
-------------------------------

Here is a small application that lets users download random images of cats using `TheCatApi <https://docs.thecatapi.com/>`__.
The user selects the number of cat images to download, and clicks on a button.

.. image:: examples/images/explanation1.png
    :align: center

Here's the main portion of the code:

.. literalinclude:: examples/explanation_sync.py
   :pyobject: Window


After clicking on the *Download* button, the images will start to be downloaded, and the user will be informed
of the progress on a label. Note also that the code handles not only downloading the images, but also gracefully handles errors (using
``QMessageBox.critical`` to show connection problems), and allows the user to cancel the operation by clicking
on the *Stop* button.

However, the user will have a hard time if they try to actually stop the operation: the application is unresponsive,
sluggish; clicks often don't produce any feedback, moving the mouse over the button and
clicking on it have no effect, except if the user clicks on the button in quick succession.
Trying to change the number of cats to download also doesn't have a response while the download is taking place.

This happens because the ``request.get`` calls are blocking the Qt event loop, so it can't receive user events and process
them accordingly (such as a click event on the *Stop* button, or mouse move events to highlight a button).

Example 2: Using threads
------------------------

The usual solution to the responsiveness problem demonstrated previously is to run the blocking code in a ``QThread``.

First we need to extract the download loop to run in a thread, taking care of handling errors, and emitting a signal
to the main loop whenever one of the downloads finishes:

.. literalinclude:: examples/explanation_thread.py
   :pyobject: DownloadThread

In order to use this thread object, we need to refactor the ``Window`` code to start the thread, and properly respond
to its events:

.. literalinclude:: examples/explanation_thread.py
   :pyobject: Window.on_download_button_clicked

.. literalinclude:: examples/explanation_thread.py
   :pyobject: Window.on_downloaded

.. literalinclude:: examples/explanation_thread.py
   :pyobject: Window.on_download_finished

.. literalinclude:: examples/explanation_thread.py
   :pyobject: Window.on_cancel_button_clicked


This now gives us a responsive interface: clicking on the Stop button gives immediate feedback, as well as minor
effects such as the button being highlighted when the mouse moves over it.

While this works well, it required us a considerable refactoring of the code:

1. Previously the logic was straight forward, and could be read from top to bottom. Moving the code to a thread required us
   to split the logic and the flow.
2. We could easily catch exceptions and react accordingly by showing a message box, but we can't do that from a
   ``QThread`` because widgets must always be created/live in the main thread, so we need to do some message passing.

All in all, this is not *terrible*, however it is not trivial either.

Also one can see that is easy for an application to slowly grow portions of the code that are blocking but
still quick enough that are not a problem, but then depending on the input data or some other external factor
(like a slow connection) that *quick enough* is no longer *enough* so we then need to refactor it.

As time evolves, an application will often grow many small pain points like this, requiring us to carefully examine
the code and refactor to threads later, as writing using threads in the first place is costly/non-trivial.

Example 3: Enter ``QtAsyncRunner``
----------------------------------

``qt-async-threads`` provides the :class:`QtAsyncRunner <qt_async_threads.QtAsyncRunner>` class which allows us
to easily change our existing code to use threads, without the need for a major refactoring.

First we need an instance of a ``QtAsyncRunner`` class. It is strongly suggested create this *once* in the application
startup and pass it to the objects that need it, however it is possible to let each widget/panel create their own instance.

Here we will receive the runner as part of the constructor:

.. literalinclude:: examples/explanation_async.py
   :start-at: __init__
   :end-before: setWindowTitle

Next, we will change our original ``_on_download_button_clicked`` function so it becomes ``async``. This is easy,
we just need to add the ``async`` keyword before ``def``:

.. literalinclude:: examples/explanation_async.py
   :start-at: def on_download_button_clicked
   :end-before: self.download_button.setEnabled

The objective here is for the ``request.get`` calls to run in a separate thread, so we use
the :meth:`QtAsyncRunner.run <qt_async_threads.QtAsyncRunner.run>` method to run the function and its arguments
into a thread, so we change this:

.. literalinclude:: examples/explanation_sync.py
   :start-at: # Search
   :end-before: except ConnectionError

Into this:

.. literalinclude:: examples/explanation_async.py
   :start-at: # Search
   :end-before: except ConnectionError

Note that ``run`` is ``async``, so we need to put ``await`` in front of it.

Finally, we just need to change the signal connection: Qt doesn't know how to execute ``async`` methods, so
we need to ask the ``runner`` to wrap it for us:


.. literalinclude:: examples/explanation_async.py
   :start-at: Connect signals
   :end-before: async def

And that's it! Now the application is just as responsive as the version using ``QThread``, but with minimal changes.

.. important::

  This is the point of the ``qt-async-threads`` package: easily taking an existing application and,
  with minimal changes, employ threads to execute blocking calls.


Example 4: Running in parallel
------------------------------

We can improve things further: downloads are something which is efficient to be done in parallel to maximize
bandwidth usage, and :meth:`QtAsyncRunner.run_parallel <qt_async_threads.QtAsyncRunner.run_parallel>` makes
it easy to adjust our code to run many blocking functions in parallel.

.. literalinclude:: examples/explanation_async_parallel.py
   :pyobject: Window.on_download_button_clicked

We refactor the part of the code responsible for downloading the file into the ``download_one`` function,
and then call ``QtAsyncRunner.run_parallel()`` passing a list of functions that will be executed in parallel.
Using the ``async for`` syntax, we loop over the results as they get ready, and then proceed as usual.

One small change is that we moved the handler for ``ConnectionError`` to cover the ``async for`` loop, as now
the ``run_parallel()`` call can raise that exception.
