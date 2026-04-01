import os
import re
from html import escape as html_escape
from pathlib import Path
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
            result_text = html_escape(str(response).strip()).replace("\n", "<br>")

            refs_html = ""
            if hasattr(response, "source_nodes"):
                refs_html += "<hr><b> References:</b><br>"
                for i, node in enumerate(response.source_nodes, start=1):
                    meta = getattr(node, "metadata", {})
                    title = meta.get("file_name") or meta.get("source") or "Untitled"
                    path = meta.get("file_path")
                    raw_excerpt = getattr(node, "text", "").strip()
                    # Strip OCR artifacts: control chars, Cyrillic, Arabic, CJK, etc.
                    raw_excerpt = re.sub(r'[^\x20-\x7E\n\r\t\u00A0-\u024F\u2000-\u206F\u2010-\u2027]', '', raw_excerpt)
                    text_excerpt = html_escape(raw_excerpt[:300].replace("\n", " "))
                    if len(raw_excerpt) > 300:
                        text_excerpt += "..."

                    # Resolve relative paths stored in the index to absolute
                    # paths on the current machine for portable file access
                    if path and not os.path.isabs(path):
                        path = os.path.abspath(path)

                    if path and os.path.exists(path):
                        file_url = Path(path).as_uri()
                        refs_html += (
                            f"<br><a href='{file_url}'>{i}. {html_escape(title)}</a> "
                            f"<span style='color:#999;'></span> {text_excerpt}<br>"
                        )
                    else:
                        refs_html += (
                            f"<br>{i}. {html_escape(title)}: "
                            f"<span style='color:#999;'></span> {text_excerpt}<br>"
                        )

            # Combine everything
            final_output = f"<div>{result_text}</div>{refs_html}"

            self.finished.emit(final_output)

        except Exception as e:
            self.error.emit(str(e))
