from pathlib import Path

from examples.explanation_async_parallel import Window
from pytestqt.qtbot import QtBot
from qt_async_threads import QtAsyncRunner


def test_explanation_async_parallel(qtbot: QtBot, tmp_path: Path, runner: QtAsyncRunner) -> None:
    win = Window(tmp_path, runner)
    win.directory = tmp_path
    qtbot.addWidget(win)

    win.count_spin.setValue(2)
    win.download_button.click()
    qtbot.waitUntil(runner.is_idle)
    assert win.progress_label.text() == "Done, 2 cats downloaded"
    assert len(list(tmp_path.iterdir())) == 2
