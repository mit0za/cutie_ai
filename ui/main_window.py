from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QTextBrowser, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout, QTabWidget, QToolBox
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Set the title of the windows
        self.setWindowTitle("Cutie AI")

        # Create container
        container = QWidget()
        #Set it in the middle of the screen
        self.setCentralWidget(container)

        # Horizontal layout which will display the two verticle layout
        layout = QHBoxLayout()
        # Apply layout to container
        container.setLayout(layout)
        
        # Verticale layout for tabs or sth on the left side
        left_layout = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # Vertical layout for ai's response and chatbox (main attraction)
        right_layout = QVBoxLayout()
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # Add both widget to the horizontal layout
        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        # 
        left_widget.setFixedWidth(250)

        # tabs = QTabWidget()
        # tabs.addTab(QLabel("Tab 1"), "Something something here")
        # tabs.addTab(QLabel("Tab 2"), "Something something here")
        # left_layout.addWidget(tabs)


        tabs = QTabWidget()
        tabs.addTab(QLabel("AI Context goes here"), "Context")
        tabs.addTab(QLabel("System Prompts"), "Prompts")
        left_layout.addWidget(tabs)

        # test = QTextBrowser()
        output_label = QLabel("Hello This is a chat box")
        right_layout.addWidget(output_label)

        # test = QTextEdit()

        # self.setCentralWidget(label)
        # self.setCentralWidget(test)