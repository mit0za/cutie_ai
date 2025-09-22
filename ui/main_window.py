from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, SystemThemeListener, isDarkTheme
from PySide6.QtCore import QTimer


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()

        # Create theme listener
        self.themeListener = SystemThemeListener(self)

        # Start the listener
        self.themeListener.start()

    def closeEvent(self, e):
        # Stop the listener thread
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        super().closeEvent(e)

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # Retry mechanism needed when mica effect is enabled
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))


if __name__ == "__main__":
    app = QApplication([])   # ✅ Must be QApplication, not FluentWindow
    window = MainWindow()
    window.show()
    app.exec()
