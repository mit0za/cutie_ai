from qfluentwidgets import ScrollArea
from PySide6.QtWidgets import QWidget


class ChatInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)
        self.setWindowTitle("Chat Interface")
        self.view.setObjectName("view")
        self.setObjectName("chatInterface")
