import os
import re
from html import escape as html_escape
from pathlib import Path
from PySide6.QtCore import QObject, Signal

class QueryWorker(QObject):
    finished = Signal(str, list)
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

            sources = []
            if hasattr(response, "source_nodes"):
                for i, node in enumerate(response.source_nodes, start=1):
                for node in response.source_nodes:
                    meta = getattr(node, "metadata", {}) or {}

                    title = meta.get("file_name") or meta.get("source") or "Untitled"
                    path = meta.get("file_path")
                    page = meta.get("page_label") or meta.get("page") or meta.get("page_number")
                    chunk = meta.get("chunk") or meta.get("chunk_id")

                    location_parts = []
                    if page:
                        location_parts.append(f"page {page}")
                    if chunk:
                        location_parts.append(f"chunk {chunk}")

                    location_text = f" - {', '.join(location_parts)}" if location_parts else ""

                    if path and not os.path.isabs(path):
                        path = os.path.abspath(path)

                    if path and os.path.exists(path):
                        source_text = f"{title}{location_text}|{path}"
                    else:
                        source_text = f"{title}{location_text}"

                    sources.append(source_text)

            self.finished.emit(result_text, sources)

        except Exception as e:
            self.error.emit(str(e))