from typing import NoReturn, Dict, List, Iterator
import json
from .CWLLogger import CWLLogger
from .IOManager import IOFileManager
import os


class CWLLoggerStorageManager:

    def __init__(self, root_directory):
        self._file_manager = IOFileManager(root_directory)

    def save(self) -> NoReturn:
        raise NotImplementedError()

    def load(self, limit=None) -> Iterator[Dict]:
        files = [(os.path.join(self._file_manager.ROOT_DIRECTORY, file),
                  os.path.getmtime(os.path.join(self._file_manager.ROOT_DIRECTORY, file)))
                 for file in
                 os.listdir(self._file_manager.ROOT_DIRECTORY) if
                 os.path.isfile(os.path.join(self._file_manager.ROOT_DIRECTORY, file)) and file.endswith('.json')]
        files.sort(key=lambda f: f[1], reverse=True)
        if limit is None:
            for file in files:
                with open(file[0]) as f:
                    yield json.load(f)
        else:
            for i, file in enumerate(files):
                if i<limit:
                    with open(file[0]) as f:
                        yield json.load(f)
                else:
                    break

    def collect(self):
        raise NotImplementedError()

    def get_storage_path(self) -> str:
        raise NotImplementedError()
