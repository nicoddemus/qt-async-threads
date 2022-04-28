import requests
from examples.exception import install_except_hook
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from qt_async_threads import AbstractAsyncRunner
from qt_async_threads import QtAsyncRunner


class Window(QWidget):
    def __init__(self, runner: AbstractAsyncRunner) -> None:
        super().__init__()
        self.setWindowTitle("Cat Finder")
        self.runner = runner
        self.results_label = QLabel("Idle")
        self.results_label.setTextFormat(Qt.MarkdownText)
        self.results_label.setOpenExternalLinks(True)
        self.search_button = QPushButton("Search")

        layout = QVBoxLayout(self)
        layout.addWidget(self.results_label)
        layout.addWidget(self.search_button)

        self.search_button.clicked.connect(self.runner.to_sync(self._on_search_button_clicked))

    async def _on_search_button_clicked(self, *args: object) -> None:
        response = await self.runner.run(requests.get, "https://api.thecatapi.com/v1/images/search")
        url = response.json()[0]["url"]
        self.results_label.setText(f"Found a cat! [click to open]({url})")


if __name__ == "__main__":
    install_except_hook()
    app = QApplication([])
    with QtAsyncRunner() as runner:
        win = Window(runner)
        win.show()
        app.exec()
