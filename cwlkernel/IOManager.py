import os
from os import makedirs
from os.path import exists
from typing import List, NoReturn
from pathlib import Path
import shutil
from urllib.parse import urlparse

class IOFileManager:

    ROOT_DIRECTORY: str

    def __init__(self, root_directory: str):
        root_directory = os.path.realpath(root_directory)
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

    def append_files(self, files_to_copy: List[str], relative_path: str) -> List[str]:
        real_path = os.path.realpath(os.path.join(self.ROOT_DIRECTORY, relative_path))
        Path(real_path).mkdir(parents=True, exist_ok=True)
        new_files = []
        for p in files_to_copy:
            p = urlparse(p).path
            new_filename = os.sep.join([real_path, os.path.basename(p)])
            shutil.copyfile(p, new_filename)
            self._files_registry.add(new_filename)
            new_files.append(new_filename)
        return new_files