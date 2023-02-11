from pathlib import Path
from urllib.parse import urlsplit

import requests
from examples.exception import install_except_hook
from qtpy.QtCore import pyqtSignal
from qtpy.QtCore import QObject
from qtpy.QtCore import QThread
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QFormLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QMessageBox
from qtpy.QtWidgets import QPushButton
from qtpy.QtWidgets import QSpinBox
from qtpy.QtWidgets import QWidget
from requests.exceptions import ConnectionError


class Window(QWidget):
    def __init__(self, directory: Path) -> None:
        super().__init__()

        self.setWindowTitle("Cat Downloader")
        self.directory = directory
        self._thread: DownloadThread | None = None

        # Build controls.
        self.count_spin = QSpinBox()
        self.count_spin.setValue(5)
        self.count_spin.setMinimum(1)
        self.progress_label = QLabel("Idle, click below to start downloading")
        self.download_button = QPushButton("Download")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)

        layout = QFormLayout(self)
        layout.addRow("How many cats?", self.count_spin)
        layout.addRow("Status", self.progress_label)
        layout.addRow(self.download_button)
        layout.addRow(self.stop_button)

        # Connect signals.
        self.download_button.clicked.connect(self.on_download_button_clicked)
        self.stop_button.clicked.connect(self.on_cancel_button_clicked)

    def on_download_button_clicked(self, checked: bool = False) -> None:
        self.progress_label.setText("Searching...")
        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self._thread = DownloadThread(self.count_spin.value(), self)
        self._thread.downloaded_signal.connect(self.on_downloaded)
        self._thread.finished.connect(self.on_download_finished)
        self._thread.start()

    def on_downloaded(self, index: int, name: str, data: bytes) -> None:
        # Save the contents of the image to a file.
        path = self.directory / f"{index:02d}_cat{Path(name).suffix}"
        path.write_bytes(data)

        # Show progress.
        self.progress_label.setText(f"Downloaded {name}")

    def on_download_finished(self) -> None:
        assert self._thread is not None
        if self._thread.cancelled:
            QMessageBox.information(self, "Cancelled", "Download cancelled")
        elif self._thread.error is not None:
            msg = f"Error connecting to TheCatApi:\n{self._thread.error}"
            QMessageBox.critical(self, "Error", msg)

        self.progress_label.setText(f"Done, {self._thread.downloaded_count} cats downloaded")
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def on_cancel_button_clicked(self) -> None:
        assert self._thread is not None
        self._thread.cancelled = True


class DownloadThread(QThread):
    # Signal emitted when a cat image has been downloaded.
    # Arguments: index, basename, image data
    downloaded_signal = pyqtSignal(int, str, bytes)

    def __init__(self, cat_count: int, parent: QObject) -> None:
        super().__init__(parent)
        self.cat_count = cat_count
        self.downloaded_count = 0
        self.cancelled = False
        self.error: str | None = None

    def run(self) -> None:
        """Executes this code in a separate thread, as to not block the main thread."""
        for i in range(self.cat_count):
            try:
                # Search.
                search_response = requests.get("https://api.thecatapi.com/v1/images/search")
                search_response.raise_for_status()

                # Download.
                url = search_response.json()[0]["url"]
                download_response = requests.get(url)
            except ConnectionError as e:
                self.error = str(e)
                return

            parts = urlsplit(url)
            self.downloaded_signal.emit(i, Path(parts.path).name, download_response.content)
            self.downloaded_count += 1

            if self.cancelled:
                return


if __name__ == "__main__":
    install_except_hook()
    app = QApplication([])
    win = Window(Path(__file__).parent / "cats")
    win.show()
    app.exec()
