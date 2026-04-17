import os
import zipfile
import shutil
from qfluentwidgets import (ScrollArea, ExpandLayout, ScrollArea, setTheme, setThemeColor, isDarkTheme,
                            SettingCardGroup, SwitchSettingCard, FluentIcon, OptionsSettingCard, CustomColorSettingCard, InfoBar, FolderListSettingCard, RangeSettingCard, PushSettingCard, CardWidget)
from PySide6.QtWidgets import QWidget, QLabel, QFileDialog, QGridLayout, QSizePolicy
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

        # Database project management group — export and import the
        # self-contained chroma_db/ directory as a portable .zip archive.
        self.projectGroup = SettingCardGroup(
            self.tr("Project Database"), self.scrollWidget)

        # Index status group — live index statistics
        self.indexStatusGroup = SettingCardGroup(
            self.tr("Index Status"), self.scrollWidget)
        self.indexStatusCard = CardWidget(self.indexStatusGroup)
        # Build the status card UI once; values update via signalBus.
        self._build_index_status_card()

        # "Export Project" button — compresses the entire ./chroma_db/
        # directory into a single .zip file so it can be shared across machines.
        self.exportProjectCard = PushSettingCard(
            self.tr('Export'),
            FluentIcon.SHARE,
            self.tr('Export Project'),
            self.tr('Compress chroma_db/ into a .zip file for sharing'),
            self.projectGroup
        )

        # "Import Project" button — lets the user pick a previously exported
        # .zip file, extracts it and restores the chroma_db/ directory.
        self.importProjectCard = PushSettingCard(
            self.tr('Import'),
            FluentIcon.DOWNLOAD,
            self.tr('Import Project'),
            self.tr('Restore chroma_db/ from a previously exported .zip file'),
            self.projectGroup
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

        # MODEL PATHS
        self.modelGroup = SettingCardGroup(self.tr("Model Locations"), self.scrollWidget)
        
        # LLM File Picker
        self.llmPathCard = PushSettingCard(
            self.tr('Browse'),
            FluentIcon.FOLDER,
            self.tr('LLM Model Path'),
            cfg.llmModelPath.value,
            self.modelGroup
        )
        
        # Embedding Folder Picker
        self.embedPathCard = PushSettingCard(
            self.tr('Browse'),
            FluentIcon.FOLDER,
            self.tr('Embedding Model Folder'),
            cfg.embedModelPath.value,
            self.modelGroup
        )
        
        # Reranker Folder Picker
        self.rerankerPathCard = PushSettingCard(
            self.tr('Browse'),
            FluentIcon.FOLDER,
            self.tr('Reranker Model Folder'),
            cfg.rerankerModelPath.value,
            self.modelGroup
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

        # add index status group to settings
        self.indexStatusGroup.addSettingCard(self.indexStatusCard)

        # add project database group (export / import)
        self.projectGroup.addSettingCard(self.exportProjectCard)
        self.projectGroup.addSettingCard(self.importProjectCard)

        # add personalize group to settings
        self.personalGroup.addSettingCard(self.micaCard)
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)

        # add model path cards
        self.modelGroup.addSettingCard(self.llmPathCard)
        self.modelGroup.addSettingCard(self.embedPathCard)
        self.modelGroup.addSettingCard(self.rerankerPathCard)

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
        self.expandLayout.addWidget(self.indexStatusGroup)
        self.expandLayout.addWidget(self.projectGroup)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.modelGroup)
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
        # Listen for backend index stats so the UI stays in sync.
        signalBus.indexStatsUpdated.connect(self._update_index_status)

        # Wire up export and import buttons to their handler methods
        self.exportProjectCard.clicked.connect(self.__onExportProject)
        self.importProjectCard.clicked.connect(self.__onImportProject)

    def __onThemeChanged(self, *_):
        from qfluentwidgets import isDarkTheme
        self.setProperty("theme", "dark" if isDarkTheme() else "light")
        StyleSheet.SETTING_INTERFACE.apply(self)

    def _build_index_status_card(self):
        """Build the index status card layout and value labels."""
        layout = QGridLayout(self.indexStatusCard)
        self.index_status_layout = layout
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(8)

        label_style = "color: #888;"
        value_style = "color: #ddd;" if isDarkTheme() else "color: #333;"

        ready_label = QLabel(self.tr("Index Ready"))
        ready_label.setStyleSheet(label_style)
        self.index_ready_value = QLabel(self.tr("Loading..."))
        self.index_ready_value.setStyleSheet(value_style)

        doc_label = QLabel(self.tr("Documents"))
        doc_label.setStyleSheet(label_style)
        self.doc_count_value = QLabel("0")
        self.doc_count_value.setStyleSheet(value_style)

        node_label = QLabel(self.tr("Nodes"))
        node_label.setStyleSheet(label_style)
        self.node_count_value = QLabel("0")
        self.node_count_value.setStyleSheet(value_style)

        time_label = QLabel(self.tr("Last Indexed"))
        time_label.setStyleSheet(label_style)
        self.last_index_value = QLabel(self.tr("Unknown"))
        self.last_index_value.setStyleSheet(value_style)

        layout.addWidget(ready_label, 0, 0)
        layout.addWidget(self.index_ready_value, 0, 1)
        layout.addWidget(doc_label, 1, 0)
        layout.addWidget(self.doc_count_value, 1, 1)
        layout.addWidget(node_label, 2, 0)
        layout.addWidget(self.node_count_value, 2, 1)
        layout.addWidget(time_label, 3, 0)
        layout.addWidget(self.last_index_value, 3, 1)

        # Let the card follow the layout's natural height so all four
        # status rows remain visible inside the SettingCardGroup.
        self.indexStatusCard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._sync_index_status_card_height()

    def _sync_index_status_card_height(self):
        """Resize the status card to fit its content height."""
        content_height = self.index_status_layout.sizeHint().height()
        margins = self.index_status_layout.contentsMargins()
        self.indexStatusCard.setFixedHeight(
            content_height + margins.top() + margins.bottom()
        )

    def _update_index_status(self, stats: dict):
        """Update index status values from the backend stats payload."""
        ready = stats.get("ready", False)
        doc_count = stats.get("doc_count", 0)
        node_count = stats.get("node_count", 0)
        last_index_time = stats.get("last_index_time")

        self.index_ready_value.setText(self.tr("Yes") if ready else self.tr("No"))
        self.doc_count_value.setText(str(doc_count))
        self.node_count_value.setText(str(node_count))
        if last_index_time:
            self.last_index_value.setText(str(last_index_time))
        else:
            if not ready and doc_count == 0 and node_count == 0:
                self.last_index_value.setText(self.tr("Not indexed yet"))
            else:
                self.last_index_value.setText(self.tr("Unknown"))

        # Re-apply the height after text updates so longer values do not get clipped.
        self._sync_index_status_card_height()

    def __onExportProject(self):
        """
        Export the entire chroma_db/ directory as a single .zip archive.

        The chroma_db/ folder is self-contained — it stores both the vector
        index and a copy of the original source documents. Compressing it
        into a .zip lets the user share the full project database with
        teammates, who can then import it on their own machine without
        needing to re-index from the raw data files.

        Workflow:
        1. Validate that the chroma_db/ directory exists and is not empty.
        2. Open a native "Save As" dialog so the user picks the destination.
        3. Walk every file inside chroma_db/ and add it to the archive,
           preserving the internal directory structure.
        4. Show a success or error toast notification when finished.
        """
        # Resolve the absolute path to the chroma_db directory,
        # which sits at the project root alongside main.py.
        chroma_dir = os.path.abspath("./chroma_db")

        # Guard: make sure the database folder actually exists and has content
        if not os.path.isdir(chroma_dir) or not os.listdir(chroma_dir):
            InfoBar.error(
                self.tr("Export failed"),
                self.tr("No chroma_db/ directory found or it is empty."),
                duration=3000,
                parent=self
            )
            return

        # Let the user choose where to save the .zip file via a native dialog
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Project Database"),
            os.path.join(
                QStandardPaths.writableLocation(QStandardPaths.DesktopLocation),
                "chroma_db_export.zip"
            ),
            self.tr("ZIP Archive (*.zip)")
        )

        # If the user cancelled the dialog, bail out silently
        if not save_path:
            return

        try:
            # Create the zip archive using deflate compression.
            # os.walk traverses every subdirectory inside chroma_db/,
            # and each file is stored with a relative path rooted at
            # the parent of chroma_db/ so that extracting reproduces
            # the original folder structure (chroma_db/...).
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for dirpath, dirnames, filenames in os.walk(chroma_dir):
                    for filename in filenames:
                        # Build the full filesystem path to the current file
                        abs_file = os.path.join(dirpath, filename)
                        # Compute the archive-internal path relative to the
                        # parent of chroma_db/, so the zip contains
                        # "chroma_db/subdir/file.ext" entries.
                        arc_name = os.path.relpath(abs_file, os.path.dirname(chroma_dir))
                        zf.write(abs_file, arc_name)

            InfoBar.success(
                self.tr("Export complete"),
                self.tr(f"Saved to {save_path}"),
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                self.tr("Export failed"),
                str(e),
                duration=5000,
                parent=self
            )

    def __onImportProject(self):
        """
        Import a previously exported .zip archive and restore chroma_db/.

        This is the counterpart to __onExportProject. The user selects a
        .zip file that was created by the export feature. The method then:

        1. Opens a native file picker filtered to .zip files.
        2. Validates that the archive actually contains a chroma_db/ root
           directory (basic sanity check to reject unrelated zip files).
        3. Removes the existing chroma_db/ directory to avoid mixing stale
           data with the imported dataset.
        4. Extracts the archive contents to the project root, recreating
           the chroma_db/ folder with its full internal structure.
        5. Shows a toast telling the user to restart the application so
           the engine manager picks up the newly imported index.
        """
        # Open a native file picker that only shows .zip files
        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Import Project Database"),
            QStandardPaths.writableLocation(QStandardPaths.DesktopLocation),
            self.tr("ZIP Archive (*.zip)")
        )

        # If the user cancelled the dialog, bail out silently
        if not zip_path:
            return

        try:
            # Verify the selected file is a valid zip archive before proceeding
            if not zipfile.is_zipfile(zip_path):
                InfoBar.error(
                    self.tr("Import failed"),
                    self.tr("Selected file is not a valid ZIP archive."),
                    duration=3000,
                    parent=self
                )
                return

            # Peek inside the archive to confirm it contains a chroma_db/
            # directory. This prevents the user from accidentally importing
            # an unrelated zip that would dump random files into the project.
            with zipfile.ZipFile(zip_path, 'r') as zf:
                archive_entries = zf.namelist()
                has_chroma_dir = any(
                    entry.startswith("chroma_db/") for entry in archive_entries
                )

                if not has_chroma_dir:
                    InfoBar.error(
                        self.tr("Import failed"),
                        self.tr("The archive does not contain a chroma_db/ directory."),
                        duration=3000,
                        parent=self
                    )
                    return

            # Determine the project root (where main.py and chroma_db/ live)
            project_root = os.path.abspath(".")
            chroma_dir = os.path.join(project_root, "chroma_db")

            # Remove the existing chroma_db/ so imported data fully replaces
            # it. This avoids stale vectors or documents from a previous
            # indexing run mixing with the newly imported dataset.
            if os.path.isdir(chroma_dir):
                shutil.rmtree(chroma_dir)

            # Extract the archive into the project root. Because every entry
            # in the zip is prefixed with "chroma_db/", this recreates the
            # chroma_db/ directory with all its subdirectories and files.
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(project_root)

            # Notify the user that the import succeeded and they need to
            # restart the application for the engine manager to pick up
            # the newly imported vector index and documents.
            InfoBar.success(
                self.tr("Import complete"),
                self.tr("Database restored. Please restart the application to load the imported data."),
                duration=5000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                self.tr("Import failed"),
                str(e),
                duration=5000,
                parent=self
            )
