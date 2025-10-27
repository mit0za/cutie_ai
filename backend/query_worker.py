from PySide6.QtCore import QObject, Signal

class QueryWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, engine, query_text):
        super().__init__()
        self.engine = engine
        self.query_text = query_text

    def run(self):
        """Background worker for LLM query"""
        try:
            response = self.engine.query(self.query_text)
            self.finished.emit(str(response))
        except Exception as e:
            self.error.emit(str(e))