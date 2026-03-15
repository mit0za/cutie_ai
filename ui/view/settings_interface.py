from qfluentwidgets import (ScrollArea, ExpandLayout, ScrollArea, setTheme, setThemeColor, isDarkTheme,  
                            SettingCardGroup, SwitchSettingCard, FluentIcon, OptionsSettingCard, CustomColorSettingCard, InfoBar, FolderListSettingCard, RangeSettingCard)
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal, QStandardPaths
from ui.config import cfg, isWin11
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

        # data 
        self.dataGroup = SettingCardGroup(
            self.tr("Data"), self.scrollWidget)
        self.dataPicker = FolderListSettingCard(
            cfg.dataFolders,
            self.tr("Locate data"),
            directory=QStandardPaths.writableLocation(
                QStandardPaths.AppConfigLocation),
            parent=self.dataGroup
        )
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

        # LLM SETTINGS
        self.llmSetting = SettingCardGroup(
            self.tr("LLM Settings"), self.scrollWidget)
        self.temperatureCard = OptionsSettingCard(
            cfg.temperature,
            FluentIcon.CALORIES,
            self.tr("Temperature"),
            self.tr("Change LLM creativity. Lower values force strict factual answers."),
            texts=[
                "1", "2", "3", "4", "5", "6", "7", "8", "9"
            ],
            parent=self.llmSetting
        )
        self.maxTokensCard = OptionsSettingCard(
            cfg.max_new_tokens,
            FluentIcon.DOCUMENT,
            self.tr("Max New Tokens"),
            self.tr("Maximum length of the generated AI response."),
            texts= [
                "128", "256", "512", "1024", "2048", "4096", "8192"
            ],
            parent=self.llmSetting
        )
        # self.verboseCard = SwitchSettingCard(
        #     FluentIcon.COMMAND_PROMPT,
        #     self.tr("Verbose Logging"),
        #     self.tr("Print detailed generation steps to the console for debugging."),
        #     cfg.verbose,
        #     parent=self.llmSetting
        # )

        self.retrievalGroup = SettingCardGroup(
            self.tr("Retrieval Parameters"), self.scrollWidget)
        self.topKCard = RangeSettingCard(
            cfg.similarity_top_k,
            FluentIcon.SEARCH,
            self.tr("Similarity Top-K"),
            self.tr("Broad search: Number of chunks initially pulled from the vector database."),
            parent=self.retrievalGroup
        )
        self.topNCard = RangeSettingCard(
            cfg.top_n,
            FluentIcon.FILTER,
            self.tr("Reranker Top-N"),
            self.tr("Precise filter: Number of highly relevant chunks passed to the LLM."),
            parent=self.retrievalGroup
        )
        self.chunkSizeCard = OptionsSettingCard(
            cfg.citation_chunk_size,
            FluentIcon.ALIGNMENT,
            self.tr("Citation Chunk Size"),
            self.tr("Size of text blocks used to generate citations."),
            texts= ["128", "256", "512", "1024", "2048"],
            parent=self.retrievalGroup
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

        # add data group to settings
        self.dataGroup.addSettingCard(self.dataPicker)

        # add personalize group to settings
        self.personalGroup.addSettingCard(self.micaCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)

        # add llm to settings card
        self.llmSetting.addSettingCard(self.temperatureCard)
        self.llmSetting.addSettingCard(self.maxTokensCard)
        # self.llmSetting.addSettingCard(self.verboseCard)

        # add retrieval to settings card
        self.retrievalGroup.addSettingCard(self.topKCard)
        self.retrievalGroup.addSettingCard(self.topNCard)
        self.retrievalGroup.addSettingCard(self.chunkSizeCard)

        # add setting card group to layout
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        # Add data group and personalGroup to the setting page
        self.expandLayout.addWidget(self.dataGroup)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.llmSetting)
        self.expandLayout.addWidget(self.retrievalGroup)


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