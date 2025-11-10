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

            refs_html = ""
            if hasattr(response, "source_nodes"):
                refs_html += "<hr><b> References:</b><br>"
                for i, node in enumerate(response.source_nodes, start=1):
                    meta = getattr(node, "metadata", {})
                    title = meta.get("file_name") or meta.get("source") or "Untitled"
                    path = meta.get("file_path")
                    text_excerpt = getattr(node, "text", "").strip()
                    text_excerpt = text_excerpt[:300].replace("\n", " ") + ("..." if len(text_excerpt) > 300 else "")

                    if path and os.path.exists(path):
                        refs_html += (
                            f"<br><a href='file://{path}'>{i}. {title}</a> "
                            f"<span style='color:#999;'></span> {text_excerpt}<br>"
                        )
                    else:
                        refs_html += (
                            f"<br>{i}. {title}: "
                            f"<span style='color:#999;'></span> {text_excerpt}<br>"
                        )

            # Combine everything
            final_output = f"<div>{result_text}</div>{refs_html}"

            self.finished.emit(final_output)

        except Exception as e:
            self.error.emit(str(e))
