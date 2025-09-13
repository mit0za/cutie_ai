from PySide6.QtCore import QObject, Signal
from backend.engine_manager import build_query_engine

class EngineWorker(QObject):
    finished = Signal(object) # Get success signal if success
    error = Signal(str) # emit error if failed

    def run(self):
        try:
            engine = build_query_engine()
            self.finished.emit(engine)
        except Exception as e:
            self.error.emit(str(e))