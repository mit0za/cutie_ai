from qfluentwidgets import ScrollArea, setTheme, Theme, TextBrowser
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

class ChatInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("chatInterface")
        setTheme(Theme.DARK)

        # layout setup
        self.view = QWidget()
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        main_layout = QVBoxLayout(self.view)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # chat display
        self.chat_display = TextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setReadOnly(True)
        main_layout.addWidget(self.chat_display) # add to verticle layout
