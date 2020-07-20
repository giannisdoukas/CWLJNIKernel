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
        self._files_registry: Dict = {}

    @property
    def files_counter(self):
        return len(self._files_registry)

    def read(self, relative_path: str) -> bytes:
        full_path = os.path.join(self.ROOT_DIRECTORY, relative_path)

        with open(full_path, 'rb') as f:
            text = f.read()
        return text

    def write(self, relative_path: str, binary_data: bytes, metadata=None) -> str:
        real_path = os.path.realpath(os.path.join(self.ROOT_DIRECTORY, relative_path))
        Path(os.path.dirname(real_path)).mkdir(exist_ok=True, parents=True)
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

    def remove(self, path: str):
        os.remove(path)
        self._files_registry.pop(path)

    def clear(self):
        for f in os.listdir(self.ROOT_DIRECTORY):
            if os.path.isfile(f):
                os.remove(f)
                self._files_registry.pop(f)


class ResultsManager(IOFileManager):

    def get_last_result_by_id(self, result_id: str) -> Optional[str]:
        """
        The results manager may have multiple results with the same id, from multiple executions. That function will
        return the path of the last result
        @param result_id id to the Results manager. If the result_id has the format of path then the last goes to the
        id and the previous one to the produced by [_produced_by]/[result_id]
        @return: the path of last result with the requested id or None
        """

        produced_by, result_id = os.path.split(result_id)
        results_filter = filter(lambda item: item[1]['id'] == result_id, self.get_files_registry().items())
        produced_by = produced_by.strip()
        if len(produced_by) > 0:
            results_filter = filter(lambda item: item[1]['_produced_by'] == produced_by, results_filter)

        results = sorted(
            results_filter,
            key=lambda item: item[1]['result_counter']
        )
        if len(results) == 0:
            return None
        return results[-1][0]
