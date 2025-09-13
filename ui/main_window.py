from PySide6.QtWidgets import (QApplication, QMainWindow, QTextBrowser, 
                               QVBoxLayout, QWidget, QHBoxLayout)
from ui.widget.chat_box import ChatBox
from ui.widget.chat_display import ChatDisplay
from backend.engine_manager import build_query_engine
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.query_engine = None
        self.setWindowTitle("Cutie AI")

        # Create container
        container = QWidget()
        #Set it in the middle of the screen
        self.setCentralWidget(container)

        # Use horizontal layout (will add left_layout later)
        main_layout = QHBoxLayout(container)

        # Right side
        right_layout = QVBoxLayout()
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget)

        # Chat display
        self.chat_display = ChatDisplay()
        right_layout.addWidget(self.chat_display, stretch=1) # Add chat display

        self.chat_box = ChatBox()
        right_layout.addWidget(self.chat_box) # Add chat_box

        self.chat_box.send_button.clicked.connect(self.handle_send)

    def get_engine(self):
        if self.query_engine is None:
            self.query_engine = build_query_engine()
        return self.query_engine
    
    def handle_send(self):
        query = self.chat_box.input_widget.toPlainText().strip()
        if not query:
            return
        self.chat_box.input_widget.clear()

        engine = self.get_engine()

        resp = engine.query(query)
        self.chat_display.append(f"<b>Assistant:</b> {resp}")




if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()