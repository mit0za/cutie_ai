from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Loading Engine")
        layout = QVBoxLayout(self)
        self.label = QLabel("Initializing engine...")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # busy indicator
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
