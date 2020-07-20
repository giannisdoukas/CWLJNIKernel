from collections import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from cwlkernel.IOManager import IOFileManager
from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent


class WorkflowRepository(Iterable):
    class __SingletonWorkflowRepository__:
        _registry: Dict[str, Tuple[WorkflowComponent, Path]]
        _file_repository: IOFileManager

        def __init__(self, directory: Path):
            self._registry = {}
            directory.mkdir(parents=True, exist_ok=True)
            self._file_repository = IOFileManager(str(directory.absolute()))

        def validate(self, tool: WorkflowComponent):
            """
            :raises TypeError if the tool is not type of dict
            :raises MissingIdError if there is not id in the tool/inputs/outputs
            :param tool:
            :return:
            """
            if not isinstance(tool, WorkflowComponent):
                raise TypeError(f'WorkflowComponent expected but type of {type(tool)} given')
            if not isinstance(tool.id, str):
                raise MissingIdError('Missing WorkflowComponent\'s id')
            for tool_input in tool.inputs:
                if 'id' not in tool_input:
                    raise MissingIdError(f'Missing id for input: {tool_input}')
            for output in tool.outputs:
                if 'id' not in output:
                    raise MissingIdError(f'Missing id for outputs: {output}')

        def register_tool(self, tool: WorkflowComponent, relative_directory: Optional[Path] = None) -> None:
            self.validate(tool)
            if tool.id in self._registry:
                raise KeyError(f'Dublicate key error: {tool.id}')
            relative_directory = relative_directory.as_posix() if relative_directory is not None else f'{tool.id}.cwl'
            path = Path(self._file_repository.write(relative_directory, tool.to_yaml().encode()))
            self._registry[tool.id] = (deepcopy(tool), path)

        def get_by_id(self, tool_id: str) -> Optional[WorkflowComponent]:
            comp = self._registry.get(tool_id, None)
            return comp[0] if comp is not None else None

        def get_entry_by_id(self, tool_id: str):
            return self._registry.get(tool_id, None)

        def __iter__(self) -> Iterator[WorkflowComponent]:
            for tool in self._registry.values():
                yield tool[0]

        def delete(self):
            self._registry = {}
            self._file_repository.clear()

        def get_tools_path_by_id(self, tool_id: str) -> Optional[Path]:
            comp = self._registry.get(tool_id, None)
            return comp[1] if comp is not None else None

        def delete_by_id(self, tool_id: str) -> Optional[WorkflowComponent]:
            path = self.get_tools_path_by_id(tool_id)
            if path is None:
                return None
            self._file_repository.remove(path.as_posix())
            self._registry.pop(tool_id)

    __repo__: __SingletonWorkflowRepository__ = None

    def __init__(self, directory: Path):
        """Initialize the singleton repository object if not exists."""
        if WorkflowRepository.__repo__ is None:
            WorkflowRepository.__repo__ = WorkflowRepository.__SingletonWorkflowRepository__(directory)

    def __getattr__(self, item):
        return getattr(WorkflowRepository.__repo__, item)

    def __iter__(self) -> Iterator[Dict]:
        for tool in WorkflowRepository.__repo__:
            yield tool

    @classmethod
    def get_instance(cls) -> '__SingletonWorkflowRepository__':
        if cls.__repo__ is None:
            raise RuntimeError('Repository has not been initialized')
        return cls.__repo__


class MissingIdError(Exception):
    pass
