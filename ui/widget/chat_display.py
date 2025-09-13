from PySide6.QtWidgets import QTextBrowser, QSizePolicy, QApplication
class ChatDisplay(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Expand fully in both directions
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.append("<b>System:</b> Welcome! Ask me anything...")

