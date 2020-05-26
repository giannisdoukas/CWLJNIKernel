from collections import Iterable
from copy import deepcopy
from typing import Dict, Iterator, Optional

from cwlkernel.cwlrepository.CWLComponent import WorkflowComponent


class WorkflowRepository(Iterable):
    class __SingletonWorkflowRepository__:
        _registry: Dict[str, WorkflowComponent]

        def __init__(self):
            self._registry = {}

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
            for input in tool.inputs:
                if 'id' not in input:
                    raise MissingIdError(f'Missing id for input: {input}')
            for output in tool.outputs:
                if 'id' not in output:
                    raise MissingIdError(f'Missing id for outputs: {output}')

        def register_tool(self, tool: WorkflowComponent) -> None:
            self.validate(tool)
            if tool.id in self._registry:
                raise KeyError(f'Dublicate key error: {tool.id}')
            self._registry[tool.id] = deepcopy(tool)

        def register_tools(self, *args):
            for tool in args:
                self.register_tool(tool)

        def get_by_id(self, id: str) -> Optional[WorkflowComponent]:
            return self._registry.get(id, None)

        def __iter__(self) -> Iterator[WorkflowComponent]:
            for tool in self._registry.values():
                yield tool

        def delete(self):
            self._registry = {}

    __repo__: __SingletonWorkflowRepository__ = None

    def __init__(self):
        if WorkflowRepository.__repo__ is None:
            WorkflowRepository.__repo__ = WorkflowRepository.__SingletonWorkflowRepository__()

    def __getattr__(self, item):
        return getattr(WorkflowRepository.__repo__, item)

    def __iter__(self) -> Iterator[Dict]:
        for tool in WorkflowRepository.__repo__:
            yield tool

    @classmethod
    def get_instance(cls) -> Optional:
        return cls.__repo__


class MissingIdError(Exception):
    pass
