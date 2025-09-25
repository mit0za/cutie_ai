from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, SystemThemeListener, isDarkTheme
# from PySide6.QtCore 
from PySide6.QtGui import QIcon
from ui.config import cfg


class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)


    def initWindow(self):
        """Dictate how the app started"""

        # Size
        self.resize(960, 780)
        self.setMinimumWidth(760)
        
        # Title
        self.setWindowTitle('Cutie AI')

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        # Move app to the middle of the screen
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()



if __name__ == "__main__":
    app = QApplication([])   
    window = MainWindow()
    window.show()
    app.exec()
