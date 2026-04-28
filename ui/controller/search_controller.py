"""
Search Controller
=================

Manages the interaction between the SearchInterface view and the
RetrievalWorker backend. Handles user search input, spawns background
retrieval threads, and delegates result rendering back to the view.

This controller operates independently from the chat pipeline's
PushButtonController, using the pure retrieval pathway that bypasses
the LLM entirely. The separation ensures that document search remains
fast and lightweight regardless of LLM load.

Architecture:
    SearchController (this) -> RetrievalWorker (background thread)
    SearchController (this) <- RetrievalWorker.finished / error signals
    SearchController (this) -> SearchInterface.display_results (view rendering)
"""

import time
from qfluentwidgets import InfoBar, InfoBarPosition
from PySide6.QtCore import Qt, QThread, QObject
from backend.retrieval_worker import RetrievalWorker
from ui.signal_bus import signalBus


class SearchController(QObject):
    """
    Controller that bridges the SearchInterface with the RetrievalWorker.

    Responsibilities:
        - Listen for search button clicks and Enter key presses
        - Validate input and engine readiness before searching
        - Spawn RetrievalWorker threads for non-blocking retrieval
        - Delegate result rendering to the view layer
        - Manage loading states and error feedback

    The controller requires an EngineController reference (via attach_engine)
    to access the vector index and reranker. It listens to signalBus.indexReady
    to know when the retrieval pipeline becomes available.
    """

    def __init__(self, parent):
        """
        Args:
            parent: The SearchInterface instance that owns this controller.
        """
        super().__init__(parent)
        self.parent = parent
        self.engine_controller = None
        self._search_start_time = None

        # Hold references to the active worker and thread to prevent
        # premature garbage collection while retrieval is in progress.
        self._active_thread = None
        self._active_worker = None

        # Connect UI interaction signals
        self.parent.search_button.clicked.connect(self.on_search)
        self.parent.search_input.searchSignal.connect(self._on_search_signal)

        # Listen for index readiness via the global signal bus so the
        # search button is enabled as soon as retrieval becomes possible.
        signalBus.indexReady.connect(self.on_index_ready)

    def attach_engine(self, engine_controller):
        """
        Bind this controller to the shared EngineController.

        If the index is already initialized (e.g., the engine finished
        loading before this method was called), the search button is
        enabled immediately.

        Args:
            engine_controller: Shared EngineController instance that holds
                               the vector index and reranker references.
        """
        self.engine_controller = engine_controller

        # Handle the race condition where the index loaded before we attached
        if engine_controller.index is not None:
            self.on_index_ready()

    def on_index_ready(self):
        """
        Callback when the vector index becomes available.
        Enables the search button so the user can begin searching.
        This is triggered by signalBus.indexReady, which fires when
        EngineController receives the index from EngineManager.
        """
        self.parent.search_button.setEnabled(True)
        self.parent.status_label.setText("Index loaded — ready to search.")

    def _on_search_signal(self, text):
        """
        Handler for SearchLineEdit's searchSignal (emitted on Enter key
        or search icon click). Delegates to the main search handler.
        """
        self.on_search()

    def on_search(self):
        """
        Main search handler triggered by the search button or Enter key.

        Validates input, clears previous results, starts the loading spinner,
        and spawns a background RetrievalWorker thread for non-blocking
        semantic retrieval against the vector index.
        """
        query = self.parent.search_input.text().strip()

        if not query:
            InfoBar.warning(
                title="Empty Query",
                content="Please enter a search query.",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=2000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self.parent
            )
            return

        if not self.engine_controller or not self.engine_controller.index:
            InfoBar.warning(
                title="Index Not Ready",
                content="The search index is still loading. Please wait.",
                orient=Qt.Horizontal,
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self.parent
            )
            return

        # Reset cached results and filter controls before starting a new query.
        self.parent.prepare_new_search()
        self.parent.progress_ring.setVisible(True)
        self.parent.search_button.setEnabled(False)
        self.parent.status_label.setText("Searching...")
        self._search_start_time = time.time()

        # Spawn retrieval worker on a dedicated QThread.
        # This prevents the UI from freezing during embedding computation
        # and cross-encoder reranking, which can take several seconds.
        self._active_thread = QThread()
        self._active_worker = RetrievalWorker(
            index=self.engine_controller.index,
            query_text=query,
            reranker=self.engine_controller.reranker,
        )
        self._active_worker.moveToThread(self._active_thread)

        # Wire up the worker lifecycle signals.
        # The thread.started -> worker.run pattern ensures the worker
        # executes in the correct thread context.
        self._active_thread.started.connect(self._active_worker.run)
        self._active_worker.finished.connect(self._on_results)
        self._active_worker.error.connect(self._on_error)
        self._active_worker.finished.connect(self._active_thread.quit)
        self._active_worker.error.connect(self._active_thread.quit)
        self._active_worker.finished.connect(self._active_worker.deleteLater)
        self._active_thread.finished.connect(self._active_thread.deleteLater)

        self._active_thread.start()

    def _on_results(self, results):
        """
        Callback when the RetrievalWorker successfully returns results.

        Computes elapsed search time and delegates the actual result card
        rendering to the view layer (SearchInterface.display_results),
        maintaining clean separation between controller logic and view
        presentation.

        Args:
            results (list[dict]): List of structured result dicts from
                                  RetrievalWorker, each containing title,
                                  file_path, score, text, and metadata.
        """
        elapsed = time.time() - self._search_start_time if self._search_start_time else 0

        self.parent.progress_ring.setVisible(False)
        self.parent.search_button.setEnabled(True)

        # Delegate rendering to the view layer
        self.parent.display_results(results, elapsed)

    def _on_error(self, error_msg):
        """
        Callback when the RetrievalWorker encounters an error.
        Restores the UI to its ready state and displays an error notification.
        """
        self.parent.progress_ring.setVisible(False)
        self.parent.search_button.setEnabled(True)
        self.parent.status_label.setText("Search failed.")

        InfoBar.error(
            title="Search Error",
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            duration=6000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent
        )
