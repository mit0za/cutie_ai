from enum import Enum
from pathlib import Path
from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet  """

    CHAT_INTERFACE = "chat_interface"
    SETTING_INTERFACE = "setting_interface"

    def path(self, theme=Theme.AUTO):
        base = Path(__file__).resolve().parent / "qss"
        return str(base / f"{self.value}.qss")
