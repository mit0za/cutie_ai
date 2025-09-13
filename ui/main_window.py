from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox)
from PySide6.QtCore import QTimer, QThread
from backend.engine_worker import EngineWorker
from ui.widget import ChatBox, ChatDisplay, LoadingDialog

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
        self.chat_box.send_button.clicked.connect(self.handle_send) # Connect chat_box to handle_send func

        self.loading_dialog = LoadingDialog(self) # Loading pop up

        self.thread = QThread() # Create new background thread
        self.worker = EngineWorker() # Create worker obj

        self.worker.moveToThread(self.thread) # Attach worker to this thread
        self.thread.started.connect(self.worker.run) # once thread starts, calls "worker.run"

        """Either one of these will trigger which then will alert the UI"""
        self.worker.finished.connect(self.on_engine_ready) 
        self.worker.error.connect(self.on_engine_error)

        # Clean up
        self.worker.finished.connect(self.thread.quit) # stop thread once finished
        self.worker.finished.connect(self.worker.deleteLater) # free worker
        self.thread.finished.connect(self.thread.deleteLater) # free thread

        self.thread.start()
        self.loading_dialog.exec()

    def on_engine_ready(self, engine):
        self.query_engine = engine
        self.loading_dialog.accept()

    def on_engine_error(self, message):
        self.loading_dialog.reject()
        QMessageBox.critical(self, "Error", f"Failed to load engine:\n{message}")
    
    def handle_send(self):
        query = self.chat_box.input_widget.toPlainText().strip()
        if not query or not self.query_engine:
            return
        self.chat_box.input_widget.clear()

        self.chat_display.append(f"<b>You:</b> {query}")
        resp = self.query_engine.query(query)
        self.chat_display.append(f"<b>Assistant:</b> {resp}")



if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()