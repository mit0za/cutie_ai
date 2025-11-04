from qfluentwidgets import ScrollArea, setTheme, Theme, TextBrowser, TextEdit, FluentIcon, PrimaryToolButton, setCustomStyleSheet, InfoBar, InfoBarPosition
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy 
from PySide6.QtCore import QTimer, Qt, QUrl
from ui.style_sheet import StyleSheet
from ui.controller.engine_controller import EngineController
from ui.controller.pushButton_controller import PushButtonController
from PySide6.QtGui import QDesktopServices

class ChatInterface(ScrollArea):
    """ Home interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("chatInterface")
        setTheme(Theme.DARK)
        StyleSheet.SETTING_INTERFACE.apply(self)

        # layout setup
        self.view = QWidget()
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        # use verticle layout for displaying text and input area
        main_layout = QVBoxLayout(self.view) 
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # chat display
        self.chat_display = TextBrowser()
        self.chat_display.setObjectName("textBrowser")
        # self.chat_display.setOpenExternalLinks(True)
        # self.chat_display.setReadOnly(True)
        self.chat_display.setOpenLinks(False)
        self.chat_display.anchorClicked.connect(self._open_link_with_desktop_services)

        # Style text browser
        chatDisplay_qss = "TextBrowser{background-color: transparent;} TextBrowser#textBrowser:focus {background-color: transparent;} TextBrowser#textBrowser:hover,TextBrowser#textBrowser:pressed{background-color: transparent;}"
        setCustomStyleSheet(self.chat_display, chatDisplay_qss, chatDisplay_qss)
        self.chat_display.setFocusPolicy(Qt.NoFocus)

        main_layout.addWidget(self.chat_display) # add to verticle layout

        # Use horizontal layout for input area and button
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(5)

        # Input box
        self.input_box = TextEdit()
        self.input_box.setObjectName("textEdit")
        self.input_box.setPlaceholderText("Asking anything...")
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


    def autoResize(self):
        doc = self.input_box.document()
        doc.setTextWidth(self.input_box.viewport().width())
        new_height = min(max(40, int(doc.size().height()) + 10), 200)
        self.input_box.setFixedHeight(new_height)

    def _open_link_with_desktop_services(self, url: QUrl):
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

