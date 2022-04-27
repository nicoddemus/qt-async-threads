from examples.simple import Window
from pytestqt.qtbot import QtBot
from qt_async_threads import QtAsyncRunner


def test_simple(qtbot: QtBot, runner: QtAsyncRunner) -> None:
    win = Window(runner)
    qtbot.addWidget(win)
