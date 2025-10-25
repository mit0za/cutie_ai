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
        self.engine_thread.llm_ready.connect(self.on_llm_ready)
        self.engine_thread.db_ready.connect(self.on_db_ready)
        self.engine_thread.need_data.connect(self.on_need_data)
        self.engine_thread.critical_error.connect(self.on_critical_error)

    def start(self):
        self.engine_thread.start()

    def on_progress(self, msg):
        InfoBar.info(
            title="Initializing Engine",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500,
            parent=self.parent
        )

    def on_ready(self, engine):
        self.query_engine = engine
        self.parent.push_button.setEnabled(True)
        InfoBar.success(
            title="Engine Ready",
            content="LLM engine is fully operational",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self.parent
        )

    def on_error(self, error):
        InfoBar.error(
            title='Engine Error',
            content=str(error),
            orient=Qt.Horizontal,
            isClosable=True,
            duration=6000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent
        )

    def on_llm_ready(self):
        """ LLm initialization successful."""
        InfoBar.success(
            title="LLM Ready",
            content="Llama 3.1:8B and embedding model initialized successfully.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self.parent
        )

    def on_db_ready(self):
        """Database connection successful."""
        InfoBar.success(
            title="Database Ready",
            content="Chroma vector database connected.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self.parent
        )

    def on_need_data(self, msg: str):
        """Notify user to locate data directory."""
        InfoBar.warning(
            title="Data Folder Required",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=6000,
            parent=self.parent
        )

    def on_critical_error(self, msg: str):
        """Critical error: no data nor index found."""
        self.info_bar = InfoBar.error(
            title="Critical Setup Error",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            duration=0,
            parent=self.parent
        )