from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """ Signal bus """

    micaEnableChanged = Signal(bool)

    # Emitted when the vector index and reranker are fully initialized
    # and ready for pure semantic retrieval (no LLM required).
    # Listeners (e.g. SearchController) use this to enable search UI.
    indexReady = Signal()

    # Global progress notification (engine init / indexing pipeline)
    progressStarted = Signal(int)
    progressUpdated = Signal(int, int, str)
    progressFinished = Signal()
    progressError = Signal(str)

    # Emits index status stats for UI display.
    # Payload: dict with keys like ready, doc_count, node_count, last_index_time.
    indexStatsUpdated = Signal(dict)


signalBus = SignalBus()
