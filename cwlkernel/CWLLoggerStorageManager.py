import json
import os
from datetime import datetime
from typing import Dict, Iterator

from .IOManager import IOFileManager


class CWLLoggerStorageManager:
    __FORMAT__ = '%Y%b%d%H%M%f'

    def __init__(self, root_directory):
        self._file_manager = IOFileManager(root_directory)

    def save(self, logs) -> str:
        filename = datetime.utcnow().strftime(self.__FORMAT__)
        filename += '.json'
        self._file_manager.write(filename, json.dumps(logs).encode())
        return os.path.join(self._file_manager.ROOT_DIRECTORY, filename)

    def load(self, limit=None) -> Iterator[Dict]:
        files = []
        for file in os.listdir(self._file_manager.ROOT_DIRECTORY):
            if os.path.isfile(os.path.join(self._file_manager.ROOT_DIRECTORY, file)) and file.endswith('.json'):
                files.append(
                    (os.path.join(self._file_manager.ROOT_DIRECTORY, file),
                     datetime.strptime(os.path.basename(file)[:-5], self.__FORMAT__))
                )
        files.sort(key=lambda f: f[1], reverse=True)
        if limit is None:
            for file in files:
                with open(file[0]) as f:
                    yield json.load(f)
        else:
            for i, file in enumerate(files):
                if i < limit:
                    with open(file[0]) as f:
                        yield json.load(f)
                else:
                    break

    def get_storage_path(self) -> str:
        return self._file_manager.ROOT_DIRECTORY
