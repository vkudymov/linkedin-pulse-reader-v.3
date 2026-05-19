from __future__ import annotations


class StorageError(RuntimeError):
    pass


class StorageConfigError(StorageError):
    pass


class StorageResponseError(StorageError):
    pass

