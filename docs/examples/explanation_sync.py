from pathlib import Path
from urllib.parse import urlsplit

import requests
from examples.exception import install_except_hook
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QWidget


class Window(QWidget):
    def __init__(self, directory: Path) -> None:
        super().__init__()
        self.setWindowTitle("Cat Downloader")

        self.directory = directory

        self.count_spin = QSpinBox()
        self.count_spin.setValue(5)
        self.count_spin.setMinimum(1)
        self.progress_label = QLabel("Idle, click below to start downloading")
        self.download_button = QPushButton("Download")

        layout = QFormLayout(self)
        layout.addRow("How many cats?", self.count_spin)
        layout.addRow("Status", self.progress_label)
        layout.addRow(self.download_button)

        self.download_button.clicked.connect(self._on_download_button_clicked)

    def _on_download_button_clicked(self, *args: object) -> None:
        for i in range(self.count_spin.value()):
            self.progress_label.setText("Searching...")
            QApplication.processEvents()
            search_response = requests.get("https://api.thecatapi.com/v1/images/search")
            search_response.raise_for_status()

            url = search_response.json()[0]["url"]
            parts = urlsplit(url)

            download_response = requests.get(url)
            path = self.directory / f"{i:02d}_cat{Path(parts.path).suffix}"
            path.write_bytes(download_response.content)
            self.progress_label.setText(f"Downloaded {path.name}")
            QApplication.processEvents()

        self.progress_label.setText(f"Done, {self.count_spin.value()} cats downloaded")


if __name__ == "__main__":
    install_except_hook()
    app = QApplication([])
    win = Window(Path(__file__).parent / "cats")
    win.show()
    app.exec()
