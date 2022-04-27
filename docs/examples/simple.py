from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from qt_async_threads import AbstractAsyncRunner
from qt_async_threads import QtAsyncRunner


class Window(QWidget):
    def __init__(self, runner: AbstractAsyncRunner) -> None:
        super().__init__()
        self.runner = runner
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(
            self.runner.to_sync(self._on_download_button_clicked)
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.download_button)

    async def _on_download_button_clicked(self, *args: object) -> None:
        print("Hello")


if __name__ == "__main__":
    app = QApplication([])
    with QtAsyncRunner() as runner:
        win = Window(runner)
        win.show()
        app.exec()
