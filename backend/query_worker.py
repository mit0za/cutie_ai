import os
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
            result_text = str(response).strip()

            refs = []
            if hasattr(response, "source_nodes"):
                for node in response.source_nodes:
                    meta = getattr(node, "metadata", {})
                    title = meta.get("file_name") or meta.get("source") or "Untitled"
                    path = meta.get("file_path", None)
                    refs.append((title, path))

            final_output = result_text
            if refs:
                final_output += "<br><br><br><b>References:</b> "
                final_output += "<details><summary>Show references</summary><ol>"
                for title, path in refs:
                    if path and os.path.exists(path):
                        final_output += f"<li><a href='file://{path}'>{title}</a></li>"
                    else:
                        final_output += f"<li>{title}</li>"
                final_output += "</ol></details>"

            self.finished.emit(final_output)

        except Exception as e:
            self.error.emit(str(e))
