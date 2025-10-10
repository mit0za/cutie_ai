from qfluentwidgets import (ScrollArea, ExpandLayout, ScrollArea, setTheme, setThemeColor, isDarkTheme,  
                            SettingCardGroup, SwitchSettingCard, FluentIcon, OptionsSettingCard, CustomColorSettingCard, InfoBar)
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal
from ui.config import cfg, isWin11
from utils.style_sheet import StyleSheet
from ui.signal_bus import signalBus
from ui.style_sheet import StyleSheet

class SettingsInterface(ScrollArea):
    """ Settings interface """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel(self.tr("Settings"), self)

        # personalization
        self.personalGroup = SettingCardGroup(
            self.tr('Personalization'), self.scrollWidget)
        self.micaCard = SwitchSettingCard(
            FluentIcon.TRANSPARENT,
            self.tr('Mica effect'),
            self.tr('Apply semi transparent to windows and surfaces'),
            cfg.micaEnabled,
            self.personalGroup
        )
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FluentIcon.BRUSH,
            self.tr('Application theme'),
            self.tr("Change the appearance of your application"),
            texts=[
                self.tr('Light'), self.tr('Dark'),
                self.tr('Use system setting')
            ],
            parent=self.personalGroup
        )
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FluentIcon.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            self.personalGroup
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FluentIcon.ZOOM,
            self.tr("Interface zoom"),
            self.tr("Change the size of widgets and fonts"),
            texts=[
                "100%", "125%", "150%", "175%", "200%",
                self.tr("Use system setting")
            ],
            parent=self.personalGroup
        )

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('settingInterface')

        # init style sheet
        self.scrollWidget.setObjectName('scrollwidget')
        self.settingLabel.setObjectName('settingLabel')

        self.setProperty("theme", "dark" if isDarkTheme() else "light")
        StyleSheet.SETTING_INTERFACE.apply(self)
        cfg.themeChanged.connect(self.__onThemeChanged)

        self.micaCard.setEnabled(isWin11())

        # init layout
        self.__initLayout()
        self.__connectSignalToSlot()


    def __initLayout(self):
        self.settingLabel.move(36, 30)

        # add cards to group
        self.personalGroup.addSettingCard(self.micaCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.personalGroup)


    def __showRestartTooltip(self):
        """toast restart msg"""
        InfoBar.success(
            self.tr("Updated successfully"),
            self.tr("Configuration takes effect after restart"),
            duration=1500,
            parent=self
        )
    def __connectSignalToSlot(self):
        """ connect signal to slot """
        # Show toast msg
        cfg.appRestartSig.connect(self.__showRestartTooltip)

        cfg.themeChanged.connect(setTheme) 
        self.themeColorCard.colorChanged.connect(lambda c: setThemeColor(c))
        self.micaCard.checkedChanged.connect(signalBus.micaEnableChanged)

    def __onThemeChanged(self, *_):
        from qfluentwidgets import isDarkTheme
        self.setProperty("theme", "dark" if isDarkTheme() else "light")
        StyleSheet.SETTING_INTERFACE.apply(self)