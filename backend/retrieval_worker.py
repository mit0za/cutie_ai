"""
Pure semantic retrieval worker - bypasses LLM, returns raw NodeWithScore list.
Converts to plain dicts before emitting to avoid Qt cross-thread pickle issues.
"""
from PySide6.QtCore import QObject, Signal


def _node_to_dict(nws):
    """Convert NodeWithScore to plain dict for cross-thread signal.
    All values must be JSON-serializable (str, float, None) for Qt pickle.
    """
    node = nws.node
    meta = getattr(node, "metadata", None) or {}
    # Ensure metadata is fully serializable - Path and other objects break pickle
    safe_meta = {}
    for k, v in list((meta or {}).items()):
        try:
            safe_meta[str(k)] = str(v) if v is not None else ""
        except Exception:
            safe_meta[str(k)] = ""
    score = getattr(nws, "score", None)
    if score is not None:
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = None
    return {
        "text": (getattr(node, "text", None) or "").strip(),
        "score": score,
        "metadata": safe_meta,
    }


class RetrievalWorker(QObject):
    """Background worker for pure document retrieval (no LLM)."""

    finished = Signal(list)  # List[dict] - serializable for cross-thread
    error = Signal(str)

    def __init__(self, retriever, query_text: str):
        super().__init__()
        self.retriever = retriever
        self.query_text = query_text

    def run(self):
        """Run retrieval in background thread."""
        try:
            nodes = self.retriever.retrieve(self.query_text)
            data = [_node_to_dict(nws) for nws in nodes]
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))
