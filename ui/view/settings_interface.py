from qfluentwidgets import ScrollArea
from PySide6.QtWidgets import QWidget


class SettingsInterface(ScrollArea):
    """ Settings interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)
        self.setWindowTitle("Settings Interface")
        self.view.setObjectName("view")
        self.setObjectName("settingsInterface")
