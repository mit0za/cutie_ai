import gc
import os
import shutil
from qfluentwidgets import InfoBar, InfoBarPosition
from PySide6.QtCore import Qt, QTimer
from backend.engine_manager import EngineManager
from ui.config import cfg
from ui.signal_bus import signalBus

class EngineController:
    """ This is where we move all engine related stuff here so it's more modular and clean in chat_interface.py"""
    def __init__(self, parent):
        self.parent = parent # So it will know where to attach toast to (in our case it's chat_interface)
        self.engine_thread = EngineManager()
        self.engine_info = None
        self.query_engine = None

        # Pure retrieval pipeline state: stores the raw vector index and
        # cross-encoder reranker so the Document Search feature can perform
        # semantic retrieval without invoking the LLM.
        self.index = None
        self.reranker = None

        # Connect to signals
        self._connect_engine_signals(self.engine_thread)
        signalBus.indexClearRequested.connect(self.on_clear_index_requested)
        signalBus.indexRebuildRequested.connect(self.on_rebuild_index_requested)

        cfg.dataFolders.valueChanged.connect(self.on_data_folder_changed)

    def _connect_engine_signals(self, engine: EngineManager):
        """
        Wire all EngineManager signals to local handlers and forward
        step-level progress to the global SignalBus so the Progress
        Notification Dialog can display pipeline status.
        """
        engine.progress.connect(self.on_progress)
        engine.engine_ready.connect(self.on_engine_ready)
        engine.index_ready.connect(self.on_index_ready)
        engine.index_stats.connect(signalBus.indexStatsUpdated)
        engine.error.connect(self.on_error)
        engine.llm_ready.connect(self.on_llm_ready)
        engine.db_ready.connect(self.on_db_ready)
        engine.need_data.connect(self.on_need_data)
        engine.critical_error.connect(self.on_critical_error)

        # Forward granular step signals to the global bus for the dialog
        engine.pipeline_started.connect(signalBus.progressStarted)
        engine.step_progress.connect(signalBus.progressUpdated)
        engine.pipeline_finished.connect(signalBus.progressFinished)
        engine.error.connect(signalBus.progressError)
        engine.critical_error.connect(signalBus.progressError)


    def start(self):
        self.engine_thread.start()

    def on_progress(self, msg):
        InfoBar.info(
            title="Initializing Engine",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3500,
            parent=self.parent
        )

    def on_engine_ready(self, engine):
        self.query_engine = engine
        self.parent.push_button.setEnabled(True)
        InfoBar.success(
            title="Engine Ready",
            content="LLM engine is fully operational",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self.parent
        )

    def on_index_ready(self, index, reranker):
        """
        Called when the vector index and reranker are initialized.
        Stores them locally for the pure retrieval pipeline used by
        Document Search, then broadcasts readiness via the global signal bus
        so other components (e.g. SearchController) can react.
        """
        self.index = index
        self.reranker = reranker
        signalBus.indexReady.emit()

    def on_error(self, error):
        InfoBar.error(
            title='Engine Error',
            content=str(error),
            orient=Qt.Horizontal,
            isClosable=True,
            duration=60000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent
        )

    def on_llm_ready(self):
        """ LLm initialization successful."""
        InfoBar.success(
            title="LLM Ready",
            content="Llama 3.1:8B and embedding model initialized successfully.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self.parent
        )

    def on_db_ready(self):
        """Database connection successful."""
        InfoBar.success(
            title="Database Ready",
            content="Chroma vector database connected.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self.parent
        )

    def on_need_data(self, msg: str):
        """Notify user to locate data directory."""
        InfoBar.warning(
            title="Data Folder Required",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=6000,
            parent=self.parent
        )

    def on_critical_error(self, msg: str):
        """Critical error: no data nor index found."""
        self.info_bar = InfoBar.error(
            title="Critical Setup Error",
            content=msg,
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            duration=-1,
            parent=self.parent
        )

    def on_data_folder_changed(self, new_paths):
        """Triggered when user updates data folder in settings."""
        InfoBar.info(
            title="Data Folder Updated",
            content="New data path selected. Rebuilding index...",
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self.parent
        )

        QTimer.singleShot(800, self.restarting_engine)

    def on_clear_index_requested(self):
        """Clear local index storage after stopping the engine thread."""
        try:
            self._stop_engine_for_maintenance()
            self._reset_engine_state()
            removed_paths = self._clear_index_storage()
            signalBus.indexStatsUpdated.emit({
                "ready": False,
                "doc_count": 0,
                "node_count": 0,
                "last_index_time": None,
                "source": "cleared",
            })
            InfoBar.success(
                title="Index Cleared",
                content=f"Removed {len(removed_paths)} local index item(s).",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=5000,
                parent=self.parent
            )
        except Exception as e:
            InfoBar.error(
                title="Clear Index Failed",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=8000,
                parent=self.parent
            )

    def on_rebuild_index_requested(self):
        """Clear local index storage and restart the engine to rebuild it."""
        data_paths = cfg.dataFolders.value or []
        if not data_paths:
            InfoBar.warning(
                title="Data Folder Required",
                content="Select at least one data folder before rebuilding the index.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=6000,
                parent=self.parent
            )
            return

        try:
            self._stop_engine_for_maintenance()
            self._reset_engine_state()
            self._clear_index_storage()
            signalBus.indexStatsUpdated.emit({
                "ready": False,
                "doc_count": 0,
                "node_count": 0,
                "last_index_time": None,
                "source": "rebuilding",
            })
            InfoBar.info(
                title="Rebuilding Index",
                content="Existing index removed. Rebuild is starting from configured data folders.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=6000,
                parent=self.parent
            )
            self.restarting_engine()
        except Exception as e:
            InfoBar.error(
                title="Rebuild Index Failed",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=8000,
                parent=self.parent
            )
    
    def restarting_engine(self):
        # Restart the engine thread safely
        if self.engine_thread.isRunning():
            self.engine_thread.quit()
            self.engine_thread.wait()

        # Reset retrieval pipeline state so stale references are not used
        # while the new engine thread is initializing.
        self.index = None
        self.reranker = None

        # Create a new thread and re-wire all signals (including progress forwarding)
        self.engine_thread = EngineManager()
        self._connect_engine_signals(self.engine_thread)

        self.engine_thread.start()

    def _stop_engine_for_maintenance(self):
        """
        Stop the current engine thread before deleting index files.

        Deleting ChromaDB files while the engine is still initializing can
        leave file handles open, so maintenance waits briefly for the thread
        to stop and asks the user to retry if it is still busy.
        """
        if self.engine_thread.isRunning():
            self.engine_thread.quit()
            if not self.engine_thread.wait(5000):
                raise RuntimeError(
                    "Engine is still initializing. Please wait for startup to finish and try again."
                )

    def _reset_engine_state(self):
        """Reset cached engine references so stale index objects are not reused."""
        self.engine_info = None
        self.query_engine = None
        self.index = None
        self.reranker = None
        self.parent.push_button.setEnabled(False)
        # Release ChromaDB and LlamaIndex handles before removing files on Windows.
        gc.collect()

    def _clear_index_storage(self):
        """Remove local index directories and status metadata safely."""
        project_root = os.path.abspath(os.getcwd())
        targets = [
            os.path.join(project_root, "chroma_db"),
            os.path.join(project_root, "storageContext"),
            os.path.join(project_root, "cache"),
            os.path.join(project_root, "app", "config", "index_status.json"),
        ]

        removed_paths = []
        for target in targets:
            if os.path.commonpath([project_root, target]) != project_root:
                raise RuntimeError(f"Refusing to remove path outside project root: {target}")

            if os.path.isdir(target):
                shutil.rmtree(target)
                removed_paths.append(target)
            elif os.path.isfile(target):
                os.remove(target)
                removed_paths.append(target)

        return removed_paths
