from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType


class AlreadyRunningError(RuntimeError):
    pass


class SingleInstanceLock:
    def __init__(self, lock_path: str | Path) -> None:
        self.lock_path = Path(lock_path)
        self._file = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.lock_path.open("a+", encoding="utf-8")
        try:
            self._lock_file()
        except OSError as exc:
            self._file.close()
            self._file = None
            raise AlreadyRunningError(
                "Another CryptoBot instance is already running. "
                "Stop the existing process before starting a new polling bot."
            ) from exc

        self._file.seek(0)
        self._file.truncate()
        self._file.write(str(os.getpid()))
        self._file.flush()

    def release(self) -> None:
        if self._file is None:
            return

        try:
            self._unlock_file()
        finally:
            self._file.close()
            self._file = None

    def __enter__(self) -> SingleInstanceLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    if os.name == "nt":

        def _lock_file(self) -> None:
            import msvcrt

            assert self._file is not None
            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)

        def _unlock_file(self) -> None:
            import msvcrt

            assert self._file is not None
            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)

    else:

        def _lock_file(self) -> None:
            import fcntl

            assert self._file is not None
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        def _unlock_file(self) -> None:
            import fcntl

            assert self._file is not None
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
