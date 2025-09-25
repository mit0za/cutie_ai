import sys
from qfluentwidgets import QConfig, ConfigItem, BoolValidator, OptionsConfigItem, OptionsValidator, RangeConfigItem, RangeValidator, Theme, qconfig

def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000

class Config(QConfig):
    """ Config of the application """
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)

    # Material
    blurRadius  = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

YEAR = 2025
AUTHOR = "Ethan Yin"

cfg = Config()
cfg.themeMode.value = Theme.AUTO
qconfig.load("app/config/config.json", cfg)