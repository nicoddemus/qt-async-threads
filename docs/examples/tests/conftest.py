from typing import Iterator

import pytest
from pytestqt.qtbot import QtBot
from qt_async_threads import QtAsyncRunner


@pytest.fixture
def runner(qtbot: QtBot) -> Iterator[QtAsyncRunner]:
    with QtAsyncRunner() as runner:
        yield runner
