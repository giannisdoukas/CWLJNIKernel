from os import makedirs
import os
from os.path import exists
from typing import NoReturn, List


class IOFileManager:

    ROOT_DIRECTORY: str

    def __init__(self, root_directory: str):
        if not exists(root_directory):
            makedirs(root_directory)
        self.ROOT_DIRECTORY = root_directory
        self._files_registry = set()

    def read(self, relative_path: str) -> bytes:
        full_path = os.path.join(self.ROOT_DIRECTORY, relative_path)

        with open(full_path, 'rb') as f:
            text = f.read()
        return text

    def write(self, relative_path: str, binary_data: bytes) -> str:
        real_path = os.path.realpath(os.path.join(self.ROOT_DIRECTORY, relative_path))
        with open(real_path, 'wb') as f:
            self._files_registry.add(real_path)
            f.write(binary_data)
        return real_path

    def get_files(self) -> List[str]:
        return list(self._files_registry)