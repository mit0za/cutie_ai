from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
import sys

def main():
    # Create core Qt app
    app = QApplication(sys.argv) 

    # Init main window
    window = MainWindow()
    window.show() # window will not show unless specify

    # start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    # freeze_support()
    main()

# query = "The new observatory that was built in Adelaide University grounds. How much was it expected to cost?"
# query = "Tell me about what happen from 1854 to 1870."
# resp = query_engine.query(query)
# print(format_response(resp))
# print(format_metadata(resp))
