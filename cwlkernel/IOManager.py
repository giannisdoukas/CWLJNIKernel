from os import makedirs
import os
from os.path import exists
from typing import NoReturn

class IOFileManager:

    ROOT_DIRECTORY: str

    def __init__(self, root_directory: str):
        if not exists(root_directory):
            makedirs(root_directory)
        self.ROOT_DIRECTORY = root_directory

    def read(self, relative_path: str) -> bytes:
        full_path = os.path.join(self.ROOT_DIRECTORY, relative_path)

        with open(full_path, 'rb') as f:
            text = f.read()
        return text

    def write(self, relative_path: str, binary_data: bytes) -> NoReturn:
        full_path = os.path.join(self.ROOT_DIRECTORY, relative_path)
        with open(full_path, 'wb') as f:
            f.write(binary_data)
