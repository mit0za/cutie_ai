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
    ComboBox, LineEdit, PushButton,
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
        article_title = metadata.get("article_title") or metadata.get("title")
        if article_title:
            meta_parts.append(f"Article: {article_title}")
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
        """
        Open the source document with the system's default application.
        Resolves relative paths against the project root so the index
        remains portable across different machines.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
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

        # Local filter/sort controls operate on the last retrieved result set.
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(8)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        sort_row = QHBoxLayout()
        sort_row.setSpacing(8)

        self.file_type_combo = ComboBox(self)
        self.file_type_combo.addItem("All Types")
        self.file_type_combo.setMinimumWidth(140)

        self.source_filter_input = LineEdit(self)
        self.source_filter_input.setPlaceholderText("Filter by source name...")
        self.source_filter_input.setClearButtonEnabled(True)

        self.sort_combo = ComboBox(self)
        self.sort_combo.addItems([
            "Relevance (High to Low)",
            "Relevance (Low to High)",
            "Title (A-Z)",
            "Title (Z-A)",
            "Source (A-Z)",
            "Source (Z-A)",
        ])
        self.sort_combo.setMinimumWidth(230)

        self.clear_filters_button = PushButton("Clear Filters", self)
        self.clear_filters_button.setMinimumWidth(130)

        filter_control_style = """
            ComboBox, LineEdit, PushButton {
                color: #f2f2f2;
                background-color: #202020;
                border: 1px solid #555;
                border-radius: 6px;
            }
            ComboBox QLabel, PushButton QLabel {
                color: #f2f2f2;
            }
        """
        self.file_type_combo.setStyleSheet(filter_control_style)
        self.source_filter_input.setStyleSheet(filter_control_style)
        self.sort_combo.setStyleSheet(filter_control_style)
        self.clear_filters_button.setStyleSheet(filter_control_style)

        filter_row.addWidget(CaptionLabel("Type"))
        filter_row.addWidget(self.file_type_combo)
        filter_row.addWidget(CaptionLabel("Source"))
        filter_row.addWidget(self.source_filter_input, stretch=1)

        sort_row.addWidget(CaptionLabel("Sort"))
        sort_row.addWidget(self.sort_combo)
        sort_row.addWidget(self.clear_filters_button)
        sort_row.addStretch(1)

        filter_layout.addLayout(filter_row)
        filter_layout.addLayout(sort_row)
        main_layout.addLayout(filter_layout)

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

        self._all_results = []
        self._last_elapsed = 0.0
        self._updating_filter_options = False
        self._connect_filter_controls()

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
        self._all_results = list(results)
        self._last_elapsed = elapsed
        self._update_file_type_options(self._all_results)
        self.apply_filters_and_sort()

    def apply_filters_and_sort(self, *_):
        """
        Apply local file type/source filters and sort cached search results.

        This method does not call the retrieval worker again. It reshapes the
        most recent result set returned by semantic retrieval, so users can
        refine results instantly without another vector search.
        """
        if self._updating_filter_options:
            return

        self.clear_results()

        if not self._all_results:
            self.status_label.setText(f"No results found. ({self._last_elapsed:.2f}s)")
            return

        filtered_results = [
            result for result in self._all_results
            if self._matches_file_type(result) and self._matches_source_filter(result)
        ]
        filtered_results = self._sort_results(filtered_results)

        if not filtered_results:
            self.status_label.setText(
                f"No results match current filters. "
                f"({len(self._all_results)} original result(s), {self._last_elapsed:.2f}s)"
            )
            return

        if len(filtered_results) == len(self._all_results):
            self.status_label.setText(
                f"Found {len(filtered_results)} result(s) in {self._last_elapsed:.2f}s"
            )
        else:
            self.status_label.setText(
                f"Showing {len(filtered_results)} of {len(self._all_results)} result(s) "
                f"in {self._last_elapsed:.2f}s"
            )

        # Determine the max score for normalizing the progress bars.
        # All scores are divided by this value so the top result gets 100%.
        max_score = max(r.get("score", 0) for r in filtered_results)
        if max_score <= 0:
            max_score = 1.0

        for rank, result in enumerate(filtered_results, start=1):
            card = ResultCard(
                result, rank=rank, max_score=max_score, parent=self.view
            )
            self.results_layout.addWidget(card)

    def reset_filters(self):
        """Reset filter controls without clearing cached retrieval results."""
        self.file_type_combo.setCurrentText("All Types")
        self.source_filter_input.clear()
        self.sort_combo.setCurrentIndex(0)
        self.apply_filters_and_sort()

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

    def prepare_new_search(self):
        """Clear cached results and reset filters before a new retrieval."""
        self._all_results = []
        self._last_elapsed = 0.0
        self.reset_filters()
        self.clear_results()

    def _connect_filter_controls(self):
        """Connect filter controls to local result re-rendering."""
        self.file_type_combo.currentTextChanged.connect(self.apply_filters_and_sort)
        self.source_filter_input.textChanged.connect(self.apply_filters_and_sort)
        self.sort_combo.currentTextChanged.connect(self.apply_filters_and_sort)
        self.clear_filters_button.clicked.connect(self.reset_filters)

    def _update_file_type_options(self, results):
        """Populate the file type combo from the current result set."""
        current_type = self.file_type_combo.currentText()
        file_types = sorted({
            self._get_file_type(result)
            for result in results
            if self._get_file_type(result)
        })

        self._updating_filter_options = True
        self.file_type_combo.clear()
        self.file_type_combo.addItem("All Types")
        self.file_type_combo.addItems(file_types)
        if current_type in file_types:
            self.file_type_combo.setCurrentText(current_type)
        else:
            self.file_type_combo.setCurrentText("All Types")
        self._updating_filter_options = False

    def _matches_file_type(self, result):
        """Return True when the result matches the selected file type."""
        selected_type = self.file_type_combo.currentText()
        if selected_type == "All Types":
            return True
        return self._get_file_type(result) == selected_type

    def _matches_source_filter(self, result):
        """Return True when the source/title contains the filter text."""
        filter_text = self.source_filter_input.text().strip().lower()
        if not filter_text:
            return True

        metadata = result.get("metadata", {}) or {}
        haystack_parts = [
            result.get("title", ""),
            os.path.basename(result.get("file_path") or ""),
            metadata.get("source", ""),
            metadata.get("file_name", ""),
            metadata.get("article_title", ""),
            metadata.get("title", ""),
        ]
        return filter_text in " ".join(str(part) for part in haystack_parts).lower()

    def _sort_results(self, results):
        """Return a sorted copy based on the selected sort option."""
        sort_text = self.sort_combo.currentText()
        sorted_results = list(results)

        if sort_text == "Relevance (Low to High)":
            sorted_results.sort(key=lambda result: result.get("score", 0.0))
        elif sort_text == "Title (A-Z)":
            sorted_results.sort(key=self._get_result_title)
        elif sort_text == "Title (Z-A)":
            sorted_results.sort(key=self._get_result_title, reverse=True)
        elif sort_text == "Source (A-Z)":
            sorted_results.sort(key=self._get_source_name)
        elif sort_text == "Source (Z-A)":
            sorted_results.sort(key=self._get_source_name, reverse=True)
        else:
            sorted_results.sort(
                key=lambda result: result.get("score", 0.0),
                reverse=True,
            )

        return sorted_results

    def _get_file_type(self, result):
        """Extract the upper-case file extension used by the type filter."""
        source = result.get("file_path") or result.get("title") or ""
        extension = os.path.splitext(source)[1].lstrip(".").upper()
        return extension or "UNKNOWN"

    def _get_result_title(self, result):
        """Return a stable lower-case title value for sorting."""
        return str(result.get("title") or "").lower()

    def _get_source_name(self, result):
        """Return a stable lower-case source file name for sorting."""
        file_path = result.get("file_path") or ""
        source_name = os.path.basename(file_path) if file_path else result.get("title", "")
        return str(source_name or "").lower()
