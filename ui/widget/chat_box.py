from PySide6.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QSizePolicy, QPushButton
from PySide6.QtCore import QTimer

class ChatBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Horizontal Layouat
        input_layout = QHBoxLayout(self)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(5)

        # Input widget
        self.input_widget = QTextEdit(undoRedoEnabled=1)
        self.input_widget.setPlaceholderText("Ask anything...")
        self.input_widget.setMinimumHeight(50)
        self.input_widget.setMaximumHeight(300)
        self.input_widget.setFixedHeight(20)

        # Fixed = capped height, Expanding = uncapped width
        self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Call autoResize function everything input field changes
        self.input_widget.textChanged.connect(self.autoResize)

        # Schedule autoResize func to run once after ui shows
        QTimer.singleShot(0, self.autoResize)

        # stretch=1 = expand to fill available space
        input_layout.addWidget(self.input_widget, stretch=1)

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFixedHeight(50)
        input_layout.addWidget(self.send_button)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def autoResize(self):
        doc = self.input_widget.document()
        # ensure wrapping width is current so the height calc is accurate
        doc.setTextWidth(self.input_widget.viewport().width())
        doc_height = doc.size().height()
        # add a little padding and clamp
        new_height = min(max(50, int(doc_height) + 8), 200)
        self.input_widget.setFixedHeight(new_height)