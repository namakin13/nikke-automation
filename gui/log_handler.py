"""
gui/log_handler.py
ログレコードをキューに積む Handler。

GUI スレッドは after() ポーリングでキューを drain して
CTkTextbox に追記する。Handler 側はスレッドセーフ。
"""
from __future__ import annotations

import logging
import queue


class QueueLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.queue: queue.Queue[str] = queue.Queue()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(self.format(record))
        except Exception:
            self.handleError(record)
