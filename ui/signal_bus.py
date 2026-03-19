from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """ Signal bus """

    micaEnableChanged = Signal(bool)

    # Emitted when the vector index and reranker are fully initialized
    # and ready for pure semantic retrieval (no LLM required).
    # Listeners (e.g. SearchController) use this to enable search UI.
    indexReady = Signal()


signalBus = SignalBus()