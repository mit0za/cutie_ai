from qfluentwidgets import ScrollArea, setTheme, Theme, TextEdit, FluentIcon, PrimaryToolButton, InfoBar, InfoBarPosition, qconfig, isDarkTheme
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QLabel, QPushButton
from PySide6.QtCore import QTimer, Qt, QUrl
from ui.style_sheet import StyleSheet
from ui.controller.engine_controller import EngineController
from ui.controller.pushButton_controller import PushButtonController
from PySide6.QtGui import QDesktopServices

class ChatBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None, sources=None):
        super().__init__(parent)

        self.is_user = is_user
        self.sources = sources or []
        self.sources_visible = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.main_layout.addWidget(self.label)

        self.sources_button = None
        self.sources_container = None

        if not self.is_user and self.sources:
            self.sources_button = QPushButton("View Sources ▼")
            self.sources_button.setCursor(Qt.PointingHandCursor)
            self.sources_button.clicked.connect(self.toggle_sources)
            self.main_layout.addWidget(self.sources_button)

            self.sources_container = QWidget()
            self.sources_layout = QVBoxLayout(self.sources_container)
            self.sources_layout.setContentsMargins(12, 12, 12, 12)
            self.sources_layout.setSpacing(4)

            for source in self.sources:
                source_label = QLabel(f"• {source}")
                source_label.setWordWrap(True)
                source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.sources_layout.addWidget(source_label)

            self.sources_container.setVisible(False)
            self.main_layout.addWidget(self.sources_container)

        self.update_style()
        qconfig.themeChanged.connect(self.update_style)

    def toggle_sources(self):
        if not self.sources_container:
            return

        self.sources_visible = not self.sources_visible
        self.sources_container.setVisible(self.sources_visible)

        if self.sources_button:
            if self.sources_visible:
                self.sources_button.setText("Hide Sources ▲")
            else:
                self.sources_button.setText("View Sources ▼")

    def update_style(self):
        if self.is_user:
            bg = "#0060c0"
            text_color = "white"
            border_color = "#0060c0"
        else:
            bg = "#2b2b2b" if isDarkTheme() else "#e9e9eb"
            text_color = "white" if isDarkTheme() else "black"
            border_color = "#3a3a3a" if isDarkTheme() else "#d0d0d0"

        button_bg = "#3a3a3a" if isDarkTheme() else "#dcdcdc"
        button_text = "white" if isDarkTheme() else "black"

        self.setStyleSheet(f"""
            ChatBubble {{
                background-color: {bg};
                border-radius: 10px;
            }}
            QLabel {{
                font-size: 14px;
                color: {text_color};
                background-color: transparent;
                border: none;
            }}
            QPushButton {{
                text-align: left;
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid {border_color};
                background-color: {button_bg};
                color: {button_text};
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)

class ChatInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("chatInterface")
        setTheme(Theme.DARK)
        StyleSheet.CHAT_INTERFACE.apply(self)
        self.loading_bubble = None
        self.loading_row_layout = None

        # layout setup
        self.view = QWidget()
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        # use vertical layout for displaying text and input area
        main_layout = QVBoxLayout(self.view) 
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Replace TextBrowser with a dedicated ScrollArea for the bubbles
        self.chat_scroll = ScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        self.message_container = QWidget()
        self.message_container.setStyleSheet("background-color: transparent;")
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setAlignment(Qt.AlignTop) # Stack bubbles from the top down
        self.message_layout.setContentsMargins(0, 0, 10, 0)
        self.message_layout.setSpacing(15) # Space between messages
        
        self.chat_scroll.setWidget(self.message_container)
        main_layout.addWidget(self.chat_scroll)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(5)

        self.input_box = TextEdit()
        self.input_box.setObjectName("textEdit")
        self.input_box.setPlaceholderText("Ask anything...")
        self.input_box.setMinimumHeight(40)
        self.input_box.setMaximumHeight(200)
        self.input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_box.textChanged.connect(self.autoResize)
        QTimer.singleShot(0, self.autoResize)

        # Add input_box to horizontal layout
        input_layout.addWidget(self.input_box, stretch=1)

        # Style text edit
        # inputBox_qss = "TextEdit{background-color: transparent;} TextEdit#textEdit:focus {background-color: transparent;} TextEdit#textEdit:hover,TextEdit#textEdit:pressed{background-color: transparent;}"
        # setCustomStyleSheet(self.input_box, inputBox_qss, inputBox_qss)
        # self.input_box.setFocusPolicy(Qt.NoFocus)
        
        # Push button
        self.push_button = PrimaryToolButton(FluentIcon.UP)
        # self.push_button = PrimaryPushButton(FluentIcon.UP)
        self.push_button.setFixedHeight(45)
        self.push_button.setEnabled(False)
        
        # Add input_layout to horizontal layout
        input_layout.addWidget(self.push_button)

        # add horizontal layout to main layout
        main_layout.addLayout(input_layout)

        ## LLM set up ##
        self.engine_controller = EngineController(self)
        self.engine_controller.start()

        ## PushButton controller ##
        self.push_button_controller = PushButtonController(self)
        # connect to signal
        self.push_button.clicked.connect(self.push_button_controller.on_clicked)
        self.push_button_controller.attach_engine(self.engine_controller)

    def show_loading(self):
        if self.loading_bubble is not None:
            return

        self.loading_bubble = ChatBubble("Thinking...", is_user=False)

        max_width = int(self.chat_scroll.viewport().width() * 0.85)
        if max_width > 0:
            self.loading_bubble.setMaximumWidth(max_width)

        self.loading_row_layout = QHBoxLayout()
        self.loading_row_layout.setContentsMargins(0, 0, 0, 0)
        self.loading_row_layout.addWidget(self.loading_bubble)
        self.loading_row_layout.addStretch(1)

        self.message_layout.addLayout(self.loading_row_layout)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def hide_loading(self):
        if self.loading_bubble is None:
            return

        self.loading_bubble.setParent(None)
        self.loading_bubble.deleteLater()
        self.loading_bubble = None
        self.loading_row_layout = None

    # --- HELPER TO ADD BUBBLES ---
    def add_message(self, text, is_user=True):
        """Call this function from your PushButtonController to add a new message"""
        bubble = ChatBubble(text, is_user=is_user)
        
        # Set dynamic max width based on current window size (e.g., 85% of view)
        max_width = int(self.chat_scroll.viewport().width() * 0.85)
        if max_width > 0:
            bubble.setMaximumWidth(max_width)
        
        # Handle alignment at the layout level, not inside the bubble
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        if is_user:
            row_layout.addStretch(1) # Pushes user bubble to the right
            row_layout.addWidget(bubble)
        else:
            row_layout.addWidget(bubble)
            row_layout.addStretch(1) # Pushes AI bubble to the left
            
        self.message_layout.addLayout(row_layout)
        
        # Auto-scroll to the bottom so the newest message is always visible
        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def autoResize(self):
        doc = self.input_box.document()
        doc.setTextWidth(self.input_box.viewport().width())
        new_height = min(max(40, int(doc.size().height()) + 10), 200)
        self.input_box.setFixedHeight(new_height)

    def open_link_with_desktop_services(self, url: QUrl):
        """Open docx and pdf with default application."""
        try:
            if not QDesktopServices.openUrl(url):
                InfoBar.warning(
                    title="Unable to Open File",
                    content=f"Could not open: {url.toString()}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=4000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                title="Error Opening File",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=6000,
                parent=self
            )