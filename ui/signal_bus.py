from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """ Signal bus """

    micaEnableChanged = Signal(bool)


signalBus = SignalBus()