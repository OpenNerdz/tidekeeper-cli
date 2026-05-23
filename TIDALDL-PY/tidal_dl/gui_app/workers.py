from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()
    log = Signal(str)


class TaskWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.setAutoDelete(False)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class DownloadWorker(QRunnable):
    def __init__(self, backend, items):
        super().__init__()
        self.setAutoDelete(False)
        self.backend = backend
        self.items = items
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            for item in self.items:
                self.signals.log.emit(f"Starting {item.title}\n")
                self.backend.download(item, self.signals.log.emit)
                self.signals.log.emit(f"Finished {item.title}\n")
            self.signals.result.emit(self.items)
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()
