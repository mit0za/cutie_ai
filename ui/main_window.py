from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, SystemThemeListener, isDarkTheme, FluentIcon, NavigationItemPosition
from PySide6.QtGui import QIcon
from ui.config import cfg
from ui.view.chat_interface import ChatInterface
from ui.view.settings_interface import SettingsInterface

class MainWindow(FluentWindow):

    def __init__(self):
        super().__init__()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        # create side bar interface
        self.chatInterface = ChatInterface(self)
        self.settingInterface = SettingsInterface(self)

        # add interface to side bar
        self.initSidebar()
        self.initWindow()


    def initSidebar(self):
        """ add side bar"""
        self.addSubInterface(self.chatInterface, FluentIcon.CHAT, self.tr("Chat"))
        self.navigationInterface.addSeparator()

        pos = NavigationItemPosition.SCROLL

        self.addSubInterface(self.settingInterface, FluentIcon.SETTING, self.tr("Settings"), NavigationItemPosition.BOTTOM)


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


