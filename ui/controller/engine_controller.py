from qfluentwidgets import InfoBar, InfoBarPosition
from PySide6.QtCore import Qt
from backend.engine_manager import EngineManager

class EngineController:
    """ This is where we move all engine related stuff here so it's more modular and clean in chat_interface.py"""
    def __init__(self, parent):
        self.parent = parent # So it will know wher eto attach toast to (in our case it's chat_interface)
        self.engine_thread = EngineManager()
        self.engine_info = None
        self.query_engine = None

        # Connect to signals
        self.engine_thread.progress.connect(self.on_progress)
        self.engine_thread.finished.connect(self.on_ready)
        self.engine_thread.error.connect(self.on_error)

    def start(self):
        self.engine_thread.start()

    def on_progress(self, msg):
        InfoBar.info(
            title="Setting up LLM",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2998,
            parent=self.parent
        )

    def on_ready(self, engine):
        self.query_engine = engine
        self.parent.push_button.setEnabled(True)
        InfoBar.success(
            title="LLM Ready",
            content="LLama initialized successfully!",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self.parent
        )

    def on_error(self, error):
        InfoBar.error(
            title='Engine Error',
            content=str(error),
            orient=Qt.Horizontal,
            isClosable=True,
            duration=4999,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent
        )