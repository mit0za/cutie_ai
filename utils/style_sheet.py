from enum import Enum
from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig

class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet"""
    CHAT_INTERFACE = "chat_interface"
    SETTING_INTERFACE = "setting_interface"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        theme_name = theme.value.lower()
        return f"ui/qss/{theme_name}/{self.value}.qss"