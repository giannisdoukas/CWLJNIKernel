import os
import sys
import traceback
from pathlib import Path
from subprocess import DEVNULL
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    NoReturn)
from uuid import uuid4, UUID

from cwltool.context import RuntimeContext
from cwltool.factory import Factory
from ruamel import yaml

from .IOManager import IOFileManager


class CoreExecutor:

    def __init__(self, file_manager: IOFileManager):
        self.file_manager = file_manager
        self._workflow_path = None
        self._data_paths = []

    def set_data(self, data: List[str]) -> List[str]:
        self._data_paths = [self.file_manager.write(f'{str(uuid4())}.yml', d.encode()) for d in data]
        return self._data_paths

    def set_workflow_path(self, workflow_str: str) -> str:
        """
        :param workflow_str: the cwl
        :return: the path where we executor stored the workflow
        """
        self._workflow_path = workflow_str
        return self._workflow_path

    def execute(self) -> Tuple[UUID, Dict, Optional[Exception]]:
        """
        :return: Run ID, dict with new files, exception if there is any
        """
        run_id = uuid4()

        runtime_context = RuntimeContext()
        runtime_context.outdir = self.file_manager.ROOT_DIRECTORY
        runtime_context.basedir = self.file_manager.ROOT_DIRECTORY
        runtime_context.default_stdin = DEVNULL
        runtime_context.default_stdout = DEVNULL
        runtime_context.default_stderr = DEVNULL
        os.chdir(self.file_manager.ROOT_DIRECTORY)
        factory = Factory(runtime_context=runtime_context)
        executable = factory.make(self._workflow_path)
        data = {}
        for data_file in self._data_paths:
            with open(data_file) as f:
                new_data = yaml.load(f, Loader=yaml.Loader)
                data = {**new_data, **data}
        try:
            result: Dict = executable(**data)
            return run_id, result, None
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return run_id, {}, e

    @classmethod
    def validate_input_files(cls, yaml_input: Dict, cwd: Path) -> NoReturn:
        for arg in yaml_input:
            if isinstance(yaml_input[arg], dict) and 'class' in yaml_input[arg] and yaml_input[arg]['class'] == 'File':
                # TODO: check about path vs location
                selector = 'location' if 'location' in yaml_input[arg] else 'path'
                file_path = Path(yaml_input[arg][selector])
                if not file_path.is_absolute():
                    file_path = cwd / file_path
                if not file_path.exists():
                    raise FileNotFoundError(file_path)
