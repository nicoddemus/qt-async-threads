from pathlib import Path

from examples.explanation_sync import Window
from pytestqt.qtbot import QtBot


def test_explanation_thread(qtbot: QtBot, tmp_path: Path) -> None:
    win = Window(tmp_path)
    win.directory = tmp_path
    qtbot.addWidget(win)

    win.count_spin.setValue(1)
    win.download_button.click()

    def check() -> None:
        assert win.progress_label.text() == "Done, 1 cats downloaded"

    qtbot.waitUntil(check)
    assert len(list(tmp_path.iterdir())) == 1
