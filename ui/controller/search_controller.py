"""Controller for Document Search - pure semantic retrieval (no LLM)."""
from qfluentwidgets import InfoBar, InfoBarPosition
from PySide6.QtCore import Qt
from backend.retrieval_worker import _node_to_dict


class SearchController:
    """Handles search trigger and result display for Document Search view."""

    def __init__(self, parent, engine_controller):
        self.parent = parent
        self.engine_controller = engine_controller

    def on_search(self, query: str):
        """Trigger retrieval when user searches."""
        query = query.strip()
        if not query:
            InfoBar.warning(
                title="Empty Query",
                content="Please enter a search term.",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=2000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self.parent,
            )
            return

        if not self.engine_controller or not self.engine_controller.retriever:
            InfoBar.warning(
                title="Retriever Not Ready",
                content="Waiting for index to load. Please try again shortly.",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self.parent,
            )
            return

        self.parent.set_search_loading(True)
        # Run retrieval on main thread to avoid Qt signal serialization issues
        # (blocks UI briefly; retrieval is typically fast)
        try:
            nodes = self.engine_controller.retriever.retrieve(query)
            data = [_node_to_dict(nws) for nws in nodes]
            self.parent.set_search_loading(False)
            self.parent.display_results(data)
        except Exception as e:
            self.parent.set_search_loading(False)
            self._on_error(str(e))

    def _on_error(self, error: str):
        self.parent.set_search_loading(False)
        InfoBar.error(
            title="Search Error",
            content=str(error),
            orient=Qt.Horizontal,
            isClosable=True,
            duration=6000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent,
        )
