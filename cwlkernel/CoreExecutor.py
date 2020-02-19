from io import StringIO
from typing import List, Tuple, Optional
from uuid import uuid4

from cwltool.main import main as cwltool_main

from .IOManager import IOFileManager


class CoreExecutor:

    def __init__(self, file_manager: IOFileManager):
        self.file_manager = file_manager
        self._workflow_path = None
        self._data_paths = []

    def set_data(self, data: List[str]) -> List[str]:
        self._data_paths = [self.file_manager.write(f'{str(uuid4())}.yml', d.encode()) for d in data]
        return self._data_paths

    def set_workflow(self, workflow_str: str) -> str:
        """
        :param workflow_str: the cwl
        :return: the path where we executor stored the workflow
        """
        self._workflow_path = self.file_manager.write(f'{str(uuid4())}.cwl', workflow_str.encode())
        return self._workflow_path

    def execute(self) -> Tuple[StringIO, StringIO, Optional[Exception]]:
        args = [self._workflow_path, *self._data_paths]
        stdout = StringIO()
        stderr = StringIO()

        if cwltool_main(argsl=args, stderr=stderr, stdout=stdout) != 0:
            return stdout, stderr, RuntimeError('On Kernel Exception: Error on executing workflow')
        return stdout, stderr, None
