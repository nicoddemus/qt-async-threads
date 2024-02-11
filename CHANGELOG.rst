0.6.0
-----

- Now ``QtAsyncRunner.close()`` will cause all running coroutines to never be called back into the main thread.

  Letting coroutines resume into the main thread after ``close()``
  has been called can be problematic, specially in tests, as ``close()`` is often called during test teardown.
  If the user missed to properly wait on a coroutine during the test, what can
  happen is that the coroutine will resume (when the thread finishes), possibly after resources have already
  been cleared, specially widgets.

  Dropping seems harsh, but follows what other libraries like ``asyncio`` do when faced with the same
  situation.

  We might consider adding a ``wait`` flag or something like that in the future to instead of cancelling the coroutines,
  wait for them.

- ``AsyncTester.start_and_wait()`` now receives an optional ``timeout_s`` parameter, which overwrites
  ``AsyncTester.timeout_s``.

0.5.2
-----

- New attribute ``AsyncTester.timeout_s``, with the timeout in seconds until ``start_and_wait``
  raises ``TimeoutError``.

0.4.0
-----

- Support `PyQt5`_, `PyQt6`_, `PySide2`_, and `PySide6`_ thanks to `qtpy`_.
- Support Python 3.11.

.. _PyQt5: https://pypi.org/project/PyQt5/
.. _PyQt6: https://pypi.org/project/PyQt6/
.. _PySide2: https://pypi.org/project/PySide2/
.. _PySide6: https://pypi.org/project/PySide6/
.. _qtpy: https://pypi.org/project/qtpy/

0.3.1
-----

- Relax requirements for PyQt to ``>=5.12``.

0.3.0
-----

- Added missing ``py.typed`` file, enabling type-checking.

0.2.1
-----

- Fixed small linting issues, automatic deploy.

0.1
---

First release.
