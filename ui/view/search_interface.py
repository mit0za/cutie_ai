"""
Document Search Interface
=========================

A dedicated UI view for performing pure semantic document retrieval.
This interface is intentionally separated from the main Q&A chat view
to provide a focused document exploration experience without any LLM
involvement.

The interface provides:
    - A search bar for entering natural language queries
    - A results panel displaying retrieved document chunks as visual cards
    - Relevance score visualization (normalized progress bars) for each result
    - Clickable source file links for quick document access
    - Metadata display (year, article title, etc.) when available

Architecture:
    SearchInterface (this view)
        -> SearchController (logic layer)
            -> RetrievalWorker (backend, runs in QThread)

    The view owns the SearchController and provides display_results() /
    clear_results() methods that the controller calls to update the UI.
    ResultCard widgets are created dynamically for each search result.
"""

import os
from qfluentwidgets import (
    ScrollArea, setTheme, Theme, SearchLineEdit, PrimaryPushButton,
    SubtitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    IndeterminateProgressRing, ProgressBar, CardWidget, FluentIcon,
)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from ui.style_sheet import StyleSheet
from ui.controller.search_controller import SearchController


class ResultCard(CardWidget):
    """
    A visual card component for displaying a single document retrieval result.

    Each card renders the following information:
        - Rank number and document title (header row)
        - Numerical relevance score with a normalized progress bar
        - Source file name with tooltip showing the full path (clickable)
        - Optional metadata chips (year, article title, etc.)
        - Truncated text excerpt from the retrieved document chunk

    The progress bar is normalized against the maximum score in the current
    result set so that the top result always shows a full bar, and lower-scored
    results show proportionally shorter bars. This gives users an intuitive
    sense of relative relevance without needing to interpret raw score values.

    Args:
        result_data (dict): Structured result from RetrievalWorker containing
                            title, file_path, score, text, and metadata.
        rank (int): 1-based position in the result list.
        max_score (float): Maximum score in the current result set,
                           used to normalize the progress bar.
        parent: Parent QWidget.
    """

    def __init__(self, result_data, rank, max_score=1.0, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # ── Header row: rank + title on the left, score on the right ──
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title_text = f"#{rank}  {result_data['title']}"
        title_label = StrongBodyLabel(title_text)
        title_label.setWordWrap(True)

        score_val = result_data.get("score", 0.0)
        score_label = CaptionLabel(f"Relevance: {score_val:.4f}")

        header_layout.addWidget(title_label, stretch=1)
        header_layout.addWidget(score_label)
        layout.addLayout(header_layout)

        # ── Relevance score bar ──
        # Normalized against the top result so the highest-scored card
        # always displays a full bar, making relative comparison intuitive.
        score_bar = ProgressBar(self)
        if max_score > 0:
            normalized = int((score_val / max_score) * 100)
        else:
            normalized = 0
        score_bar.setRange(0, 100)
        score_bar.setValue(max(0, min(100, normalized)))
        score_bar.setFixedHeight(4)
        layout.addWidget(score_bar)

        # ── Source file path (clickable to open with system default app) ──
        file_path = result_data.get("file_path")
        if file_path:
            file_name = os.path.basename(file_path)
            path_label = CaptionLabel(f"Source: {file_name}")
            path_label.setToolTip(file_path)
            path_label.setCursor(Qt.PointingHandCursor)
            # Capture file_path in the lambda's default argument to avoid
            # late-binding closure issues when multiple cards are created.
            path_label.mousePressEvent = lambda event, p=file_path: self._open_file(p)
            layout.addWidget(path_label)

        # ── Metadata chips (displayed when the ingestion pipeline has
        #    extracted structured metadata like year or article title) ──
        metadata = result_data.get("metadata", {})
        meta_parts = []
        if "year" in metadata:
            meta_parts.append(f"Year: {metadata['year']}")
        if "article_title" in metadata:
            meta_parts.append(f"Article: {metadata['article_title']}")
        if meta_parts:
            meta_label = CaptionLabel("  |  ".join(meta_parts))
            layout.addWidget(meta_label)

        # ── Text excerpt ──
        # Truncate long chunks to keep the card compact while still
        # providing enough context for the user to judge relevance.
        excerpt_text = result_data.get("text", "")
        if len(excerpt_text) > 600:
            excerpt_text = excerpt_text[:600] + "..."

        text_label = BodyLabel(excerpt_text)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

    def _open_file(self, file_path):
        """Open the source document with the system's default application."""
        url = QUrl.fromLocalFile(file_path)
        QDesktopServices.openUrl(url)


class SearchInterface(ScrollArea):
    """
    Main interface for the Document Search feature.

    This view provides a pure semantic retrieval experience separate from
    the LLM-powered Q&A chat. Users enter a natural language query and
    receive a ranked list of the most semantically relevant document chunks
    from the vector store, visualized as interactive ResultCard widgets.

    The SearchController is created internally but requires an EngineController
    reference (via attach_engine) to access the vector index and reranker.
    This reference is typically passed by MainWindow after both the
    ChatInterface and SearchInterface have been constructed.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("searchInterface")
        setTheme(Theme.DARK)
        StyleSheet.SETTING_INTERFACE.apply(self)

        # ── Root scrollable container ──
        self.view = QWidget()
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        main_layout = QVBoxLayout(self.view)
        main_layout.setContentsMargins(36, 20, 36, 20)
        main_layout.setSpacing(12)

        # ── Page title and description ──
        title_label = SubtitleLabel("Document Search")
        main_layout.addWidget(title_label)

        desc_label = CaptionLabel(
            "Pure semantic retrieval — bypasses the LLM entirely for fast document search."
        )
        main_layout.addWidget(desc_label)

        # ── Search bar row: input field + search button ──
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("Enter your search query...")
        self.search_input.setClearButtonEnabled(True)

        self.search_button = PrimaryPushButton("Search", self)
        self.search_button.setIcon(FluentIcon.SEARCH)
        self.search_button.setFixedWidth(120)
        # Disabled until the vector index is ready
        self.search_button.setEnabled(False)

        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # ── Status label (shows result count, timing, or readiness) ──
        self.status_label = CaptionLabel("")
        main_layout.addWidget(self.status_label)

        # ── Loading spinner (centered, hidden by default) ──
        self.progress_ring = IndeterminateProgressRing(self)
        self.progress_ring.setFixedSize(36, 36)
        self.progress_ring.setVisible(False)

        spinner_layout = QHBoxLayout()
        spinner_layout.addStretch()
        spinner_layout.addWidget(self.progress_ring)
        spinner_layout.addStretch()
        main_layout.addLayout(spinner_layout)

        # ── Results container ──
        # ResultCard widgets are dynamically added/removed from this layout
        # by the display_results() and clear_results() methods.
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(8)
        main_layout.addLayout(self.results_layout)

        # Push remaining space to the top so result cards stack downward
        main_layout.addStretch(1)

        # ── Initialize the search controller ──
        self.search_controller = SearchController(self)

    def attach_engine(self, engine_controller):
        """
        Connect this interface to the shared EngineController.

        Called by MainWindow after both ChatInterface and SearchInterface
        are created, enabling the search controller to access the vector
        index and reranker for pure retrieval operations.

        Args:
            engine_controller: The EngineController instance managing
                              the LlamaIndex engine lifecycle.
        """
        self.search_controller.attach_engine(engine_controller)

    def display_results(self, results, elapsed):
        """
        Render retrieval results as ResultCard widgets in the results panel.

        Called by SearchController after a successful retrieval. Each result
        dict is transformed into a visual ResultCard with score normalization
        applied across the entire result set.

        Args:
            results (list[dict]): Structured results from RetrievalWorker.
            elapsed (float): Wall-clock seconds the retrieval took.
        """
        if not results:
            self.status_label.setText(f"No results found. ({elapsed:.2f}s)")
            return

        self.status_label.setText(
            f"Found {len(results)} result(s) in {elapsed:.2f}s"
        )

        # Determine the max score for normalizing the progress bars.
        # All scores are divided by this value so the top result gets 100%.
        max_score = max(r.get("score", 0) for r in results)
        if max_score <= 0:
            max_score = 1.0

        for rank, result in enumerate(results, start=1):
            card = ResultCard(
                result, rank=rank, max_score=max_score, parent=self.view
            )
            self.results_layout.addWidget(card)

    def clear_results(self):
        """
        Remove all ResultCard widgets from the results panel.
        Called before each new search to reset the display.
        """
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
