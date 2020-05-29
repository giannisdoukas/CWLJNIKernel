import os
import shutil
from copy import deepcopy
from os import makedirs

from os.path import exists
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, ParseResult


class IOFileManager:
    ROOT_DIRECTORY: str

    def __init__(self, root_directory: str):
        root_directory = os.path.realpath(root_directory)
        if not exists(root_directory):
            makedirs(root_directory)
        self.ROOT_DIRECTORY = root_directory
        self._files_registry = {}

    def read(self, relative_path: str) -> bytes:
        full_path = os.path.join(self.ROOT_DIRECTORY, relative_path)

        with open(full_path, 'rb') as f:
            text = f.read()
        return text

    def write(self, relative_path: str, binary_data: bytes, metadata=None) -> str:
        real_path = os.path.realpath(os.path.join(self.ROOT_DIRECTORY, relative_path))
        with open(real_path, 'wb') as f:
            self._files_registry[real_path] = metadata if metadata is not None else {}
            f.write(binary_data)
        return real_path

    def get_files(self) -> List[str]:
        return list(self._files_registry)

    def get_files_registry(self) -> Dict:
        return deepcopy(self._files_registry)

    def append_files(
            self,
            files_to_copy: List[str],
            relative_path: str = '.',
            metadata: Optional[Dict] = None
    ) -> List[str]:
        real_path = os.path.realpath(os.path.join(self.ROOT_DIRECTORY, relative_path))
        Path(real_path).mkdir(parents=True, exist_ok=True)
        new_files = []
        for p in files_to_copy:
            p = urlparse(p).path
            new_filename = os.sep.join([real_path, os.path.basename(p)])
            shutil.copyfile(p, new_filename)
            self._files_registry[new_filename] = metadata if metadata is not None else {}
            new_files.append(new_filename)
        return new_files

    def get_files_uri(self) -> ParseResult:
        return urlparse(self.ROOT_DIRECTORY, scheme='file')

    def clear(self):
        for f in os.listdir(self.ROOT_DIRECTORY):
            if os.path.isfile(f):
                os.remove(f)
