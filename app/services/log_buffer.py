import logging
from collections import deque


_buffer: deque[str] = deque(maxlen=50)


class ErrorBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        msg = self.format(record)
        _buffer.append(msg)


def get_last_errors(limit: int = 10) -> list[str]:
    if limit <= 0:
        return []
    return list(_buffer)[-limit:]
