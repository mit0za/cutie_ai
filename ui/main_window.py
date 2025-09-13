from PySide6.QtWidgets import (QApplication, QMainWindow, QTextBrowser, 
                               QVBoxLayout, QWidget, QHBoxLayout)
from widget.chat_box import ChatBox
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
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
        chat_display = QTextBrowser()
        right_layout.addWidget(chat_display)

        # Input layout
        # input_layout = QHBoxLayout()
        # right_layout.addLayout(input_layout)

        chat_box = ChatBox()
        right_layout.addWidget(chat_box)





if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()