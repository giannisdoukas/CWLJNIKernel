import json
import os
from datetime import datetime
from typing import Dict, Iterator

from .CWLLogger import CWLLogger
from .IOManager import IOFileManager


class CWLLoggerStorageManager:

    def __init__(self, root_directory):
        self._file_manager = IOFileManager(root_directory)
        self._logger_collector = CWLLogger()
        self._logs = {}

    def save(self) -> str:
        filename = datetime.utcnow().strftime('%Y%b%d%H%M%f')
        filename += '.json'
        self._file_manager.write(filename, json.dumps(self._logs).encode())
        return os.path.join(self._file_manager.ROOT_DIRECTORY, filename)

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
        self._logs = self._logger_collector.to_dict()
        return self

    def get_storage_path(self) -> str:
        return self._file_manager.ROOT_DIRECTORY
