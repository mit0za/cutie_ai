"""
Non-blocking Progress Notification Dialog.

Displays a collapsible flyout panel anchored to the bottom-right corner of the
main window.  It listens to the global SignalBus progress signals and renders
each pipeline step with a status icon, message text, and an overall progress bar.
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QGraphicsOpacityEffect, QSizePolicy
)
from PySide6.QtGui import QFont, QColor
from qfluentwidgets import (
    ProgressBar, FluentIcon, ToolButton,
    isDarkTheme, IndeterminateProgressRing
)
from ui.signal_bus import signalBus


# -- Single step row shown inside the dialog ----------------------------------

class _StepItem(QWidget):
    """Represents one pipeline step inside the progress list."""

    # Visual states for a step
    PENDING = 0
    RUNNING = 1
    DONE = 2
    ERROR = 3

    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # Status icon label (updated when state changes)
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(22)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        # Spinner shown only while the step is actively running
        self.spinner = IndeterminateProgressRing()
        self.spinner.setFixedSize(18, 18)
        self.spinner.setVisible(False)
        layout.addWidget(self.spinner)

        # Step description text
        self.text_label = QLabel(message)
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.text_label)

        # Duration label shown on the right (e.g. "2.4s")
        self.duration_label = QLabel("")
        self.duration_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.duration_label.setFixedWidth(70)
        self.duration_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.duration_label)

        # Start in the pending state
        self.set_state(self.PENDING)

    def update_message(self, message: str):
        """Replace the description text for this step."""
        self.text_label.setText(message)

    def update_duration(self, text: str):
        """Update the duration label text."""
        self.duration_label.setText(text)

    def set_state(self, state: int):
        """Update visual appearance to reflect the given state."""
        self.spinner.setVisible(state == self.RUNNING)

        if state == self.PENDING:
            # Grey bullet to indicate "not started yet"
            self.icon_label.setText("○")
            self.icon_label.setVisible(True)
            color = QColor(150, 150, 150)
        elif state == self.RUNNING:
            # Hide the static icon while the spinner is active
            self.icon_label.setVisible(False)
            color = QColor(0, 159, 254)  # Fluent accent blue
        elif state == self.DONE:
            # Green check mark to indicate success
            self.icon_label.setText("✓")
            self.icon_label.setVisible(True)
            color = QColor(0, 200, 83)
        else:
            # Red cross for errors
            self.icon_label.setText("✕")
            self.icon_label.setVisible(True)
            color = QColor(255, 69, 58)

        self.text_label.setStyleSheet(f"color: {color.name()};")


# -- Main dialog widget -------------------------------------------------------

class ProgressDialog(QWidget):
    """
    A non-blocking, slide-up flyout that shows background task progress.

    The dialog is designed to float above the main content area. It slides
    in from the bottom-right when progress begins and can be manually
    dismissed or will auto-hide shortly after all steps complete.
    """

    # Fixed dimensions for the flyout panel
    PANEL_WIDTH = 360
    PANEL_HEIGHT = 340

    def __init__(self, parent=None):
        super().__init__(parent)

        # Start fully hidden off-screen; position is set by reposition()
        self.setFixedSize(self.PANEL_WIDTH, self.PANEL_HEIGHT)
        self.setVisible(False)

        # Opacity effect used by the fade-in / fade-out animation
        self._opacity_fx = QGraphicsOpacityEffect(self)
        self._opacity_fx.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_fx)

        # Internal state tracking
        self._step_items: list[_StepItem] = []
        self._current_step = -1
        self._total_steps = 0
        self._is_shown = False
        self._step_start_ts = {}
        self._step_end_ts = {}
        self._duration_timer = QTimer(self)
        self._duration_timer.setInterval(250)
        self._duration_timer.timeout.connect(self._refresh_running_duration)

        self._build_ui()
        self._connect_signals()

    # -- UI construction -------------------------------------------------------

    def _build_ui(self):
        """Assemble the widget tree for the progress flyout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Card-style container with rounded corners and shadow
        self._card = QWidget()
        self._card.setObjectName("progressCard")
        self._apply_card_style()
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(8)

        # -- Header row: title + close button --
        header = QHBoxLayout()
        self._title_label = QLabel("Background Tasks")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        header.addWidget(self._title_label)
        header.addStretch()

        # Close button to manually dismiss the panel
        self._close_btn = ToolButton(FluentIcon.CLOSE)
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.clicked.connect(self.slide_out)
        header.addWidget(self._close_btn)
        card_layout.addLayout(header)

        # -- Overall progress bar --
        self._progress_bar = ProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(4)
        card_layout.addWidget(self._progress_bar)

        # -- Status summary label (e.g. "Step 2 / 7") --
        self._status_label = QLabel("Waiting…")
        self._status_label.setStyleSheet("color: grey; font-size: 11px;")
        card_layout.addWidget(self._status_label)

        # -- Scrollable list of step items --
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()  # push items to the top
        scroll.setWidget(self._list_widget)
        card_layout.addWidget(scroll, 1)

        root.addWidget(self._card)

    def _apply_card_style(self):
        """Apply a theme-aware card style (dark or light)."""
        if isDarkTheme():
            bg = "rgba(39, 39, 39, 230)"
            border = "rgba(255, 255, 255, 0.08)"
        else:
            bg = "rgba(251, 251, 251, 230)"
            border = "rgba(0, 0, 0, 0.06)"

        self._card.setStyleSheet(
            f"#progressCard {{"
            f"  background: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 8px;"
            f"}}"
        )

    # -- Signal wiring ---------------------------------------------------------

    def _connect_signals(self):
        """Subscribe to global progress signals from the SignalBus."""
        signalBus.progressStarted.connect(self._on_started)
        signalBus.progressUpdated.connect(self._on_updated)
        signalBus.progressFinished.connect(self._on_finished)
        signalBus.progressError.connect(self._on_error)

    # -- Slot handlers ---------------------------------------------------------

    def _on_started(self, total_steps: int):
        """Reset the dialog and prepare for a new pipeline run."""
        self._clear_steps()
        self._total_steps = total_steps
        self._current_step = -1
        self._progress_bar.setValue(0)
        self._status_label.setText("Starting…")
        self._title_label.setText("Background Tasks")
        self._step_start_ts.clear()
        self._step_end_ts.clear()
        self._duration_timer.stop()
        self.slide_in()

    def _on_updated(self, step_index: int, total_steps: int, message: str):
        """Advance to the given step, marking previous steps as done."""
        self._total_steps = total_steps

        # Mark all previous steps as completed
        for i in range(step_index):
            if i < len(self._step_items):
                self._step_items[i].set_state(_StepItem.DONE)
                self._finalize_step_duration(i)

        # Create the step widget if it does not already exist
        while len(self._step_items) <= step_index:
            item = _StepItem("…")
            # Insert before the trailing stretch
            self._list_layout.insertWidget(self._list_layout.count() - 1, item)
            self._step_items.append(item)

        # Update current step to RUNNING state
        current = self._step_items[step_index]
        current.update_message(message)
        current.set_state(_StepItem.RUNNING)
        if step_index not in self._step_start_ts:
            self._step_start_ts[step_index] = time.monotonic()
        self._update_step_duration(step_index, running=True)

        self._current_step = step_index

        # Compute overall percentage based on completed steps
        pct = int(((step_index) / max(total_steps, 1)) * 100)
        self._progress_bar.setValue(pct)
        self._status_label.setText(f"Step {step_index + 1} / {total_steps}")

        # Auto-show if hidden
        if not self._is_shown:
            self.slide_in()

        if not self._duration_timer.isActive():
            self._duration_timer.start()

    def _on_finished(self):
        """Mark all remaining steps as done and schedule auto-hide."""
        for item in self._step_items:
            item.set_state(_StepItem.DONE)
        for i in range(len(self._step_items)):
            self._finalize_step_duration(i)

        self._progress_bar.setValue(100)
        self._status_label.setText("All tasks completed")
        self._title_label.setText("Background Tasks ✓")
        self._duration_timer.stop()

        # Auto-hide after 6 seconds so the user can still glance at results
        QTimer.singleShot(6000, self.slide_out)

    def _on_error(self, error_msg: str):
        """Mark the current step as failed and display the error."""
        if 0 <= self._current_step < len(self._step_items):
            self._step_items[self._current_step].set_state(_StepItem.ERROR)
            self._step_items[self._current_step].update_message(error_msg)
            self._finalize_step_duration(self._current_step)

        self._status_label.setText("Error occurred")
        self._title_label.setText("Background Tasks ✕")
        self._duration_timer.stop()

    # -- Step management -------------------------------------------------------

    def _clear_steps(self):
        """Remove all step widgets from the list."""
        for item in self._step_items:
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._step_items.clear()
        self._step_start_ts.clear()
        self._step_end_ts.clear()

    def _format_duration(self, seconds: float) -> str:
        """Format duration seconds for display."""
        if seconds < 0:
            seconds = 0
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        rem = seconds - (minutes * 60)
        return f"{minutes}m {rem:04.1f}s"

    def _finalize_step_duration(self, step_index: int):
        """Freeze duration for a completed or failed step."""
        if step_index in self._step_end_ts:
            return
        start_ts = self._step_start_ts.get(step_index)
        if start_ts is None:
            return
        self._step_end_ts[step_index] = time.monotonic()
        self._update_step_duration(step_index, running=False)

    def _update_step_duration(self, step_index: int, running: bool):
        """Update duration label for a given step."""
        if step_index >= len(self._step_items):
            return
        start_ts = self._step_start_ts.get(step_index)
        if start_ts is None:
            return
        end_ts = self._step_end_ts.get(step_index)
        if running or end_ts is None:
            elapsed = time.monotonic() - start_ts
        else:
            elapsed = end_ts - start_ts
        self._step_items[step_index].update_duration(self._format_duration(elapsed))

    def _refresh_running_duration(self):
        """Refresh live duration for the currently running step."""
        if self._current_step >= 0:
            self._update_step_duration(self._current_step, running=True)

    # -- Slide / fade animations -----------------------------------------------

    def slide_in(self):
        """Animate the panel into view from the bottom-right corner."""
        if self._is_shown:
            return
        self._is_shown = True
        self._apply_card_style()  # refresh theme on each show
        self.setVisible(True)
        self.raise_()

        # Fade in
        anim = QPropertyAnimation(self._opacity_fx, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

        # Slide upward by shifting the Y position
        start = QPoint(self.x(), self.y() + 30)
        end = QPoint(self.x(), self.y())
        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(300)
        slide.setStartValue(start)
        slide.setEndValue(end)
        slide.setEasingCurve(QEasingCurve.OutCubic)
        slide.start(QPropertyAnimation.DeleteWhenStopped)

    def slide_out(self):
        """Animate the panel out of view and hide it."""
        if not self._is_shown:
            return
        self._is_shown = False

        anim = QPropertyAnimation(self._opacity_fx, b"opacity", self)
        anim.setDuration(250)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(lambda: self.setVisible(False))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def toggle(self):
        """Toggle panel visibility (used by the toolbar button)."""
        if self._is_shown:
            self.slide_out()
        else:
            self.slide_in()

    # -- Geometry helpers ------------------------------------------------------

    def reposition(self):
        """
        Place the dialog at the bottom-right of the parent widget.
        Call this from the parent's resizeEvent so the flyout stays anchored.
        """
        if self.parentWidget():
            pw = self.parentWidget().width()
            ph = self.parentWidget().height()
            margin = 16
            self.move(pw - self.PANEL_WIDTH - margin, ph - self.PANEL_HEIGHT - margin)
