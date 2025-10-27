from qfluentwidgets import InfoBar, InfoBarPosition
from PySide6.QtCore import Qt, QThread, Signal, QObject
from backend.engine_manager import EngineManager
from ui.config import cfg
from backend.query_worker import QueryWorker

class PushButtonController(QObject):
    """ Handles send button click and user input for chat messages"""

    send_signal = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.engine_thread = None
        self.engine_controller = None

        # connect signal
        self.send_signal.connect(self.process_message)

    def attach_engine(self, engine_controller):
        """ Attach engine (EngineManager) from chat_interface"""
        self.engine_controller = engine_controller

    def on_clicked(self):
        text = self.parent.input_box.toPlainText().strip()

        if not text:
            InfoBar.warning(
                title="Empty Message",
                content="Please type something to send.",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=2000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self)
            return
        self.send_signal.emit(text)

    def process_message(self, text):
        """ Run when message is sent"""
        if not self.engine_controller or not self.engine_controller.query_engine:
            self.parent.chat_display.append("<i>Engine not ready yet...</i>")
            return
        
        self.parent.chat_display.append(f"<b>You:</b> {text}")
        self.parent.input_box.clear()

        self.thread = QThread()
        self.worker = QueryWorker(self.engine_controller.query_engine, text)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.display_response)
        self.worker.error.connect(self.show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def display_response(self, response):
        """Display model's reply"""
        self.parent.chat_display.append(f"<b>Llama:</b> {response}")

    def show_error(self, error):
        InfoBar.error(
            title="Engine Error",
            content=str(error),
            orient=Qt.Horizontal,
            isClosable=True,
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent
        )
    
