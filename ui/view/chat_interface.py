from qfluentwidgets import ScrollArea, setTheme, Theme, TextEdit, FluentIcon, PrimaryToolButton, InfoBar, InfoBarPosition, qconfig, isDarkTheme
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QLabel
from PySide6.QtCore import QTimer, Qt, QUrl
from ui.style_sheet import StyleSheet
from ui.controller.engine_controller import EngineController
from ui.controller.pushButton_controller import PushButtonController
from PySide6.QtGui import QDesktopServices

# 1. Define the Chat Bubble right here in the same file
class ChatBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)

        self.is_user = is_user
        self.label = QLabel(text)

        layout = QHBoxLayout(self)
        if is_user:
            layout.addStretch()
            layout.addWidget(self.label)
        else:
            layout.addWidget(self.label)
            layout.addStretch()

        self.update_style()
        
        qconfig.themeChanged.connect(self.update_style)
    
    def update_style(self):
        if self.is_user:
            bg = "#0060c0"
            text_color = "white"
        else:
            if isDarkTheme():
                bg = "#2b2b2b"
                text_color = "white"
            else:
                bg = "#eaeaea"
                text_color = "black"

        self.label.setStyleSheet(f"""
            padding: 12px;
            border-radius: 10px;
            font-size: 14px;
            color: {text_color};
            background-color: {bg};
        """)

# 2. Your main ChatInterface
class ChatInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("chatInterface")
        setTheme(Theme.DARK)
        StyleSheet.CHAT_INTERFACE.apply(self)

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

    # --- HELPER TO ADD BUBBLES ---
    def add_message(self, text, is_user=True):
        """Call this function from your PushButtonController to add a new message"""
        bubble = ChatBubble(text, is_user=is_user)
        self.message_layout.addWidget(bubble)
        
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