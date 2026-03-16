"""Document Search interface - pure semantic retrieval, no LLM."""
import os
from qfluentwidgets import (
    ScrollArea,
    setTheme,
    Theme,
    SearchLineEdit,
    FluentIcon,
    SimpleCardWidget,
    BodyLabel,
    CaptionLabel,
    PrimaryPushButton,
    setCustomStyleSheet,
    InfoBar,
    InfoBarPosition,
)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from ui.style_sheet import StyleSheet


class SearchResultCard(SimpleCardWidget):
    """Single search result card."""

    def __init__(self, rank: int, score: float, file_name: str, file_path: str, excerpt: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: #N  score  |  filename
        header = QHBoxLayout()
        rank_label = BodyLabel(f"#{rank}")
        rank_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        score_label = CaptionLabel(f"score: {score:.4f}" if score is not None else "score: N/A")
        score_label.setStyleSheet("color: #888;")
        name_label = BodyLabel(file_name)
        name_label.setStyleSheet("font-weight: bold;")
        header.addWidget(rank_label)
        header.addWidget(score_label)
        header.addWidget(BodyLabel(" | "))
        header.addWidget(name_label, 1)
        layout.addLayout(header)

        # Excerpt
        excerpt_label = CaptionLabel(excerpt)
        excerpt_label.setWordWrap(True)
        excerpt_label.setMaximumHeight(60)
        layout.addWidget(excerpt_label)

        # Open file button
        self.open_btn = PrimaryPushButton(FluentIcon.FOLDER, "Open File")
        self.open_btn.setFixedWidth(120)
        self.open_btn.clicked.connect(self._open_file)
        layout.addWidget(self.open_btn)

    def _open_file(self):
        if self.file_path and os.path.exists(self.file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        else:
            InfoBar.warning(
                title="File Not Found",
                content=f"Path does not exist: {self.file_path}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=4000,
                parent=self.window(),
            )


class SearchInterface(ScrollArea):
    """Document Search - pure semantic retrieval view."""

    def __init__(self, parent=None, engine_controller=None):
        super().__init__(parent=parent)
        self.setObjectName("searchInterface")
        self.engine_controller = engine_controller
        setTheme(Theme.DARK)
        StyleSheet.SETTING_INTERFACE.apply(self)

        self.scrollWidget = QWidget()
        self.main_layout = QVBoxLayout(self.scrollWidget)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(12)

        # Search area
        search_layout = QHBoxLayout()
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("Enter search keywords...")
        self.search_input.setFixedHeight(40)
        search_layout.addWidget(self.search_input, 1)

        self.main_layout.addLayout(search_layout)

        # Results area
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(8)

        self.results_label = BodyLabel("Search results will appear here.")
        self.results_label.setStyleSheet("color: #888;")
        self.results_layout.addWidget(self.results_label)

        self.main_layout.addWidget(self.results_container, 1)

        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Controller
        from ui.controller.search_controller import SearchController
        self.search_controller = SearchController(self, engine_controller)
        self.search_input.searchSignal.connect(self.search_controller.on_search)
        self.search_input.returnPressed.connect(self.search_input.search)

    def set_search_loading(self, loading: bool):
        """Enable/disable search input during retrieval."""
        self.search_input.setEnabled(not loading)

    def display_results(self, nodes):
        """Display retrieval results. nodes: list of dicts from RetrievalWorker."""
        # Clear previous cards
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if not nodes:
            self.results_label.setText("No results found.")
            self.results_label.show()
            return

        self.results_label.setText(f"Found {len(nodes)} result(s):")
        self.results_label.show()

        for i, item in enumerate(nodes, 1):
            if isinstance(item, dict):
                text = item.get("text", "") or ""
                score = item.get("score")
                meta = item.get("metadata", {}) or {}
            else:
                # Fallback for NodeWithScore (direct call)
                node = item.node
                score = item.score
                meta = getattr(node, "metadata", {}) or {}
                text = (getattr(node, "text", "") or "").strip()
            fname = str(meta.get("file_name") or meta.get("source") or "Unknown")
            path = str(meta.get("file_path") or "")
            excerpt = text[:300].replace("\n", " ") + ("..." if len(text) > 300 else "")

            card = SearchResultCard(
                rank=i,
                score=score,
                file_name=fname,
                file_path=path,
                excerpt=excerpt or "(no content)",
                parent=self.results_container,
            )
            card.setMinimumHeight(120)
            self.results_layout.addWidget(card)

        self.results_layout.addStretch(1)
        # Defer layout update - ensures viewport/scroll area recalculates correctly
        QTimer.singleShot(0, self._refresh_results_layout)

    def _refresh_results_layout(self):
        """Called after display_results to force layout recalculation."""
        self.results_container.updateGeometry()
        self.scrollWidget.updateGeometry()
