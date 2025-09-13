from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from backend.engine_manager import build_query_engine
import sys

# Set up UI
app = QApplication(sys.argv) # Core of QT

window = MainWindow()
window.show() # window will not show unless specify

sys.exit(app.exec())

# query = "The new observatory that was built in Adelaide University grounds. How much was it expected to cost?"
# query = "Tell me about what happen from 1854 to 1870."
# resp = query_engine.query(query)
# print(format_response(resp))
# print(format_metadata(resp))
