from pathlib import Path
from urllib.parse import urlsplit

import requests
from examples.exception import install_except_hook
from qt_async_threads import QtAsyncRunner
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QFormLayout
from qtpy.QtWidgets import QLabel
from qtpy.QtWidgets import QMessageBox
from qtpy.QtWidgets import QPushButton
from qtpy.QtWidgets import QSpinBox
from qtpy.QtWidgets import QWidget
from requests.exceptions import ConnectionError


class Window(QWidget):
    def __init__(self, directory: Path, runner: QtAsyncRunner) -> None:
        super().__init__()
        self.runner = runner

        self.setWindowTitle("Cat Downloader")
        self.directory = directory
        self._cancelled = False

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
        self.download_button.clicked.connect(self.runner.to_sync(self.on_download_button_clicked))
        self.stop_button.clicked.connect(self.on_cancel_button_clicked)

    async def on_download_button_clicked(self, checked: bool = False) -> None:
        self.progress_label.setText("Searching...")
        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self._cancelled = False
        downloaded_count = 0
        try:
            for i in range(self.count_spin.value()):
                try:
                    # Search.
                    search_response = await self.runner.run(
                        requests.get, "https://api.thecatapi.com/v1/images/search"
                    )
                    search_response.raise_for_status()

                    # Download.
                    url = search_response.json()[0]["url"]
                    download_response = await self.runner.run(requests.get, url)
                except ConnectionError as e:
                    QMessageBox.critical(self, "Error", f"Error connecting to TheCatApi:\n{e}")
                    return

                # Save the contents of the image to a file.
                parts = urlsplit(url)
                path = self.directory / f"{i:02d}_cat{Path(parts.path).suffix}"
                path.write_bytes(download_response.content)
                downloaded_count += 1

                # Show progress.
                self.progress_label.setText(f"Downloaded {path.name}")
                QApplication.processEvents()
                if self._cancelled:
                    QMessageBox.information(self, "Cancelled", "Download cancelled")
                    break
        finally:
            self.progress_label.setText(f"Done, {downloaded_count} cats downloaded")
            self.download_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def on_cancel_button_clicked(self) -> None:
        self._cancelled = True


if __name__ == "__main__":
    install_except_hook()
    with QtAsyncRunner() as runner:
        app = QApplication([])
        win = Window(Path(__file__).parent / "cats", runner)
        win.show()
        app.exec()
